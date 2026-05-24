import os
import random
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient

app = Flask(__name__)
CORS(app)

HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
client = InferenceClient(model=MODEL_ID, token=HF_TOKEN)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.path.join(BASE_DIR, "valid_words.txt")
VALID_WORDS = set()
VALID_WORDS_LIST = []

try:
    with open(DICT_PATH, "r", encoding="utf-8") as f:
        VALID_WORDS = {line.strip().lower() for line in f if line.strip()}
    VALID_WORDS_LIST = list(VALID_WORDS)
    print(f"Loaded {len(VALID_WORDS)} words.")
except Exception as e:
    print(f"Error loading dictionary: {e}")

def get_vector(word):
    try:

        result = client.feature_extraction(word)
        

        if hasattr(result, 'tolist'):
            vec = result.tolist()
        else:
            vec = result
            

        if isinstance(vec, list) and len(vec) > 0 and isinstance(vec[0], list):
            vec = vec[0]
            

        if not isinstance(vec, list) or len(vec) < 50:
            print(f"DEBUG: Bad vector received for '{word}': {vec}")
            return None, "Model returned invalid vector size"
            
        return vec, None
    except Exception as e:
        print(f"DEBUG: Exception in get_vector: {e}")
        return None, str(e)
def cosine_similarity(v1, v2):
    arr1, arr2 = np.array(v1).flatten(), np.array(v2).flatten()
    norm1, norm2 = np.linalg.norm(arr1), np.linalg.norm(arr2)
    if norm1 == 0 or norm2 == 0: return 0.0
    return float(np.dot(arr1, arr2) / (norm1 * norm2))

@app.route('/get_initial_word', methods=['GET'])
def get_initial_word():
    if not VALID_WORDS_LIST: return jsonify({"error": "Dict empty"}), 500
    word = random.choice(VALID_WORDS_LIST)
    vec, err = get_vector(word)
    if vec is None: return jsonify({"error": f"AI error: {err}"}), 500
    return jsonify({"word": word, "vector": vec})

@app.route('/guess', methods=['POST'])
def guess():
    data = request.get_json()
    user_word = data.get('word', '').lower().strip()
    secret_vec = data.get('secret_vector')
    
    if user_word not in VALID_WORDS: return jsonify({"error": "Not in dict"}), 404
    
    user_vec, err = get_vector(user_word)
    if user_vec is None: return jsonify({"error": f"AI error: {err}"}), 500
    
    score = cosine_similarity(user_vec, secret_vec)
    threshold = 0.25
    final = max(0, min(100, round((max(0, score) - threshold) / (1 - threshold) * 100, 1))) if score > threshold else 0
    return jsonify({"score": final})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
