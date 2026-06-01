import os
import re
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 1. Настройка ключа Gemini (берется из переменных окружения)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_llm_score(target, guess):
    # Промпт, который Gemini выполняет идеально благодаря своим размерам
    system_instruction = (
        "You are the core engine of 'Baratsi', an Armenian word association game. "
        "Analyze how naturally a human mind connects the 'Guess word' to the 'Secret word' based on everyday life and Armenian culture.\n"
        "You MUST think step-by-step using this EXACT format:\n"
        "Reasoning: <one short sentence in English explaining the association>\n"
        "Score: <a precise, non-rounded integer from 0 to 100>\n\n"
        "Scoring Philosophy:\n"
        "- 90-100: Absolute synonyms or direct cultural matches.\n"
        "- 70-89: Strong everyday pairing (e.g., 'անձրև' and 'անձրևանոց').\n"
        "- 40-69: Broad thematic link.\n"
        "- 0-9: Absolutely no semantic connection (e.g., 'հիվանդ' and 'կիթառ' MUST get between 0 and 4).\n\n"
        "CRITICAL: Be extremely organic. Do not round scores to multiples of 5 or 10. Use unique numbers like 43, 67, 81."
    )
    
    prompt = f"{system_instruction}\n\nSecret word: {target}\nGuess word: {guess}"
    
    try:
        # Вызываем сверхбыструю модель Flash
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        content = response.text.strip()
        print(f"DEBUG: Gemini Output:\n{content}")
        
        # Жесткий и надежный парсинг числа
        match = re.search(r'Score:\s*(\d+)', content)
        if match:
            return max(0, min(100, int(match.group(1))))
            
        # Запасной паттерн на случай форс-мажора
        matches = re.findall(r'\d+', content)
        if matches:
            return max(0, min(100, int(matches[-1])))
            
    except Exception as e:
        print(f"!!! GEMINI API ERROR !!!: {e}")
        
    return 15 # Наш стандартный безопасный фолбэк


@app.route('/get_initial_word', methods=['GET'])
def get_initial_word():
    # Список слов для начала игры (можно расширить)
    words = ["սուրճ", "համակարգիչ", "գիրք", "արև", "լեռ", "ծով"]
    import random
    return jsonify({"word": random.choice(words)})

@app.route('/guess', methods=['POST'])
@app.route('/guess', methods=['POST'])
@app.route('/guess', methods=['POST'])
def guess_word():
    data = request.get_json(force=True, silent=True)
    
    if data is None:
        return jsonify({"error": "No JSON payload"}), 400
        
    # Теперь ищем ключи, которые реально прилетают из JS
    target = data.get('secret_word') 
    guess = data.get('word')
    
    if not target or not guess:
        return jsonify({"error": f"Missing keys. Received: {data}"}), 400
    
    # Вызываем оценку
    score = get_llm_score(target, guess)
    return jsonify({"score": score})

if __name__ == '__main__':
    app.run(debug=True)
