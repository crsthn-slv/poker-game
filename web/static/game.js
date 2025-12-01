/**
 * Game Logic for Terminal Poker Web
 */

// State
let socket = null;
let sessionId = null;
let currentRoundState = null;
let myHoleCards = [];
let myNickname = 'Unknown';

// DOM Elements
const terminalOutput = document.getElementById('terminal-output');
const controlsArea = document.getElementById('controls-area');
const actionButtons = document.querySelectorAll('.action-btn');
const raiseControls = document.getElementById('raise-controls');
const raiseSlider = document.getElementById('raise-slider');
const raiseAmountInput = document.getElementById('raise-amount');
const myCardsDisplay = document.getElementById('my-cards');
const myStackDisplay = document.getElementById('my-stack');
const myBetDisplay = document.getElementById('my-bet');
const potDisplay = document.getElementById('pot-display');
const communityCardsDisplay = document.getElementById('community-cards');
const winProbDisplay = document.getElementById('win-prob');
const probDisplayContainer = document.getElementById('prob-display');


const btnNextRound = document.getElementById('btn-next-round');
const btnQuitGame = document.getElementById('btn-quit-game');
const btnHeaderQuit = document.getElementById('btn-header-quit');
const btnHeaderNewGame = document.getElementById('btn-header-new-game');
const endRoundControls = document.getElementById('end-round-controls');

const actionButtonsContainer = document.querySelector('.action-buttons');

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

    // Get nickname from local storage
    const storedNick = localStorage.getItem('poker_nickname');
    if (storedNick) {
        myNickname = storedNick;
    }

    connectWebSocket(sessionId);
}

// Event Listeners
document.getElementById('btn-fold').addEventListener('click', () => sendAction('fold', 0));
document.getElementById('btn-call').addEventListener('click', () => sendAction('call', currentRoundState?.amount_to_call || 0));
document.getElementById('btn-allin').addEventListener('click', () => sendAction('raise', -1));



document.getElementById('btn-allin').addEventListener('click', () => sendAction('raise', -1));

btnHeaderQuit.addEventListener('click', () => {
    btnQuitGame.click(); // Reuse the same logic
});

btnHeaderNewGame.addEventListener('click', startNewGame);

btnNextRound.addEventListener('click', () => {
    sendAction('next_round', 0);
    endRoundControls.classList.add('hidden');
    controlsArea.classList.add('disabled');
});

btnQuitGame.addEventListener('click', () => {
    if (confirm('Are you sure you want to quit? Your history will be saved.')) {
        sendAction('quit', 0);
        // Give a small delay for server to process and save, then redirect
        setTimeout(() => {
            window.location.href = '/static/index.html';
        }, 500);
    }
});

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
        logToTerminal('Connected to game server.', 'system');
        // document.getElementById('game-status').textContent = 'STATUS: ONLINE';
        // document.getElementById('game-status').style.color = 'var(--success-color)';
    };

    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleGameMessage(message.type, message.data);
    };

    socket.onclose = () => {
        logToTerminal('Connection lost.', 'error');
        // document.getElementById('game-status').textContent = 'STATUS: OFFLINE';
        // document.getElementById('game-status').style.color = 'var(--danger-color)';
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
            // Fallback: Parse community cards from terminal output if structured event is missing
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
            console.log('Received street_start:', data); // Debug log
            handleStreetStart(data);
            break;

        case 'game_update':
            handleGameUpdate(data);
            break;

        case 'action_required':
            handleActionRequired(data);
            break;

        case 'round_result_data':
            controlsArea.classList.add('disabled');
            hideRaiseControls();
            break;

        case 'wait_for_next_round':
            handleWaitForNextRound();
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

function handleWaitForNextRound() {
    controlsArea.classList.remove('disabled');

    // Hide action buttons container
    actionButtonsContainer.classList.add('hidden');

    // Show End Round Controls
    endRoundControls.classList.remove('hidden');
    btnNextRound.focus();
}

function handleActionRequired(data) {
    currentRoundState = data.round_state;

    controlsArea.classList.remove('disabled');
    endRoundControls.classList.add('hidden');

    // Show action buttons container
    actionButtonsContainer.classList.remove('hidden');

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
        if (btn === btnNextRound) return; // Skip next round button

        const action = btn.dataset.action;
        const isValid = data.valid_actions.some(a => a.action === action);
        btn.disabled = !isValid;
    });

    // Update Stack and Bet
    if (currentRoundState.seats) {
        const mySeat = currentRoundState.seats.find(seat => seat.name === myNickname);
        if (mySeat) {
            myStackDisplay.textContent = mySeat.stack;
        }
    }

    updateMyBetDisplay(currentRoundState);

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

    // Fix: Extract amount_to_call from valid_actions for the Call button
    // Fix: Extract amount_to_call from valid_actions for the Call button
    const callAction = data.valid_actions.find(a => a.action === 'call');
    const btnCall = document.getElementById('btn-call');
    if (callAction) {
        currentRoundState.amount_to_call = callAction.amount;
        if (callAction.amount === 0) {
            btnCall.textContent = 'Check (C)';
        } else {
            btnCall.textContent = `Call {${callAction.amount}} (C)`;
        }
    } else {
        // Fallback if call is not valid (though disabled logic handles visibility)
        btnCall.textContent = 'Call';
    }

    // Update Community Cards and Pot
    if (currentRoundState.community_card) {
        renderCommunityCards(currentRoundState.community_card);
    }

    if (currentRoundState.pot) {
        updatePotDisplay(currentRoundState.pot);
    }

    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function sendAction(action, amount) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    // Don't disable controls immediately for next_round to allow animation/transition if needed
    // But generally good practice to prevent double clicks
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

// Function to convert ANSI codes to HTML
function ansiToHtml(text) {
    if (!text) return '';

    // Basic ANSI color map
    const colors = {
        '30': 'black', '31': '#ff5555', '32': '#50fa7b', '33': '#f1fa8c',
        '34': '#bd93f9', '35': '#ff79c6', '36': '#8be9fd', '37': '#f8f8f2',
        '90': '#6272a4' // Bright black / Gray
    };

    // Replace color codes
    let html = text.replace(/\x1B\[(\d+)m/g, (match, code) => {
        if (code === '0') return '</span>'; // Reset
        if (code === '1') return '<span style="font-weight:bold">'; // Bold
        if (code === '2') return '<span style="opacity:0.6">'; // Faint
        if (colors[code]) return `<span style="color:${colors[code]}">`; // Color
        return '';
    });

    // Ensure all open spans are closed at the end of the string
    // This is a simple approach and might not handle nested spans perfectly,
    // but works for basic color/style changes.
    while (html.includes('<span')) {
        if (!html.includes('</span>')) {
            html += '</span>';
        } else {
            break; // Assume balanced if a closing tag exists
        }
    }

    return html;
}

function logToTerminal(text, type = 'action') {
    const div = document.createElement('div');
    div.className = `line ${type}`;
    if (type === 'raw') {
        // For 'raw' type, assume text contains ANSI codes and render as HTML
        div.innerHTML = ansiToHtml(text);
    } else {
        // For other types, treat as plain text
        div.textContent = text;
    }
    terminalOutput.appendChild(div);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
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
    const street = roundState.street;

    // Calculate total bet for the current street only? Or total for the round?
    // Usually "Bet" in HUD means current street bet or total contribution to pot.
    // Let's show total contribution to the pot in the current round (all streets)
    // or just the current street. 
    // "quanto de fichas já apostei no round" implies total for the round (hand).

    // Iterate over all streets in action history
    Object.values(roundState.action_histories).forEach(streetActions => {
        streetActions.forEach(action => {
            // Check if action is from me (by name or uuid if we had it)
            // We use name for now as we have myNickname
            // Note: action_histories usually have uuid, not name directly in some versions,
            // but let's check what we have.
            // If we don't have name in action, we need to match uuid.

            // We need to find my UUID from seats if not known
            let myUuid = null;
            if (roundState.seats) {
                const mySeat = roundState.seats.find(s => s.name === myNickname);
                if (mySeat) myUuid = mySeat.uuid;
            }

            if (action.uuid === myUuid) {
                if (action.action === 'CALL') {
                    totalBet += action.paid || action.amount;
                } else if (action.action === 'RAISE') {
                    totalBet += action.amount; // Raise amount is usually the total bet for the street? 
                    // In PyPokerEngine, RAISE amount is the target total amount for the street.
                    // But we are summing up. 
                    // Wait, if I raise to 20, I added 20 to the pot (minus what I already bet).
                    // PyPokerEngine history is a bit tricky.
                    // Let's look at 'paid' if available, or 'amount'.
                    // Actually, simpler way: 
                    // Total bet = Initial Stack - Current Stack
                    // But this includes previous rounds if we don't track initial stack of the round.

                    // Let's try to use the 'paid' field if available, which represents chips put in pot.
                    // If 'paid' is not there, we might need to rely on logic.
                    // For RAISE, 'amount' is usually the total amount matched.
                    // Let's assume 'paid' is reliable if present (it was added in our backend logic).
                } else if (action.action === 'SMALLBLIND' || action.action === 'BIGBLIND') {
                    totalBet += action.amount;
                }

                // If we use the 'paid' field from our backend enhancement, it's safer.
                // In receive_game_update_message we saw: paid = new_action.get('paid', 0)
                // But action_histories might be raw from PyPokerEngine.
                // Let's check if we can calculate simply:
                // Total Bet = (Start Stack of Round) - (Current Stack)
                // But we don't easily have Start Stack of Round unless we tracked it.
            }
        });
    });

    // Alternative: Calculate from stack difference if we knew initial stack of the round.
    // Since we don't, let's try to sum up 'amount' or 'paid' from history carefully.

    // Re-calculating using a safer approach for PyPokerEngine action history:
    // Iterate streets, find my actions.
    // For each street, my contribution is the max 'amount' I committed?
    // No, because I might have called then raised.

    // Let's use a simplified approach:
    // Iterate all actions. If it's me:
    // If action is SB/BB/ANTE: add amount.
    // If action is CALL: add amount (or paid).
    // If action is RAISE: This is tricky. RAISE 50 means "make my total bet for this street 50".
    // So for a street, my contribution is the final amount I raised/called to.

    let myTotalBetInHand = 0;

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
                        // In PyPokerEngine, CALL amount is the target amount to match?
                        // Or the amount added?
                        // Usually 'amount' in CALL is the target. 'paid' is what was added.
                        // If we don't have 'paid', we have to track previous bet.
                        // Let's assume we use the logic:
                        // My bet for the street = max(action.amount) for my actions?
                        // Yes, for CALL and RAISE, the 'amount' is the total chips in front of player for that street.
                        // So we just need the LAST 'amount' I committed in this street.
                        // Exception: SB/BB are forced bets, usually counted towards the street bet.

                        // Let's try: For each street, find the last action I did.
                        // The 'amount' of that action is my total contribution for that street.
                        // Wait, SB/BB are separate actions.
                        // If I SB (5), then CALL (10), my total for street is 10.
                        // If I RAISE (20), my total is 20.
                        // So, for each street, find the max 'amount' associated with my CALL/RAISE/SB/BB actions.
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
            myTotalBetInHand += myStreetBet;
        }
    });

    myBetDisplay.textContent = myTotalBetInHand;
}

async function startNewGame() {
    if (!confirm('Are you sure you want to start a new game? Current progress will be lost.')) {
        return;
    }

    const storedConfig = localStorage.getItem('poker_config');
    if (!storedConfig) {
        alert('No configuration found. Please start from the home page.');
        window.location.href = '/static/index.html';
        return;
    }

    try {
        const config = JSON.parse(storedConfig);

        // Disable button to prevent double click
        btnHeaderNewGame.disabled = true;
        btnHeaderNewGame.textContent = '...';

        // Create Game Session
        const response = await fetch('/api/game/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (!response.ok) throw new Error('Failed to create game');

        const data = await response.json();
        const newSessionId = data.session_id;

        // Redirect to new session
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

    // Strip ANSI codes
    const cleanText = text.replace(/\x1B\[[0-9;]*[mK]/g, '');

    // Split into lines to handle history blobs
    const lines = cleanText.split('\n');

    // Find the LAST line that contains "Community cards:"
    // This ensures we show the most recent state
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
            // Split by whitespace to get individual cards
            // Filter out empty strings and ensure it looks like a card 
            // Valid card: 2-3 chars (e.g. "Ah", "10s", "K♦")
            // Avoid parsing "Pot", "->", numbers like "100" as cards unless they look like cards
            const potentialCards = cardsPart.split(/\s+/);

            const validSuits = ['S', 'H', 'D', 'C', '♠', '♥', '♦', '♣'];
            const validRanks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'T', 'J', 'Q', 'K', 'A'];

            const cards = potentialCards.filter(c => {
                if (c.length < 2 || c.length > 3) return false;
                // Check if it ends with a valid suit or starts with a valid rank?
                // Or just simple length check + exclusion of known non-card words
                if (['Pot', '->'].includes(c)) return false;
                if (!isNaN(c)) return false; // Exclude pure numbers
                return true;
            });

            if (cards.length > 0) {
                console.log('Parsed community cards from log:', cards);
                renderCommunityCards(cards);
            }
        }
    }
}
