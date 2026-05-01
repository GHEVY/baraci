import os
import time
import random
import requests
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import lru_cache

app = Flask(__name__)
CORS(app)

# Կարգավորումներ
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_API_URL = "https://router.huggingface.co/hf-inference/models/intfloat/multilingual-e5-base/pipeline/feature-extraction"

headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# Բառարանի բեռնում
VALID_WORDS = set()
VALID_WORDS_LIST = []
try:
    with open("valid_words.txt", "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip().lower()
            if word: VALID_WORDS.add(word)
    VALID_WORDS_LIST = list(VALID_WORDS)
    print(f"Loaded {len(VALID_WORDS)} words.")
except Exception as e:
    print(f"Error loading dictionary: {e}")

# AI Վեկտորի տրամաբանություն
@lru_cache(maxsize=1000)
def get_vector(word):
    max_retries = 3
    last_error = "Unknown"
    for attempt in range(max_retries):
        try:
            if not HF_TOKEN or HF_TOKEN == "None":
                return None, "HF_TOKEN-ը բացակայում է: Ավելացրեք այն Render-ի Environment փոփոխականներում:"

            response = requests.post(HF_API_URL, headers=headers, json={"inputs": [word]})
            if response.status_code == 200:
                vectors = response.json()
                return np.array(vectors[0]), None
            
            # Եթե մոդելը քնած է (503 Service Unavailable), սպասում ենք և նորից փորձում
            if response.status_code == 503:
                error_data = response.json()
                wait_time = error_data.get("estimated_time", 20.0)
                print(f"Model is loading. Waiting {wait_time}s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(min(wait_time, 25))
                last_error = "503 Model Loading"
                continue
                
            try:
                err_json = response.json()
                err_text = err_json.get("error", response.text)
            except:
                err_text = response.text
                
            print(f"HF Error: {response.status_code} - {err_text}")
            last_error = f"HF Error {response.status_code}: {err_text}"
            return None, last_error
        except Exception as e:
            print(f"Request error: {e}")
            last_error = f"Exception: {str(e)}"
            return None, last_error
    return None, last_error

def cosine_similarity(v1, v2):
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 == 0 or n2 == 0: return 0
    return np.dot(v1, v2) / (n1 * n2)

# Երթուղիներ (Routes)
@app.route('/get_initial_word', methods=['GET'])
def get_initial_word():
    if not VALID_WORDS_LIST:
        return jsonify({"error": "Բառարանը դատարկ է"}), 500
    
    random_word = random.choice(VALID_WORDS_LIST)
    vector, err_msg = get_vector(random_word)
    
    if vector is None:
        return jsonify({"error": f"AI-ն անհասանելի է: {err_msg}"}), 500

    return jsonify({
        "word": random_word,
        "vector": vector.tolist()  # Վեկտորը ուղարկում ենք բրաուզերին
    })

@app.route('/guess', methods=['POST'])
def guess():
    data = request.get_json(silent=True)
    if not data: return jsonify({"error": "No data"}), 400

    user_word = data.get('word', '').lower().strip()
    secret_vector_list = data.get('secret_vector')

    if not user_word or secret_vector_list is None:
        return jsonify({"error": "Տվյալները թերի են"}), 400
    
    if user_word not in VALID_WORDS:
        return jsonify({"error": "Բառը չկա բազայում"}), 404

    v_user, err_msg = get_vector(user_word)
    if v_user is None:
        return jsonify({"error": f"AI-ն անհասանելի է: {err_msg}"}), 500

    v_secret = np.array(secret_vector_list)
    score = cosine_similarity(v_user, v_secret)
    
    # Փոխակերպում ենք 0-100 միջակայքի
    final_score = max(0, min(100, round(float(score) * 100, 2)))

    return jsonify({
        "word": user_word,
        "score": final_score
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
