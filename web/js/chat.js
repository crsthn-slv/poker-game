/**
 * Chat Message Data Structures and Utilities
 * Handles chat message creation, rendering, and management
 */

/**
 * Chat message data structure
 * @typedef {Object} ChatMessage
 * @property {string} messageId - Unique identifier
 * @property {string} messageType - Type: 'bet', 'card_reveal', 'bot_message'
 * @property {number} timestamp - Timestamp in milliseconds
 * @property {string} [playerName] - Player name (for bet messages)
 * @property {string} [action] - Action type: 'fold', 'call', 'raise', 'all-in'
 * @property {number} [amount] - Bet amount
 * @property {string} content - Message text content
 * @property {string} [icon] - Icon identifier
 * @property {string} [color] - Color code
 */

/**
 * Creates a bet message
 * @param {string} playerName - Player name
 * @param {string} action - Action type
 * @param {number} [amount] - Bet amount
 * @returns {ChatMessage}
 */
function createBetMessage(playerName, action, amount = null) {
    const messageId = `bet_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const actionText = action === 'all-in' ? 'All-in' : action.charAt(0).toUpperCase() + action.slice(1);
    const amountText = amount !== null && amount !== undefined ? ` ${amount}` : '';
    const content = `${playerName}: ${actionText}${amountText}`;

    // Color mapping based on action type
    const colorMap = {
        'fold': '#018bf6',    // Blue
        'call': '#3a9f75',    // Green
        'raise': '#fa8c01',   // Orange
        'all-in': '#ef4637'   // Red
    };

    return {
        messageId,
        messageType: 'bet',
        timestamp: Date.now(),
        playerName,
        action,
        amount,
        content,
        icon: 'action',
        color: colorMap[action] || '#ffffff'
    };
}

/**
 * Creates a card reveal message
 * @param {string} street - Street name: 'flop', 'turn', 'river'
 * @param {Array<string>} cards - Array of card strings
 * @returns {ChatMessage}
 */
function createCardRevealMessage(street, cards) {
    const messageId = `reveal_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const streetNames = {
        'flop': 'Flop',
        'turn': 'Turn',
        'river': 'River'
    };
    const streetText = streetNames[street] || street.charAt(0).toUpperCase() + street.slice(1);
    const cardsText = cards.join(' ');
    const content = `${streetText}: ${cardsText}`;

    return {
        messageId,
        messageType: 'card_reveal',
        timestamp: Date.now(),
        content,
        icon: 'card',
        color: '#018bf6' // Blue
    };
}

/**
 * Creates a bot message
 * @param {string} content - Message content (max 50 characters)
 * @param {string} [botName] - Bot name
 * @returns {ChatMessage}
 */
function createBotMessage(content, botName = null) {
    // Truncate to 50 characters
    const truncatedContent = content.length > 50 ? content.substring(0, 47) + '...' : content;
    const messageId = `bot_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const fullContent = botName ? `${botName}: ${truncatedContent}` : truncatedContent;

    return {
        messageId,
        messageType: 'bot_message',
        timestamp: Date.now(),
        content: fullContent,
        icon: 'bot',
        color: '#fa8c01' // Orange (8-bit style)
    };
}

/**
 * Renders a chat message as DOM element
 * @param {ChatMessage} message - Chat message object
 * @returns {HTMLElement} - DOM element
 */
function renderChatMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message chat-${message.messageType}`;
    messageDiv.setAttribute('data-message-id', message.messageId);
    
    // Apply color styling
    if (message.color) {
        messageDiv.style.color = message.color;
        messageDiv.style.borderLeft = `3px solid ${message.color}`;
    }

    // Add icon if specified
    if (message.icon) {
        const iconSpan = document.createElement('span');
        iconSpan.className = `chat-icon chat-icon-${message.icon}`;
        iconSpan.textContent = getIconSymbol(message.icon);
        messageDiv.appendChild(iconSpan);
    }

    // Add content
    const contentSpan = document.createElement('span');
    contentSpan.className = 'chat-content';
    contentSpan.textContent = message.content;
    messageDiv.appendChild(contentSpan);

    // Add timestamp (optional, for debugging)
    const timestampSpan = document.createElement('span');
    timestampSpan.className = 'chat-timestamp';
    timestampSpan.textContent = new Date(message.timestamp).toLocaleTimeString();
    timestampSpan.style.display = 'none'; // Hidden by default
    messageDiv.appendChild(timestampSpan);

    return messageDiv;
}

/**
 * Gets icon symbol for message type
 * @param {string} iconType - Icon type
 * @returns {string} - Icon symbol
 */
function getIconSymbol(iconType) {
    const icons = {
        'action': '⚡',
        'card': '🃏',
        'bot': '🤖'
    };
    return icons[iconType] || '•';
}

/**
 * Chat message queue for rapid updates
 */
class ChatMessageQueue {
    constructor() {
        this.queue = [];
        this.processedIds = new Set();
        this.isProcessing = false;
    }

    /**
     * Adds message to queue if not duplicate
     * @param {ChatMessage} message - Message to add
     */
    add(message) {
        if (!this.processedIds.has(message.messageId)) {
            this.queue.push(message);
            this.processedIds.add(message.messageId);
        }
    }

    /**
     * Processes queue and renders messages
     * @param {HTMLElement} container - Chat container element
     * @param {boolean} autoScroll - Whether to auto-scroll
     */
    process(container, autoScroll = true) {
        if (this.isProcessing || this.queue.length === 0) return;

        this.isProcessing = true;

        while (this.queue.length > 0) {
            const message = this.queue.shift();
            const messageElement = renderChatMessage(message);
            container.appendChild(messageElement);
        }

        if (autoScroll) {
            container.scrollTop = container.scrollHeight;
        }

        this.isProcessing = false;
    }

    /**
     * Clears queue
     */
    clear() {
        this.queue = [];
        this.processedIds.clear();
    }
}

/**
 * Global chat message queue instance
 */
const chatMessageQueue = new ChatMessageQueue();

/**
 * Detects if user has scrolled up (prevents auto-scroll)
 * @param {HTMLElement} container - Chat container element
 * @returns {boolean} - True if user scrolled up
 */
function hasUserScrolledUp(container) {
    if (!container) return false;
    const threshold = 50; // pixels from bottom
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    return distanceFromBottom > threshold;
}

/**
 * Wraps long bot messages to fit chat width
 * @param {string} text - Message text
 * @param {number} maxWidth - Maximum width in characters
 * @returns {string} - Wrapped text
 */
function wrapBotMessage(text, maxWidth = 50) {
    if (text.length <= maxWidth) return text;
    
    const words = text.split(' ');
    const lines = [];
    let currentLine = '';

    words.forEach(word => {
        if ((currentLine + word).length <= maxWidth) {
            currentLine += (currentLine ? ' ' : '') + word;
        } else {
            if (currentLine) lines.push(currentLine);
            currentLine = word.length > maxWidth ? word.substring(0, maxWidth) : word;
        }
    });

    if (currentLine) lines.push(currentLine);
    return lines.join('\n');
}

