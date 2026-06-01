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
MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"
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
    # Жесткий системный промпт для ИИ-судьи
    system_instruction = (
        "You are a strict linguistic referee for the Armenian word game 'Baratsi'. "
        "Compare the secret word and the guess word based ONLY on their semantic closeness in Armenian culture and language. "
        "Output EXACTLY one integer from 0 to 100, where 100 means they are exact synonyms, and 0 means completely unrelated. "
        "Do not write any explanations, introduction, markdown, or extra text. Just output the digits."
    )
    
    user_content = f"Secret word: {target}\nGuess word: {guess}"
    
    try:
        # 2. Исправленный метод: используем chat.completions.create вместо conversational
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            max_tokens=5,      # Защита от лишнего текста + высокая скорость
            temperature=0.01   # Минимальная температура для максимальной стабильности
        )
        
        # Получаем чистый текст ответа
        content = response.choices[0].message.content.strip()
        print(f"DEBUG: LLM raw response -> '{content}'")
        
        # Наш парсер регуляркой
        matches = re.findall(r'\d+', content)
        if matches:
            score = int(matches[0])
            return max(0, min(100, score))
        else:
            print("DEBUG: No number found in response!")
            return 0
            
    except Exception as e:
        print(f"DEBUG: CRITICAL ERROR IN LLM CALL -> {e}")
        return 0

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
