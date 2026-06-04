"""Embed questions.json into a self-contained HTML quiz app."""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

data = json.loads(open(r"C:\Users\Adi\Code\Chinease_medicine\questions.json", encoding='utf-8').read())
data_json = json.dumps(data, ensure_ascii=False)

html = f'''<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>מבחני רפואה סינית</title>
<style>
  :root {{
    --jade:    #1B4332;
    --sage:    #40916C;
    --mint:    #74C69D;
    --cream:   #FDF8F0;
    --warm:    #F8EDD9;
    --gold:    #C9A84C;
    --gold-lt: #F0D58C;
    --text:    #1A1A1A;
    --muted:   #6B7280;
    --correct: #2D6A4F;
    --wrong:   #B91C1C;
    --radius:  16px;
    --shadow:  0 4px 24px rgba(0,0,0,0.10);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', 'Arial Hebrew', 'David', sans-serif;
    background: var(--cream);
    color: var(--text);
    min-height: 100dvh;
    direction: rtl;
  }}

  /* ── Header ── */
  .header {{
    background: linear-gradient(135deg, var(--jade) 0%, var(--sage) 100%);
    color: white;
    padding: 18px 20px 16px;
    text-align: center;
    position: sticky; top: 0; z-index: 10;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
  }}
  .header h1 {{ font-size: 1.25rem; font-weight: 700; letter-spacing: 0.03em; }}
  .header .subtitle {{ font-size: 0.8rem; opacity: 0.8; margin-top: 2px; }}

  /* ── Screen management ── */
  .screen {{ display: none; animation: fadeIn 0.3s ease; }}
  .screen.active {{ display: block; }}
  @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:none; }} }}

  /* ── Topic selection ── */
  #homeScreen {{ padding: 20px 16px 32px; }}
  .home-title {{
    text-align: center;
    margin-bottom: 24px;
  }}
  .home-title h2 {{ font-size: 1.4rem; color: var(--jade); font-weight: 700; }}
  .home-title p  {{ color: var(--muted); font-size: 0.9rem; margin-top: 6px; }}

  .topic-grid {{
    display: flex; flex-direction: column; gap: 14px;
  }}
  .topic-card {{
    background: white;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 20px 22px;
    display: flex; align-items: center; gap: 16px;
    cursor: pointer;
    border: 2px solid transparent;
    transition: transform 0.18s, border-color 0.18s, box-shadow 0.18s;
    position: relative; overflow: hidden;
  }}
  .topic-card::before {{
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(135deg, var(--jade) 0%, var(--sage) 100%);
    opacity: 0; transition: opacity 0.18s;
  }}
  .topic-card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0,0,0,0.14); border-color: var(--mint); }}
  .topic-card:active {{ transform: scale(0.98); }}
  .topic-icon {{
    font-size: 2.4rem;
    min-width: 52px; text-align: center;
    position: relative;
  }}
  .topic-info {{ flex: 1; position: relative; }}
  .topic-name {{ font-size: 1.1rem; font-weight: 700; color: var(--jade); }}
  .topic-count {{ font-size: 0.82rem; color: var(--muted); margin-top: 4px; }}

  /* ── Quiz screen ── */
  #quizScreen {{ padding: 0 0 100px; }}

  .quiz-nav {{
    display: flex; align-items: center; gap: 12px;
    padding: 14px 16px;
  }}
  .btn-back {{
    background: none; border: none; cursor: pointer;
    color: var(--jade); font-size: 1.6rem; line-height: 1;
    padding: 4px 8px; border-radius: 8px;
    transition: background 0.15s;
  }}
  .btn-back:hover {{ background: rgba(27,67,50,0.08); }}
  .topic-label {{
    font-size: 0.95rem; font-weight: 600; color: var(--jade); flex: 1;
  }}
  .score-badge {{
    background: var(--warm); border-radius: 20px;
    padding: 4px 14px; font-size: 0.85rem; font-weight: 600;
    color: var(--jade);
  }}

  /* Progress bar */
  .progress-wrap {{ padding: 0 16px 12px; }}
  .progress-bar {{
    height: 6px; background: #E5E7EB; border-radius: 99px; overflow: hidden;
  }}
  .progress-fill {{
    height: 100%;
    background: linear-gradient(90deg, var(--sage), var(--mint));
    border-radius: 99px;
    transition: width 0.4s ease;
  }}
  .progress-text {{
    font-size: 0.78rem; color: var(--muted);
    text-align: left; margin-top: 4px;
  }}

  /* Question card */
  .question-card {{
    margin: 0 16px;
    background: white;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 22px 20px 18px;
    min-height: 120px;
  }}
  .question-number {{
    display: inline-block;
    background: var(--jade);
    color: white;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 99px;
    margin-bottom: 12px;
  }}
  .question-text {{
    font-size: 1.05rem;
    line-height: 1.65;
    color: var(--text);
  }}

  /* Options */
  .options-list {{
    padding: 16px 16px 0;
    display: flex; flex-direction: column; gap: 10px;
  }}
  .option-btn {{
    background: white;
    border: 2px solid #E5E7EB;
    border-radius: 12px;
    padding: 14px 18px;
    font-size: 0.97rem;
    line-height: 1.5;
    text-align: right;
    cursor: pointer;
    color: var(--text);
    transition: border-color 0.15s, background 0.15s, transform 0.12s;
    display: flex; align-items: flex-start; gap: 12px;
    position: relative;
  }}
  .option-btn:hover:not(:disabled) {{
    border-color: var(--mint);
    background: #F0FDF4;
    transform: translateX(-2px);
  }}
  .option-btn:active:not(:disabled) {{ transform: scale(0.98); }}
  .option-label {{
    min-width: 28px; height: 28px;
    background: var(--warm);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.85rem; color: var(--jade);
    flex-shrink: 0;
  }}
  .option-text {{ flex: 1; padding-top: 2px; }}

  /* States */
  .option-btn.correct {{
    border-color: var(--correct);
    background: #D1FAE5;
  }}
  .option-btn.correct .option-label {{
    background: var(--correct); color: white;
  }}
  .option-btn.wrong {{
    border-color: var(--wrong);
    background: #FEE2E2;
  }}
  .option-btn.wrong .option-label {{
    background: var(--wrong); color: white;
  }}
  .option-btn.reveal {{
    border-color: var(--correct);
    background: #ECFDF5;
    opacity: 0.85;
  }}
  .option-btn:disabled {{ cursor: default; transform: none !important; }}

  /* Feedback */
  .feedback-bar {{
    margin: 14px 16px 0;
    border-radius: 12px;
    padding: 12px 18px;
    font-size: 0.95rem;
    font-weight: 600;
    text-align: center;
    display: none;
  }}
  .feedback-bar.correct-fb {{ background:#D1FAE5; color: var(--correct); display: block; }}
  .feedback-bar.wrong-fb   {{ background:#FEE2E2; color: var(--wrong);   display: block; }}

  /* Source */
  .source-tag {{
    display: none;
    margin: 8px 16px 0;
    font-size: 0.78rem;
    color: var(--muted);
    text-align: center;
  }}
  .source-tag.visible {{ display: block; }}

  /* Next button */
  .next-wrap {{
    padding: 16px 16px 0;
  }}
  .btn-next {{
    width: 100%;
    background: linear-gradient(135deg, var(--jade), var(--sage));
    color: white;
    border: none; border-radius: 12px;
    padding: 15px;
    font-size: 1rem; font-weight: 700;
    cursor: pointer;
    transition: opacity 0.15s, transform 0.12s;
    display: none;
  }}
  .btn-next:hover {{ opacity: 0.92; }}
  .btn-next:active {{ transform: scale(0.98); }}
  .btn-next.visible {{ display: block; }}

  /* ── Results screen ── */
  #resultsScreen {{ padding: 32px 16px; text-align: center; }}
  .results-circle {{
    width: 140px; height: 140px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--jade), var(--sage));
    color: white;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    margin: 0 auto 24px;
    box-shadow: 0 8px 32px rgba(27,67,50,0.35);
  }}
  .results-score {{ font-size: 2.5rem; font-weight: 800; line-height: 1; }}
  .results-total {{ font-size: 1rem; opacity: 0.85; }}
  .results-pct   {{ font-size: 1.4rem; font-weight: 700; color: var(--jade); margin-bottom: 8px; }}
  .results-msg   {{ font-size: 1rem; color: var(--muted); margin-bottom: 32px; }}
  .results-btns  {{ display: flex; flex-direction: column; gap: 12px; }}
  .btn-primary {{
    background: linear-gradient(135deg, var(--jade), var(--sage));
    color: white; border: none; border-radius: 12px;
    padding: 15px; font-size: 1rem; font-weight: 700;
    cursor: pointer; transition: opacity 0.15s;
  }}
  .btn-primary:hover {{ opacity: 0.9; }}
  .btn-secondary {{
    background: white; color: var(--jade);
    border: 2px solid var(--sage); border-radius: 12px;
    padding: 14px; font-size: 1rem; font-weight: 600;
    cursor: pointer; transition: background 0.15s;
  }}
  .btn-secondary:hover {{ background: #F0FDF4; }}
</style>
</head>
<body>

<header class="header">
  <h1>מבחני רפואה סינית</h1>
  <p class="subtitle">אסופת מבחנים 2012–2019 | IATCM</p>
</header>

<!-- Home screen -->
<div id="homeScreen" class="screen active">
  <div class="home-title">
    <h2>בחרי נושא לתרגול</h2>
    <p>שאלות רנדומליות מתוך מבחני ההסמכה</p>
  </div>
  <div class="topic-grid" id="topicGrid"></div>
</div>

<!-- Quiz screen -->
<div id="quizScreen" class="screen">
  <div class="quiz-nav">
    <button class="btn-back" id="btnBack">&#8594;</button>
    <span class="topic-label" id="quizTopicLabel"></span>
    <span class="score-badge" id="scoreBadge">0/0</span>
  </div>

  <div class="progress-wrap">
    <div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:0%"></div></div>
    <div class="progress-text" id="progressText"></div>
  </div>

  <div class="question-card">
    <span class="question-number" id="qNumber">שאלה 1</span>
    <p class="question-text" id="qText"></p>
  </div>

  <div class="options-list" id="optionsList"></div>

  <div class="feedback-bar" id="feedbackBar"></div>
  <div class="source-tag" id="sourceTag"></div>

  <div class="next-wrap">
    <button class="btn-next" id="btnNext">שאלה הבאה ←</button>
  </div>
</div>

<!-- Results screen -->
<div id="resultsScreen" class="screen">
  <div class="results-circle">
    <span class="results-score" id="resScore">0</span>
    <span class="results-total" id="resTotal">/ 0</span>
  </div>
  <div class="results-pct" id="resPct">0%</div>
  <div class="results-msg" id="resMsg"></div>
  <div class="results-btns">
    <button class="btn-primary" id="btnRestart">נסה שוב באותו נושא</button>
    <button class="btn-secondary" id="btnHome">חזור לבחירת נושא</button>
  </div>
</div>

<script>
const DATA = {data_json};

// ── State ────────────────────────────────────────────────────────────────────
let activeTopic = null;
let queue = [];
let qIdx = 0;
let correct = 0;
let answered = 0;
const BATCH = 20;   // questions per session

const LETTERS = ['א', 'ב', 'ג', 'ד'];
const ICONS   = {{'yesodot':'☯','dikur':'🪡','itur':'📍','tsmakim':'🌿','maaravit':'🏥'}};

// ── Helpers ──────────────────────────────────────────────────────────────────
function show(id) {{
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  window.scrollTo(0, 0);
}}

function shuffle(arr) {{
  for (let i = arr.length - 1; i > 0; i--) {{
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }}
  return arr;
}}

// ── Build home ───────────────────────────────────────────────────────────────
function buildHome() {{
  const grid = document.getElementById('topicGrid');
  grid.innerHTML = '';
  DATA.topics.forEach(t => {{
    const card = document.createElement('div');
    card.className = 'topic-card';
    card.innerHTML = `
      <div class="topic-icon">${{ICONS[t.id] || '📖'}}</div>
      <div class="topic-info">
        <div class="topic-name">${{t.name}}</div>
        <div class="topic-count">${{t.questions.length}} שאלות</div>
      </div>
      <div style="color:var(--muted);font-size:1.2rem;">&#8592;</div>
    `;
    card.addEventListener('click', () => startQuiz(t));
    grid.appendChild(card);
  }});
}}

// ── Start quiz ───────────────────────────────────────────────────────────────
function startQuiz(topic) {{
  activeTopic = topic;
  queue = shuffle([...topic.questions]).slice(0, BATCH);
  qIdx = 0; correct = 0; answered = 0;

  document.getElementById('quizTopicLabel').textContent = topic.name;
  show('quizScreen');
  renderQuestion();
}}

// ── Render question ──────────────────────────────────────────────────────────
function renderQuestion() {{
  const q = queue[qIdx];
  const total = queue.length;

  document.getElementById('qNumber').textContent = `שאלה ${{qIdx + 1}}`;
  document.getElementById('qText').textContent = q.q;
  document.getElementById('scoreBadge').textContent = `${{correct}}/${{answered}}`;

  const pct = Math.round((qIdx / total) * 100);
  document.getElementById('progressFill').style.width = pct + '%';
  document.getElementById('progressText').textContent =
    `${{qIdx + 1}} מתוך ${{total}}`;

  const list = document.getElementById('optionsList');
  list.innerHTML = '';

  // Shuffle option order with tracking
  const indices = shuffle([0, 1, 2, 3]);
  q._shuffled = indices;  // save for reveal

  indices.forEach((origIdx, displayPos) => {{
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    btn.setAttribute('data-orig', origIdx);
    btn.innerHTML = `
      <span class="option-label">${{LETTERS[displayPos]}}</span>
      <span class="option-text">${{q.options[origIdx]}}</span>
    `;
    btn.addEventListener('click', () => selectOption(btn, origIdx, q));
    list.appendChild(btn);
  }});

  document.getElementById('feedbackBar').className = 'feedback-bar';
  document.getElementById('feedbackBar').textContent = '';
  document.getElementById('sourceTag').className = 'source-tag';
  document.getElementById('sourceTag').textContent = '';
  const btnNext = document.getElementById('btnNext');
  btnNext.classList.remove('visible');
  btnNext.textContent = (qIdx + 1 < queue.length) ? 'שאלה הבאה ←' : 'לתוצאות';
}}

// ── Select option ─────────────────────────────────────────────────────────────
function selectOption(btn, origIdx, q) {{
  const btns = document.querySelectorAll('.option-btn');
  btns.forEach(b => b.disabled = true);

  answered++;
  const isCorrect = origIdx === q.answer;
  if (isCorrect) correct++;

  // Mark chosen
  btn.classList.add(isCorrect ? 'correct' : 'wrong');

  // Reveal correct if wrong
  if (!isCorrect) {{
    btns.forEach(b => {{
      if (parseInt(b.getAttribute('data-orig')) === q.answer) {{
        b.classList.add('reveal');
      }}
    }});
  }}

  // Feedback
  const fb = document.getElementById('feedbackBar');
  if (isCorrect) {{
    fb.className = 'feedback-bar correct-fb';
    fb.textContent = '✓ תשובה נכונה!';
  }} else {{
    fb.className = 'feedback-bar wrong-fb';
    fb.textContent = '✗ תשובה שגויה';
  }}

  document.getElementById('scoreBadge').textContent = `${{correct}}/${{answered}}`;
  document.getElementById('btnNext').classList.add('visible');

  // Show source
  if (q.source) {{
    const st = document.getElementById('sourceTag');
    st.textContent = `מקור: ${{q.source}}`;
    st.className = 'source-tag visible';
  }}
}}

// ── Next ─────────────────────────────────────────────────────────────────────
document.getElementById('btnNext').addEventListener('click', () => {{
  qIdx++;
  if (qIdx < queue.length) {{
    renderQuestion();
  }} else {{
    showResults();
  }}
}});

// ── Results ───────────────────────────────────────────────────────────────────
function showResults() {{
  const pct = Math.round((correct / answered) * 100);
  document.getElementById('resScore').textContent = correct;
  document.getElementById('resTotal').textContent = `/ ${{answered}}`;
  document.getElementById('resPct').textContent = pct + '%';

  let msg;
  if (pct >= 90)      msg = 'מצוין! שליטה מרשימה בחומר 🏆';
  else if (pct >= 75) msg = 'כל הכבוד! תוצאה טובה מאוד 👍';
  else if (pct >= 60) msg = 'לא רע! קצת עוד תרגול ותהיה מושלם 💪';
  else                msg = 'כדאי לחזור על החומר ולנסות שוב 📖';
  document.getElementById('resMsg').textContent = msg;

  show('resultsScreen');
}}

document.getElementById('btnRestart').addEventListener('click', () => startQuiz(activeTopic));
document.getElementById('btnHome').addEventListener('click', () => show('homeScreen'));
document.getElementById('btnBack').addEventListener('click', () => show('homeScreen'));

// ── Init ──────────────────────────────────────────────────────────────────────
buildHome();
</script>
</body>
</html>'''

out = r"C:\Users\Adi\Code\Chinease_medicine\index.html"
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✓ Written: {out}")
print(f"  Size: {len(html):,} bytes")
