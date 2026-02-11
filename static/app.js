/**
 * Prompt Injection Lab — Frontend Logic
 */

// ── State ────────────────────────────────────────────────────────────────────
let levels = [];
let currentLevel = null;
let chatHistories = {};  // level_id -> [{role, content, type}]
let hintIndices = {};    // level_id -> next hint index
let sending = false;

// ── DOM Elements ─────────────────────────────────────────────────────────────
const sidebar = document.getElementById('level-list');
const progressCounter = document.getElementById('progress-counter');
const levelName = document.getElementById('level-name');
const levelDescription = document.getElementById('level-description');
const levelDifficulty = document.getElementById('level-difficulty');
const levelSolvedBadge = document.getElementById('level-solved-badge');
const defenseTags = document.getElementById('defense-tags');
const chatArea = document.getElementById('chat-area');
const inputArea = document.getElementById('input-area');
const messageInput = document.getElementById('message-input');
const btnSend = document.getElementById('btn-send');
const btnHint = document.getElementById('btn-hint');
const btnResetAll = document.getElementById('btn-reset-all');
const attemptCounter = document.getElementById('attempt-counter');
const victoryOverlay = document.getElementById('victory-overlay');
const victorySecret = document.getElementById('victory-secret');
const victoryAttempts = document.getElementById('victory-attempts');
const btnVictoryClose = document.getElementById('btn-victory-close');

// ── Defense display names ────────────────────────────────────────────────────
const DEFENSE_LABELS = {
    input_filter: 'Input Filter',
    output_filter: 'Output Filter',
    sandwich: 'Sandwich Defense',
    few_shot: 'Few-Shot Resistance',
    judge: 'Judge LLM',
};

// ── Init ─────────────────────────────────────────────────────────────────────
async function init() {
    await loadLevels();
    renderSidebar();
    bindEvents();
}

async function loadLevels() {
    const res = await fetch('/api/levels');
    levels = await res.json();
}

// ── Sidebar ──────────────────────────────────────────────────────────────────
function renderSidebar() {
    const solved = levels.filter(l => l.solved).length;
    progressCounter.textContent = `${solved} / ${levels.length} solved`;

    sidebar.innerHTML = levels.map(level => {
        const icon = level.solved ? '\u2705' : '\uD83D\uDD12';
        const activeClass = currentLevel && currentLevel.id === level.id ? 'active' : '';
        return `
            <div class="level-item ${activeClass}" data-level-id="${level.id}">
                <span class="level-icon">${icon}</span>
                <div class="level-info">
                    <div class="level-title">${level.id}. ${level.name}</div>
                </div>
                <span class="level-diff diff-${level.difficulty}">${level.difficulty}</span>
            </div>
        `;
    }).join('');
}

// ── Level Selection ──────────────────────────────────────────────────────────
function selectLevel(levelId) {
    currentLevel = levels.find(l => l.id === levelId);
    if (!currentLevel) return;

    // Init chat history for this level if needed
    if (!chatHistories[levelId]) {
        chatHistories[levelId] = [];
    }
    if (hintIndices[levelId] === undefined) {
        hintIndices[levelId] = 0;
    }

    // Update header
    levelName.textContent = `Level ${currentLevel.id}: ${currentLevel.name}`;
    levelDescription.textContent = currentLevel.description;

    // Difficulty badge
    levelDifficulty.textContent = currentLevel.difficulty;
    levelDifficulty.className = `px-2 py-0.5 rounded text-xs font-bold diff-${currentLevel.difficulty}`;
    levelDifficulty.classList.remove('hidden');

    // Solved badge
    if (currentLevel.solved) {
        levelSolvedBadge.classList.remove('hidden');
    } else {
        levelSolvedBadge.classList.add('hidden');
    }

    // Defense tags
    if (currentLevel.defenses.length > 0) {
        defenseTags.innerHTML = currentLevel.defenses.map(d =>
            `<span class="defense-tag">${DEFENSE_LABELS[d] || d}</span>`
        ).join('');
    } else {
        defenseTags.innerHTML = '<span class="text-xs text-gray-600 italic">No defenses active</span>';
    }

    // Show input area
    inputArea.classList.remove('hidden');
    updateAttemptCounter();

    // Render chat
    renderChat();
    renderSidebar();

    // Focus input
    messageInput.focus();
}

function updateAttemptCounter() {
    if (!currentLevel) return;
    const count = currentLevel.attempts || 0;
    attemptCounter.textContent = count > 0 ? `${count} attempt${count !== 1 ? 's' : ''}` : '';
}

// ── Chat Rendering ───────────────────────────────────────────────────────────
function renderChat() {
    if (!currentLevel) return;
    const history = chatHistories[currentLevel.id] || [];

    if (history.length === 0) {
        chatArea.innerHTML = `
            <div class="msg-system">
                <p>Level ${currentLevel.id} — ${currentLevel.name}</p>
                <p class="mt-1">Extract the hidden secret to solve this challenge.</p>
            </div>
        `;
        chatArea.scrollTop = chatArea.scrollHeight;
        return;
    }

    chatArea.innerHTML = history.map(msg => {
        if (msg.type === 'user') {
            return `<div class="msg-user">
                <div class="msg-label text-blue-400">You</div>
                <div>${escapeHtml(msg.content)}</div>
            </div>`;
        } else if (msg.type === 'assistant') {
            return `<div class="msg-assistant">
                <div class="msg-label text-gray-500">Assistant</div>
                <div>${escapeHtml(msg.content)}</div>
            </div>`;
        } else if (msg.type === 'blocked') {
            return `<div class="msg-blocked">
                <div class="msg-label text-red-400 shield-icon">Blocked</div>
                <div>${escapeHtml(msg.content)}</div>
                ${msg.reason ? `<div class="text-xs mt-1 opacity-70">${escapeHtml(msg.reason)}</div>` : ''}
            </div>`;
        } else if (msg.type === 'hint') {
            return `<div class="msg-hint">
                <div class="msg-label text-yellow-500">Hint</div>
                <div>${escapeHtml(msg.content)}</div>
            </div>`;
        } else if (msg.type === 'victory') {
            return `<div class="msg-system" style="color: #22c55e;">
                <p>\u2705 Secret extracted!</p>
            </div>`;
        }
        return '';
    }).join('');

    chatArea.scrollTop = chatArea.scrollHeight;
}

// ── Send Message ─────────────────────────────────────────────────────────────
async function sendMessage() {
    if (sending || !currentLevel) return;
    const message = messageInput.value.trim();
    if (!message) return;

    sending = true;
    btnSend.disabled = true;
    btnSend.textContent = '...';
    messageInput.value = '';

    const history = chatHistories[currentLevel.id];

    // Add user message
    history.push({ type: 'user', content: message });

    // Add loading indicator
    history.push({ type: 'assistant', content: 'Thinking...' });
    renderChat();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ level_id: currentLevel.id, message }),
        });
        const data = await res.json();

        // Remove loading indicator
        history.pop();

        if (data.blocked) {
            history.push({
                type: 'blocked',
                content: data.response || 'Message blocked by defense.',
                reason: data.block_reason,
            });
        } else {
            history.push({ type: 'assistant', content: data.response });
        }

        // Update attempt count
        currentLevel.attempts = (currentLevel.attempts || 0) + 1;
        updateAttemptCounter();

        // Check for victory
        if (data.secret_leaked) {
            history.push({ type: 'victory', content: '' });
            currentLevel.solved = true;
            renderChat();
            renderSidebar();
            showVictory();
        } else {
            renderChat();
        }

    } catch (err) {
        // Remove loading indicator
        history.pop();
        history.push({
            type: 'blocked',
            content: `Network error: ${err.message}`,
            reason: 'Could not reach the server.',
        });
        renderChat();
    } finally {
        sending = false;
        btnSend.disabled = false;
        btnSend.textContent = 'Send';
        messageInput.focus();
    }
}

// ── Hints ────────────────────────────────────────────────────────────────────
async function requestHint() {
    if (!currentLevel) return;
    const idx = hintIndices[currentLevel.id] || 0;

    const res = await fetch(`/api/levels/${currentLevel.id}/hint?hint_index=${idx}`);
    const data = await res.json();

    const history = chatHistories[currentLevel.id];
    history.push({ type: 'hint', content: data.hint });
    renderChat();

    if (data.has_more) {
        hintIndices[currentLevel.id] = idx + 1;
    }
}

// ── Victory ──────────────────────────────────────────────────────────────────
function showVictory() {
    // We don't have the actual secret on the client — show a generic message
    victorySecret.textContent = 'The secret was in the AI\'s response above!';
    victoryAttempts.textContent = `Solved in ${currentLevel.attempts} attempt${currentLevel.attempts !== 1 ? 's' : ''}`;
    victoryOverlay.style.display = 'flex';
    chatArea.classList.add('chat-victory-flash');
    setTimeout(() => chatArea.classList.remove('chat-victory-flash'), 1000);
}

function hideVictory() {
    victoryOverlay.style.display = 'none';
}

// ── Reset ────────────────────────────────────────────────────────────────────
async function resetAll() {
    if (!confirm('Reset all progress? This cannot be undone.')) return;
    await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
    });
    chatHistories = {};
    hintIndices = {};
    currentLevel = null;
    await loadLevels();
    renderSidebar();
    // Reset main view
    levelName.textContent = 'Select a level';
    levelDescription.textContent = 'Choose a challenge from the sidebar to begin.';
    levelDifficulty.classList.add('hidden');
    levelSolvedBadge.classList.add('hidden');
    defenseTags.innerHTML = '';
    inputArea.classList.add('hidden');
    chatArea.innerHTML = `
        <div class="text-center text-gray-600 mt-20">
            <p class="text-4xl mb-4">\uD83D\uDD12</p>
            <p>Select a level to begin your injection challenge.</p>
        </div>
    `;
}

// ── Utilities ────────────────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ── Event Binding ────────────────────────────────────────────────────────────
function bindEvents() {
    // Level selection
    sidebar.addEventListener('click', (e) => {
        const item = e.target.closest('.level-item');
        if (item) {
            selectLevel(parseInt(item.dataset.levelId));
        }
    });

    // Send message
    btnSend.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
    });

    // Hints
    btnHint.addEventListener('click', requestHint);

    // Reset
    btnResetAll.addEventListener('click', resetAll);

    // Victory close
    btnVictoryClose.addEventListener('click', hideVictory);
    victoryOverlay.addEventListener('click', (e) => {
        if (e.target === victoryOverlay) hideVictory();
    });
}

// ── Boot ─────────────────────────────────────────────────────────────────────
init();
