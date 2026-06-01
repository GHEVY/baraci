import os
import random
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient

app = Flask(__name__)
CORS(app)

# 1. Исправленная инициализация клиента (api_key вместо token)
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"
client = InferenceClient(api_key=HF_TOKEN)

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
def get_llm_score(target, guess):
    system_instruction = (
        "You are an expert linguistic judge for the Armenian word game 'Baratsi'. "
        "Evaluate the semantic similarity between 'Secret word' and 'Guess word' in Armenian on a scale from 0 to 100.\n"
        "Rules:\n"
        "1. Output EXACTLY one integer from 0 to 100. No text, no markdown, no punctuation.\n"
        "2. Use the entire scale naturally and dynamically. Do not automatically round your scores to the nearest 5 or 10. "
        "Be precise and granular (e.g., feel free to return 14, 23, 47, 61, 82 if that accurately reflects the semantic distance)."
    )
    
    user_content = f"Secret word: {target}\nGuess word: {guess}"
    
    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            max_tokens=4,
            # ПОВЫШАЕМ ТЕМПЕРАТУРУ: дает естественный разброс чисел,
            # убирает зацикливание на круглых цифрах, но держит логику.
            temperature=0.3 
        )
        
        content = response.choices[0].message.content.strip()
        print(f"DEBUG: LLM raw response -> '{content}'")
        
        matches = re.findall(r'\d+', content)
        if matches:
            score = int(matches[0])
            return max(0, min(100, score))
            
    except Exception as e:
        print(f"WARNING: HF API Error ({e}). Using fallback score.")
        
    return 15 # Дефолтный фолбэк на случай падения сети

@app.route('/get_initial_word', methods=['GET'])
def get_initial_word():
    if not VALID_WORDS_LIST:
        return jsonify({"error": "Dictionary is empty"}), 500
    word = random.choice(VALID_WORDS_LIST)
    return jsonify({"word": word})

@app.route('/guess', methods=['POST'])
def guess():
    data = request.get_json() or {}
    user_word = data.get('word', '').lower().strip()
    secret_word = data.get('secret_word', '').lower().strip()
    
    if user_word not in VALID_WORDS: 
        return jsonify({"error": "Բառը բառարանում չկա"}), 404
    
    if not secret_word:
        return jsonify({"error": "Secret word missing"}), 400
    
    # Если пользователь сразу угадал слово — не тратим токены API, возвращаем 100
    if user_word == secret_word:
        return jsonify({"score": 100})
        
    score = get_llm_score(secret_word, user_word)
    
    return jsonify({"score": score})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
