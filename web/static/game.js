/**
 * Game Logic for Terminal Poker Web (Mobile Refactor)
 */

import { i18n } from '/static/localization.js';

// State
let socket = null;
let sessionId = null;
let currentRoundState = null;
let myHoleCards = [];
let myNickname = 'Unknown';
let myStack = 0;

// DOM Elements - Header
const myCardsDisplay = document.getElementById('my-cards');
const myStackDisplay = document.getElementById('my-stack');
const potDisplay = document.getElementById('pot-display');
const btnMenuToggle = document.getElementById('btn-menu-toggle');

// DOM Elements - Chat
const chatContainer = document.getElementById('chat-container');
const chatContent = document.getElementById('chat-content');

// DOM Elements - Footer
const actionBar = document.getElementById('action-bar');
const btnFold = document.getElementById('btn-fold');
const btnCall = document.getElementById('btn-call');
const btnRaise = document.getElementById('btn-raise');

const raiseControls = document.getElementById('raise-controls');
const raiseAmountInput = document.getElementById('raise-amount');
const btnCancelRaise = document.getElementById('btn-cancel-raise');
const btnConfirmRaise = document.getElementById('btn-confirm-raise');
const btnRaiseMinus = document.getElementById('btn-raise-minus'); // If I added these in HTML? No, I didn't add +/- buttons in HTML step 25. Wait.
// I checked step 25 HTML. I did NOT add +/- buttons. I added `raise-input-wrapper`.
// I will stick to the HTML I wrote.

const btnAllIn = document.getElementById('btn-allin');

const endRoundControls = document.getElementById('end-round-controls');
const btnNextRound = document.getElementById('btn-next-round');
const eliminationControls = document.getElementById('elimination-controls');
const btnSimulate = document.getElementById('btn-simulate');
const btnElimNewGame = document.getElementById('btn-elim-new-game');
const btnQuitGame = document.getElementById('btn-quit-game');

// Modals
const menuModal = document.getElementById('menu-modal');
const btnMenuClose = document.getElementById('btn-menu-close');
const btnHeaderNewGame = document.getElementById('btn-header-new-game');
const btnHeaderQuit = document.getElementById('btn-header-quit');

const customModal = document.getElementById('custom-modal');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const btnModalCancel = document.getElementById('btn-modal-cancel');
const btnModalConfirm = document.getElementById('btn-modal-confirm');

const thinkingIndicator = document.getElementById('thinking-indicator');
const thinkingText = document.getElementById('thinking-text');

let onModalConfirm = null;

// Initialize
init();

function init() {
    const urlParams = new URLSearchParams(window.location.search);
    sessionId = urlParams.get('session_id');

    if (!sessionId) {
        alert(i18n.get('MSG_NO_SESSION') || 'No Session ID');
        window.location.href = '/static/index.html';
        return;
    }

    const storedNick = localStorage.getItem('poker_nickname');
    if (storedNick) myNickname = storedNick;

    // Clear old i18n cache
    Object.keys(localStorage).forEach(key => {
        if (key.startsWith('i18n_')) localStorage.removeItem(key);
    });

    i18n.init(i18n.currentLang).then(() => {
        connectWebSocket(sessionId);
        updateUIText();
    });
}

function updateUIText() {
    // Update static text if needed, mostly handled by data-i18n in HTML
    // But dynamic buttons might need updates
}

// --- Event Listeners ---

// Menu
btnMenuToggle.addEventListener('click', () => menuModal.classList.remove('hidden'));
btnMenuClose.addEventListener('click', () => menuModal.classList.add('hidden'));

btnHeaderQuit.addEventListener('click', () => {
    menuModal.classList.add('hidden');
    showModal(i18n.get('MODAL_QUIT_TITLE'), i18n.get('MODAL_QUIT_MSG'), () => {
        sendAction('quit', 0);
        setTimeout(() => window.location.href = '/static/index.html', 500);
    });
});

btnHeaderNewGame.addEventListener('click', () => {
    menuModal.classList.add('hidden');
    showModal(i18n.get('MODAL_NEW_GAME_TITLE'), i18n.get('MODAL_NEW_GAME_MSG'), () => {
        startNewGame();
    });
});

// Actions
btnFold.addEventListener('click', () => {
    addChatMessage('user', 'Fold', myNickname); // Immediate feedback
    sendAction('fold', 0);
});

btnCall.addEventListener('click', () => {
    const amount = currentRoundState?.amount_to_call || 0;
    const text = amount > 0 ? `Call ${amount}` : 'Check';
    addChatMessage('user', text, myNickname); // Immediate feedback
    sendAction('call', amount);
});

btnRaise.addEventListener('click', showRaiseControls);

// Raise Controls
btnCancelRaise.addEventListener('click', hideRaiseControls);

btnConfirmRaise.addEventListener('click', () => {
    const amount = parseInt(raiseAmountInput.value);
    addChatMessage('user', `Raise ${amount}`, myNickname); // Immediate feedback
    sendAction('raise', amount);
    hideRaiseControls();
});

btnAllIn.addEventListener('click', () => {
    // All in logic might need max stack calculation
    // For now, sending -1 usually means All-In in many backends, or we set max.
    // The previous code used -1.
    addChatMessage('user', 'ALL IN!', myNickname);
    sendAction('raise', -1);
    hideRaiseControls();
});

// End Round
btnNextRound.addEventListener('click', () => {
    sendAction('next_round', 0);
    endRoundControls.classList.add('hidden');
    actionBar.classList.add('disabled');
});

// Elimination
if (btnSimulate) {
    btnSimulate.addEventListener('click', () => {
        sendAction('simulate', 0);
        btnSimulate.classList.add('hidden');
        addSystemMessage(i18n.get('BTN_SIMULATE') + '...');
    });
}

if (btnElimNewGame) {
    btnElimNewGame.addEventListener('click', () => {
        showModal(i18n.get('MODAL_NEW_GAME_TITLE'), i18n.get('MODAL_NEW_GAME_MSG'), () => {
            startNewGame();
        });
    });
}

btnQuitGame.addEventListener('click', () => {
    showModal(i18n.get('MODAL_QUIT_TITLE'), i18n.get('MODAL_QUIT_MSG'), () => {
        sendAction('quit', 0);
        setTimeout(() => window.location.href = '/static/index.html', 500);
    });
});

// Modal
btnModalCancel.addEventListener('click', hideModal);
btnModalConfirm.addEventListener('click', () => {
    if (onModalConfirm) onModalConfirm();
    hideModal();
});

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

function showRaiseControls() {
    raiseControls.classList.remove('hidden');
    raiseAmountInput.focus();
}

function hideRaiseControls() {
    raiseControls.classList.add('hidden');
}

// --- WebSocket & Game Logic ---

function sendAction(action, amount) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    if (action !== 'next_round') {
        actionBar.classList.add('disabled');
    }

    socket.send(JSON.stringify({
        type: 'action',
        data: {
            action: action,
            amount: parseInt(amount)
        }
    }));
}

function connectWebSocket(sid) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${sid}?lang=${i18n.currentLang}`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        addSystemMessage(i18n.get('MSG_CONNECTED') || 'Connected');
    };

    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleGameMessage(message.type, message.data);
    };

    socket.onclose = () => {
        addSystemMessage(i18n.get('MSG_CONN_LOST') || 'Connection Lost');
        actionBar.classList.add('disabled');
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        addSystemMessage(i18n.get('MSG_CONN_ERROR') || 'Connection Error');
    };
}

function handleGameMessage(type, data) {
    console.log('Received:', type, data);

    switch (type) {
        case 'status':
            addSystemMessage(data);
            break;

        case 'terminal_output':
            parseAndLogMessage(data);
            break;

        case 'game_start':
            addSystemMessage(i18n.get('MSG_GAME_STARTED'), true);
            break;

        case 'round_start_data':
            myHoleCards = data.hole_cards;
            renderCards(myHoleCards);
            // Display "Round X" if available, otherwise fallback
            const roundMsg = data.round_count
                ? `${i18n.get('MSG_ROUND') || 'Round'} ${data.round_count}`
                : i18n.get('MSG_NEW_ROUND');
            addSystemMessage(`--- ${roundMsg} ---`, true);
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
            if (endRoundControls.classList.contains('hidden')) {
                actionBar.classList.add('disabled');
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
            addSystemMessage(data);
            break;

        case 'error':
            addSystemMessage('Error: ' + data);
            break;

        case 'player_eliminated':
            handlePlayerEliminated(data);
            break;

        case 'chat_message':
            hideThinking();
            if (data.sender && data.content) {
                if (data.sender === myNickname) return;
                addChatMessage(data.type || 'opponent', data.content, data.sender, data);
            }
            break;

        case 'bot_thinking':
            handleBotThinking(data);
            break;
    }
}

// --- Message Parsing & Rendering ---

function stripAnsi(text) {
    return text.replace(/\x1B\[[0-9;]*[mK]/g, '');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatCardsInText(text) {
    // First escape HTML to prevent XSS
    let safeText = escapeHtml(text);

    // Convert newlines to <br> for Dealer messages
    safeText = safeText.replace(/\n/g, '<br>');

    // Regex for cards with Red suits (Hearts ♥, Diamonds ♦)
    // Matches RankSuit (e.g. 10♥, K♦) or SuitRank (e.g. ♥10, ♦K)
    // Ranks: 2-9, T, J, Q, K, A, 10
    const redCardRegex = /((?:10|[2-9TJQKA])[♦♥]|[♦♥](?:10|[2-9TJQKA]))/g;

    return safeText.replace(redCardRegex, '<span style="color: #ff5252;">$1</span>');
}

// Deduplication state
let lastChatMessage = { content: '', time: 0 };
let pendingFinalStacks = null;
let isShowingCards = false;

function parseAndLogMessage(rawText) {
    if (!rawText) return;
    const cleanText = stripAnsi(rawText).trim();
    if (!cleanText) return;

    // Define ignore patterns early
    const ignorePatterns = [
        /^Available actions/i,
        /^Your cards/i,
        /^To Call/i,
        /^\[WEB\]/i,
        /^\[SYSTEM\]/i,
        /^─/,
        /^–/, // En-dash
        /^—/, // Em-dash
        /^-/, // Hyphen
        /^>/, // User input echo
        /^\[ACTION\]/, // Backend action logs
        /^.+? (folded|called|raised|checked|all-in|SB|BB)/i, // Standard player actions (handled by chat bubbles)
        /^Pot .* \| Your chips/i, // Hide repeated pot/stack info during player turn
        /^Community cards/i // Hide backend community cards msg (handled by Dealer msg)
    ];

    // Handle "Final stacks" buffering - Check FIRST to avoid filtering
    if (cleanText.toLowerCase().startsWith('final stacks:')) {
        pendingFinalStacks = cleanText;
        return;
    }

    if (pendingFinalStacks) {
        if (ignorePatterns.some(p => p.test(cleanText))) return; // Ignore noise
        const combined = pendingFinalStacks + '\n' + cleanText;
        addChatMessage('opponent', combined, 'Dealer');
        pendingFinalStacks = null;
        return;
    }

    // Handle "Participant cards" - Individual messages
    // DISABLED: We now rely on backend 'chat_message' events for natural language
    /*
    if (cleanText.toLowerCase().startsWith('participant cards:')) {
        isShowingCards = true;
        // addChatMessage('opponent', 'Show your cards', 'Dealer');
        return;
    }

    if (isShowingCards) {
        // Check for end of section
        const lower = cleanText.toLowerCase();
        if (lower.startsWith('winner') || lower.startsWith('final stacks') || lower.startsWith('---')) {
            isShowingCards = false;
            // Fall through to handle this line (e.g. Winner line)
        } else {
            // Parse card line: "Name (Pos): Cards | Hand"
            // Regex: Name (Group 1), Optional Pos (Group 2), Content (Group 3)
            const cardRegex = /^(.+?)(?:\s*\((.+?)\))?:\s*(.+)$/;
            const match = cleanText.match(cardRegex);
            if (match) {
                const name = match[1].trim();
                // Collapse multiple spaces and remove newlines
                const content = match[3].trim().replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ');

                // Determine type (user or opponent)
                const type = (name === myNickname) ? 'user' : 'opponent';

                // Find stack
                let stack = null;
                if (currentRoundState && currentRoundState.seats) {
                    const seat = currentRoundState.seats.find(s => s.name === name);
                    if (seat) stack = seat.stack;
                }

                addChatMessage(type, `I have ${content}`, name, { stack: stack });
                return;
            }
            // Ignore other lines in this block (noise)
            return;
        }
    }
    */

    // 1. Check for Community Cards (Keep as visual aid in chat)
    if (cleanText.includes('[') && cleanText.includes(']')) {
        const match = cleanText.match(/\[(.*?)\]/);
        if (match) {
            const cardsStr = match[1];
            const cards = cardsStr.split(/\s+/).filter(c => {
                return /^[2-9TJQKA][shdcSHDC♥♦♣♠]$/.test(c);
            });
            if (cards.length > 0) {
                addCommunityCardsMessage(cards);
                return;
            }
        }
    }

    // 2. Check for "Wins" / "Winner" / "Won"
    const lower = cleanText.toLowerCase();
    if (lower.includes('wins') || lower.includes('winner') || lower.includes('won')) {
        addChatMessage('opponent', cleanText, 'Dealer');
        return;
    }

    // 3. Filter out noisy terminal output
    if (ignorePatterns.some(p => p.test(cleanText))) return;
    if (cleanText.startsWith('|')) return;

    // 4. Special handling for Pot and Game Events
    if (cleanText.toLowerCase().startsWith('pot')) {
        // Ignore "Pot" messages that start with Pot (likely backend updates)
        // Unless it's a "Pot won" message which usually contains "wins" handled above
        return;
    }

    if (cleanText.toLowerCase().startsWith('round summary')) {
        // Ignore Round Summary
        return;
    }

    // 5. Parse "Name Action Amount" from terminal output (Robust fallback for bots)
    // DISABLED: We now rely on explicit 'chat_message' events from web_player.py to avoid duplicates.
    /*
    const terminalActionRegex = /^(.+?) (called|raised|folded|checked|all-in|SB|BB)(?:(?:\(| )(\d+)\)?)?$/i;
    const termMatch = cleanText.match(terminalActionRegex);
    if (termMatch) {
        const name = termMatch[1].trim();
        const action = termMatch[2].toUpperCase();
        const amount = termMatch[3] || '';

        // Ignore if it's me (my actions are handled by UI buttons usually, or "You" check)
        // Also ignore "Pot" if it matched (though handled above)
        if (name !== 'You' && name !== myNickname && name.toLowerCase() !== 'pot') {
            let displayAction = action;
            if (action === 'SB') displayAction = 'Small Blind';
            if (action === 'BB') displayAction = 'Big Blind';

            const text = `${displayAction} ${amount}`.trim();
            addChatMessage('opponent', text, name);
            return;
        }
    }
    */

    // 6. Fallback: Try to parse "Player declared" if game_update missed it
    // This is a safety net for reconnected sessions or missed events
    const actionRegex = /Player ['"](.+?)['"] declared ['"](.+?):(\d+?)['"]/;
    const match = cleanText.match(actionRegex);
    if (match) {
        const name = match[1];
        const action = match[2].toUpperCase();
        const amount = match[3];
        if (name !== myNickname) {
            addChatMessage('opponent', `${action} ${amount > 0 ? amount : ''}`, name);
            return;
        }
    }

    // 7. Final Fallback
    addSystemMessage(cleanText);
}

function addChatMessage(type, content, senderName, options = {}) {
    // Simple deduplication: ignore if same content and sender within 500ms
    const now = Date.now();
    const uniqueKey = `${type}:${senderName}:${content}`;
    if (lastChatMessage.content === uniqueKey && (now - lastChatMessage.time) < 1000) {
        return;
    }
    lastChatMessage = { content: uniqueKey, time: now };

    const row = document.createElement('div');
    row.className = `msg-row ${type}`;

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    // Format cards in text to be red if Hearts/Diamonds
    bubble.innerHTML = formatCardsInText(content);

    if (type === 'opponent') {
        // Avatar
        const avatar = document.createElement('div');
        avatar.style.position = 'relative'; // For badge positioning

        // Check if it's the Dealer/System bot
        if (senderName === 'Dealer' || senderName === 'System') {
            avatar.className = 'avatar-circle robot';
            avatar.textContent = '🤖';
            avatar.style.backgroundColor = '#7c4dff'; // Purple for bot
            avatar.style.border = '1px solid #b388ff';
        } else {
            avatar.className = 'avatar-circle';
            avatar.textContent = getInitials(senderName);
            avatar.style.backgroundColor = getAvatarColor(senderName);

            // Bet Badge
            if (options.bet !== undefined && options.bet !== null) {
                const badge = document.createElement('div');
                badge.className = 'avatar-bet-badge';
                badge.textContent = options.bet;
                avatar.appendChild(badge);
            }
        }

        // Name label
        const nameLabel = document.createElement('span');
        nameLabel.className = 'sender-name';
        let displayName = senderName;
        if (options.stack !== undefined && options.stack !== null) {
            displayName += ` (${options.stack})`;
        }
        nameLabel.textContent = displayName;

        const wrapper = document.createElement('div');
        wrapper.style.display = 'flex';
        wrapper.style.flexDirection = 'column';

        wrapper.appendChild(nameLabel);
        wrapper.appendChild(bubble);

        row.appendChild(avatar);
        row.appendChild(wrapper);
    } else {
        row.appendChild(bubble);
    }

    chatContent.appendChild(row);
    scrollToBottom();
}

function addSystemMessage(text, isSystem = false) {
    // Remove dashes from text (e.g. "--- FLOP ---" -> "FLOP")
    const cleanText = text.replace(/^-+\s*|\s*-+$/g, '');

    // Check if it's a divider (starts with --- in original text) or explicit centered content
    // Note: We check original 'text' for dashes to identify dividers coming from backend
    // Also explicitly check for Street names to ensure they are centered
    const upper = cleanText.toUpperCase();
    const isDivider = isSystem || text.startsWith('---') ||
        text === 'GAME STARTED' ||
        text === 'GAME OVER' ||
        ['PREFLOP', 'FLOP', 'TURN', 'RIVER', 'SHOWDOWN'].includes(upper) ||
        upper.includes('WINNER') ||
        upper.includes('WON');

    if (!isDivider) {
        // Render as "Dealer" bot message
        addChatMessage('opponent', cleanText, 'Dealer');
        return;
    }

    const row = document.createElement('div');
    row.className = `msg-row system centered`;

    const badge = document.createElement('div');
    badge.className = 'msg-system-badge';
    badge.textContent = cleanText; // Use clean text (no dashes)

    row.appendChild(badge);
    chatContent.appendChild(row);
    scrollToBottom();
}

function addCommunityCardsMessage(cards) {
    const row = document.createElement('div');
    row.className = 'msg-row system centered'; // Explicitly centered

    const container = document.createElement('div');
    container.className = 'chat-community-cards';

    cards.forEach(card => {
        const div = document.createElement('div');
        const isRed = card[0] === 'H' || card[0] === 'D' || card.includes('♥') || card.includes('♦');
        div.className = `playing-card ${isRed ? 'red' : ''}`;
        div.textContent = getCardSymbol(card);
        container.appendChild(div);
    });

    row.appendChild(container);
    chatContent.appendChild(row);
    scrollToBottom();
}

function scrollToBottom() {
    // Scroll the container
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function getInitials(name) {
    if (!name) return '??';
    return name.substring(0, 2).toUpperCase();
}

function getAvatarColor(name) {
    // Generate consistent color from name
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
    return '#' + '00000'.substring(0, 6 - c.length) + c;
}

// --- Game State Handling ---

// Assuming there's a WebSocket onmessage handler that dispatches these events
// This switch statement is added based on the user's instruction and context.



function handleStreetStart(data) {
    if (data.street) {
        // Send just the street name, addSystemMessage will handle centering and no dashes
        const streetKey = `MSG_STREET_${data.street.toUpperCase()}`;
        let msg = i18n.get(streetKey) || data.street.toUpperCase();

        // Append community cards if available in round_state
        if (data.round_state && data.round_state.community_card && data.round_state.community_card.length > 0) {
            const cards = data.round_state.community_card.map(c => getCardSymbol(c)).join(' ');
            msg += `: [${cards}]`;
        }

        addSystemMessage(msg, true);
    }
    if (data.round_state) {
        currentRoundState = data.round_state;
        updateStats(currentRoundState);
    }
}

function handleGameUpdate(data) {
    // Update stats
    if (data.round_state) {
        currentRoundState = data.round_state;
        updateStats(currentRoundState);
    }

    // Note: We used to generate opponent chat messages here, but it was unreliable due to UUID mismatches.
    // Now we rely on explicit 'chat_message' events sent by the backend or 'terminal_output' parsing.
    // We only handle "Me" actions here if needed (blinds), but even those are better handled by backend/terminal.
    if (data.action && data.round_state) {
        const actionObj = data.action;
        const seats = data.round_state.seats;
        const pUuid = actionObj.player_uuid || actionObj.uuid;
        const player = seats.find(s => s.uuid === pUuid);

        if (player && player.name === myNickname) {
            const act = actionObj.action;
            const amt = actionObj.amount || 0;
            let text = act;
            if (['CALL', 'RAISE', 'BET', 'SMALLBLIND', 'BIGBLIND'].includes(act) && amt > 0) {
                text += ` ${amt}`;
            }
            // Only show Blinds here. Other actions are optimistic.
            if (['SMALLBLIND', 'BIGBLIND'].includes(act)) {
                addChatMessage('user', text, player.name);
            }
        }
    }
}

function handleActionRequired(data) {
    hideThinking();
    currentRoundState = data.round_state;
    updateStats(currentRoundState);

    actionBar.classList.remove('disabled');
    endRoundControls.classList.add('hidden');

    // Update buttons based on valid actions
    const validActions = data.valid_actions || [];

    const canFold = validActions.some(a => a.action === 'fold');
    const canCall = validActions.some(a => a.action === 'call');
    const canRaise = validActions.some(a => a.action === 'raise');

    btnFold.disabled = !canFold;
    btnCall.disabled = !canCall;
    btnRaise.disabled = !canRaise;

    // Update Call Button Text
    let callAmount = 0;
    const callAction = validActions.find(a => a.action === 'call');
    if (callAction) {
        callAmount = callAction.amount;
        currentRoundState.amount_to_call = callAmount;
        const label = btnCall.querySelector('.btn-label');
        if (callAction.amount === 0) {
            label.textContent = i18n.get('BTN_CHECK') || 'CHECK';
        } else {
            label.textContent = `${i18n.get('BTN_CALL') || 'CALL'} ${callAction.amount}`;
        }
    }

    // Update Raise Limits
    const raiseAction = validActions.find(a => a.action === 'raise');
    if (raiseAction) {
        raiseAmountInput.min = raiseAction.amount.min;
        raiseAmountInput.max = raiseAction.amount.max;
        raiseAmountInput.value = raiseAction.amount.min;
    }

    // --- Dealer Message ---
    // Calculate Pot
    let totalPot = 0;
    if (currentRoundState.pot) {
        if (currentRoundState.pot.main) totalPot += currentRoundState.pot.main.amount;
        if (currentRoundState.pot.side) currentRoundState.pot.side.forEach(s => totalPot += s.amount);
    }

    // Get My Stack
    let myStack = 0;
    if (currentRoundState.seats) {
        const mySeat = currentRoundState.seats.find(s => s.name === myNickname);
        if (mySeat) myStack = mySeat.stack;
    }

    // Community Cards
    const cards = currentRoundState.community_card || [];
    const cardsStr = cards.map(c => getCardSymbol(c)).join(' ');

    let msg = i18n.get('MSG_POT_STATUS', { pot: totalPot, stack: myStack });
    if (callAmount > 0) {
        msg += ' ' + i18n.get('MSG_CALL_REQUIRED', { amount: callAmount });
    } else {
        msg += ' ' + i18n.get('MSG_CHECK_ALLOWED');
    }

    if (cards.length > 0) {
        msg += '\n' + i18n.get('MSG_COMMUNITY_CARDS', { cards: cardsStr });
    }

    addChatMessage('opponent', msg, 'Dealer');

    scrollToBottom();
}

function handleWaitForNextRound() {
    actionBar.classList.add('disabled');
    endRoundControls.classList.remove('hidden');

    btnNextRound.classList.remove('hidden');
    eliminationControls.classList.add('hidden');
}

function handleGameOver(data) {
    actionBar.classList.add('disabled');
    endRoundControls.classList.remove('hidden');

    btnNextRound.classList.add('hidden');
    eliminationControls.classList.remove('hidden');

    addSystemMessage(i18n.get('MSG_GAME_OVER') || 'GAME OVER');
}

function handlePlayerEliminated(data) {
    actionBar.classList.add('disabled');
    endRoundControls.classList.remove('hidden');

    btnNextRound.classList.add('hidden');
    eliminationControls.classList.remove('hidden');

    addSystemMessage(i18n.get('MODAL_ELIMINATED_MSG') || 'YOU HAVE BEEN ELIMINATED');
    renderCards([]); // Clear cards
}

function handleBotThinking(data) {
    if (data.player) {
        thinkingText.textContent = `${data.player} is thinking`;
        thinkingIndicator.classList.remove('hidden');
    }
}

function hideThinking() {
    thinkingIndicator.classList.add('hidden');
}

function updateStats(roundState) {
    if (!roundState) return;

    // Pot
    if (roundState.pot) {
        let totalPot = 0;
        if (roundState.pot.main) totalPot += roundState.pot.main.amount;
        if (roundState.pot.side) roundState.pot.side.forEach(s => totalPot += s.amount);
        potDisplay.textContent = totalPot;
    }

    // My Stack
    if (roundState.seats) {
        const mySeat = roundState.seats.find(s => s.name === myNickname);
        if (mySeat) {
            myStackDisplay.textContent = mySeat.stack;
        }
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

async function startNewGame() {
    const storedConfig = localStorage.getItem('poker_config');
    if (!storedConfig) return;

    try {
        const config = JSON.parse(storedConfig);
        const response = await fetch('/api/game/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (!response.ok) throw new Error('Failed');

        const data = await response.json();
        window.location.href = `/static/game.html?session_id=${data.session_id}`;

    } catch (error) {
        alert('Error starting new game');
    }
}
