import numpy as np
import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 1. Բեռնում ենք բազան
print("Loading vector database...")
try:
    # allow_pickle=True-ն անհրաժեշտ է, եթե numpy-ն պահել է օբյեկտներ (ինչպես words list-ը)
    data = np.load("jermabar_final.npz", allow_pickle=True)
    words_list = data['words'].tolist()
    vectors_array = data['vectors']
    word_to_index = {word: i for i, word in enumerate(words_list)}
    print(f"Database loaded. Total words: {len(words_list)}")
except Exception as e:
    print(f"Error loading database: {e}")
    words_list = []
    vectors_array = []

def select_random_secret_word():
    # Վերցնում ենք միայն հայերեն տառեր պարունակող բառերը
    armenian_words = [w for w in words_list if any('\u0531' <= c <= '\u058F' for c in w)]
    if armenian_words:
        return random.choice(armenian_words)
    return "համակարգիչ"

# Սահմանում ենք թիրախային բառը սերվերը միանալիս
secret_word = select_random_secret_word()
print(f"--- ACTIVE SECRET WORD: {secret_word} ---")

def get_vector(word):
    if not words_list: return None
    idx = word_to_index.get(word.lower().strip())
    if idx is not None:
        return vectors_array[idx]
    return None

def cosine_similarity(v1, v2):
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0
    # Կիրառվում է վեկտորների սկալյար արտադրյալի բանաձևը
    return np.dot(v1, v2) / (norm1 * norm2)

@app.route('/')
def home():
    return "Jermabar API is running!"

@app.route('/get_initial_word', methods=['GET'])
def get_initial_word():
    return jsonify({"word": secret_word})

@app.route('/guess', methods=['POST'])
def guess():
    data_json = request.get_json()
    if not data_json or 'word' not in data_json:
        return jsonify({"error": "Բառը բացակայում է"}), 400
        
    user_word = data_json.get('word', '').lower().strip()
    
    v_user = get_vector(user_word)
    v_target = get_vector(secret_word)
    
    if v_user is None:
        return jsonify({"error": "Բառը չգտնվեց բազայում"}), 404
        
    score = cosine_similarity(v_user, v_target)
    # Վերածում ենք տոկոսի (0-100)
    final_score = round(float(score) * 100, 2)
    
    if final_score < 0:
        final_score = 0.0
    
    return jsonify({
        "word": user_word,
        "score": final_score,
        "is_correct": user_word == secret_word
    })

@app.route('/reset_word', methods=['GET'])
def reset_manual():
    global secret_word
    secret_word = select_random_secret_word()
    return jsonify({
        "status": "success",
        "message": "Բառը փոխված է",
        "new_word_debug": secret_word
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
