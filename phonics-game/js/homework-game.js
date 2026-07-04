(() => {
  const $ = id => document.getElementById(id);
  const MAX_TRIES = 3;
  const DEFAULT_AUDIO = { level1: 'assets/phonics_audio.mp3?v=18', level2: 'assets/brighter-a.mp3?v=2' };
  const screens = ['startScreen', 'learnScreen', 'quizScreen', 'resultScreen'].map($);
  const state = {
    level: null, items: [], deck: [], q: null, qNo: 0, score: 0, tries: 0, answered: false,
    quizSize: 5, optionCount: 4, audio: new Audio(), timer: null, sequenceTimer: null,
    following: false, followItems: [], followEnd: 0, followRowName: '', fallback: false
  };

  const sessionModes = [
    { size: 5, options: 4, label: '🚂 小站 5 題', note: 'Quick Practice' },
    { size: 10, options: 6, label: '🎟️ 功課 10 題', note: 'Homework' },
    { size: 20, options: 8, label: '🏆 挑戰 20 題', note: 'Challenge' }
  ];

  function show(id) { stopFollowRow(); stopAudio(); screens.forEach(s => s.classList.remove('active')); $(id).classList.add('active'); scrollTo(0, 0); }
  function shuffle(a) { return [...a].sort(() => Math.random() - 0.5); }
  function unique(a) { return [...new Set(a)]; }
  function rowKey(rowName) { const m = String(rowName).match(/^([AEIOU])\b/i); return m ? m[1].toUpperCase() : rowName; }
  function stopAudio() { clearTimeout(state.timer); state.audio.pause(); state.audio.playbackRate = 1; }

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
      { id: 'level1', title: 'Level 1：子音列車', text: 'BA、BE、BI、BO、BU ...', audio: DEFAULT_AUDIO.level1, config: window.PHONICS_CLIPS || {} },
      { id: 'level2', title: 'Brighter Phonics Train：A/E/I/O/U Stations', text: 'AB-AZ、EB-EZ、IB-IZ、OB-OZ、UB-UZ', audio: DEFAULT_AUDIO.level2, config: window.PHONICS_LEVEL2_CLIPS || {} }
    ].filter(l => Object.keys(l.config).length);
  }

  function normalize(level) {
    const out = [];
    Object.entries(level.config).forEach(([rowName, row]) => {
      let clips = row, audio = level.audio;
      if (row && row.clips) { clips = row.clips; audio = row.audio || audio; }
      Object.entries(clips || {}).forEach(([label, range]) => {
        if (Array.isArray(range)) out.push({ rowName, rowKey: rowKey(rowName), label, start: +range[0], end: +range[1], audio });
      });
    });
    return out;
  }

  function makeButton(text, className, ariaLabel) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = className; b.textContent = text;
    if (ariaLabel) b.setAttribute('aria-label', ariaLabel);
    return b;
  }

  function renderLevels() {
    const box = $('levelGrid'); box.textContent = '';
    levels().forEach(level => {
      const items = normalize(level);
      const b = makeButton('', 'level-card train-card', '選擇 ' + level.title);
      const h = document.createElement('h3'); h.textContent = level.title;
      const p = document.createElement('p'); p.textContent = level.text;
      const s = document.createElement('p'); s.className = 'small'; s.textContent = '🚉 ' + items.length + ' 個音節車卡';
      b.append(h, p, s);
      b.addEventListener('click', () => selectLevel(level));
      box.appendChild(b);
    });
  }

  function ensureSessionControls() {
    if ($('sessionModes')) return;
    const box = document.createElement('div');
    box.id = 'sessionModes'; box.className = 'session-modes';
    sessionModes.forEach(mode => {
      const btn = makeButton(mode.label, 'big-btn secondary session-btn', mode.note);
      btn.dataset.size = mode.size; btn.dataset.options = mode.options;
      btn.addEventListener('click', () => chooseSession(mode.size, mode.options));
      box.appendChild(btn);
    });
    $('selectedLevelText').after(box);
    chooseSession(5, 4);
  }

  function chooseSession(size, options) {
    state.quizSize = size; state.optionCount = options;
    document.querySelectorAll('.session-btn').forEach(btn => {
      btn.classList.toggle('active', +btn.dataset.size === size);
    });
    const msg = $('sessionHint');
    if (msg) msg.textContent = '今次旅程：' + size + ' 題，每題 ' + options + ' 張車卡。';
  }

  function selectLevel(level) {
    stopFollowRow();
    state.level = level; state.items = normalize(level); state.fallback = false;
    $('selectedLevelTitle').textContent = '🚉 ' + level.title;
    $('selectedLevelText').textContent = '先跟住讀，再坐 phonics train 做小挑戰。共有 ' + state.items.length + ' 張音節車卡。';
    $('audioStatus').textContent = '請撳車卡或「播放第一個」。正式練習用老師音軌。';
    $('quizMode').textContent = '🚂 開車做練習';
    show('learnScreen'); renderReview(); renderQuizRowFilter(); ensureSessionControls(); renderTrainTrack();
  }

  function renderReview() {
    const sel = $('reviewRow'); sel.textContent = '';
    unique(state.items.map(i => i.rowName)).forEach(r => {
      const o = document.createElement('option'); o.value = r; o.textContent = r.replace(' row - ', ' Station - '); sel.appendChild(o);
    });
    renderReviewGrid();
  }

  function renderTrainTrack() {
    let track = $('trainTrack');
    if (!track) {
      track = document.createElement('div'); track.id = 'trainTrack'; track.className = 'train-track';
      $('reviewGrid').before(track);
    }
    const row = $('reviewRow').value;
    const labels = state.items.filter(i => i.rowName === row).map(i => i.label).slice(0, 8).join(' → ');
    track.textContent = '🚂 ' + (row ? rowKey(row) + ' Station' : 'Station') + '：' + labels + ' ...';
  }

  function renderReviewGrid() {
    stopFollowRow(); renderTrainTrack();
    const row = $('reviewRow').value, grid = $('reviewGrid'); grid.textContent = '';
    state.items.filter(i => i.rowName === row).forEach(item => {
      const b = makeButton(item.label, 'answer-btn carriage', '播放 ' + item.label + ' 音節');
      b.dataset.label = item.label;
      b.addEventListener('click', () => play(item));
      grid.appendChild(b);
    });
  }

  function play(item, rate = 1) {
    stopFollowRow(); playClip(item, rate);
  }

  function playClip(item, rate = 1) {
    stopAudio();
    state.audio.src = item.audio; state.audio.currentTime = item.start; state.audio.playbackRate = rate;
    $('audioStatus').textContent = '播放車卡 ' + item.label + '｜' + item.rowName;
    const p = state.audio.play();
    if (p) p.catch(() => speak(item.label));
    state.timer = setTimeout(() => { state.audio.pause(); state.audio.playbackRate = 1; }, Math.max(220, (item.end - item.start) * 1000 / rate));
  }

  function highlightReview(label) {
    document.querySelectorAll('#reviewGrid .answer-btn').forEach(b => b.classList.toggle('active', b.dataset.label === label));
  }

  function stopFollowRow() {
    state.following = false;
    clearTimeout(state.sequenceTimer);
    state.audio.removeEventListener('timeupdate', followHighlight);
    highlightReview('');
  }

  function followHighlight() {
    if (!state.following) return;
    const now = state.audio.currentTime;
    const current = state.followItems.find(i => now >= i.start && now <= i.end + 0.3);
    if (current) { highlightReview(current.label); $('audioStatus').textContent = '火車讀緊：' + current.label; }
    if (now >= state.followEnd || state.audio.ended) {
      stopAudio(); stopFollowRow(); $('audioStatus').textContent = '到站完成：' + state.followRowName;
    }
  }

  function followRow() {
    const row = $('reviewRow').value;
    const rowItems = state.items.filter(i => i.rowName === row).sort((a, b) => a.start - b.start);
    if (!rowItems.length) return;
    stopFollowRow(); stopAudio();
    const first = rowItems[0], last = rowItems[rowItems.length - 1];
    state.following = true; state.followItems = rowItems; state.followEnd = last.end + 0.35; state.followRowName = row;
    state.audio.src = first.audio; state.audio.currentTime = first.start; state.audio.playbackRate = 1;
    highlightReview(first.label);
    $('audioStatus').textContent = '火車出發，跟住讀：' + rowKey(row) + ' Station';
    state.audio.addEventListener('timeupdate', followHighlight);
    const p = state.audio.play();
    if (p) p.catch(() => { stopFollowRow(); speak(first.label); $('audioStatus').textContent = '手機阻止自動播放，請先點一張車卡。'; });
    state.sequenceTimer = setTimeout(() => {
      if (!state.following) return;
      stopAudio(); stopFollowRow(); $('audioStatus').textContent = '到站完成：' + row;
    }, Math.max(1000, (state.followEnd - first.start) * 1000));
  }

  function renderQuizRowFilter() {
    const sel = $('quizRowFilter'); sel.textContent = '';
    const all = document.createElement('option'); all.value = 'all'; all.textContent = 'All Stations'; sel.appendChild(all);
    unique(state.items.map(i => i.rowKey)).filter(k => /^[AEIOU]$/.test(k)).forEach(k => {
      const o = document.createElement('option'); o.value = k; o.textContent = k + ' Station'; sel.appendChild(o);
    });
  }

  function quizPool() {
    const filter = $('quizRowFilter').value;
    if (filter === 'all') return state.items;
    return state.items.filter(i => i.rowKey === filter);
  }

  function startQuiz() {
    stopFollowRow();
    const pool = quizPool(); if (!pool.length) return;
    state.deck = [];
    while (state.deck.length < state.quizSize) state.deck = state.deck.concat(shuffle(pool));
    state.deck = state.deck.slice(0, state.quizSize); state.qNo = 0; state.score = 0; state.tries = 0;
    show('quizScreen'); nextQuestion();
  }

  function choices(correct) {
    const pool = quizPool();
    const labels = unique(pool.map(i => i.label)).filter(x => x !== correct.label);
    const sameRow = pool.filter(i => i.rowName === correct.rowName && i.label !== correct.label).map(i => i.label);
    return shuffle([correct.label, ...shuffle(unique([...sameRow, ...labels])).slice(0, state.optionCount - 1)]);
  }

  function nextQuestion() {
    if (state.qNo >= state.quizSize) return result();
    state.q = state.deck[state.qNo++]; state.tries = 0; state.answered = false;
    $('questionLabel').textContent = '🚂'; $('quizMsg').textContent = '聽一聽，揀啱車卡！'; $('feedback').textContent = '';
    $('progressText').textContent = '第 ' + state.qNo + ' / ' + state.quizSize + ' 站'; $('scoreText').textContent = '星星 ' + state.score; $('triesText').textContent = '機會 3/3';
    $('progressFill').style.width = ((state.qNo - 1) / state.quizSize * 100) + '%';
    const grid = $('choices'); grid.textContent = '';
    choices(state.q).forEach(label => {
      const b = makeButton(label, 'answer-btn carriage', '選擇車卡 ' + label);
      b.addEventListener('click', () => answer(label, b)); grid.appendChild(b);
    });
  }

  function answer(label, b) {
    if (state.answered) return;
    if (label === state.q.label) {
      state.score++; state.answered = true; b.classList.add('correct'); disable(true); $('questionLabel').textContent = state.q.label; $('feedback').textContent = '✅ 好嘢！火車行前一步！';
    } else {
      state.tries++; b.classList.add('wrong'); b.disabled = true;
      if (state.tries >= MAX_TRIES) { state.answered = true; disable(true); reveal(); $('questionLabel').textContent = state.q.label; $('feedback').textContent = '答案係 ' + state.q.label + '，再聽一次會更好。'; }
      else $('feedback').textContent = '差少少，再聽一次～仲有 ' + (MAX_TRIES - state.tries) + ' 次機會。';
    }
    $('scoreText').textContent = '星星 ' + state.score; $('triesText').textContent = '機會 ' + Math.max(0, MAX_TRIES - state.tries) + '/3';
  }

  function disable(v) { document.querySelectorAll('#choices .answer-btn').forEach(b => { b.disabled = v; }); }
  function reveal() { document.querySelectorAll('#choices .answer-btn').forEach(b => { if (b.textContent === state.q.label) b.classList.add('correct'); }); }
  function result() {
    show('resultScreen'); $('progressFill').style.width = '100%'; $('finalScore').textContent = state.score + ' / ' + state.quizSize;
    $('resultNote').textContent = state.score >= Math.ceil(state.quizSize * 0.8) ? '🎉 到站啦！今日 phonics train 好成功！' : '💪 完成旅程，可以重溫再試。';
    if (state.fallback) $('resultNote').textContent += ' 有題目使用了電腦聲音。';
  }

  function wire() {
    renderLevels();
    $('backToStart').addEventListener('click', () => show('startScreen'));
    $('quizMode').addEventListener('click', startQuiz);
    $('reviewMode').addEventListener('click', () => show('learnScreen'));
    $('reviewRow').addEventListener('change', renderReviewGrid);
    $('quizRowFilter').addEventListener('change', () => { if ($('quizScreen').classList.contains('active')) startQuiz(); });
    $('playFirstReview').addEventListener('click', () => { const item = state.items.find(i => i.rowName === $('reviewRow').value); if (item) play(item); });
    $('followRow').addEventListener('click', followRow);
    $('stopFollowRow').addEventListener('click', () => { stopAudio(); stopFollowRow(); $('audioStatus').textContent = '已停車。'; });
    $('playQuestion').addEventListener('click', () => state.q && playClip(state.q));
    $('slowQuestion').addEventListener('click', () => state.q && playClip(state.q, 0.75));
    $('nextQuestion').addEventListener('click', nextQuestion);
    $('restartBtn').addEventListener('click', () => show('learnScreen'));
    $('againBtn').addEventListener('click', startQuiz);
    $('homeBtn').addEventListener('click', () => show('startScreen'));
  }
  document.addEventListener('DOMContentLoaded', wire);
})();
