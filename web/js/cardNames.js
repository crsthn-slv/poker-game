/**
 * Mapeamento de códigos de cartas para nomes em português
 * Formato: 'SA' -> 'Ás de Espadas'
 */

const cardNames = {
    // Espadas (Spades)
    'SA': 'Ás de Espadas',
    'S2': '2 de Espadas',
    'S3': '3 de Espadas',
    'S4': '4 de Espadas',
    'S5': '5 de Espadas',
    'S6': '6 de Espadas',
    'S7': '7 de Espadas',
    'S8': '8 de Espadas',
    'S9': '9 de Espadas',
    'ST': '10 de Espadas',
    'SJ': 'Valete de Espadas',
    'SQ': 'Dama de Espadas',
    'SK': 'Rei de Espadas',
    
    // Copas (Hearts)
    'HA': 'Ás de Copas',
    'H2': '2 de Copas',
    'H3': '3 de Copas',
    'H4': '4 de Copas',
    'H5': '5 de Copas',
    'H6': '6 de Copas',
    'H7': '7 de Copas',
    'H8': '8 de Copas',
    'H9': '9 de Copas',
    'HT': '10 de Copas',
    'HJ': 'Valete de Copas',
    'HQ': 'Dama de Copas',
    'HK': 'Rei de Copas',
    
    // Ouros (Diamonds)
    'DA': 'Ás de Ouros',
    'D2': '2 de Ouros',
    'D3': '3 de Ouros',
    'D4': '4 de Ouros',
    'D5': '5 de Ouros',
    'D6': '6 de Ouros',
    'D7': '7 de Ouros',
    'D8': '8 de Ouros',
    'D9': '9 de Ouros',
    'DT': '10 de Ouros',
    'DJ': 'Valete de Ouros',
    'DQ': 'Dama de Ouros',
    'DK': 'Rei de Ouros',
    
    // Paus (Clubs)
    'CA': 'Ás de Paus',
    'C2': '2 de Paus',
    'C3': '3 de Paus',
    'C4': '4 de Paus',
    'C5': '5 de Paus',
    'C6': '6 de Paus',
    'C7': '7 de Paus',
    'C8': '8 de Paus',
    'C9': '9 de Paus',
    'CT': '10 de Paus',
    'CJ': 'Valete de Paus',
    'CQ': 'Dama de Paus',
    'CK': 'Rei de Paus'
};

/**
 * Converte código da carta para nome completo
 * @param {string} cardCode - Código da carta (ex: 'S6', 'HA')
 * @returns {string} - Nome completo da carta (ex: '6 de Espadas', 'Ás de Copas')
 */
function getCardName(cardCode) {
    if (!cardCode) return cardCode;
    return cardNames[cardCode] || cardCode;
}

/**
 * Converte array de códigos de cartas para array de nomes
 * @param {Array<string>} cards - Array de códigos de cartas
 * @returns {Array<string>} - Array de nomes de cartas
 */
function getCardNames(cards) {
    if (!Array.isArray(cards)) return [];
    return cards.map(card => getCardName(card));
}

