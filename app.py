from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import numpy as np
import os

app = Flask(__name__)
CORS(app)


HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

# 2. Բեռնում ենք բառարանը (valid_words.txt)
def load_dictionary():
    try:
        with open('valid_words.txt', 'r', encoding='utf-8') as f:
            # Վերցնում ենք միայն բառերը
            return set(line.split()[0].lower() for line in f)
    except FileNotFoundError:
        print("Սխալ: valid_words.txt ֆայլը չի գտնվել!")
        return set()

allowed_words = load_dictionary()

# 3. Ֆունկցիա AI-ից վեկտոր ստանալու համար
def get_embedding(text):
    try:
        response = requests.post(API_URL, headers=HEADERS, json={"inputs": text}, timeout=10)
        
        # Եթե Hugging Face-ը սխալ է տալիս
        if response.status_code != 200:
            print(f"HF Error: {response.status_code} - {response.text}")
            return "loading"

        result = response.json()
        
        # Metric-AI-ն սովորաբար տալիս է [[0.1, 0.2, ...]]
        if isinstance(result, list):
            # Եթե լիստի մեջ լիստ է, վերցնում ենք առաջինը
            data = np.array(result)
            return data[0] if data.ndim > 1 else data
            
        return "loading"
    except Exception as e:
        print(f"Local error: {e}")
        return "loading"

# 4. Հիմնական Route-ը խաղի համար
@app.route('/guess', methods=['POST'])
def guess():
    data = request.json
    user_word = data.get('word', '').lower().strip()
    secret_word = "խնձոր"  # Առայժմ ստատիկ, հետո կարող ես փոխել

    # Ստուգում 1: Արդյո՞ք բառը կա բառարանում
    if user_word not in allowed_words:
        return jsonify({"error": "Այսպիսի բառ չկա բառարանում"}), 400

    # Ստուգում 2: Ստանում ենք վեկտորները AI-ից
    v_user = get_embedding(user_word)
    v_secret = get_embedding(secret_word)

    if v_user == "loading" or v_secret == "loading":
        return jsonify({"error": "AI-ն դեռ պատրաստվում է, փորձեք 10 վայրկյանից"}), 503

    # Հաշվում ենք նմանությունը (Cosine Similarity)
    similarity = np.dot(v_user, v_secret) / (np.linalg.norm(v_user) * np.linalg.norm(v_secret))
    percentage = round(float(similarity) * 100, 2)

    return jsonify({
        "word": user_word,
        "percentage": percentage
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
