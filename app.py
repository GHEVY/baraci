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
        "You are the core engine of 'Baratsi', an Armenian word association game. "
        "Analyze how naturally a human mind connects the 'Guess word' to the 'Secret word' based on everyday life, Armenian culture, and typical context.\n"
        "To provide a human-like score, you MUST think step-by-step using this EXACT format:\n"
        "Reasoning: <one short sentence in English explaining the human or cultural connection between the two Armenian words>\n"
        "Score: <a highly precise, non-rounded integer from 0 to 100>\n\n"
        "Scoring Philosophy:\n"
        "- 90-100: Absolute synonyms or direct grammatical forms.\n"
        "- 70-89: Powerful everyday or cultural pairing (e.g., 'խորոված' /barbecue/ and 'մանղալ' /manghal/ should be ~87).\n"
        "- 40-69: Broad thematic link or shared context (e.g., 'գիրք' /book/ and 'սուրճ' /coffee/ should be ~54).\n"
        "- 10-39: Weak, highly abstract, or accidental connection.\n"
        "- 0-9: Absolutely no semantic connection in real life (e.g., 'հիվանդ' and 'կիթառ' MUST get between 0 and 4).\n\n"
        "CRITICAL: Be extremely organic. Do not round scores to multiples of 5 or 10. Use unique numbers like 13, 37, 46, 62, 79, 81."
    )
    
    user_content = f"Secret word: {target}\nGuess word: {guess}"
    
    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            max_tokens=45,    
            temperature=0.4   
        )
        
        content = response.choices[0].message.content.strip()
        print(f"DEBUG: LLM Thought & Output:\n{content}")
        
        match = re.search(r'Score:\s*(\d+)', content)
        if match:
            score = int(match.group(1))
            return max(0, min(100, score))
            
        matches = re.findall(r'\d+', content)
        if matches:
            return max(0, min(100, int(matches[-1]))) # Берем последнее число из текста
            
    except Exception as e:
        print(f"WARNING: API Error ({e}). Fallback applied.")
        
    return 15

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
