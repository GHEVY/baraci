import os
import random
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient

app = Flask(__name__)
CORS(app)

# Используем модель-инструктор для оценки близости слов
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"
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
def get_llm_score(target, guess):
    prompt = (
        f"Compare the Armenian words '{target}' and '{guess}'. "
        "Return a number from 0 to 100 representing their semantic similarity. "
        "Return ONLY the number, without any extra text."
    )
    
    try:
        # Используем .conversational вместо .text_generation
        # Передаем промпт внутри списка сообщений
        response = client.conversational(
            messages=[{"role": "user", "content": prompt}]
        )
        
        # У объекта response есть поле generated_text
        content = response.generated_text if hasattr(response, 'generated_text') else str(response)
        
        print(f"DEBUG: LLM raw response -> '{content}'")
        
        matches = re.findall(r'\d+', content)
        if matches:
            score = int(matches[0])
            return max(0, min(100, score))
        else:
            print("DEBUG: No number found in response!")
            return 0 # Или -1, если хочешь отлавливать ошибки
            
    except Exception as e:
        print(f"DEBUG: CRITICAL ERROR -> {e}")
        return 0

@app.route('/get_initial_word', methods=['GET'])
def get_initial_word():
    # Теперь нам не нужен вектор, просто отдаем слово
    word = random.choice(VALID_WORDS_LIST)
    return jsonify({"word": word})

@app.route('/guess', methods=['POST'])
def guess():
    data = request.get_json()
    user_word = data.get('word', '').lower().strip()
    secret_word = data.get('secret_word') # Ожидаем строку, а не вектор!
    
    if user_word not in VALID_WORDS: 
        return jsonify({"error": "Բառը բառարանում չկա"}), 404
    
    if not secret_word:
        return jsonify({"error": "Secret word missing"}), 400
    
    # Получаем оценку напрямую от LLM
    score = get_llm_score(secret_word, user_word)
    
    return jsonify({"score": score})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
