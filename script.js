let bestPct = -1;
let history = [];
let hintCooldown = false;

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

function updateScale(pct) {
  const color = getColor(pct);
  curInd.classList.add('visible');
  curInd.style.left = clampedLeft(pct);
  curVal.textContent = pct.toFixed(1) + '%';
  curVal.style.color = color;
  curVal.style.filter = `drop-shadow(0 0 8px ${color})`;

  if (pct > bestPct) {
    bestPct = pct;
    setTimeout(() => {
      bestInd.classList.add('visible');
      bestInd.style.left = clampedLeft(bestPct);
      bestVal.textContent = bestPct.toFixed(1) + '%';
    }, 60);
  }
}

function updateResultCard(word, pct, source) {
  const color = getColor(pct);
  resultCard.classList.add('visible');
  resultCard.style.borderColor = color + '44';
  resultCard.style.boxShadow = `0 20px 60px rgba(0,0,0,0.4), 0 0 40px ${color}18, inset 0 1px 0 rgba(255,255,255,0.06)`;
  resultWord.textContent = word;
  resultScore.textContent = pct.toFixed(1) + '%';
  resultScore.style.color = color;
  resultScore.style.textShadow = `0 0 20px ${color}`;

  const badge = document.getElementById('result-source');
  if (badge) {
    badge.textContent = source === 'api' ? '🌐 API' : source === 'db' ? '📖 DB' : '🎲 Պատահական';
    badge.style.color = source === 'random' ? 'var(--muted)' : '#7B61FF';
  }
  resultCard.style.animation = 'none';
  void resultCard.offsetWidth;
  resultCard.style.animation = '';
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
    el.style.animationDelay = (idx * 0.04) + 's';
    if (item.pct > 90) {
      el.style.borderColor = 'rgba(255,61,0,0.3)';
      el.style.boxShadow = '0 0 20px rgba(255,61,0,0.08)';
    }
    el.innerHTML = `
      <div class="history-rank">${idx + 1}</div>
      <div class="history-color-dot" style="background:${color};box-shadow:0 0 8px ${color}"></div>
      <div class="history-word">${item.word}</div>
      <div class="history-mini-bar">
        <div class="history-mini-bar-fill" style="width:${item.pct}%;background:${color}"></div>
      </div>
      <div class="history-score" style="color:${color};text-shadow:0 0 10px ${color}88">${item.pct.toFixed(1)}%</div>
    `;
    historyList.appendChild(el);
  });
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

async function showHint() {
  if (hintCooldown) return;

  await loadWords();
  const db = getWordDb();
  const entries = Object.entries(db);

  if (entries.length === 0) {
    hintText.textContent = 'Բազան դեռ բեռնված չե...';
    openHintPopup();
    return;
  }

  const tried = new Set(history.map(h => h.word));
  let pool = entries.filter(([w, v]) => v >= 50 && !tried.has(w));
  if (pool.length === 0) pool = entries.filter(([w]) => !tried.has(w));
  if (pool.length === 0) pool = entries;

  const [word, score] = pool[Math.floor(Math.random() * pool.length)];
  const color = getColor(score);

  hintText.innerHTML = `<strong style="font-size:1.25rem;letter-spacing:2px;color:${color}">${word}</strong>`;

  openHintPopup();

  hintCooldown = true;
  hintBtn.style.opacity = '0.45';
  hintBtn.style.pointerEvents = 'none';
  setTimeout(() => {
    hintCooldown = false;
    hintBtn.style.opacity = '1';
    hintBtn.style.pointerEvents = 'auto';
  }, 3000);
}

function openHintPopup() {
  if (!hintPopup) return;
  hintPopup.style.display = 'block';
  hintPopup.classList.remove('visible');
  void hintPopup.offsetWidth;
  hintPopup.classList.add('visible');
}

function closeHintPopup() {
  if (!hintPopup) return;
  hintPopup.classList.remove('visible');
}

async function processWord(rawWord) {
  const word = rawWord.trim().toLowerCase();
  if (!word) return;

  wordInput.disabled = true;
  closeHintPopup();
  errorNotif.style.display = 'none';
  resultCard.classList.remove('visible');

  if (!isArmenianWord(word)) {
    errorNotif.style.display = 'block';
    errorNotif.innerHTML = '<strong style="color:#FF6B6B;">🚠 Սխալ</strong> Գրեք միայն հայերեն';
    wordInput.disabled = false;
    wordInput.focus();
    return;
  }

  const result = await getScore(word);

  if (result.notFound) {
    errorNotif.style.display = 'block';
    errorNotif.innerHTML = '<strong style="color:#FFC107;">⚠️ Չգտնված</strong> Բառը բառարանում չի հայտնաբերվել';
    wordInput.disabled = false;
    wordInput.focus();
    return;
  }

  const { score: pct, source } = result;

  const existingIdx = history.findIndex(h => h.word === word);
  if (existingIdx !== -1) {
    history[existingIdx].pct = pct;
  } else {
    history.push({ word, pct });
  }

  updateScale(pct);
  updateResultCard(word, pct, source);
  spawnParticles(pct);
  renderHistory();

  wordInput.disabled = false;
  wordInput.focus();
}

function clearHistory() {
  history = [];
  bestPct = -1;
  curInd.classList.remove('visible');
  bestInd.classList.remove('visible');
  resultCard.classList.remove('visible');
  closeHintPopup();
  renderHistory();
}

wordInput.addEventListener('keydown', async (e) => {
  if (e.key === 'Enter') {
    const val = wordInput.value.trim();
    wordInput.value = '';
    await processWord(val);
  }
});

function setupEventListeners() {
  clearBtn.addEventListener('click', clearHistory);
  hintBtn.addEventListener('click', showHint);
  hintClose.addEventListener('click', closeHintPopup);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', async () => {
    await loadWords();
    renderHistory();
    wordInput.focus();
    setupEventListeners();
  });
} else {
  (async () => {
    await loadWords();
    renderHistory();
    wordInput.focus();
    setupEventListeners();
  })();
}
