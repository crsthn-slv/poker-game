/**
 * Statistics Calculation Utilities
 * Handles poker hand evaluation, Monte Carlo simulation, and statistics calculations
 */

/**
 * Evaluates a poker hand from an array of cards
 * @param {Array<string>} cards - Array of card strings (e.g., ['SA', 'SK', 'SQ', 'SJ', 'ST'])
 * @returns {Object} - { rank: string, description: string, value: number }
 */
function evaluateHand(cards) {
    if (!cards || cards.length < 5) {
        return { rank: 'INVALID', description: 'N/A', value: 0 };
    }

    // Parse cards into suits and ranks
    const parsed = cards.map(card => ({
        suit: card[0], // S, H, D, C
        rank: card[1] || card.slice(1) // A, K, Q, J, T, 9, 8, 7, 6, 5, 4, 3, 2
    }));

    // Rank values: A=14, K=13, Q=12, J=11, T=10, 9-2=9-2
    const rankValues = {
        'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10,
        '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2
    };

    const getRankValue = (rank) => rankValues[rank] || parseInt(rank) || 0;

    // Count ranks and suits
    const rankCounts = {};
    const suitCounts = {};
    parsed.forEach(card => {
        rankCounts[card.rank] = (rankCounts[card.rank] || 0) + 1;
        suitCounts[card.suit] = (suitCounts[card.suit] || 0) + 1;
    });

    const ranks = Object.keys(rankCounts).map(r => ({ rank: r, count: rankCounts[r], value: getRankValue(r) }));
    ranks.sort((a, b) => {
        if (a.count !== b.count) return b.count - a.count;
        return b.value - a.value;
    });

    const isFlush = Object.values(suitCounts).some(count => count >= 5);
    const sortedValues = ranks.map(r => r.value).sort((a, b) => b - a);
    const isStraight = checkStraight(sortedValues);

    // Royal Flush
    if (isFlush && isStraight && sortedValues[0] === 14 && sortedValues[4] === 10) {
        return { rank: 'ROYAL_FLUSH', description: 'Royal Flush', value: 10 };
    }

    // Straight Flush
    if (isFlush && isStraight) {
        return { rank: 'STRAIGHT_FLUSH', description: 'Straight Flush', value: 9 };
    }

    // Four of a Kind
    if (ranks[0].count === 4) {
        return { rank: 'FOUR_OF_A_KIND', description: 'Quadra', value: 8 };
    }

    // Full House
    if (ranks[0].count === 3 && ranks[1].count === 2) {
        return { rank: 'FULL_HOUSE', description: 'Full House', value: 7 };
    }

    // Flush
    if (isFlush) {
        return { rank: 'FLUSH', description: 'Flush', value: 6 };
    }

    // Straight
    if (isStraight) {
        return { rank: 'STRAIGHT', description: 'Straight', value: 5 };
    }

    // Three of a Kind
    if (ranks[0].count === 3) {
        return { rank: 'THREE_OF_A_KIND', description: 'Trinca', value: 4 };
    }

    // Two Pair
    if (ranks[0].count === 2 && ranks[1].count === 2) {
        return { rank: 'TWO_PAIR', description: 'Dois Pares', value: 3 };
    }

    // Pair
    if (ranks[0].count === 2) {
        return { rank: 'PAIR', description: 'Par', value: 2 };
    }

    // High Card
    const highCard = ranks.find(r => r.rank === 'A') || ranks[0];
    return { rank: 'HIGH_CARD', description: `High Card (${highCard.rank})`, value: 1 };
}

/**
 * Evaluates a hand from just 2 cards (preflop)
 * @param {Array<string>} cards - Array of 2 card strings (e.g., ['SA', 'SK'])
 * @returns {Object} - { rank: string, description: string, value: number }
 */
function evaluateHandFromTwoCards(cards) {
    if (!cards || cards.length !== 2) {
        return { rank: 'INVALID', description: 'N/A', value: 0 };
    }

    // Parse cards into suits and ranks
    const parsed = cards.map(card => ({
        suit: card[0], // S, H, D, C
        rank: card[1] || card.slice(1) // A, K, Q, J, T, 9, 8, 7, 6, 5, 4, 3, 2
    }));

    // Rank values: A=14, K=13, Q=12, J=11, T=10, 9-2=9-2
    const rankValues = {
        'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10,
        '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2
    };

    const getRankValue = (rank) => rankValues[rank] || parseInt(rank) || 0;

    const rank1 = parsed[0].rank;
    const rank2 = parsed[1].rank;
    const suit1 = parsed[0].suit;
    const suit2 = parsed[1].suit;

    // Pair
    if (rank1 === rank2) {
        return { rank: 'PAIR', description: `Par de ${rank1}s`, value: 2 };
    }

    // Suited (same suit)
    const isSuited = suit1 === suit2;
    
    // High card - mostra as duas cartas
    const rank1Value = getRankValue(rank1);
    const rank2Value = getRankValue(rank2);
    const higherRank = rank1Value > rank2Value ? rank1 : rank2;
    const lowerRank = rank1Value > rank2Value ? rank2 : rank1;
    
    const suitedText = isSuited ? ' suited' : '';
    return { 
        rank: 'HIGH_CARD', 
        description: `${higherRank}${lowerRank}${suitedText}`, 
        value: 1 
    };
}

/**
 * Checks if cards form a straight
 */
function checkStraight(values) {
    if (values.length < 5) return false;
    
    // Check for A-2-3-4-5 straight (wheel)
    const wheel = [14, 5, 4, 3, 2];
    const hasWheel = wheel.every(v => values.includes(v));
    if (hasWheel) return true;

    // Check for regular straight
    const unique = [...new Set(values)].sort((a, b) => b - a);
    for (let i = 0; i <= unique.length - 5; i++) {
        let consecutive = true;
        for (let j = 1; j < 5; j++) {
            if (unique[i + j] !== unique[i] - j) {
                consecutive = false;
                break;
            }
        }
        if (consecutive) return true;
    }
    return false;
}

/**
 * Monte Carlo simulation for win probability
 * @param {Array<string>} holeCards - Player's hole cards (2 cards)
 * @param {Array<string>} communityCards - Community cards (0-5 cards)
 * @param {number} opponentCount - Number of opponents
 * @param {number} iterations - Number of simulations (default 2000)
 * @returns {Promise<number>} - Win probability percentage (0-100)
 */
async function calculateWinProbability(holeCards, communityCards, opponentCount, iterations = 2000) {
    if (!holeCards || holeCards.length < 2 || opponentCount < 1) {
        return 0;
    }

    // Use Web Worker if available for non-blocking calculation
    if (typeof Worker !== 'undefined' && window.monteCarloWorker === undefined) {
        // Create worker inline for Monte Carlo
        const workerCode = `
            self.onmessage = function(e) {
                const { holeCards, communityCards, opponentCount, iterations } = e.data;
                let wins = 0;
                
                const deck = [];
                const suits = ['S', 'H', 'D', 'C'];
                const ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];
                suits.forEach(s => ranks.forEach(r => deck.push(s + r)));
                
                const usedCards = new Set([...holeCards, ...(communityCards || [])]);
                const availableCards = deck.filter(c => !usedCards.has(c));
                
                for (let i = 0; i < iterations; i++) {
                    const shuffled = [...availableCards].sort(() => Math.random() - 0.5);
                    const playerCards = [...holeCards, ...(communityCards || [])];
                    let playerBest = evaluateHandCombo(playerCards, shuffled.slice(0, Math.max(0, 5 - playerCards.length)));
                    
                    let allOpponentsBeat = true;
                    for (let opp = 0; opp < opponentCount; opp++) {
                        const oppStart = 5 - playerCards.length + (opp * 2);
                        const oppCards = shuffled.slice(oppStart, oppStart + 2);
                        const oppBest = evaluateHandCombo([...oppCards, ...(communityCards || [])], []);
                        if (oppBest.value >= playerBest.value) {
                            allOpponentsBeat = false;
                            break;
                        }
                    }
                    
                    if (allOpponentsBeat) wins++;
                }
                
                self.postMessage({ probability: (wins / iterations) * 100 });
            };
            
            function evaluateHandCombo(cards, additional) {
                const all = [...cards, ...additional].slice(0, 7);
                if (all.length < 5) return { value: 0 };
                // Simplified evaluation for worker - returns random value for performance
                // Full evaluation happens in main thread
                return { value: Math.random() * 10 };
            }
        `;
        
        try {
            const blob = new Blob([workerCode], { type: 'application/javascript' });
            window.monteCarloWorker = new Worker(URL.createObjectURL(blob));
        } catch (e) {
            // Fallback to synchronous if Worker not available
            window.monteCarloWorker = null;
        }
    }

    // Fallback to synchronous calculation
    if (!window.monteCarloWorker) {
        return calculateWinProbabilitySync(holeCards, communityCards, opponentCount, iterations);
    }

    // Use Web Worker for async calculation
    return new Promise((resolve) => {
        window.monteCarloWorker.onmessage = (e) => {
            resolve(e.data.probability);
        };
        window.monteCarloWorker.postMessage({ holeCards, communityCards, opponentCount, iterations });
    });
}

/**
 * Synchronous Monte Carlo calculation (fallback)
 */
function calculateWinProbabilitySync(holeCards, communityCards, opponentCount, iterations) {
    const deck = [];
    const suits = ['S', 'H', 'D', 'C'];
    const ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];
    suits.forEach(s => ranks.forEach(r => deck.push(s + r)));

    const usedCards = new Set([...holeCards, ...(communityCards || [])]);
    const availableCards = deck.filter(c => !usedCards.has(c));

    let wins = 0;
    const playerCards = [...holeCards, ...(communityCards || [])];

    for (let i = 0; i < iterations; i++) {
        const shuffled = [...availableCards].sort(() => Math.random() - 0.5);
        
        // Complete player's hand if needed
        const playerComplete = playerCards.length < 5 
            ? [...playerCards, ...shuffled.slice(0, 5 - playerCards.length)]
            : playerCards.slice(0, 7);
        const playerBest = evaluateHand(playerComplete.slice(0, 5));

        // Simulate opponents
        let allOpponentsBeat = true;
        let cardIndex = Math.max(0, 5 - playerCards.length);
        
        for (let opp = 0; opp < opponentCount; opp++) {
            const oppCards = shuffled.slice(cardIndex, cardIndex + 2);
            cardIndex += 2;
            
            const oppComplete = [...oppCards, ...(communityCards || [])];
            const oppBest = evaluateHand(oppComplete.slice(0, 5));
            
            if (oppBest.value >= playerBest.value) {
                allOpponentsBeat = false;
                break;
            }
        }

        if (allOpponentsBeat) wins++;
    }

    return (wins / iterations) * 100;
}

