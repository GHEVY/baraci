let bestPct = -1;
let history = [];
let hintCooldown = false;

// 1. Սահմանում ենք Render-ի հասցեն
const API_URL = 'https://jermabar.onrender.com/guess';

// 2. Էլեմենտների հղումները
const wordInput   = document.getElementById('word-input');
const curInd      = document.getElementById('cur-indicator');
const bestInd     = document.getElementById('best-indicator');
const curVal      = document.getElementById('cur-val');
const bestVal     = document.getElementById('best-val');
const resultCard  = document.getElementById('result-card');
const resultWord  = document.getElementById('result-word');
const resultScore = document.getElementById('result-score');
const historyList = document.getElementById('history-list');
const emptyState  = document.getElementById('empty-state');
const clearBtn    = document.getElementById('clear-btn');
const hintBtn     = document.getElementById('hint-btn');
const hintPopup   = document.getElementById('hint-popup');
const hintText    = document.getElementById('hint-text');
const hintClose   = document.getElementById('hint-close');
const errorNotif  = document.getElementById('error-notification');

// --- Էֆեկտներ և Գույներ ---

function lerpColor(a, b, t) {
  return `rgb(${Math.round(a[0]+(b[0]-a[0])*t)},${Math.round(a[1]+(b[1]-a[1])*t)},${Math.round(a[2]+(b[2]-a[2])*t)})`;
}

function getColor(pct) {
  if (pct <= 50) return lerpColor([0,229,255], [123,97,255], pct / 50);
  return lerpColor([123,97,255], [255,61,0], (pct - 50) / 50);
}

function isArmenianWord(word) {
  const armenianRegex = /^[\u0531-\u058F\s]+$/u;
  return armenianRegex.test(word);
}

function clampedLeft(pct) {
  return Math.min(Math.max(pct, 0), 100) + '%';
}

function spawnParticles(pct) {
  if (pct < 85) return;
  const layer = document.getElementById('particles');
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight * 0.4;
  for (let i = 0; i < 18; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const size  = 4 + Math.random() * 6;
    const angle = Math.random() * Math.PI * 2;
    const dist  = 60 + Math.random() * 120;
    const color = getColor(pct);
    p.style.cssText = `left:${cx}px;top:${cy}px;width:${size}px;height:${size}px;
      background:${color};box-shadow:0 0 6px ${color};
      --dx:${(Math.cos(angle)*dist).toFixed(1)}px;
      --dy:${(Math.sin(angle)*dist).toFixed(1)}px;
      animation-duration:${(0.6+Math.random()*0.6).toFixed(2)}s;`;
    layer.appendChild(p);
    setTimeout(() => p.remove(), 1200);
  }
}

// --- Սերվերի հետ կապ (API) ---

async function getScoreFromServer(word) {
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word: word })
        });

        if (!response.ok) {
            if (response.status === 404) return { notFound: true };
            throw new Error('Server Error');
        }

        const data = await response.json();
        return { score: data.score, found: true };
    } catch (err) {
        console.error("API Error:", err);
        return { error: true };
    }
}

// --- Հիմնական տրամաբանություն ---

async function processWord(rawWord) {
  const word = rawWord.trim().toLowerCase();
  if (!word) return;

  wordInput.disabled = true;
  errorNotif.style.display = 'none';

  if (!isArmenianWord(word)) {
    errorNotif.style.display = 'block';
    errorNotif.innerHTML = 'Գրեք միայն հայերեն';
    wordInput.disabled = false;
    return;
  }

  // Կանչում ենք սերվերը
  const result = await getScoreFromServer(word);

  if (result.notFound) {
    errorNotif.style.display = 'block';
    errorNotif.innerHTML = 'Բառը բազայում չկա';
    wordInput.disabled = false;
    return;
  }

  if (result.error) {
    errorNotif.style.display = 'block';
    errorNotif.innerHTML = 'Կապի սխալ սերվերի հետ';
    wordInput.disabled = false;
    return;
  }

  const pct = result.score;
  
  // Թարմացնում ենք պատմությունը
  if (!history.find(h => h.word === word)) {
    history.push({ word, pct });
  }

  updateScale(pct);
  updateResultCard(word, pct);
  spawnParticles(pct);
  renderHistory();

  wordInput.disabled = false;
  wordInput.focus();
}

function updateScale(pct) {
  const color = getColor(pct);
  curInd.classList.add('visible');
  curInd.style.left = clampedLeft(pct);
  curVal.textContent = pct.toFixed(1) + '%';
  curVal.style.color = color;

  if (pct > bestPct) {
    bestPct = pct;
    bestInd.classList.add('visible');
    bestInd.style.left = clampedLeft(bestPct);
    bestVal.textContent = bestPct.toFixed(1) + '%';
  }
}

function updateResultCard(word, pct) {
  const color = getColor(pct);
  resultCard.classList.add('visible');
  resultWord.textContent = word;
  resultScore.textContent = pct.toFixed(1) + '%';
  resultScore.style.color = color;
}

function renderHistory() {
  historyList.innerHTML = '';
  const sorted = [...history].sort((a, b) => b.pct - a.pct);

  if (sorted.length === 0) {
    historyList.appendChild(emptyState);
    return;
  }

  sorted.forEach((item, idx) => {
    const color = getColor(item.pct);
    const el = document.createElement('div');
    el.className = 'history-item';
    el.innerHTML = `
      <div class="history-rank">${idx + 1}</div>
      <div class="history-word">${item.word}</div>
      <div class="history-score" style="color:${color}">${item.pct.toFixed(1)}%</div>
    `;
    historyList.appendChild(el);
  });
}

// --- Իրադարձություններ (Events) ---

wordInput.addEventListener('keydown', async (e) => {
  if (e.key === 'Enter') {
    const val = wordInput.value;
    wordInput.value = '';
    await processWord(val);
  }
});

clearBtn.addEventListener('click', () => {
  history = [];
  bestPct = -1;
  renderHistory();
  resultCard.classList.remove('visible');
});

// Պարզ հուշի տրամաբանություն
hintBtn.addEventListener('click', () => {
    hintPopup.style.display = 'block';
    hintText.textContent = "Փորձեք գտնել համակարգչին առնչվող բառեր...";
});

hintClose.addEventListener('click', () => {
    hintPopup.style.display = 'none';
});