// ============================================
// AUTO-LOAD FROM URL
// ============================================
const backendUrl = "https://classical-zoloft-budgets-identity.trycloudflare.com/";

window.addEventListener('DOMContentLoaded', async () => {
  // Check if there is a "?code=..." in the URL
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  
  if (code) {
    try {
      // Change the UI to show it's loading
      document.querySelector('.landing-subtitle').textContent = "Downloading test from server...";
      document.querySelector('label[for="file-input"]').style.display = 'none';
      
      // Fetch the JSON directly from your FastAPI backend
      const response = await fetch(`${backendUrl}api/get-test/${code}`);
      if (!response.ok) throw new Error('Test not found on server. Check your code!');
      
      testData = await response.json();
      if (!testData.questions) throw new Error('Invalid test format');
      
      initTest();
    } catch (err) {
      document.getElementById('load-error').textContent = err.message;
      document.querySelector('label[for="file-input"]').style.display = 'inline-flex'; // Show upload button again
    }
  }
});

// ... (Paste all of your original JS below this) ...

// ============================================
// STATE
// ============================================
let testData = null;
let userAnswers = { mcq: {}, tf: {}, short: {} };
let shortSelfGrades = {};

function formatScore(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return '0';
  return String(parseFloat(num.toFixed(2)));
}

// ============================================
// SCREENS
// ============================================
function showScreen(screenId) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(screenId).classList.add('active');
  window.scrollTo(0, 0);
}

// ============================================
// FILE LOADING
// ============================================
document.getElementById('file-input').addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (ev) => {
    try {
      testData = JSON.parse(ev.target.result);
      if (!testData.questions) throw new Error('Invalid test format');
      initTest();
    } catch (err) {
      document.getElementById('load-error').textContent = 'Invalid JSON file: ' + err.message;
    }
  };
  reader.readAsText(file);
});

// ============================================
// INIT TEST
// ============================================
function initTest() {
  userAnswers = { mcq: {}, tf: {}, short: {} };
  shortSelfGrades = {};

  // Set header info
  document.getElementById('theme-title').textContent = testData.main_theme || 'Test';
  const scoring = testData.scoring || {};
  document.getElementById('score-info').textContent = `Total: ${scoring.total_score || '?'} pts`;

  // Set section point labels
  const mcqSection = scoring.mcq_section || {};
  const tfSection = scoring.tf_section || {};
  const shortSection = scoring.short_section || {};
  document.getElementById('mcq-points').textContent =
    `${mcqSection.total_points || 0} pts (${mcqSection.points_each || 0} each)`;
  document.getElementById('tf-points').textContent =
    `${tfSection.total_points || 0} pts (${tfSection.points_each || 0} each)`;
  document.getElementById('short-points').textContent =
    `${shortSection.total_points || 0} pts (${shortSection.points_each || 0} each)`;

  // Render questions
  renderMCQ(testData.questions.multiple_choice || []);
  renderTF(testData.questions.true_false || []);
  renderShort(testData.questions.short_answer || []);

  updateProgress();
  showScreen('test-screen');
}

// ============================================
// RENDER MCQ
// ============================================
function renderMCQ(questions) {
  const container = document.getElementById('mcq-questions');
  container.innerHTML = '';

  if (questions.length === 0) {
    document.getElementById('section-mcq').style.display = 'none';
    return;
  }

  questions.forEach((q) => {
    const card = document.createElement('div');
    card.className = 'question-card';
    card.id = `mcq-${q.id}`;

    card.innerHTML = `
      <div class="question-card-header">
        <span class="question-number">Question ${q.id}</span>
        <span class="question-points">${q.points} pts</span>
      </div>
      <div class="question-topic">${q.topic}</div>
      <div class="question-text">${q.question}</div>
      <div class="options-list">
        ${q.options.map((opt) => {
          const letter = opt.charAt(0);
          return `<button class="option-btn" data-qid="${q.id}" data-letter="${letter}" onclick="selectMCQ(${q.id}, '${letter}')">
            <span class="option-letter">${letter}</span>
            <span>${opt.substring(3)}</span>
          </button>`;
        }).join('')}
      </div>
    `;

    container.appendChild(card);
  });
}

// ============================================
// RENDER T/F
// ============================================
function renderTF(questions) {
  const container = document.getElementById('tf-questions');
  container.innerHTML = '';

  if (questions.length === 0) {
    document.getElementById('section-tf').style.display = 'none';
    return;
  }

  questions.forEach((q) => {
    const card = document.createElement('div');
    card.className = 'question-card';
    card.id = `tf-${q.id}`;

    card.innerHTML = `
      <div class="question-card-header">
        <span class="question-number">Question ${q.id}</span>
        <span class="question-points">${q.points} pts</span>
      </div>
      <div class="question-topic">${q.topic}</div>
      <div class="question-text">${q.statement}</div>
      <div class="tf-buttons">
        <button class="tf-btn" data-qid="${q.id}" data-value="true" onclick="selectTF(${q.id}, true)">✓ True</button>
        <button class="tf-btn" data-qid="${q.id}" data-value="false" onclick="selectTF(${q.id}, false)">✗ False</button>
      </div>
    `;

    container.appendChild(card);
  });
}

// ============================================
// RENDER SHORT ANSWER
// ============================================
function renderShort(questions) {
  const container = document.getElementById('short-questions');
  container.innerHTML = '';

  if (questions.length === 0) {
    document.getElementById('section-short').style.display = 'none';
    return;
  }

  questions.forEach((q) => {
    const card = document.createElement('div');
    card.className = 'question-card';
    card.id = `short-${q.id}`;

    card.innerHTML = `
      <div class="question-card-header">
        <span class="question-number">Question ${q.id}</span>
        <span class="question-points">${q.points} pts</span>
      </div>
      <div class="question-topic">${q.topic}</div>
      <div class="question-text">${q.question}</div>
      <textarea class="short-answer-input" data-qid="${q.id}"
        placeholder="Type your answer here..."
        oninput="updateShortAnswer(${q.id}, this.value)"></textarea>
    `;

    container.appendChild(card);
  });
}

// ============================================
// SELECTION HANDLERS
// ============================================
function selectMCQ(qid, letter) {
  userAnswers.mcq[qid] = letter;

  // Update UI
  document.querySelectorAll(`#mcq-${qid} .option-btn`).forEach(btn => {
    btn.classList.remove('selected');
    if (btn.dataset.letter === letter) btn.classList.add('selected');
  });

  updateProgress();
}

function selectTF(qid, value) {
  userAnswers.tf[qid] = value;

  // Update UI
  const card = document.getElementById(`tf-${qid}`);
  card.querySelectorAll('.tf-btn').forEach(btn => {
    btn.classList.remove('selected-true', 'selected-false');
    const btnVal = btn.dataset.value === 'true';
    if (btnVal === value) {
      btn.classList.add(value ? 'selected-true' : 'selected-false');
    }
  });

  updateProgress();
}

function updateShortAnswer(qid, value) {
  userAnswers.short[qid] = value.trim();
  updateProgress();
}

// ============================================
// PROGRESS
// ============================================
function updateProgress() {
  const mcqTotal = (testData.questions.multiple_choice || []).length;
  const tfTotal = (testData.questions.true_false || []).length;
  const shortTotal = (testData.questions.short_answer || []).length;

  const mcqDone = Object.keys(userAnswers.mcq).length;
  const tfDone = Object.keys(userAnswers.tf).length;
  const shortDone = Object.values(userAnswers.short).filter(v => v.length > 0).length;

  const total = mcqTotal + tfTotal + shortTotal;
  const done = mcqDone + tfDone + shortDone;

  document.getElementById('progress-info').textContent = `${done}/${total} answered`;

  const pct = total > 0 ? (done / total) * 100 : 0;
  document.getElementById('progress-bar').style.width = pct + '%';

  // Enable submit when all MCQ and TF are answered (short answer is optional)
  const allRequired = mcqDone >= mcqTotal && tfDone >= tfTotal;
  document.getElementById('submit-btn').disabled = !allRequired;
}

// ============================================
// SUBMIT TEST
// ============================================
document.getElementById('submit-btn').addEventListener('click', () => {
  if (!confirm('Are you sure you want to submit? MCQ and T/F will be graded automatically.')) return;
  gradeAndShowResults();
});

function gradeAndShowResults() {
  const scoring = testData.scoring || {};
  const mcqQuestions = testData.questions.multiple_choice || [];
  const tfQuestions = testData.questions.true_false || [];
  const shortQuestions = testData.questions.short_answer || [];

  // Grade MCQ
  let mcqCorrect = 0;
  const mcqResults = mcqQuestions.map(q => {
    const userAns = userAnswers.mcq[q.id] || '';
    const isCorrect = userAns === q.answer;
    if (isCorrect) mcqCorrect++;
    return { ...q, userAnswer: userAns, isCorrect };
  });
  const mcqScore = mcqCorrect * (scoring.mcq_section?.points_each || 0);

  // Grade TF
  let tfCorrect = 0;
  const tfResults = tfQuestions.map(q => {
    const userAns = userAnswers.tf[q.id];
    const isCorrect = userAns === q.answer;
    if (isCorrect) tfCorrect++;
    return { ...q, userAnswer: userAns, isCorrect };
  });
  const tfScore = tfCorrect * (scoring.tf_section?.points_each || 0);

  // Short answer — not auto-graded
  const shortResults = shortQuestions.map(q => ({
    ...q,
    userAnswer: userAnswers.short[q.id] || '(No answer)',
  }));

  // Calculate totals
  const autoScore = mcqScore + tfScore;
  const totalPossible = scoring.total_score || 10;

  // Update results UI
  document.getElementById('results-score-value').textContent = formatScore(autoScore);
  document.getElementById('results-score-total').textContent = `/ ${totalPossible}`;

  const pct = (autoScore / totalPossible) * 100;
  let subtitle = '';
  if (pct >= 90) subtitle = 'Excellent work! 🎉';
  else if (pct >= 70) subtitle = 'Good job! Keep it up 👍';
  else if (pct >= 50) subtitle = 'Not bad, but room for improvement 📚';
  else subtitle = 'Keep studying, you\'ll get there! 💪';
  document.getElementById('results-subtitle').textContent = subtitle;

  // Score circle color
  const circle = document.getElementById('results-score-circle');
  if (pct >= 70) circle.style.borderColor = 'var(--success)';
  else if (pct >= 50) circle.style.borderColor = 'var(--warning)';
  else circle.style.borderColor = 'var(--error)';

  // Breakdown cards
  document.getElementById('breakdown-mcq-score').textContent =
    `${mcqCorrect}/${mcqQuestions.length} (${formatScore(mcqScore)} pts)`;
  document.getElementById('breakdown-tf-score').textContent =
    `${tfCorrect}/${tfQuestions.length} (${formatScore(tfScore)} pts)`;
  document.getElementById('breakdown-short-score').textContent =
    `Self-graded`;

  // Render review
  renderReview(mcqResults, tfResults, shortResults, scoring);

  showScreen('results-screen');
}

// ============================================
// RENDER REVIEW
// ============================================
function renderReview(mcqResults, tfResults, shortResults, scoring) {
  const container = document.getElementById('review-container');
  container.innerHTML = '';

  // MCQ Review
  if (mcqResults.length > 0) {
    container.innerHTML += '<h3 style="margin-bottom:1rem;font-size:1.1rem;">📋 Multiple Choice</h3>';
    mcqResults.forEach(q => {
      const statusClass = q.isCorrect ? 'correct' : 'incorrect';
      const statusText = q.isCorrect ? '✓ Correct' : '✗ Incorrect';
      const userOption = q.options.find(o => o.startsWith(q.userAnswer)) || 'No answer';
      const correctOption = q.options.find(o => o.startsWith(q.answer)) || q.answer;

      container.innerHTML += `
        <div class="review-card ${statusClass}">
          <span class="review-status ${statusClass}">${statusText}</span>
          <div class="review-question">${q.question}</div>
          <div class="review-detail">Your answer: <strong>${userOption}</strong></div>
          ${!q.isCorrect ? `<div class="review-detail">Correct answer: <strong>${correctOption}</strong></div>` : ''}
        </div>
      `;
    });
  }

  // TF Review
  if (tfResults.length > 0) {
    container.innerHTML += '<h3 style="margin:2rem 0 1rem;font-size:1.1rem;">✅ True / False</h3>';
    tfResults.forEach(q => {
      const statusClass = q.isCorrect ? 'correct' : 'incorrect';
      const statusText = q.isCorrect ? '✓ Correct' : '✗ Incorrect';
      const userStr = q.userAnswer === true ? 'True' : q.userAnswer === false ? 'False' : 'No answer';
      const correctStr = q.answer ? 'True' : 'False';

      container.innerHTML += `
        <div class="review-card ${statusClass}">
          <span class="review-status ${statusClass}">${statusText}</span>
          <div class="review-question">${q.statement}</div>
          <div class="review-detail">Your answer: <strong>${userStr}</strong></div>
          ${!q.isCorrect ? `<div class="review-detail">Correct answer: <strong>${correctStr}</strong></div>` : ''}
          <div class="review-explanation">${q.explanation}</div>
        </div>
      `;
    });
  }

  // Short Answer Review
  if (shortResults.length > 0) {
    container.innerHTML += '<h3 style="margin:2rem 0 1rem;font-size:1.1rem;">✍️ Short Answer</h3>';
    shortResults.forEach(q => {
      const cardId = `short-review-${q.id}`;
      container.innerHTML += `
        <div class="review-card self-grade" id="${cardId}">
          <span class="review-status self-grade">📝 Self-grade</span>
          <div class="review-question">${q.question}</div>
          <div class="review-detail">Your answer: <strong>${escapeHtml(q.userAnswer)}</strong></div>
          <div class="review-detail">Model answer: <strong>${q.answer}</strong></div>
          <div class="self-grade-prompt" id="prompt-${q.id}">
            <span class="prompt-text">Did you get this right?</span>
            <div class="prompt-buttons">
              <button class="btn btn-success btn-sm" onclick="selfGrade(${q.id}, true, ${q.points})">Yes ✓</button>
              <button class="btn btn-error btn-sm" onclick="selfGrade(${q.id}, false, ${q.points})">No ✗</button>
            </div>
          </div>
        </div>
      `;
    });
  }
}

// ============================================
// SELF GRADING (SHORT ANSWER)
// ============================================
function selfGrade(qid, gotRight, points) {
  shortSelfGrades[qid] = gotRight;

  // Replace the prompt with result
  const prompt = document.getElementById(`prompt-${qid}`);
  if (gotRight) {
    prompt.outerHTML = `<div class="self-grade-resolved yes">✓ You marked this as correct (+${points} pts)</div>`;
  } else {
    prompt.outerHTML = `<div class="self-grade-resolved no">✗ You marked this as incorrect (0 pts)</div>`;
  }

  // Update card style
  const card = document.getElementById(`short-review-${qid}`);
  card.classList.remove('self-grade');
  card.classList.add(gotRight ? 'correct' : 'incorrect');

  // Update total score
  updateFinalScore();
}

function updateFinalScore() {
  const scoring = testData.scoring || {};
  const mcqQuestions = testData.questions.multiple_choice || [];
  const tfQuestions = testData.questions.true_false || [];

  // Re-calculate auto scores
  let mcqScore = 0;
  mcqQuestions.forEach(q => {
    if (userAnswers.mcq[q.id] === q.answer) mcqScore += q.points;
  });

  let tfScore = 0;
  tfQuestions.forEach(q => {
    if (userAnswers.tf[q.id] === q.answer) tfScore += q.points;
  });

  // Add self-graded short answer points
  let shortScore = 0;
  const shortQuestions = testData.questions.short_answer || [];
  shortQuestions.forEach(q => {
    if (shortSelfGrades[q.id] === true) shortScore += q.points;
  });

  const total = mcqScore + tfScore + shortScore;
  document.getElementById('results-score-value').textContent = formatScore(total);

  // Update short breakdown
  const shortCorrect = Object.values(shortSelfGrades).filter(v => v === true).length;
  const shortTotal = shortQuestions.length;
  const graded = Object.keys(shortSelfGrades).length;
  document.getElementById('breakdown-short-score').textContent =
    graded === shortTotal
      ? `${shortCorrect}/${shortTotal} (${formatScore(shortScore)} pts)`
      : `${graded}/${shortTotal} graded`;

  // Update circle color based on final score
  const totalPossible = scoring.total_score || 10;
  const pct = (total / totalPossible) * 100;
  const circle = document.getElementById('results-score-circle');
  if (pct >= 70) circle.style.borderColor = 'var(--success)';
  else if (pct >= 50) circle.style.borderColor = 'var(--warning)';
  else circle.style.borderColor = 'var(--error)';
}

// ============================================
// RETAKE
// ============================================
document.getElementById('retake-btn').addEventListener('click', () => {
  initTest();
});

// ============================================
// UTILS
// ============================================
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
