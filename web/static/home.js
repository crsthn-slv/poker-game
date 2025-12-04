/**
 * HOME SCREEN - Match History & Navigation
 * Handles match list display, navigation between views, and settings
 */

import { i18n } from '/static/localization.js';

// ============================================================================
// STATE
// ============================================================================

let currentNickname = localStorage.getItem('nickname') || '';
let playerId = localStorage.getItem('player_id') || null;
let matches = [];
let activeView = 'conversations';

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize localization
    const savedLang = localStorage.getItem('game_lang') || 'en';
    i18n.init(savedLang);

    // Update UI with language
    updateLanguageButtons(savedLang);

    // Check if user has nickname
    if (!currentNickname) {
        // Redirect to initial setup (index.html)
        window.location.href = '/';
        return;
    }

    // Display nickname in header
    document.getElementById('player-nickname').textContent = currentNickname;

    // Initialize settings
    initializeSettings();

    // Load match history
    await loadMatchHistory();

    // Setup event listeners
    setupEventListeners();
});

// ============================================================================
// MATCH HISTORY LOADING
// ============================================================================

async function loadMatchHistory() {
    const loadingState = document.getElementById('loading-state');
    const emptyState = document.getElementById('empty-state');
    const matchList = document.getElementById('match-list');

    try {
        // Show loading
        loadingState.classList.remove('hidden');
        emptyState.classList.add('hidden');

        // Fetch from API
        const response = await fetch(`/api/match/history/${encodeURIComponent(currentNickname)}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        matches = data.matches || [];

        if (data.player_id) {
            playerId = data.player_id;
            localStorage.setItem('player_id', playerId);
        }

        // Hide loading
        loadingState.classList.add('hidden');

        // Render matches or show empty state
        if (matches.length === 0) {
            emptyState.classList.remove('hidden');
        } else {
            renderMatchList(matches);
        }

    } catch (error) {
        console.error('[HOME] Error loading match history:', error);
        loadingState.classList.add('hidden');
        emptyState.classList.remove('hidden');

        // Show error in empty state
        const emptyTitle = emptyState.querySelector('h3');
        emptyTitle.textContent = 'Error loading matches';
        emptyTitle.setAttribute('data-i18n', 'ERROR_LOADING_MATCHES');
    }
}

function renderMatchList(matchesData) {
    const matchList = document.getElementById('match-list');

    // Clear existing items (keep loading/empty states)
    const items = matchList.querySelectorAll('.match-item');
    items.forEach(item => item.remove());

    // Render each match
    matchesData.forEach(match => {
        const matchItem = createMatchItem(match);
        matchList.appendChild(matchItem);
    });
}

function createMatchItem(match) {
    const item = document.createElement('div');
    item.className = 'match-item';
    item.dataset.matchId = match.id;

    // Format timestamp
    const timestamp = new Date(match.last_updated || match.created_at);
    const timeStr = formatTimestamp(timestamp);

    // Progress text
    const progressText = match.status === 'active'
        ? `${match.current_round}/${match.total_rounds} rounds`
        : match.status === 'completed'
            ? `Completed · ${match.total_rounds} rounds`
            : 'Abandoned';

    item.innerHTML = `
        <div class="match-header">
            <div class="match-title">Match ${match.match_number}</div>
            <div class="match-status ${match.status}">${match.status}</div>
        </div>
        <div class="match-details">
            <div class="match-detail-item">
                <span class="match-detail-label">Stack:</span>
                <span>${match.initial_stack}</span>
            </div>
            <div class="match-detail-item">
                <span class="match-detail-label">Opponents:</span>
                <span>${match.num_opponents}</span>
            </div>
            <div class="match-detail-item">
                <span>${progressText}</span>
            </div>
        </div>
        <div class="match-timestamp">${timeStr}</div>
    `;

    // Click handler
    item.addEventListener('click', () => handleMatchClick(match));

    return item;
}

function formatTimestamp(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

function handleMatchClick(match) {
    console.log('[HOME] Match clicked:', match);

    // Store match data for game screen
    sessionStorage.setItem('current_match', JSON.stringify(match));

    if (match.status === 'active') {
        // Resume active match
        // TODO: Navigate to game screen with match resumption
        alert(`Resuming Match ${match.match_number}... (Coming soon)`);
    } else if (match.status === 'completed') {
        // View completed match (read-only)
        // TODO: Navigate to read-only game view
        alert(`Viewing completed Match ${match.match_number}... (Coming soon)`);
    } else {
        alert(`Match ${match.match_number} was abandoned`);
    }
}

// ============================================================================
// NAVIGATION
// ============================================================================

function setupEventListeners() {
    // Bottom navigation
    document.querySelectorAll('.nav-item').forEach(navItem => {
        navItem.addEventListener('click', () => {
            const view = navItem.dataset.view;
            switchView(view);
        });
    });

    // FAB - New Match
    document.getElementById('fab-new-match').addEventListener('click', handleNewMatch);

    // Settings - Save nickname
    document.getElementById('btn-save-nickname').addEventListener('click', handleSaveNickname);

    // Language buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const lang = btn.dataset.lang;
            i18n.init(lang);
            updateLanguageButtons(lang);
        });
    });
    // Bottom Sheet - Range Inputs
    setupRangeInput('match-stack', 'match-stack-value');
    setupRangeInput('match-opponents', 'match-opponents-value');
    setupRangeInput('match-rounds', 'match-rounds-value');

    // Bottom Sheet - Actions
    document.getElementById('btn-cancel-match').addEventListener('click', closeBottomSheet);
    document.getElementById('btn-start-match').addEventListener('click', startNewMatch);
    document.getElementById('new-match-overlay').addEventListener('click', closeBottomSheet);
}

function setupRangeInput(inputId, valueId) {
    const input = document.getElementById(inputId);
    const valueDisplay = document.getElementById(valueId);

    input.addEventListener('input', () => {
        valueDisplay.textContent = input.value;
    });
}

function switchView(viewName) {
    activeView = viewName;

    // Update view containers
    document.querySelectorAll('.view-container').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(`${viewName}-view`).classList.add('active');

    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.view === viewName) {
            item.classList.add('active');
        }
    });
}

// ============================================================================
// NEW MATCH
// ============================================================================

function handleNewMatch() {
    openBottomSheet();
}

function openBottomSheet() {
    const sheet = document.getElementById('new-match-sheet');
    const overlay = document.getElementById('new-match-overlay');

    overlay.classList.add('active');
    sheet.classList.add('active');
}

function closeBottomSheet() {
    const sheet = document.getElementById('new-match-sheet');
    const overlay = document.getElementById('new-match-overlay');

    overlay.classList.remove('active');
    sheet.classList.remove('active');
}

async function startNewMatch() {
    const stack = parseInt(document.getElementById('match-stack').value);
    const opponents = parseInt(document.getElementById('match-opponents').value);
    const rounds = parseInt(document.getElementById('match-rounds').value);

    // Close sheet immediately for better UX
    closeBottomSheet();

    try {
        const matchConfig = {
            nickname: currentNickname,
            initial_stack: stack,
            num_opponents: opponents,
            total_rounds: rounds
        };

        const response = await fetch('/api/match/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(matchConfig)
        });

        if (!response.ok) {
            throw new Error('Failed to create match');
        }

        const data = await response.json();
        console.log('[HOME] Match created:', data);

        // Reload match history
        await loadMatchHistory();

        // TODO: Navigate to game screen with new match
        alert(`Match ${data.match_number} created! (Game start coming soon)`);

    } catch (error) {
        console.error('[HOME] Error creating match:', error);
        alert('Failed to create match. Please try again.');
    }
}

// ============================================================================
// SETTINGS
// ============================================================================

function initializeSettings() {
    // Set nickname in settings
    document.getElementById('settings-nickname').value = currentNickname;

    // Display player ID
    if (playerId) {
        document.getElementById('player-id-display').textContent = playerId;
    }
}

async function handleSaveNickname() {
    const newNickname = document.getElementById('settings-nickname').value.trim();

    if (!newNickname) {
        alert('Nickname cannot be empty');
        return;
    }

    if (newNickname === currentNickname) {
        alert('Nickname unchanged');
        return;
    }

    // Update nickname
    currentNickname = newNickname;
    localStorage.setItem('nickname', currentNickname);

    // Update header
    document.getElementById('player-nickname').textContent = currentNickname;

    // Reload match history with new nickname
    await loadMatchHistory();

    alert('Nickname updated!');
}

function updateLanguageButtons(lang) {
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === lang);
    });
}
