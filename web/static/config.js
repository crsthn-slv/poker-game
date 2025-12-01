/**
 * Configuration Logic for Terminal Poker Web
 */

// DOM Elements
const nicknameInput = document.getElementById('nickname');
const startBtn = document.getElementById('start-btn');

// Initialize
const storedNickname = localStorage.getItem('poker_nickname');
if (storedNickname) {
    nicknameInput.value = storedNickname;
}

// Event Listeners
startBtn.addEventListener('click', initializeGame);

async function initializeGame() {
    const nick = nicknameInput.value.trim();
    if (!nick) {
        alert('Please enter a nickname');
        return;
    }

    localStorage.setItem('poker_nickname', nick);

    const config = {
        nickname: nick,
        initial_stack: parseInt(document.getElementById('initial-stack').value),
        num_bots: parseInt(document.getElementById('num-bots').value),
        show_probability: document.getElementById('show-prob').checked
    };

    localStorage.setItem('poker_config', JSON.stringify(config));

    try {
        startBtn.disabled = true;
        startBtn.textContent = 'CONNECTING...';

        // Create Game Session
        const response = await fetch('/api/game/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (!response.ok) throw new Error('Failed to create game');

        const data = await response.json();
        const sessionId = data.session_id;

        // Redirect to game page
        window.location.href = `/static/game.html?session_id=${sessionId}`;

    } catch (error) {
        console.error(error);
        alert('Error starting game: ' + error.message);
        startBtn.disabled = false;
        startBtn.textContent = 'INITIALIZE_GAME';
    }
}
