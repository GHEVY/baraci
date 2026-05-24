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


HF_TOKEN = os.environ.get("HF_TOKEN")
HF_API_URL = "https://router.huggingface.co/hf-inference/models/intfloat/multilingual-e5-small"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}


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


@lru_cache(maxsize=1000)
def get_vector(word):
    try:
        # Убираем все лишнее, просто делаем запрос
        response = requests.post(HF_API_URL, headers=headers, json={"inputs": word})
        
        if response.status_code == 200:
            result = response.json()
            # Пытаемся достать вектор из разных вариантов структуры API
            if isinstance(result, list):
                if len(result) > 0:
                    # Если вернулся список списков, берем первый, иначе сам список
                    vector = result[0] if isinstance(result[0], list) else result
                    return vector, None
        
        # Если API ответило не 200 или пришел пустой список
        print(f"DEBUG: API returned {response.status_code}: {response.text}")
        return None, "Error"
        
    except Exception as e:
        print(f"DEBUG: Exception: {e}")
        return None, "Exception"
    
def cosine_similarity(v1, v2):
    if v1 is None or v2 is None or len(v1) == 0 or len(v2) == 0:
        return 0.0

    arr1 = np.array(v1).flatten()
    arr2 = np.array(v2).flatten()
    
    n1 = np.linalg.norm(arr1)
    n2 = np.linalg.norm(arr2)

    if n1 == 0 or n2 == 0:
        return 0.0

    return float(np.dot(arr1, arr2) / (n1 * n2))


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
        "vector": vector
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

    # 1. Получаем вектор как список
    v_user_list, err_msg = get_vector(user_word)
    if v_user_list is None:
        return jsonify({"error": f"AI-ն անհասանելի է: {err_msg}"}), 500

    # 2. Превращаем в numpy-массивы только здесь
    v_user = np.array(v_user_list)
    v_secret = np.array(secret_vector_list)
    
    # 3. Считаем
    score = cosine_similarity(v_user, v_secret)
    
    # ... дальше твоя логика расчета final_score ...
    threshold = 0.25
    final_score = max(0, min(100, round((max(0, score) - threshold) / (1 - threshold) * 100, 1))) if score > threshold else 0

    return jsonify({"word": user_word, "score": final_score})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
