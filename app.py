import os
import random
import requests
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ----------------------------------------------------
# Настройки Hugging Face API
# ----------------------------------------------------
# Здесь мы задаем твой токен. На Render лучше прописать его в Environment Variables.
HF_TOKEN = os.environ.get("HF_TOKEN")
# Хорошая мультиязычная модель для косинусного сходства (поддерживает армянский)
HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# ----------------------------------------------------
# Загрузка текстового словаря для валидации слов
# ----------------------------------------------------
print("Loading valid words list...")
VALID_WORDS = set()
try:
    with open("valid_words.txt", "r", encoding="utf-8") as f:
        # Читаем все строчки, убираем пробелы и переводы строки
        for line in f:
            word = line.strip().lower()
            if word:
                VALID_WORDS.add(word)
    print(f"Loaded {len(VALID_WORDS)} valid words.")
except Exception as e:
    print(f"Error loading valid_words.txt: {e}")
    # Будет пустым, если файла нет, но мы добавим дефолтное слово
    VALID_WORDS.add("համակարգիչ")

# ----------------------------------------------------
# Логика работы с векторами через Hugging Face
# ----------------------------------------------------
def get_vector_from_hf(word):
    """Отправляет слово в Hugging Face и получает вектор"""
    try:
        response = requests.post(HF_API_URL, headers=headers, json={"inputs": [word]})
        # Если API устало (rate limit) или модель загружается (est. time)
        if response.status_code != 200:
            print(f"HF Error {response.status_code}: {response.text}")
            return None
        
        # Hugging Face Feature Extraction API возвращает массив векторов.
        # Берем первый элемент [0].
        vectors = response.json()
        if isinstance(vectors, list) and len(vectors) > 0:
            return np.array(vectors[0])
        return None
    except Exception as e:
        print(f"Request error: {e}")
        return None

def cosine_similarity(v1, v2):
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0
    return np.dot(v1, v2) / (norm1 * norm2)

# ----------------------------------------------------
# Инициализация игры
# ----------------------------------------------------
def select_random_secret_word():
    if VALID_WORDS:
        return random.choice(list(VALID_WORDS))
    return "համակարգիչ"

secret_word = select_random_secret_word()
# Кэшируем секретный вектор, чтобы не отправлять запрос в HF на каждое слово юзера
secret_vector = get_vector_from_hf(secret_word)
if secret_vector is None:
    print(f"WARNING: Не удалось получить вектор для '{secret_word}'. Проверьте HF_TOKEN!")

print(f"--- ACTIVE SECRET WORD: {secret_word} ---")

# ----------------------------------------------------
# Маршруты (API)
# ----------------------------------------------------
@app.route('/')
def home():
    return "Jermabar API (Hugging Face Edition) is running!"

@app.route('/get_initial_word', methods=['GET'])
def get_initial_word():
    return jsonify({"word": secret_word})

@app.route('/guess', methods=['POST'])
def guess():
    global secret_vector, secret_word

    data_json = request.get_json(silent=True)
    if not data_json or 'word' not in data_json:
        return jsonify({"error": "Բառը բացակայում է"}), 400
        
    user_word = data_json.get('word', '').lower().strip()
    
    # 1. Запрещаем несуществующие слова (или "абырвалг")
    if user_word not in VALID_WORDS:
        return jsonify({"error": "Բառը չգտնվեց բազայում"}), 404

    # Пытаемся получить вектор секретного слова (если он не закэшировался при старте)
    if secret_vector is None:
        secret_vector = get_vector_from_hf(secret_word)
        if secret_vector is None:
            return jsonify({"error": "Сбой сервера Hugging Face"}), 500

    # 2. Получаем вектор слова пользователя
    user_vector = get_vector_from_hf(user_word)
    
    if user_vector is None:
        return jsonify({"error": "Не удалось сгенерировать вектор (HF AI недоступен)"}), 500
        
    # 3. Считаем процент
    score = cosine_similarity(user_vector, secret_vector)
    
    # HF Sentence Transformers обычно выдают значения схожести [0, 1] 
    # (или иногда [-1, 1], но чаще положительные).
    final_score = round(float(score) * 100, 2)
    
    if final_score < 0:
        final_score = 0.0
    if final_score > 100:
        final_score = 100.0
    
    return jsonify({
        "word": user_word,
        "score": final_score,
        "is_correct": user_word == secret_word
    })

@app.route('/reset_word', methods=['GET'])
def reset_manual():
    global secret_word, secret_vector
    secret_word = select_random_secret_word()
    secret_vector = get_vector_from_hf(secret_word)
    return jsonify({
        "status": "success",
        "message": "Բառը փոխված է",
        "new_word_debug": secret_word
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
