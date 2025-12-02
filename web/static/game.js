/**
 * Game Logic for Terminal Poker Web
 */

// State
let socket = null;
let sessionId = null;
let currentRoundState = null;
let myHoleCards = [];
let myNickname = 'Unknown';

import { i18n } from '/static/localization.js';

// DOM Elements
const terminalOutput = document.getElementById('terminal-output');
const controlsArea = document.getElementById('controls-area');
const actionButtons = document.querySelectorAll('.action-btn');
const raiseControls = document.getElementById('raise-controls');
const raiseAmountInput = document.getElementById('raise-amount');
const myCardsDisplay = document.getElementById('my-cards');
const myStackDisplay = document.getElementById('my-stack');
const myBetDisplay = document.getElementById('my-bet');
const potDisplay = document.getElementById('pot-display');
const communityCardsDisplay = document.getElementById('community-cards');
const winProbDisplay = document.getElementById('win-prob');
const probDisplayContainer = document.getElementById('prob-display');
const handStrengthDisplay = document.getElementById('hand-strength-display');
const handStrengthContainer = document.getElementById('hand-strength-container');


const btnNextRound = document.getElementById('btn-next-round');
const btnQuitGame = document.getElementById('btn-quit-game');
const btnHeaderQuit = document.getElementById('btn-header-quit');
const btnHeaderNewGame = document.getElementById('btn-header-new-game');
const endRoundControls = document.getElementById('end-round-controls');

const actionButtonsContainer = document.querySelector('.action-buttons');

// Modal Elements
const customModal = document.getElementById('custom-modal');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const btnModalCancel = document.getElementById('btn-modal-cancel');
const btnModalConfirm = document.getElementById('btn-modal-confirm');

// Elimination Modal Elements
const btnElimNewGame = document.getElementById('btn-elim-new-game');
const btnElimSimulate = document.getElementById('btn-simulate');
const btnElimQuit = document.getElementById('btn-quit-game'); // Reusing the main quit button

let onModalConfirm = null;

// Initialize
init();

function init() {
    // Get session_id from URL
    const urlParams = new URLSearchParams(window.location.search);
    sessionId = urlParams.get('session_id');

    if (!sessionId) {
        alert(i18n.get('MSG_NO_SESSION'));
        window.location.href = '/static/index.html';
        return;
    }

    // Get nickname from local storage
    const storedNick = localStorage.getItem('poker_nickname');
    if (storedNick) {
        myNickname = storedNick;
    }

    // Clear i18n cache to ensure new keys are loaded
    Object.keys(localStorage).forEach(key => {
        if (key.startsWith('i18n_')) {
            localStorage.removeItem(key);
        }
    });

    // Initialize i18n
    i18n.init('pt-br').then(() => {
        connectWebSocket(sessionId);
    });
}

// Event Listeners
document.getElementById('btn-fold').addEventListener('click', () => sendAction('fold', 0));
document.getElementById('btn-call').addEventListener('click', () => sendAction('call', currentRoundState?.amount_to_call || 0));
document.getElementById('btn-allin').addEventListener('click', () => sendAction('raise', -1));

btnHeaderQuit.addEventListener('click', () => {
    btnQuitGame.click(); // Reuse the same logic
});

btnHeaderNewGame.addEventListener('click', () => {
    showModal(i18n.get('MODAL_NEW_GAME_TITLE'), i18n.get('MODAL_NEW_GAME_MSG'), () => {
        startNewGame();
    });
});

btnNextRound.addEventListener('click', () => {
    sendAction('next_round', 0);
    endRoundControls.classList.add('hidden');
    controlsArea.classList.add('disabled');
});

btnQuitGame.addEventListener('click', () => {
    showModal(i18n.get('MODAL_QUIT_TITLE'), i18n.get('MODAL_QUIT_MSG'), () => {
        sendAction('quit', 0);
        // Give a small delay for server to process and save, then redirect
        setTimeout(() => {
            window.location.href = '/static/index.html';
        }, 500);
    });
});

// Modal Event Listeners
btnModalCancel.addEventListener('click', hideModal);
btnModalConfirm.addEventListener('click', () => {
    if (onModalConfirm) onModalConfirm();
    hideModal();
});

// Elimination Modal Listeners
if (btnElimSimulate) {
    btnElimSimulate.addEventListener('click', () => {
        sendAction('simulate', 0);
        // Hide simulate button after clicking to prevent multiple clicks
        btnElimSimulate.classList.add('hidden');
        logToTerminal(i18n.get('BTN_SIMULATE') + '...', 'system');
    });
}

if (btnElimNewGame) {
    btnElimNewGame.addEventListener('click', () => {
        showModal(i18n.get('MODAL_NEW_GAME_TITLE'), i18n.get('MODAL_NEW_GAME_MSG'), () => {
            startNewGame();
        });
    });
}

function showModal(title, message, onConfirm) {
    modalTitle.textContent = title;
    modalMessage.textContent = message;
    onModalConfirm = onConfirm;
    customModal.classList.remove('hidden');
}

function hideModal() {
    customModal.classList.add('hidden');
    onModalConfirm = null;
}

document.getElementById('btn-raise').addEventListener('click', showRaiseControls);
document.getElementById('btn-cancel-raise').addEventListener('click', hideRaiseControls);
document.getElementById('btn-confirm-raise').addEventListener('click', () => {
    const amount = parseInt(raiseAmountInput.value);
    sendAction('raise', amount);
    hideRaiseControls();
});

raiseAmountInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('btn-confirm-raise').click();
    }
    e.stopPropagation(); // Prevent global shortcuts
});

// Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
    // Ignore shortcuts if typing in an input
    if (document.activeElement.tagName === 'INPUT') return;

    // Allow 'n' for next round if visible
    if (e.key.toLowerCase() === 'n' && !endRoundControls.classList.contains('hidden')) {
        btnNextRound.click();
        return;
    }

    // Allow 'q' for quit if visible
    if (e.key.toLowerCase() === 'q' && !endRoundControls.classList.contains('hidden')) {
        btnQuitGame.click();
        return;
    }

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
        logToTerminal(i18n.get('MSG_CONNECTED'), 'system');
    };

    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleGameMessage(message.type, message.data);
    };

    socket.onclose = () => {
        logToTerminal(i18n.get('MSG_CONN_LOST'), 'error');
        controlsArea.classList.add('disabled');
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        logToTerminal(i18n.get('MSG_CONN_ERROR'), 'error');
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
            parseCommunityCardsFromLog(data);
            break;

        case 'game_start':
            break;

        case 'round_start_data':
            myHoleCards = data.hole_cards;
            renderCards(myHoleCards);
            renderCommunityCards([]); // Clear community cards for new round
            break;

        case 'street_start':
            handleStreetStart(data);
            break;

        case 'game_update':
            handleGameUpdate(data);
            break;

        case 'action_required':
            handleActionRequired(data);
            break;

        case 'round_result_data':
            // Only disable controls if we are NOT in the elimination/end-round state
            if (endRoundControls.classList.contains('hidden')) {
                controlsArea.classList.add('disabled');
                hideRaiseControls();
            }
            break;

        case 'wait_for_next_round':
            handleWaitForNextRound();
            break;

        case 'game_over':
            handleGameOver(data);
            break;

        case 'notification':
            logToTerminal(data, 'success');
            break;

        case 'error':
            logToTerminal(data, 'error');
            break;

        case 'player_eliminated':
            handlePlayerEliminated(data);
            break;
    }
}

function handleGameOver(data) {
    controlsArea.classList.remove('disabled'); // Enable controls so buttons can be clicked
    actionButtonsContainer.classList.add('hidden'); // Hide fold/call/raise
    endRoundControls.classList.remove('hidden'); // Show end round controls
    endRoundControls.style.display = 'flex';

    // Hide Next Round and Simulate
    btnNextRound.classList.add('hidden');
    btnNextRound.style.display = 'none';
    if (btnElimSimulate) {
        btnElimSimulate.classList.add('hidden');
        btnElimSimulate.style.display = 'none';
    }

    // Show New Game and Quit
    if (btnElimNewGame) {
        btnElimNewGame.classList.remove('hidden');
        btnElimNewGame.style.display = 'inline-block';
    }
    btnQuitGame.classList.remove('hidden');
    btnQuitGame.style.display = 'inline-block';

    logToTerminal(i18n.get('MSG_GAME_OVER') || 'Game Over', 'system');
}

function handlePlayerEliminated(data) {
    console.log('Player Eliminated Data:', data);
    controlsArea.classList.remove('disabled'); // Enable controls to allow interaction with buttons
    hideRaiseControls();

    // Hide Next Round button
    btnNextRound.classList.add('hidden');
    btnNextRound.style.display = 'none'; // Force hide

    // Show Simulate and New Game buttons
    if (btnElimSimulate) {
        btnElimSimulate.classList.remove('hidden');
        btnElimSimulate.style.display = 'inline-block'; // Force show
    }
    if (btnElimNewGame) {
        btnElimNewGame.classList.remove('hidden');
        btnElimNewGame.style.display = 'inline-block'; // Force show
    }

    // Ensure controls area is visible
    actionButtonsContainer.classList.add('hidden');
    endRoundControls.classList.remove('hidden');
    endRoundControls.style.display = 'flex'; // Ensure container is flex

    // Log elimination to terminal
    logToTerminal(i18n.get('MODAL_ELIMINATED_MSG') || 'You have been eliminated.', 'error');

    // Clear player cards and stack
    renderCards([]);
    if (myStackDisplay) myStackDisplay.textContent = '0';
}

function handleWaitForNextRound() {
    controlsArea.classList.remove('disabled');
    actionButtonsContainer.classList.add('hidden');
    endRoundControls.classList.remove('hidden');

    // Reset buttons to normal state (Next Round visible, others hidden)
    btnNextRound.classList.remove('hidden');
    btnNextRound.style.display = ''; // Reset inline style

    if (btnElimSimulate) {
        btnElimSimulate.classList.add('hidden');
        btnElimSimulate.style.display = ''; // Reset inline style
    }
    if (btnElimNewGame) {
        btnElimNewGame.classList.add('hidden');
        btnElimNewGame.style.display = ''; // Reset inline style
    }

    btnNextRound.focus();
}

function handleActionRequired(data) {
    currentRoundState = data.round_state;

    controlsArea.classList.remove('disabled');
    endRoundControls.classList.add('hidden');
    actionButtonsContainer.classList.remove('hidden');

    if (data.win_probability) {
        probDisplayContainer.classList.remove('hidden');
        winProbDisplay.textContent = (data.win_probability * 100).toFixed(1) + '%';
    } else {
        if (!data.win_probability) {
            probDisplayContainer.classList.add('hidden');
        }
    }

    if (data.hand_strength) {
        handStrengthContainer.classList.remove('hidden');
        handStrengthDisplay.textContent = data.hand_strength;
    } else {
        handStrengthContainer.classList.add('hidden');
    }

    actionButtons.forEach(btn => {
        if (btn === btnNextRound) return;

        const action = btn.dataset.action;
        let checkAction = action;
        if (action === 'allin') checkAction = 'raise';

        const isValid = data.valid_actions.some(a => a.action === checkAction);
        btn.disabled = !isValid;
    });

    updateMyStackDisplay(currentRoundState);
    updateMyBetDisplay(currentRoundState);

    const raiseAction = data.valid_actions.find(a => a.action === 'raise');
    if (raiseAction) {
        const minRaise = raiseAction.amount.min;
        const maxRaise = raiseAction.amount.max;

        raiseAmountInput.value = minRaise;
        raiseAmountInput.min = minRaise;
        raiseAmountInput.max = maxRaise;
    }

    const callAction = data.valid_actions.find(a => a.action === 'call');
    const btnCall = document.getElementById('btn-call');
    if (callAction) {
        currentRoundState.amount_to_call = callAction.amount;
        if (callAction.amount === 0) {
            btnCall.textContent = i18n.get('BTN_CHECK');
        } else {
            btnCall.textContent = `${i18n.get('BTN_CALL').replace('(C)', '')} {${callAction.amount}} (C)`;
        }
    } else {
        btnCall.textContent = i18n.get('BTN_CALL');
    }

    if (currentRoundState.community_card) {
        renderCommunityCards(currentRoundState.community_card);
    }

    if (currentRoundState.pot) {
        updatePotDisplay(currentRoundState.pot);
    }

    scrollToBottom();
}

function sendAction(action, amount) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    if (action !== 'next_round') {
        controlsArea.classList.add('disabled');
    }

    socket.send(JSON.stringify({
        type: 'action',
        data: {
            action: action,
            amount: parseInt(amount)
        }
    }));
}

function ansiToHtml(text) {
    if (!text) return '';

    const colors = {
        '30': 'black', '31': '#ff5555', '32': '#50fa7b', '33': '#f1fa8c',
        '34': '#bd93f9', '35': '#ff79c6', '36': '#8be9fd', '37': '#f8f8f2',
        '90': '#6272a4'
    };

    let html = text.replace(/\x1B\[(\d+)m/g, (match, code) => {
        if (code === '0') return '</span>';
        if (code === '1') return '<span style="font-weight:bold">';
        if (code === '2') return '<span style="opacity:0.6">';
        if (colors[code]) return `<span style="color:${colors[code]}">`;
        return '';
    });

    while (html.includes('<span')) {
        if (!html.includes('</span>')) {
            html += '</span>';
        } else {
            break;
        }
    }

    return html;
}

function logToTerminal(text, type = 'action') {
    const div = document.createElement('div');
    div.className = `line ${type}`;
    if (type === 'raw') {
        div.innerHTML = ansiToHtml(text);
    } else {
        div.textContent = text;
    }
    terminalOutput.appendChild(div);
    scrollToBottom();
}

function scrollToBottom() {
    if (window.innerWidth <= 768) {
        setTimeout(() => {
            const y = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, document.body.offsetHeight, document.documentElement.offsetHeight, document.body.scrollTop + document.documentElement.scrollTop);
            window.scrollTo(0, y + 100); // Add extra buffer
        }, 100);
    } else {
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
}

function renderCards(cards) {
    myCardsDisplay.innerHTML = '';
    cards.forEach(card => {
        const div = document.createElement('div');
        const isRed = card[0] === 'H' || card[0] === 'D' || card.includes('♥') || card.includes('♦');
        div.className = `playing-card ${isRed ? 'red' : ''}`;
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
    raiseAmountInput.focus();
}

function hideRaiseControls() {
    raiseControls.classList.add('hidden');
}

function handleStreetStart(data) {
    if (data.round_state) {
        currentRoundState = data.round_state;
        if (currentRoundState.community_card) {
            renderCommunityCards(currentRoundState.community_card);
        }
        if (currentRoundState.pot) {
            updatePotDisplay(currentRoundState.pot);
        }
        updateMyBetDisplay(currentRoundState);
        updateMyStackDisplay(currentRoundState);
    }
}

function handleGameUpdate(data) {
    if (data.round_state) {
        currentRoundState = data.round_state;
        if (currentRoundState.community_card) {
            renderCommunityCards(currentRoundState.community_card);
        }
        if (currentRoundState.pot) {
            updatePotDisplay(currentRoundState.pot);
        }
        updateMyBetDisplay(currentRoundState);
        updateMyStackDisplay(currentRoundState);
    }
}

function renderCommunityCards(cards) {
    communityCardsDisplay.innerHTML = '';
    cards.forEach(card => {
        const div = document.createElement('div');
        const isRed = card[0] === 'H' || card[0] === 'D' || card.includes('♥') || card.includes('♦');
        div.className = `playing-card ${isRed ? 'red' : ''}`;
        div.textContent = getCardSymbol(card);
        communityCardsDisplay.appendChild(div);
    });
}

function updatePotDisplay(potData) {
    let totalPot = 0;
    if (potData.main) {
        totalPot += potData.main.amount;
    }
    if (potData.side && Array.isArray(potData.side)) {
        potData.side.forEach(sidePot => {
            totalPot += sidePot.amount;
        });
    }
    potDisplay.textContent = totalPot;
}

function updateMyBetDisplay(roundState) {
    if (!roundState || !roundState.action_histories) {
        myBetDisplay.textContent = '0';
        return;
    }

    let totalBet = 0;

    // Simplified logic: sum all my contributions in the round
    // This is an approximation as PyPokerEngine history is complex
    ['preflop', 'flop', 'turn', 'river'].forEach(streetName => {
        const actions = roundState.action_histories[streetName];
        if (actions) {
            let myStreetBet = 0;
            let myUuid = null;
            if (roundState.seats) {
                const mySeat = roundState.seats.find(s => s.name === myNickname);
                if (mySeat) myUuid = mySeat.uuid;
            }

            actions.forEach(action => {
                if (action.uuid === myUuid) {
                    if (['SMALLBLIND', 'BIGBLIND'].includes(action.action)) {
                        myStreetBet += action.amount;
                    } else if (action.action === 'CALL') {
                        if (action.amount > myStreetBet) {
                            myStreetBet = action.amount;
                        }
                    } else if (action.action === 'RAISE') {
                        if (action.amount > myStreetBet) {
                            myStreetBet = action.amount;
                        }
                    }
                }
            });
            totalBet += myStreetBet;
        }
    });

    myBetDisplay.textContent = totalBet;
}

function updateMyStackDisplay(roundState) {
    if (roundState && roundState.seats) {
        const mySeat = roundState.seats.find(seat => seat.name === myNickname);
        if (mySeat) {
            myStackDisplay.textContent = mySeat.stack;
        }
    }
}

async function startNewGame() {
    const storedConfig = localStorage.getItem('poker_config');
    if (!storedConfig) {
        alert(i18n.get('MSG_NO_CONFIG'));
        window.location.href = '/static/index.html';
        return;
    }

    try {
        const config = JSON.parse(storedConfig);

        btnHeaderNewGame.disabled = true;
        btnHeaderNewGame.textContent = '...';

        const response = await fetch('/api/game/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (!response.ok) throw new Error('Failed to create game');

        const data = await response.json();
        const newSessionId = data.session_id;

        window.location.href = `/static/game.html?session_id=${newSessionId}`;

    } catch (error) {
        console.error(error);
        alert('Error starting new game: ' + error.message);
        btnHeaderNewGame.disabled = false;
        btnHeaderNewGame.textContent = 'New Game';
    }
}

function parseCommunityCardsFromLog(text) {
    if (!text) return;

    const cleanText = text.replace(/\x1B\[[0-9;]*[mK]/g, '');
    const lines = cleanText.split('\n');

    let lastCardLine = null;
    for (let i = lines.length - 1; i >= 0; i--) {
        if (lines[i].includes('Community cards:')) {
            lastCardLine = lines[i];
            break;
        }
    }

    if (lastCardLine) {
        const parts = lastCardLine.split('Community cards:');
        if (parts.length > 1) {
            const cardsPart = parts[1].trim();
            const potentialCards = cardsPart.split(/\s+/);

            const cards = potentialCards.filter(c => {
                if (c.length < 2 || c.length > 3) return false;
                if (['Pot', '->'].includes(c)) return false;
                if (!isNaN(c)) return false;
                return true;
            });

            if (cards.length > 0) {
                renderCommunityCards(cards);
            }
        }
    }
}

// Mobile Header Scroll Logic
let lastScrollTop = 0;
const headerBar = document.querySelector('.header-bar');
const handInfo = document.querySelector('.hand-info');
const delta = 5;
const headerHeight = 54; // Approx header height

window.addEventListener('scroll', () => {
    const scrollTop = Math.max(0, window.scrollY || window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop);

    // Debug log
    // console.log('Scroll:', scrollTop, 'Last:', lastScrollTop, 'Delta:', Math.abs(lastScrollTop - scrollTop));

    // Make sure they scroll more than delta
    if (Math.abs(lastScrollTop - scrollTop) <= delta) return;

    // If they scrolled down and are past the navbar, add class .header-hidden.
    if (scrollTop > lastScrollTop && scrollTop > headerHeight) {
        // Scroll Down
        // console.log('Hiding header');
        if (headerBar) headerBar.classList.add('header-hidden');
        if (handInfo) handInfo.classList.add('moved-up');
    } else {
        // Scroll Up
        // Simplified check: just show it if we are scrolling up.
        // The previous check (scrollTop + window.innerHeight < document.body.scrollHeight)
        // can fail on Safari due to dynamic address bar resizing.
        if (headerBar) headerBar.classList.remove('header-hidden');
        if (handInfo) handInfo.classList.remove('moved-up');
    }

    lastScrollTop = scrollTop;
}, { passive: true });
