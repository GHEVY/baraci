import os
import time
import random
import requests
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
HF_API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(BASE_DIR, "valid_words.txt")

VALID_WORDS = set()
VALID_WORDS_LIST = []
try:
    with open(DICT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip().lower()
            if word: VALID_WORDS.add(word)
    VALID_WORDS_LIST = list(VALID_WORDS)
    print(f"Loaded {len(VALID_WORDS)} words.")
except Exception as e:
    print(f"Error loading dictionary: {e}")


def get_vector(word):
    try:
        response = requests.post(HF_API_URL, headers=headers, json={"inputs": word}, timeout=30)

        if response.status_code != 200:
            return None, f"Error {response.status_code}"

        data = response.json()

        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], list):
                return data[0], None
            return data, None

        return None, "Invalid data format"

    except Exception as e:
        print(f"Error: {e}")
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
        return jsonify({"error": "Dictionary is empty"}), 500

    random_word = random.choice(VALID_WORDS_LIST)
    vector, err_msg = get_vector(random_word)

    if vector is None:
        return jsonify({"error": f"AI unavailable: {err_msg}"}), 500

    return jsonify({"word": random_word, "vector": vector})


@app.route('/guess', methods=['POST'])
def guess():
    data = request.get_json(silent=True)
    if not data: return jsonify({"error": "No data"}), 400

    user_word = data.get('word', '').lower().strip()
    secret_vector_list = data.get('secret_vector')

    if not user_word or secret_vector_list is None:
        return jsonify({"error": "Incomplete data"}), 400

    if user_word not in VALID_WORDS:
        return jsonify({"error": "Word not found"}), 404

    v_user_list, err_msg = get_vector(user_word)
    if v_user_list is None:
        return jsonify({"error": f"AI unavailable: {err_msg}"}), 500

    v_user = np.array(v_user_list)
    v_secret = np.array(secret_vector_list)

    score = cosine_similarity(v_user, v_secret)

    threshold = 0.25
    final_score = max(0, min(100, round((max(0, score) - threshold) / (1 - threshold) * 100, 1))) if score > threshold else 0

    return jsonify({"word": user_word, "score": final_score})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
