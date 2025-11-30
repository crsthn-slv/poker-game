/**
 * Game Logic for Terminal Poker Web
 */

// State
let socket = null;
let sessionId = null;
let currentRoundState = null;
let myHoleCards = [];

// DOM Elements
const terminalOutput = document.getElementById('terminal-output');
const controlsArea = document.getElementById('controls-area');
const actionButtons = document.querySelectorAll('.action-btn');
const raiseControls = document.getElementById('raise-controls');
const raiseSlider = document.getElementById('raise-slider');
const raiseAmountInput = document.getElementById('raise-amount');
const myCardsDisplay = document.getElementById('my-cards');
const myStackDisplay = document.getElementById('my-stack');
const winProbDisplay = document.getElementById('win-prob');
const probDisplayContainer = document.getElementById('prob-display');
const displayNick = document.getElementById('display-nick');

// Initialize
init();

function init() {
    // Get session_id from URL
    const urlParams = new URLSearchParams(window.location.search);
    sessionId = urlParams.get('session_id');

    if (!sessionId) {
        alert('No session ID found. Redirecting to home.');
        window.location.href = '/static/index.html';
        return;
    }

    // Get nickname from local storage for display (optional, server knows it)
    const storedNick = localStorage.getItem('poker_nickname');
    if (storedNick) {
        displayNick.textContent = storedNick;
    }

    connectWebSocket(sessionId);
}

// Event Listeners
document.getElementById('btn-fold').addEventListener('click', () => sendAction('fold', 0));
document.getElementById('btn-call').addEventListener('click', () => sendAction('call', currentRoundState?.amount_to_call || 0));
document.getElementById('btn-allin').addEventListener('click', () => sendAction('raise', -1));

document.getElementById('btn-raise').addEventListener('click', showRaiseControls);
document.getElementById('btn-cancel-raise').addEventListener('click', hideRaiseControls);
document.getElementById('btn-confirm-raise').addEventListener('click', () => {
    const amount = parseInt(raiseAmountInput.value);
    sendAction('raise', amount);
    hideRaiseControls();
});

raiseSlider.addEventListener('input', (e) => {
    raiseAmountInput.value = e.target.value;
});

// Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
    if (controlsArea.classList.contains('disabled')) return;

    switch (e.key.toLowerCase()) {
        case 'f': sendAction('fold', 0); break;
        case 'c': sendAction('call', currentRoundState?.amount_to_call || 0); break;
        case 'r': showRaiseControls(); break;
        case 'a': sendAction('raise', -1); break; // All in
    }
});

function connectWebSocket(sid) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${sid}`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        logToTerminal('Connected to game server.', 'system');
        document.getElementById('game-status').textContent = 'STATUS: ONLINE';
        document.getElementById('game-status').style.color = 'var(--success-color)';
    };

    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleGameMessage(message.type, message.data);
    };

    socket.onclose = () => {
        logToTerminal('Connection lost.', 'error');
        document.getElementById('game-status').textContent = 'STATUS: OFFLINE';
        document.getElementById('game-status').style.color = 'var(--danger-color)';
        controlsArea.classList.add('disabled');
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        logToTerminal('Connection error.', 'error');
    };
}

function handleGameMessage(type, data) {
    console.log('Received:', type, data);

    switch (type) {
        case 'status':
            logToTerminal(data, 'system');
            break;

        case 'terminal_output':
            logToTerminal(data, 'raw');
            break;

        case 'game_start':
            break;

        case 'round_start_data':
            myHoleCards = data.hole_cards;
            renderCards(myHoleCards);
            break;

        case 'street_start':
            break;

        case 'game_update':
            break;

        case 'action_required':
            handleActionRequired(data);
            break;

        case 'round_result_data':
            controlsArea.classList.add('disabled');
            hideRaiseControls();
            break;

        case 'game_over':
            controlsArea.classList.add('disabled');
            break;

        case 'notification':
            logToTerminal(data, 'success');
            break;

        case 'error':
            logToTerminal(data, 'error');
            break;
    }
}

function handleActionRequired(data) {
    currentRoundState = data.round_state;

    controlsArea.classList.remove('disabled');

    // Update stats
    // We can try to find our stack from the seat info if needed, but terminal output usually shows it.
    // Let's try to update it if we can match the session/uuid.
    // Since we don't have our UUID easily here without server sending it, we might skip or rely on name.

    if (data.win_probability) {
        probDisplayContainer.classList.remove('hidden');
        winProbDisplay.textContent = (data.win_probability * 100).toFixed(1) + '%';
    } else {
        // If user disabled it in config, backend won't send it or sends null
        if (!data.win_probability) {
            probDisplayContainer.classList.add('hidden');
        }
    }

    // Highlight valid actions
    actionButtons.forEach(btn => {
        const action = btn.dataset.action;
        const isValid = data.valid_actions.some(a => a.action === action);
        btn.disabled = !isValid;
    });

    // Setup raise limits
    const raiseAction = data.valid_actions.find(a => a.action === 'raise');
    if (raiseAction) {
        const minRaise = raiseAction.amount.min;
        const maxRaise = raiseAction.amount.max;

        raiseSlider.min = minRaise;
        raiseSlider.max = maxRaise;
        raiseSlider.value = minRaise;
        raiseAmountInput.value = minRaise;
        raiseAmountInput.min = minRaise;
        raiseAmountInput.max = maxRaise;
    }

    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function sendAction(action, amount) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    controlsArea.classList.add('disabled');

    socket.send(JSON.stringify({
        type: 'action',
        data: {
            action: action,
            amount: parseInt(amount)
        }
    }));
}

function logToTerminal(text, type = 'action') {
    const div = document.createElement('div');
    div.className = `line ${type}`;
    div.textContent = text;
    terminalOutput.appendChild(div);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function renderCards(cards) {
    myCardsDisplay.innerHTML = '';
    cards.forEach(card => {
        const div = document.createElement('div');
        div.className = `playing-card ${card[0] === 'H' || card[0] === 'D' ? 'red' : ''}`;
        div.textContent = getCardSymbol(card);
        myCardsDisplay.appendChild(div);
    });
}

function getCardSymbol(cardStr) {
    const suitMap = { 'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣' };
    const rankMap = { 'T': '10' };

    const suit = suitMap[cardStr[0]] || cardStr[0];
    const rank = rankMap[cardStr[1]] || cardStr[1];

    return `${suit}${rank}`;
}

function showRaiseControls() {
    raiseControls.classList.remove('hidden');
}

function hideRaiseControls() {
    raiseControls.classList.add('hidden');
}
