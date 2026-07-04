(() => {
  const $ = id => document.getElementById(id);
  const QUIZ_SIZE = 20, MAX_TRIES = 3, OPTION_COUNT = 10;
  const DEFAULT_AUDIO = { level1: 'assets/phonics_audio.mp3?v=18', level2: 'assets/phonics_level2_ab_az.mp3?v=6' };
  const screens = ['startScreen', 'learnScreen', 'quizScreen', 'resultScreen'].map($);
  const state = { level: null, items: [], deck: [], q: null, qNo: 0, score: 0, tries: 0, answered: false, audio: new Audio(), timer: null, fallback: false };

  function show(id) { screens.forEach(s => s.classList.remove('active')); $(id).classList.add('active'); scrollTo(0, 0); }
  function shuffle(a) { return [...a].sort(() => Math.random() - 0.5); }
  function speak(label) {
    state.fallback = true;
    $('audioStatus').textContent = '音檔未能播放，改用電腦聲音：' + label;
    if (!('speechSynthesis' in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(label.split('').join(' '));
    u.lang = 'en-US'; u.rate = 0.75;
    speechSynthesis.speak(u);
  }
  function levels() {
    return [
      { id: 'level1', title: 'Level 1：子音 + A/E/I/O/U', text: 'BA、BE、BI、BO、BU ...', audio: DEFAULT_AUDIO.level1, config: window.PHONICS_CLIPS || {} },
      { id: 'level2', title: 'Level 2：A + 子音', text: 'AB、AC、AD ... AZ；日後可加 E row', audio: DEFAULT_AUDIO.level2, config: window.PHONICS_LEVEL2_CLIPS || {} }
    ].filter(l => Object.keys(l.config).length);
  }
  function normalize(level) {
    const out = [];
    Object.entries(level.config).forEach(([rowName, row]) => {
      let clips = row, audio = level.audio;
      if (row && row.clips) { clips = row.clips; audio = row.audio || audio; }
      Object.entries(clips || {}).forEach(([label, range]) => {
        if (Array.isArray(range)) out.push({ rowName, label, start: +range[0], end: +range[1], audio });
      });
    });
    return out;
  }
  function renderLevels() {
    const box = $('levelGrid'); box.innerHTML = '';
    levels().forEach(level => {
      const items = normalize(level);
      const b = document.createElement('button');
      b.className = 'level-card';
      b.innerHTML = '<h3>' + level.title + '</h3><p>' + level.text + '</p><p class="small">' + items.length + ' 個音節</p>';
      b.onclick = () => selectLevel(level);
      box.appendChild(b);
    });
  }
  function selectLevel(level) {
    state.level = level; state.items = normalize(level); state.fallback = false;
    $('selectedLevelTitle').textContent = level.title;
    $('selectedLevelText').textContent = '先重溫，再做 20 題功課。共有 ' + state.items.length + ' 個音節。';
    $('audioStatus').textContent = '請撳音節或「聽一聽」播放。若音檔缺失，會用電腦聲音 fallback。';
    show('learnScreen'); renderReview();
  }
  function renderReview() {
    const sel = $('reviewRow'); sel.innerHTML = '';
    [...new Set(state.items.map(i => i.rowName))].forEach(r => {
      const o = document.createElement('option'); o.value = r; o.textContent = r; sel.appendChild(o);
    });
    renderReviewGrid();
  }
  function renderReviewGrid() {
    const row = $('reviewRow').value, grid = $('reviewGrid'); grid.innerHTML = '';
    state.items.filter(i => i.rowName === row).forEach(item => {
      const b = document.createElement('button'); b.className = 'answer-btn'; b.textContent = item.label; b.onclick = () => play(item); grid.appendChild(b);
    });
  }
  function play(item, rate = 1) {
    clearTimeout(state.timer);
    state.audio.pause(); state.audio.src = item.audio; state.audio.currentTime = item.start; state.audio.playbackRate = rate;
    $('audioStatus').textContent = '播放 ' + item.label + '｜' + item.rowName;
    const p = state.audio.play();
    if (p) p.catch(() => speak(item.label));
    state.timer = setTimeout(() => { state.audio.pause(); state.audio.playbackRate = 1; }, Math.max(120, (item.end - item.start) * 1000 / rate));
  }
  function startQuiz() {
    state.deck = [];
    while (state.deck.length < QUIZ_SIZE) state.deck = state.deck.concat(shuffle(state.items));
    state.deck = state.deck.slice(0, QUIZ_SIZE); state.qNo = 0; state.score = 0; state.tries = 0;
    show('quizScreen'); nextQuestion();
  }
  function choices(correct) {
    const labels = [...new Set(state.items.map(i => i.label))].filter(x => x !== correct.label);
    const sameRow = state.items.filter(i => i.rowName === correct.rowName && i.label !== correct.label).map(i => i.label);
    return shuffle([correct.label, ...shuffle([...new Set([...sameRow, ...labels])]).slice(0, OPTION_COUNT - 1)]);
  }
  function nextQuestion() {
    if (state.qNo >= QUIZ_SIZE) return result();
    state.q = state.deck[state.qNo++]; state.tries = 0; state.answered = false;
    $('questionLabel').textContent = '🎧'; $('quizMsg').textContent = '先撳「聽一聽」，再揀答案。'; $('feedback').textContent = '';
    $('progressText').textContent = '第 ' + state.qNo + ' / ' + QUIZ_SIZE + ' 題'; $('scoreText').textContent = '分數 ' + state.score; $('triesText').textContent = '機會 3/3';
    $('progressFill').style.width = ((state.qNo - 1) / QUIZ_SIZE * 100) + '%';
    const grid = $('choices'); grid.innerHTML = '';
    choices(state.q).forEach(label => { const b = document.createElement('button'); b.className = 'answer-btn'; b.textContent = label; b.onclick = () => answer(label, b); grid.appendChild(b); });
  }
  function answer(label, b) {
    if (state.answered) return;
    if (label === state.q.label) { state.score++; state.answered = true; b.classList.add('correct'); disable(true); $('questionLabel').textContent = state.q.label; $('feedback').textContent = '✅ 答啱！撳下一題。'; }
    else { state.tries++; b.classList.add('wrong'); b.disabled = true; if (state.tries >= MAX_TRIES) { state.answered = true; disable(true); reveal(); $('questionLabel').textContent = state.q.label; $('feedback').textContent = '答案係 ' + state.q.label + '。'; } else $('feedback').textContent = '差少少，仲有 ' + (MAX_TRIES - state.tries) + ' 次機會。'; }
    $('scoreText').textContent = '分數 ' + state.score; $('triesText').textContent = '機會 ' + Math.max(0, MAX_TRIES - state.tries) + '/3';
  }
  function disable(v) { document.querySelectorAll('#choices .answer-btn').forEach(b => b.disabled = v); }
  function reveal() { document.querySelectorAll('#choices .answer-btn').forEach(b => { if (b.textContent === state.q.label) b.classList.add('correct'); }); }
  function result() { show('resultScreen'); $('progressFill').style.width = '100%'; $('finalScore').textContent = state.score + ' / ' + QUIZ_SIZE; $('resultNote').textContent = state.score >= 16 ? '🎉 功課完成，好叻！' : '💪 完成 20 題，可以重溫再試。'; if (state.fallback) $('resultNote').textContent += ' 有題目使用了電腦聲音。'; }
  function wire() {
    renderLevels(); $('backToStart').onclick = () => show('startScreen'); $('quizMode').onclick = startQuiz; $('reviewMode').onclick = () => show('learnScreen'); $('reviewRow').onchange = renderReviewGrid;
    $('playFirstReview').onclick = () => { const item = state.items.find(i => i.rowName === $('reviewRow').value); if (item) play(item); };
    $('playQuestion').onclick = () => state.q && play(state.q); $('slowQuestion').onclick = () => state.q && play(state.q, 0.75); $('nextQuestion').onclick = nextQuestion;
    $('restartBtn').onclick = () => show('learnScreen'); $('againBtn').onclick = startQuiz; $('homeBtn').onclick = () => show('startScreen');
  }
  document.addEventListener('DOMContentLoaded', wire);
})();