let gameInterval = null;
let playerName = localStorage.getItem('playerName') || 'Jogador';
let playerUuid = null;
let lastRoundCount = 0;
let lastRoundEnded = null; // Rastreia o estado anterior de round_ended para detectar mudanças reais
let modalDismissedForRound = null; // Armazena o round_count para o qual a modal foi fechada

// Sistema de inicialização estável (baseado em PyPokerGUI)
let isInitializing = false;
let initializationCount = 0;
let playerNotFoundCount = 0; // Contador para grace period antes de marcar jogador como eliminado

// Cache de estado para evitar re-renderizações desnecessárias
let lastSeatsState = null; // JSON string dos seats para comparação
let lastCurrentPlayerUuid = null; // Último jogador atual
let lastGameStateHash = null; // Hash do gameState para throttle no polling

// Sistema de debug (desabilitado em produção)
// Por padrão desabilitado. Para ativar, defina DEBUG_MODE=true no console do navegador
const DEBUG_MODE = false; // Desabilitado por padrão em produção

function debugLog(message, data = null) {
    if (DEBUG_MODE) {
        const timestamp = new Date().toISOString();
        console.log(`[${timestamp}] DEBUG: ${message}`, data || '');
    }
}

function safeGet(obj, path, defaultValue = null) {
    try {
        const keys = path.split('.');
        let result = obj;
        for (const key of keys) {
            if (result == null || typeof result !== 'object') {
                return defaultValue;
            }
            result = result[key];
        }
        return result != null ? result : defaultValue;
    } catch (e) {
        debugLog(`Erro em safeGet para path: ${path}`, e);
        return defaultValue;
    }
}

// Mapeamento de cartas para imagens
function getCardImage(card) {
    if (!card) return null;
    // Formato: 'SA' -> 'card_SA.png'
    return `images/card_${card}.png`;
}

// Renderiza uma carta
function renderCard(card, container, className = '') {
    const cardDiv = document.createElement('div');
    cardDiv.className = `card ${className}`;

    if (card) {
        const img = document.createElement('img');
        img.src = getCardImage(card);
        img.alt = card;
        img.onerror = () => {
            cardDiv.className = `card card-back ${className}`;
            cardDiv.textContent = card || '?';
        };
        cardDiv.appendChild(img);
    } else {
        cardDiv.className = `card card-back ${className}`;
        // cardDiv.textContent = '?'; // Removido ponto de interrogação
    }

    container.appendChild(cardDiv);
}

// Atualiza cartas comunitárias
function updateCommunityCards(communityCard) {
    const container = document.getElementById('communityCards');
    container.innerHTML = '';

    if (communityCard && communityCard.length > 0) {
        communityCard.forEach(card => {
            const cardDiv = document.createElement('div');
            cardDiv.className = 'community-card';
            const img = document.createElement('img');
            img.src = getCardImage(card);
            img.alt = card;
            img.onerror = () => {
                cardDiv.textContent = card || '?';
            };
            cardDiv.appendChild(img);
            container.appendChild(cardDiv);
        });
    }
}

// Posições para 6 bots (linha superior)
function getBotPosition(botIndex, totalBots) {
    if (totalBots <= 1) {
        return { position: 'custom', left: '50%', top: '15%' };
    }
    // Distribui horizontalmente no topo (10% a 90%)
    const startX = 10;
    const endX = 90;
    const step = (endX - startX) / (totalBots - 1);

    return {
        position: 'custom',
        left: `${startX + (botIndex * step)}%`,
        top: '15%' // Fixo no topo
    };
}

// Função auxiliar para comparar se dados do seat mudaram
function seatDataChanged(seat, playerDiv, currentPlayerUuid) {
    if (!playerDiv || !seat) return true;
    
    // Compara dados críticos armazenados no elemento
    const storedStack = playerDiv.getAttribute('data-stack');
    const storedState = playerDiv.getAttribute('data-state');
    const storedCurrentPlayer = playerDiv.getAttribute('data-current-player');
    
    const currentStack = String(seat.stack || 0);
    const currentState = seat.state || '';
    const currentIsCurrentPlayer = String(seat.uuid === currentPlayerUuid);
    
    return storedStack !== currentStack || 
           storedState !== currentState || 
           storedCurrentPlayer !== currentIsCurrentPlayer;
}

// Renderiza jogadores conforme layout do Figma (otimizado)
function renderPlayers(seats, currentPlayerUuid, playerUuid) {
    const container = document.getElementById('playersContainer');
    if (!container) return;

    // Filtra apenas jogadores participando
    const activeSeats = seats.filter(s => s.state === 'participating' || s.state === 'folded');
    const activeUuids = activeSeats.map(s => s.uuid);

    // Remove jogadores que saíram
    const existingSeats = container.querySelectorAll('.player-seat');
    existingSeats.forEach(seat => {
        if (!activeUuids.includes(seat.getAttribute('data-uuid'))) {
            seat.remove();
        }
    });

    // Separa jogador principal dos bots
    const playerSeat = activeSeats.find(s => s.uuid === playerUuid);
    const botSeats = activeSeats.filter(s => s.uuid !== playerUuid);

    // Atualiza ou cria jogador principal
    if (playerSeat) {
        let playerDiv = container.querySelector(`.player-seat[data-uuid="${playerUuid}"]`);
        if (!playerDiv) {
            playerDiv = createPlayerElement(playerSeat, playerUuid, currentPlayerUuid, true);
            playerDiv.className += ' player-main';
            container.appendChild(playerDiv);
        } else {
            // Só atualiza se dados mudaram
            if (seatDataChanged(playerSeat, playerDiv, currentPlayerUuid)) {
                updatePlayerElement(playerDiv, playerSeat, playerUuid, currentPlayerUuid, true);
            }
        }
    }

    // Atualiza ou cria bots
    botSeats.forEach((seat, index) => {
        let botDiv = container.querySelector(`.player-seat[data-uuid="${seat.uuid}"]`);
        const position = getBotPosition(index, botSeats.length);

        if (!botDiv) {
            botDiv = createPlayerElement(seat, playerUuid, currentPlayerUuid, false);
            botDiv.style.position = 'absolute';
            botDiv.className += ` bot-position-${position.position}`;
            container.appendChild(botDiv);
        } else {
            // Só atualiza se dados mudaram
            if (seatDataChanged(seat, botDiv, currentPlayerUuid)) {
                updatePlayerElement(botDiv, seat, playerUuid, currentPlayerUuid, false);
            }
        }

        // Atualiza posição (pode mudar se bots saírem/entrarem)
        botDiv.style.left = position.left;
        botDiv.style.top = position.top;
    });
}

// Cria elemento de jogador
function createPlayerElement(seat, playerUuid, currentPlayerUuid, isMainPlayer) {
    const isCurrentPlayer = seat.uuid === currentPlayerUuid;
    const isPlayer = seat.uuid === playerUuid;

    const playerDiv = document.createElement('div');
    playerDiv.className = 'player-seat';
    playerDiv.setAttribute('data-uuid', seat.uuid);

    // Container principal
    const playerContent = document.createElement('div');
    playerContent.className = 'player-content';

    // Container de cartas (sempre embaixo do nome no Figma)
    const cardsContainer = document.createElement('div');
    cardsContainer.className = 'player-cards-container';

    // Renderiza cartas (sempre mostra, viradas para bots, abertas para jogador)
    if (isPlayer) {
        // Cartas do jogador serão atualizadas separadamente
        // Usa placeholders iniciais em vez de back cards
        for (let i = 0; i < 2; i++) {
            const placeholder = document.createElement('div');
            placeholder.className = 'player-card placeholder';
            placeholder.style.border = '2px dashed rgba(255, 255, 255, 0.2)';
            placeholder.style.background = 'transparent';
            cardsContainer.appendChild(placeholder);
        }
    } else {
        // Cartas viradas para bots
        renderCard(null, cardsContainer, 'player-card back bot-card');
        renderCard(null, cardsContainer, 'player-card back bot-card');
    }

    // Nome do jogador (acima das cartas)
    const nameDiv = document.createElement('div');
    nameDiv.className = 'player-name';
    nameDiv.style.display = 'flex';
    nameDiv.style.alignItems = 'center';
    nameDiv.style.gap = '8px';
    nameDiv.style.justifyContent = 'center';
    
    // Adiciona bolinha indicadora se for a vez do jogador ou bot
    if (isCurrentPlayer) {
        debugLog('Adicionando indicador de turno', {
            seatUuid: seat.uuid,
            isCurrentPlayer: isCurrentPlayer,
            isPlayer: isPlayer
        });
        
        const turnIndicator = document.createElement('div');
        turnIndicator.className = 'turn-indicator';
        turnIndicator.style.width = '12px';
        turnIndicator.style.height = '12px';
        turnIndicator.style.borderRadius = '50%';
        // Verde para jogador humano, azul para bots
        turnIndicator.style.backgroundColor = isPlayer ? '#3a9f75' : '#018bf6';
        turnIndicator.style.boxShadow = isPlayer ? '0 0 8px rgba(58, 159, 117, 0.8)' : '0 0 8px rgba(1, 139, 246, 0.8)';
        turnIndicator.style.animation = 'pulse 1.5s ease-in-out infinite';
        nameDiv.appendChild(turnIndicator);
    }
    
    const nameText = document.createElement('span');
    nameText.textContent = seat.name;
    nameDiv.appendChild(nameText);

    // Informações do jogador (stack e aposta)
    const infoDiv = document.createElement('div');
    infoDiv.className = 'player-info';

    // Stack
    const stackDiv = document.createElement('div');
    stackDiv.className = 'player-stack';
    const chipImg = document.createElement('img');
    chipImg.src = 'images/poker_pot.png';
    chipImg.className = 'chip-icon-small';
    chipImg.alt = 'chip';
    chipImg.style.width = '32px';
    chipImg.style.height = '32px';
    chipImg.style.objectFit = 'contain';
    stackDiv.appendChild(chipImg);
    const stackValue = document.createElement('span');
    stackValue.textContent = seat.stack || 0;
    stackDiv.appendChild(stackValue);
    infoDiv.appendChild(stackDiv);

    // Última jogada (sempre mostra, mesmo que vazio inicialmente)
    const lastActionDiv = document.createElement('div');
    lastActionDiv.className = 'player-last-action';
    lastActionDiv.id = `last-action-${seat.uuid}`;
    lastActionDiv.style.fontSize = '12px';
    lastActionDiv.style.color = '#fa8c01';
    lastActionDiv.style.marginTop = '4px';
    lastActionDiv.style.minHeight = '16px';
    lastActionDiv.textContent = '';
    infoDiv.appendChild(lastActionDiv);

    // Aposta (se houver)
    if (seat.paid && seat.paid > 0) {
        const betDiv = document.createElement('div');
        betDiv.className = 'player-bet';
        betDiv.textContent = `Aposta: ${seat.paid}`;
        infoDiv.appendChild(betDiv);
    }

    // Monta estrutura: cartas -> nome -> info -> status
    playerContent.appendChild(cardsContainer);
    playerContent.appendChild(nameDiv);
    playerContent.appendChild(infoDiv);

    // Status da ação (Fold, Raise, etc)
    const statusDiv = document.createElement('div');
    statusDiv.className = 'player-status';
    statusDiv.id = `status-${seat.uuid}`;
    // Recupera status anterior se existir (para não piscar/sumir rápido demais)
    const oldStatus = document.getElementById(`status-${seat.uuid}`);
    if (oldStatus) statusDiv.textContent = oldStatus.textContent;

    // Se o jogador foldou, mostra FOLDED
    if (seat.state === 'folded') {
        statusDiv.textContent = 'FOLD';
        playerDiv.style.opacity = '0.6'; // Opacidade reduzida para quem saiu
    }

    playerContent.appendChild(statusDiv);
    playerDiv.appendChild(playerContent);

    // Adiciona indicador de turno
    if (isCurrentPlayer) {
        playerDiv.classList.add('active-turn');
    }

    // Classes específicas para bots (menores)
    if (!isMainPlayer) {
        cardsContainer.classList.add('bot-card-container');
        nameDiv.classList.add('bot-name');
        infoDiv.classList.add('bot-info');
        // Cartas dentro do container serão estilizadas no renderCard ou CSS global
    }
    
    // Armazena dados no elemento para comparação futura (otimização)
    playerDiv.setAttribute('data-stack', String(seat.stack || 0));
    playerDiv.setAttribute('data-state', seat.state || '');
    playerDiv.setAttribute('data-current-player', String(isCurrentPlayer));

    return playerDiv;
}

// Atualiza elemento de jogador existente
function updatePlayerElement(playerDiv, seat, playerUuid, currentPlayerUuid, isMainPlayer) {
    const isCurrentPlayer = seat.uuid === currentPlayerUuid;
    
    // Armazena dados no elemento para comparação futura (otimização)
    playerDiv.setAttribute('data-stack', String(seat.stack || 0));
    playerDiv.setAttribute('data-state', seat.state || '');
    playerDiv.setAttribute('data-current-player', String(isCurrentPlayer));

    // Atualiza classes de turno
    if (isCurrentPlayer) {
        playerDiv.classList.add('active-turn');
    } else {
        playerDiv.classList.remove('active-turn');
    }

    // Atualiza bolinha indicadora no nome
    const nameDiv = playerDiv.querySelector('.player-name');
    if (nameDiv) {
        let turnIndicator = nameDiv.querySelector('.turn-indicator');
        const isPlayer = seat.uuid === playerUuid;
        
        if (isCurrentPlayer && !turnIndicator) {
            // Adiciona bolinha se não existir
            debugLog('Adicionando indicador de turno em updatePlayerElement', {
                seatUuid: seat.uuid,
                isCurrentPlayer: isCurrentPlayer,
                isPlayer: isPlayer
            });
            
            turnIndicator = document.createElement('div');
            turnIndicator.className = 'turn-indicator';
            turnIndicator.style.width = '12px';
            turnIndicator.style.height = '12px';
            turnIndicator.style.borderRadius = '50%';
            // Verde para jogador humano, azul para bots
            turnIndicator.style.backgroundColor = isPlayer ? '#3a9f75' : '#018bf6';
            turnIndicator.style.boxShadow = isPlayer ? '0 0 8px rgba(58, 159, 117, 0.8)' : '0 0 8px rgba(1, 139, 246, 0.8)';
            turnIndicator.style.animation = 'pulse 1.5s ease-in-out infinite';
            const nameText = nameDiv.querySelector('span');
            if (nameText) {
                nameDiv.insertBefore(turnIndicator, nameText);
            } else {
                nameDiv.appendChild(turnIndicator);
            }
        } else if (isCurrentPlayer && turnIndicator) {
            // Atualiza cor se já existe (pode ter mudado de jogador para bot ou vice-versa)
            turnIndicator.style.backgroundColor = isPlayer ? '#3a9f75' : '#018bf6';
            turnIndicator.style.boxShadow = isPlayer ? '0 0 8px rgba(58, 159, 117, 0.8)' : '0 0 8px rgba(1, 139, 246, 0.8)';
        } else if (!isCurrentPlayer && turnIndicator) {
            // Remove bolinha se não for mais a vez
            debugLog('Removendo indicador de turno', { seatUuid: seat.uuid });
            turnIndicator.remove();
        }
    }

    // Atualiza Stack
    const stackValue = playerDiv.querySelector('.player-stack span');
    if (stackValue) stackValue.textContent = seat.stack || 0;

    // Atualiza Aposta
    let betDiv = playerDiv.querySelector('.player-bet');
    if (seat.paid && seat.paid > 0) {
        if (!betDiv) {
            betDiv = document.createElement('div');
            betDiv.className = 'player-bet';
            playerDiv.querySelector('.player-info').appendChild(betDiv);
        }
        betDiv.textContent = `Aposta: ${seat.paid}`;
    } else if (betDiv) {
        betDiv.remove();
    }

    // Atualiza Status (Fold)
    const statusDiv = playerDiv.querySelector('.player-status');
    if (seat.state === 'folded') {
        statusDiv.textContent = 'FOLD';
        playerDiv.style.opacity = '0.6';
    } else {
        // Se não estiver folded, mantemos o texto de ação temporária (gerido pelo updateGameInfo)
        // ou limpamos se mudou de estado (ex: nova rodada)
        if (statusDiv.textContent === 'FOLD') {
            statusDiv.textContent = '';
            playerDiv.style.opacity = '1';
        }
    }

    // NÃO atualizamos cartas aqui para o jogador principal (feito via updatePlayerCards)
    // Para bots, as cartas são estáticas (back cards), então não precisa mexer
}

// Atualiza cartas do jogador
function updatePlayerCards(holeCard) {
    if (!playerUuid) return;

    const playerSeat = document.querySelector(`.player-seat[data-uuid="${playerUuid}"]`);
    if (!playerSeat) return;

    const cardsContainer = playerSeat.querySelector('.player-cards-container');
    if (!cardsContainer) return;

    // Se já tiver cartas renderizadas e forem as mesmas, não recria (evita piscar)
    // Mas se holeCard for fornecido, forçamos atualização para garantir visibilidade
    cardsContainer.innerHTML = '';

    if (holeCard && holeCard.length > 0) {
        holeCard.forEach(card => {
            renderCard(card, cardsContainer, 'player-card');
        });
    } else {
        // Se não houver cartas, mostra placeholders vazios (não back cards) para manter layout
        // O usuário pediu "nunca com uma backcard"
        for (let i = 0; i < 2; i++) {
            const placeholder = document.createElement('div');
            placeholder.className = 'player-card placeholder';
            placeholder.style.border = '2px dashed rgba(255, 255, 255, 0.2)';
            placeholder.style.background = 'transparent';
            cardsContainer.appendChild(placeholder);
        }
    }
}

// Atualiza informações do jogo
function updateGameInfo(gameState) {
    try {
        debugLog('=== updateGameInfo INICIADO ===', {
            gameState: gameState,
            playerUuid: playerUuid,
            lastRoundCount: lastRoundCount,
            isInitializing: isInitializing,
            initializationCount: initializationCount
        });
        
        if (!gameState || typeof gameState !== 'object') {
            debugLog('gameState inválido', gameState);
            return;
        }

        // Sistema de inicialização estável (baseado em PyPokerGUI)
        // Aguarda 2 iterações antes de considerar estado estável
        if (isInitializing) {
            initializationCount++;
            // Durante inicialização, atualiza lastRoundCount se disponível
            if (gameState.current_round && gameState.current_round.round_count) {
                lastRoundCount = gameState.current_round.round_count;
            }
            if (initializationCount >= 2) {
                isInitializing = false;
                debugLog('Inicialização concluída, estado estável', {
                    initializationCount: initializationCount,
                    lastRoundCount: lastRoundCount
                });
            } else {
                debugLog('Aguardando estabilização inicial', {
                    initializationCount: initializationCount,
                    lastRoundCount: lastRoundCount
                });
                return; // Não processa durante inicialização
            }
        }

        let round = gameState.current_round;
        debugLog('Round atual', {
            round: round,
            round_ended: round?.round_ended,
            round_count: round?.round_count,
            is_player_turn: round?.is_player_turn,
            thinking_uuid: gameState.thinking_uuid,
            has_final_stacks: !!round?.final_stacks,
            has_winners: !!round?.winners
        });
        
        if (!round || typeof round !== 'object') {
            debugLog('round inválido', round);
            return;
        }

        // Guarda o estado original do round antes de qualquer modificação
        const originalRound = round;
        
        // Verifica se a modal já está visível
        const modal = document.getElementById('roundEndModal');
        const isModalVisible = modal && modal.style.display === 'flex';
        
        // Verifica se o round terminou
        // Pode ser detectado por: round_ended === true OU pela presença de final_stacks/winners
        const roundEnded = round.round_ended === true || 
                          (round.final_stacks && typeof round.final_stacks === 'object' && Object.keys(round.final_stacks).length > 0) ||
                          (round.winners && Array.isArray(round.winners) && round.winners.length > 0);
        
        if (roundEnded && !round.round_ended) {
            // Se detectamos fim de round mas round_ended não está True, força para True
            debugLog('Fim de round detectado por final_stacks/winners, mas round_ended não está True', {
                has_final_stacks: !!round.final_stacks,
                has_winners: !!round.winners,
                round_ended: round.round_ended
            });
        }
        
        if (roundEnded) {
            const currentRoundCount = round.round_count || 0;
            
            // Se a modal já foi fechada para este round, limpa dados de fim de round
            // para permitir processamento normal do jogo
            if (modalDismissedForRound === currentRoundCount) {
                debugLog('Modal já foi fechada para este round, limpando dados de fim de round', {
                    round_count: currentRoundCount,
                    modalDismissedForRound: modalDismissedForRound,
                    isModalVisible: isModalVisible
                });
                
                // Se a modal ainda está visível, não faz nada (aguarda que seja fechada)
                if (isModalVisible) {
                    debugLog('Modal ainda está visível, aguardando fechamento', {
                        round_count: currentRoundCount
                    });
                    return;
                }
                
                // Limpa final_stacks/winners do estado local para permitir processamento normal
                // Cria uma cópia do round sem os dados de fim de round
                const cleanedRound = { ...round };
                delete cleanedRound.final_stacks;
                delete cleanedRound.winners;
                delete cleanedRound.pot_amount;
                
                // Continua processamento normalmente com o round "limpo"
                // Não retorna, permite que o código continue abaixo
                round = cleanedRound;
            } else {
                // Se modal não foi fechada e não está visível, mostra normalmente
                if (!isModalVisible) {
                    debugLog('=== ROUND TERMINOU - Mostrando modal ===', {
                        round_ended: round.round_ended,
                        has_final_stacks: !!round.final_stacks,
                        has_winners: !!round.winners,
                        round_count: currentRoundCount
                    });
                    
                    // Atualiza contador de rounds quando o round termina
                    try {
                        const roundInfo = document.getElementById('roundInfo');
                        if (roundInfo && round.round_count && typeof round.round_count === 'number') {
                            roundInfo.textContent = `${round.round_count}/10`;
                            lastRoundCount = round.round_count;
                        }
                    } catch (e) {
                        debugLog('Erro ao atualizar roundInfo no fim do round', e);
                    }
                    
                    showRoundEndModal(round);
                    // Mantém botões visíveis mas desabilitados
                    showPlayerActions(null, null, false);
                    return;
                } else {
                    // Modal já está visível, não precisa mostrar novamente
                    debugLog('Modal já está visível, não mostrando novamente', {
                        round_count: currentRoundCount
                    });
                    return;
                }
            }
        }
            

        // Verifica se um novo round começou usando múltiplos sinais
        // Detecta novo round quando:
        // 1. round_count aumentou (mudança definitiva) OU
        // 2. round_ended mudou de true para false (transição real de fim para início) E final_stacks/winners desapareceram
        // IMPORTANTE: Só detecta após inicialização e se lastRoundCount > 0 (não no primeiro round)
        if (originalRound.round_count && typeof originalRound.round_count === 'number') {
            const roundCountChanged = originalRound.round_count !== lastRoundCount;
            
            // Detecta mudança REAL de round_ended: de true para false (não apenas estar como false)
            const roundEndedChanged = lastRoundEnded === true && originalRound.round_ended === false;
            
            // Verifica desaparecimento de final_stacks/winners no estado ORIGINAL do servidor
            const originalFinalStacksDisappeared = !originalRound.final_stacks || (typeof originalRound.final_stacks === 'object' && Object.keys(originalRound.final_stacks).length === 0);
            const originalWinnersDisappeared = !originalRound.winners || (Array.isArray(originalRound.winners) && originalRound.winners.length === 0);
            const noMoreEndData = originalFinalStacksDisappeared && originalWinnersDisappeared;
            
            // Verifica se há dados de round_state atualizados (sinal de novo round)
            const roundState = originalRound.round_state || {};
            const hasUpdatedSeats = Array.isArray(roundState.seats) && roundState.seats.length > 0;
            const hasUpdatedPot = roundState.pot && typeof roundState.pot === 'object';
            
            // Só detecta novo round se:
            // 1. Não estiver inicializando (aguarda estabilização)
            // 2. lastRoundCount > 0 (não é o primeiro round)
            // 3. round_count realmente mudou (mais confiável) OU
            // 4. round_ended mudou de true para false E não há mais dados de fim de round
            const newRoundDetected = !isInitializing && lastRoundCount > 0 && (roundCountChanged || (roundEndedChanged && noMoreEndData));
            
            console.log('🟢 [DEBUG UPDATE GAME INFO] Verificando novo round:', {
                originalRoundCount: originalRound.round_count,
                lastRoundCount: lastRoundCount,
                roundCountChanged: roundCountChanged,
                lastRoundEnded: lastRoundEnded,
                currentRoundEnded: originalRound.round_ended,
                roundEndedChanged: roundEndedChanged,
                originalFinalStacksDisappeared: originalFinalStacksDisappeared,
                originalWinnersDisappeared: originalWinnersDisappeared,
                noMoreEndData: noMoreEndData,
                hasUpdatedSeats: hasUpdatedSeats,
                hasUpdatedPot: hasUpdatedPot,
                isInitializing: isInitializing,
                newRoundDetected: newRoundDetected,
                modalDismissedForRound: modalDismissedForRound
            });
            
            if (newRoundDetected) {
                console.log('🟢 [DEBUG UPDATE GAME INFO] ✅ NOVO ROUND DETECTADO!', {
                    oldRoundCount: lastRoundCount,
                    newRoundCount: originalRound.round_count,
                    roundEnded: originalRound.round_ended,
                    lastRoundEnded: lastRoundEnded,
                    roundCountChanged: roundCountChanged,
                    roundEndedChanged: roundEndedChanged,
                    originalFinalStacksDisappeared: originalFinalStacksDisappeared,
                    originalWinnersDisappeared: originalWinnersDisappeared,
                    noMoreEndData: noMoreEndData,
                    hasUpdatedSeats: hasUpdatedSeats,
                    hasUpdatedPot: hasUpdatedPot
                });
                debugLog('Novo round detectado (múltiplos sinais)', {
                    oldRoundCount: lastRoundCount,
                    newRoundCount: originalRound.round_count,
                    roundEnded: originalRound.round_ended,
                    lastRoundEnded: lastRoundEnded,
                    roundCountChanged: roundCountChanged,
                    roundEndedChanged: roundEndedChanged,
                    originalFinalStacksDisappeared: originalFinalStacksDisappeared,
                    originalWinnersDisappeared: originalWinnersDisappeared,
                    noMoreEndData: noMoreEndData,
                    hasUpdatedSeats: hasUpdatedSeats,
                    hasUpdatedPot: hasUpdatedPot
                });
                lastRoundCount = originalRound.round_count;
                lastRoundEnded = originalRound.round_ended; // Atualiza estado rastreado
                modalDismissedForRound = null; // Reseta a flag quando um novo round começa
                hideRoundEndModal();
            } else {
                // Atualiza lastRoundEnded mesmo se não detectou novo round (para rastrear mudanças futuras)
                if (originalRound.round_ended !== lastRoundEnded) {
                    console.log('🟢 [DEBUG UPDATE GAME INFO] round_ended mudou, mas não detectou novo round:', {
                        oldRoundEnded: lastRoundEnded,
                        newRoundEnded: originalRound.round_ended
                    });
                    lastRoundEnded = originalRound.round_ended;
                }
            }
        }

        const roundState = round.round_state || {};
        const seats = Array.isArray(roundState.seats) ? roundState.seats : [];

        // Atualiza pot de forma segura
        try {
            const potElement = document.getElementById('potAmount');
            if (potElement) {
                const pot = safeGet(roundState, 'pot.main.amount', 0);
                potElement.textContent = pot || 0;
            }
        } catch (e) {
            debugLog('Erro ao atualizar pot', e);
        }

        // Atualiza stack e aposta do jogador
        try {
            if (playerUuid && Array.isArray(seats)) {
                const playerSeat = seats.find(s => s && s.uuid === playerUuid);
                if (playerSeat) {
                    const stackEl = document.getElementById('playerStack');
                    const betEl = document.getElementById('playerBet');
                    if (stackEl) {
                        stackEl.textContent = playerSeat.stack || 100;
                    }
                    if (betEl) {
                        betEl.textContent = playerSeat.paid || 0;
                    }
                }
            }
        } catch (e) {
            debugLog('Erro ao atualizar stack/bet do jogador', e);
        }

        // Atualiza info do round (sempre que round_count estiver disponível)
        try {
            const roundInfo = document.getElementById('roundInfo');
            if (roundInfo) {
                // Prioriza round_count do round atual, mas mantém último conhecido se não houver
                if (round.round_count && typeof round.round_count === 'number') {
                    roundInfo.textContent = `${round.round_count}/10`;
                    lastRoundCount = round.round_count;
                } else if (lastRoundCount > 0) {
                    // Mantém último round conhecido se não houver informação nova
                    roundInfo.textContent = `${lastRoundCount}/10`;
                }
            }
        } catch (e) {
            debugLog('Erro ao atualizar roundInfo', e);
        }

        // Identifica jogador atual - PRIORIZA thinking_uuid sobre is_player_turn
        let currentPlayerUuid = null;
        
        // Fonte primária: thinking_uuid (indica quem está pensando/jogando agora)
        const thinkingUuid = gameState.thinking_uuid;
        if (thinkingUuid) {
            currentPlayerUuid = thinkingUuid;
            debugLog('Bot pensando detectado (fonte primária)', { thinkingUuid: thinkingUuid });
        }
        // Fonte secundária: current_player_uuid do round_state
        else if (roundState.current_player_uuid) {
            currentPlayerUuid = roundState.current_player_uuid;
            debugLog('Vez detectada pelo round_state', { currentPlayerUuid: currentPlayerUuid });
        }
        // Fonte terciária: is_player_turn (só se não houver thinking_uuid nem current_player_uuid)
        else if (round.is_player_turn === true && playerUuid) {
            currentPlayerUuid = playerUuid;
            debugLog('Vez do jogador humano (fallback)', { playerUuid: playerUuid });
        }
        
        debugLog('Jogador atual determinado', {
            currentPlayerUuid: currentPlayerUuid,
            is_player_turn: round.is_player_turn,
            roundState_current_player: roundState.current_player_uuid,
            thinking_uuid: thinkingUuid,
            source: thinkingUuid ? 'thinking_uuid' : (roundState.current_player_uuid ? 'round_state' : 'is_player_turn')
        });

        // Atualiza status da ação na UI (se houver ação)
        if (round.action && typeof round.action === 'object' && round.action.uuid) {
            try {
                const actionSeat = Array.isArray(seats) ? seats.find(s => s && s.uuid === round.action.uuid) : null;
                if (actionSeat) {
                    const statusEl = document.getElementById(`status-${actionSeat.uuid}`);
                    if (statusEl && round.action.action) {
                        let actionText = String(round.action.action).toUpperCase();
                        const amount = round.action.amount;
                        if (amount && typeof amount === 'number' && amount > 0 && actionText !== 'FOLD') {
                            actionText += ` ${amount}`;
                        }
                        statusEl.textContent = actionText;

                        // Atualiza última jogada abaixo das fichas
                        const lastActionEl = document.getElementById(`last-action-${actionSeat.uuid}`);
                        if (lastActionEl) {
                            let lastActionText = String(round.action.action).toUpperCase();
                            if (amount && typeof amount === 'number' && amount > 0) {
                                lastActionText += ` ${amount}`;
                            }
                            lastActionEl.textContent = lastActionText;
                        }

                        // Limpa status após 2 segundos (exceto Fold)
                        if (actionText !== 'FOLD') {
                            setTimeout(() => {
                                if (statusEl && statusEl.textContent === actionText) {
                                    statusEl.textContent = '';
                                }
                            }, 2000);
                        }
                    }
                }
            } catch (e) {
                debugLog('Erro ao atualizar status da ação', e);
            }
        }

        // Verifica se o jogador ainda está participando (com grace period)
        const playerSeat = seats.find(s => s && s.uuid === playerUuid);
        const playerStillInGame = playerSeat && (playerSeat.state === 'participating' || playerSeat.state === 'folded');
        
        // Grace period: aguarda algumas iterações antes de marcar como eliminado
        // Isso evita marcar o jogador como eliminado antes dele ser adicionado aos seats
        if (playerUuid) {
            if (playerStillInGame) {
                // Jogador encontrado, reseta contador
                playerNotFoundCount = 0;
            } else {
                // Jogador não encontrado, incrementa contador
                playerNotFoundCount++;
            }
        }
        
        // Só considera eliminado se não encontrado por 3 iterações (1.5 segundos)
        const playerEliminated = playerUuid && !playerStillInGame && playerNotFoundCount >= 3;
        
        // Renderiza jogadores apenas se houver mudanças (cache de estado)
        try {
            if (Array.isArray(seats)) {
                // Cria hash dos seats para comparação
                const seatsHash = JSON.stringify(seats.map(s => ({
                    uuid: s.uuid,
                    state: s.state,
                    stack: s.stack,
                    name: s.name
                })));
                
                // Só renderiza se seats ou currentPlayerUuid mudaram
                const seatsChanged = seatsHash !== lastSeatsState;
                const currentPlayerChanged = currentPlayerUuid !== lastCurrentPlayerUuid;
                
                if (seatsChanged || currentPlayerChanged) {
                    renderPlayers(seats, currentPlayerUuid, playerUuid);
                    lastSeatsState = seatsHash;
                    lastCurrentPlayerUuid = currentPlayerUuid;
                }
            }
        } catch (e) {
            debugLog('Erro ao renderizar jogadores', e);
        }
        
        // Se o jogador foi eliminado (após grace period), mostra mensagem e desabilita ações
        if (playerEliminated) {
            debugLog('Jogador não está mais no jogo (após grace period)', {
                playerUuid: playerUuid,
                playerSeat: playerSeat,
                seats: seats,
                playerNotFoundCount: playerNotFoundCount
            });
            
            // Desabilita todas as ações
            showPlayerActions(null, null, false);
            
            // Mostra mensagem informando que o jogador foi eliminado
            const actionButtons = document.getElementById('actionButtons');
            if (actionButtons) {
                const eliminatedMsg = document.createElement('div');
                eliminatedMsg.id = 'eliminatedMessage';
                eliminatedMsg.style.textAlign = 'center';
                eliminatedMsg.style.padding = '20px';
                eliminatedMsg.style.color = '#ff6b6b';
                eliminatedMsg.style.fontSize = '18px';
                eliminatedMsg.style.fontWeight = 'bold';
                eliminatedMsg.textContent = 'Você foi eliminado do jogo. Aguardando o fim da partida...';
                
                // Remove mensagem anterior se existir
                const existingMsg = document.getElementById('eliminatedMessage');
                if (existingMsg) {
                    existingMsg.remove();
                }
                
                actionButtons.appendChild(eliminatedMsg);
            }
        } else {
            // Remove mensagem de eliminado se o jogador voltou (não deveria acontecer, mas por segurança)
            const eliminatedMsg = document.getElementById('eliminatedMessage');
            if (eliminatedMsg) {
                eliminatedMsg.remove();
            }
        }

        // Atualiza cartas comunitárias
        try {
            const communityCards = Array.isArray(roundState.community_card) ? roundState.community_card : [];
            updateCommunityCards(communityCards);
        } catch (e) {
            debugLog('Erro ao atualizar cartas comunitárias', e);
        }

        // Atualiza cartas do jogador se disponíveis
        if (round.hole_card && Array.isArray(round.hole_card)) {
            try {
                updatePlayerCards(round.hole_card);
            } catch (e) {
                debugLog('Erro ao atualizar cartas do jogador', e);
            }
        }

        // Atualiza mensagem de turno
        try {
            updateTurnMessage(currentPlayerUuid, seats, playerUuid);
        } catch (e) {
            debugLog('Erro ao atualizar mensagem de turno', e);
        }

        // Verifica se é a vez do jogador (só se não houver bot pensando E o jogador ainda está no jogo E não foi eliminado)
        const isPlayerTurn = !playerEliminated && playerStillInGame && !thinkingUuid && round.valid_actions && round.is_player_turn === true;
        debugLog('Verificando vez do jogador', {
            isPlayerTurn: isPlayerTurn,
            playerStillInGame: playerStillInGame,
            hasValidActions: !!round.valid_actions,
            is_player_turn: round.is_player_turn,
            thinkingUuid: thinkingUuid
        });
        
        try {
            // Só mostra ações se o jogador ainda está no jogo e não foi eliminado
            if (!playerEliminated && playerStillInGame) {
                showPlayerActions(round.valid_actions, round.hole_card, isPlayerTurn);
            } else {
                // Jogador eliminado ou não encontrado, desabilita todas as ações
                showPlayerActions(null, null, false);
            }
        } catch (e) {
            debugLog('Erro ao mostrar ações do jogador', e);
        }
        
        debugLog('=== updateGameInfo FINALIZADO ===');
    } catch (e) {
        console.error('Erro crítico em updateGameInfo:', e);
        debugLog('Erro crítico em updateGameInfo', e);
    }
}

// Mostra ações disponíveis (ou botões desabilitados)
function showPlayerActions(validActions, holeCard, isTurn) {
    try {
        const container = document.getElementById('actionsContainer');
        if (!container) {
            debugLog('actionsContainer não encontrado');
            return;
        }
        container.style.display = 'flex'; // Sempre visível

        // Atualiza cartas do jogador (garante visibilidade)
        if (holeCard && Array.isArray(holeCard)) {
            updatePlayerCards(holeCard);
        }

        const foldBtn = document.getElementById('foldBtn');
        const callBtn = document.getElementById('callBtn');
        const raiseBtn = document.getElementById('raiseBtn');
        const allinBtn = document.getElementById('allinBtn');
        const actionInfo = document.getElementById('actionInfo');

        if (!foldBtn || !callBtn || !raiseBtn || !allinBtn) {
            debugLog('Botões de ação não encontrados');
            return;
        }

        // Se não for a vez, desabilita tudo
        if (!isTurn) {
            foldBtn.disabled = true;
            callBtn.disabled = true;
            raiseBtn.disabled = true;
            allinBtn.disabled = true;
            if (actionInfo) actionInfo.textContent = '';
            return;
        }

        // Fold sempre disponível se for a vez
        foldBtn.disabled = false;

        // Call
        if (validActions && validActions[1] && typeof validActions[1] === 'object') {
            callBtn.disabled = false;
            const callAmount = validActions[1].amount || 0;
            callBtn.textContent = `Call ${callAmount > 0 ? `(${callAmount})` : ''}`;
        } else {
            callBtn.disabled = true;
        }

        // Raise
        if (validActions && validActions[2] && typeof validActions[2] === 'object' && 
            validActions[2].amount && typeof validActions[2].amount === 'object' &&
            validActions[2].amount.min !== undefined && validActions[2].amount.min !== -1) {
            raiseBtn.disabled = false;
            const minRaise = validActions[2].amount.min || 0;
            const maxRaise = validActions[2].amount.max || 0;
            if (actionInfo) {
                actionInfo.textContent = `Raise: ${minRaise} - ${maxRaise}`;
            }
            const raiseAmountInput = document.getElementById('raiseAmount');
            if (raiseAmountInput) {
                raiseAmountInput.min = minRaise;
                raiseAmountInput.max = maxRaise;
                raiseAmountInput.value = minRaise;
            }
        } else {
            raiseBtn.disabled = true;
            if (actionInfo) actionInfo.textContent = '';
        }

        // All-in (se disponível)
        try {
            const playerStackEl = document.getElementById('playerStack');
            const playerStack = playerStackEl ? parseInt(playerStackEl.textContent) || 0 : 0;
            if (playerStack > 0) {
                allinBtn.disabled = false;
                allinBtn.textContent = `All-in (${playerStack})`;
            } else {
                allinBtn.disabled = true;
            }
        } catch (e) {
            debugLog('Erro ao verificar playerStack para all-in', e);
            allinBtn.disabled = true;
        }

        const raiseInput = document.getElementById('raiseInput');
        if (raiseInput) {
            raiseInput.style.display = 'none';
        }
    } catch (e) {
        console.error('Erro em showPlayerActions:', e);
        debugLog('Erro em showPlayerActions', e);
    }
}

// Atualiza mensagem de turno no topo
function updateTurnMessage(currentPlayerUuid, seats, playerUuid) {
    try {
        const turnMessage = document.getElementById('turnMessage');
        if (!turnMessage) {
            debugLog('turnMessage não encontrado');
            return;
        }

        // Só mostra a barra quando é a vez do jogador humano
        if (!currentPlayerUuid || currentPlayerUuid !== playerUuid || !Array.isArray(seats)) {
            turnMessage.style.display = 'none';
            return;
        }

        const currentPlayer = seats.find(s => s && s.uuid === currentPlayerUuid);
        if (!currentPlayer || !currentPlayer.name) {
            turnMessage.style.display = 'none';
            return;
        }

        // Mostra mensagem na barra superior apenas para jogador humano
        turnMessage.style.display = 'flex';
        const playerName = currentPlayer.name || 'Jogador';
        turnMessage.textContent = `Sua vez, ${playerName}!`;
        turnMessage.style.background = 'rgba(58, 159, 117, 0.9)'; // Verde para jogador
    } catch (e) {
        console.error('Erro em updateTurnMessage:', e);
        debugLog('Erro em updateTurnMessage', e);
    }
}

// Mostra modal de fim de round
function showRoundEndModal(round) {
    try {
        debugLog('=== showRoundEndModal INICIADO ===', { round: round });
        
        if (!round || typeof round !== 'object') {
            debugLog('round inválido em showRoundEndModal', round);
            return;
        }

        const modal = document.getElementById('roundEndModal');
        const potElement = document.getElementById('roundEndPot');
        const stacksElement = document.getElementById('roundEndStacks');
        const nextRoundBtn = document.getElementById('nextRoundBtn');

        debugLog('Elementos do modal', {
            modal: !!modal,
            potElement: !!potElement,
            stacksElement: !!stacksElement,
            nextRoundBtn: !!nextRoundBtn
        });

        if (!modal || !potElement || !stacksElement) {
            debugLog('Elementos do modal não encontrados');
            console.error('Elementos do modal não encontrados:', {
                modal: !!modal,
                potElement: !!potElement,
                stacksElement: !!stacksElement
            });
            return;
        }
        
        if (!nextRoundBtn) {
            console.error('Botão nextRoundBtn não encontrado!');
            debugLog('Botão nextRoundBtn não encontrado');
        }

        // Atualiza pot de forma segura
        const potAmount = typeof round.pot_amount === 'number' ? round.pot_amount : 0;
        potElement.textContent = potAmount;

        // Limpa conteúdo anterior
        stacksElement.innerHTML = '';
        
        if (round.final_stacks && typeof round.final_stacks === 'object' && round.final_stacks !== null) {
            try {
                // Separa vencedores e perdedores
                const winners = [];
                const losers = [];
                
                Object.values(round.final_stacks).forEach(player => {
                    if (player && typeof player === 'object') {
                        if (player.won === true) {
                            winners.push(player);
                        } else {
                            losers.push(player);
                        }
                    }
                });

                // Mostra vencedores primeiro
                if (winners.length > 0) {
                    const winnersTitle = document.createElement('div');
                    winnersTitle.style.width = '100%';
                    winnersTitle.style.fontSize = '18px';
                    winnersTitle.style.fontWeight = 'bold';
                    winnersTitle.style.color = '#3a9f75';
                    winnersTitle.style.marginBottom = '8px';
                    winnersTitle.style.textAlign = 'center';
                    winnersTitle.textContent = '🏆 Vencedor(es) 🏆';
                    stacksElement.appendChild(winnersTitle);

                    winners.forEach(player => {
                        try {
                            const playerDiv = createPlayerResultDiv(player, true, round);
                            stacksElement.appendChild(playerDiv);
                        } catch (e) {
                            debugLog('Erro ao renderizar vencedor', { player, error: e });
                            console.error('Erro ao renderizar vencedor:', e, player);
                            // Cria um elemento simples de fallback
                            const fallbackDiv = document.createElement('div');
                            fallbackDiv.textContent = `${player.name || 'Unknown'} - Erro ao carregar`;
                            fallbackDiv.style.color = '#ff6b6b';
                            stacksElement.appendChild(fallbackDiv);
                        }
                    });
                }

                // Mostra TODOS os outros jogadores (incluindo os que deram fold)
                if (losers.length > 0) {
                    const losersTitle = document.createElement('div');
                    losersTitle.style.width = '100%';
                    losersTitle.style.fontSize = '16px';
                    losersTitle.style.fontWeight = 'bold';
                    losersTitle.style.color = '#ffffff';
                    losersTitle.style.marginTop = '12px';
                    losersTitle.style.marginBottom = '8px';
                    losersTitle.style.textAlign = 'center';
                    losersTitle.textContent = 'Outros Jogadores';
                    stacksElement.appendChild(losersTitle);

                    // Mostra todos os perdedores, incluindo os que deram fold
                    losers.forEach(player => {
                        try {
                            const playerDiv = createPlayerResultDiv(player, false, round);
                            stacksElement.appendChild(playerDiv);
                        } catch (e) {
                            debugLog('Erro ao renderizar perdedor', { player, error: e });
                            console.error('Erro ao renderizar perdedor:', e, player);
                            // Cria um elemento simples de fallback
                            const fallbackDiv = document.createElement('div');
                            fallbackDiv.textContent = `${player.name || 'Unknown'} - Erro ao carregar`;
                            fallbackDiv.style.color = '#ff6b6b';
                            stacksElement.appendChild(fallbackDiv);
                        }
                    });
                }

                // Se não houver jogadores, mostra mensagem
                if (winners.length === 0 && losers.length === 0) {
                    const noPlayersMsg = document.createElement('div');
                    noPlayersMsg.textContent = 'Nenhum jogador encontrado';
                    noPlayersMsg.style.color = '#aaaaaa';
                    noPlayersMsg.style.textAlign = 'center';
                    noPlayersMsg.style.marginTop = '20px';
                    stacksElement.appendChild(noPlayersMsg);
                }

            } catch (e) {
                debugLog('Erro ao processar final_stacks', e);
                console.error('Erro ao processar final_stacks:', e);
                // Mostra mensagem de erro
                const errorMsg = document.createElement('div');
                errorMsg.textContent = 'Erro ao carregar resultados do round';
                errorMsg.style.color = '#ff6b6b';
                errorMsg.style.textAlign = 'center';
                errorMsg.style.marginTop = '20px';
                stacksElement.appendChild(errorMsg);
            }
        } else {
            // Se não houver final_stacks, mostra mensagem
            const noDataMsg = document.createElement('div');
            noDataMsg.textContent = 'Dados do round não disponíveis';
            noDataMsg.style.color = '#aaaaaa';
            noDataMsg.style.textAlign = 'center';
            noDataMsg.style.marginTop = '20px';
            stacksElement.appendChild(noDataMsg);
        }

        // Mostra modal e garante que só fecha com botão
        modal.style.display = 'flex';
        
        debugLog('Modal exibida', {
            modalDisplay: modal.style.display,
            hasNextRoundBtn: !!document.getElementById('nextRoundBtn'),
            modalVisible: window.getComputedStyle(modal).display !== 'none'
        });
        
        // Garante que o botão está visível e acessível
        if (nextRoundBtn) {
            nextRoundBtn.style.display = 'block';
            nextRoundBtn.style.visibility = 'visible';
            nextRoundBtn.style.opacity = '1';
            nextRoundBtn.disabled = false;
            debugLog('Botão nextRoundBtn configurado', {
                display: nextRoundBtn.style.display,
                visibility: nextRoundBtn.style.visibility,
                opacity: nextRoundBtn.style.opacity,
                disabled: nextRoundBtn.disabled,
                textContent: nextRoundBtn.textContent
            });
        } else {
            console.error('nextRoundBtn não encontrado após criar modal!');
            debugLog('nextRoundBtn não encontrado após criar modal');
        }
        
        debugLog('=== showRoundEndModal FINALIZADO ===');
    } catch (e) {
        console.error('Erro em showRoundEndModal:', e);
        debugLog('Erro em showRoundEndModal', e);
    }
}

// Cria div de resultado do jogador
function createPlayerResultDiv(player, isWinner, round) {
    const div = document.createElement('div');
    div.className = 'round-result-item';
    div.style.display = 'flex';
    div.style.flexDirection = 'row';
    div.style.alignItems = 'center';
    div.style.gap = '12px';
    div.style.marginBottom = '8px';
    div.style.padding = '8px 12px';
    div.style.background = isWinner ? 'rgba(58, 159, 117, 0.2)' : 'rgba(255, 255, 255, 0.05)';
    div.style.borderRadius = '8px';
    div.style.border = isWinner ? '2px solid #3a9f75' : '1px solid rgba(255, 255, 255, 0.2)';
    div.style.width = '100%';
    div.style.boxShadow = isWinner ? '0 2px 8px rgba(58, 159, 117, 0.3)' : '0 1px 4px rgba(0, 0, 0, 0.2)';

    const playerName = player.name || 'Unknown';
    const playerStack = typeof player.stack === 'number' ? player.stack : 0;
    const wonAmount = typeof player.won_amount === 'number' ? player.won_amount : 0;
    const isFolded = player.folded === true;

    // Nome e status (em linha)
    const nameDiv = document.createElement('div');
    nameDiv.style.display = 'flex';
    nameDiv.style.alignItems = 'center';
    nameDiv.style.gap = '6px';
    nameDiv.style.minWidth = '120px';
    nameDiv.style.flexShrink = '0';
    
    const nameSpan = document.createElement('span');
    nameSpan.style.fontSize = '16px';
    nameSpan.style.fontWeight = 'bold';
    nameSpan.style.color = isWinner ? '#3a9f75' : '#ffffff';
    nameSpan.textContent = playerName;
    nameDiv.appendChild(nameSpan);
    
    if (isWinner) {
        const trophy = document.createElement('span');
        trophy.textContent = '🏆';
        trophy.style.fontSize = '16px';
        nameDiv.appendChild(trophy);
    }
    
    if (isFolded) {
        const foldedBadge = document.createElement('span');
        foldedBadge.textContent = 'FOLD';
        foldedBadge.style.fontSize = '10px';
        foldedBadge.style.padding = '2px 6px';
        foldedBadge.style.background = 'rgba(255, 0, 0, 0.3)';
        foldedBadge.style.borderRadius = '3px';
        foldedBadge.style.color = '#ff6b6b';
        nameDiv.appendChild(foldedBadge);
    }
    
    div.appendChild(nameDiv);

    // Cartas (em linha)
    let cardsToShow = [];
    if (player.cards != null && player.cards !== undefined) {
        if (Array.isArray(player.cards)) {
            cardsToShow = player.cards.filter(c => c != null && c !== '' && c !== undefined);
        } else if (typeof player.cards === 'string' && player.cards.trim() !== '') {
            cardsToShow = [player.cards];
        } else if (typeof player.cards === 'object' && !Array.isArray(player.cards)) {
            // Se for objeto, tenta extrair valores
            const cardValues = Object.values(player.cards).filter(c => c != null && c !== '' && c !== undefined);
            if (cardValues.length > 0) {
                cardsToShow = cardValues;
            }
        }
    }
    
    // Mostra cartas mesmo se deu fold (para debug, mas pode remover depois)
    if (cardsToShow.length > 0) {
        const cardsContainer = document.createElement('div');
        cardsContainer.style.display = 'flex';
        cardsContainer.style.gap = '4px';
        cardsContainer.style.alignItems = 'center';
        cardsContainer.style.flexShrink = '0';
        
        cardsToShow.forEach(card => {
            if (card) {
                const cardDiv = document.createElement('div');
                cardDiv.style.width = '40px';
                cardDiv.style.height = '56px';
                cardDiv.style.borderRadius = '4px';
                cardDiv.style.overflow = 'hidden';
                cardDiv.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';
                cardDiv.style.flexShrink = '0';
                
                const cardImg = document.createElement('img');
                const cardImagePath = getCardImage(card);
                cardImg.src = cardImagePath;
                cardImg.style.width = '100%';
                cardImg.style.height = '100%';
                cardImg.style.objectFit = 'cover';
                cardImg.alt = card;
                cardImg.onerror = () => {
                    cardDiv.style.background = '#1a1a2e';
                    cardDiv.style.border = '2px solid #fa8c01';
                    cardDiv.textContent = card || '?';
                    cardDiv.style.display = 'flex';
                    cardDiv.style.alignItems = 'center';
                    cardDiv.style.justifyContent = 'center';
                    cardDiv.style.color = '#fa8c01';
                    cardDiv.style.fontSize = '10px';
                    cardDiv.style.fontWeight = 'bold';
                };
                cardDiv.appendChild(cardImg);
                cardsContainer.appendChild(cardDiv);
            }
        });
        
        div.appendChild(cardsContainer);
    } else {
        // Espaçador vazio se não tiver cartas
        const emptySpacer = document.createElement('div');
        emptySpacer.style.width = '88px'; // 2 cartas * 40px + 8px gap
        div.appendChild(emptySpacer);
    }

    // Informações de fichas (em linha)
    const stackInfo = document.createElement('div');
    stackInfo.style.display = 'flex';
    stackInfo.style.flexDirection = 'row';
    stackInfo.style.alignItems = 'center';
    stackInfo.style.gap = '8px';
    stackInfo.style.marginLeft = 'auto';
    stackInfo.style.flexShrink = '0';
    
    const stackValue = document.createElement('div');
    stackValue.style.fontSize = '16px';
    stackValue.style.fontWeight = 'bold';
    stackValue.style.color = isWinner ? '#3a9f75' : '#ffffff';
    stackValue.textContent = `$${playerStack}`;
    stackInfo.appendChild(stackValue);
    
    // Mostra quanto ganhou se for vencedor
    if (isWinner && wonAmount > 0) {
        const wonLabel = document.createElement('div');
        wonLabel.style.fontSize = '14px';
        wonLabel.style.color = '#fa8c01';
        wonLabel.textContent = `+$${Math.round(wonAmount)}`;
        stackInfo.appendChild(wonLabel);
    }
    
    div.appendChild(stackInfo);

    // Debug das cartas
    debugLog('Verificando cartas do jogador', {
        playerName: playerName,
        isFolded: isFolded,
        hasCards: player.cards != null && player.cards !== undefined,
        cardsType: typeof player.cards,
        isArray: Array.isArray(player.cards),
        cardsLength: Array.isArray(player.cards) ? player.cards.length : (typeof player.cards === 'object' && player.cards != null ? Object.keys(player.cards).length : null),
        cards: player.cards,
        cardsToShow: cardsToShow,
        cardsToShowLength: cardsToShow.length
    });

    return div;
}

// Esconde modal de fim de round
function hideRoundEndModal() {
    console.log('🔵 [DEBUG NEXT ROUND] hideRoundEndModal() chamada');
    const modal = document.getElementById('roundEndModal');
    console.log('🔵 [DEBUG NEXT ROUND] Modal encontrado:', !!modal);
    if (modal) {
        const wasVisible = modal.style.display !== 'none';
        modal.style.display = 'none';
        console.log('🔵 [DEBUG NEXT ROUND] Modal escondida. Estava visível:', wasVisible);
        debugLog('Modal de fim de round escondida');
    } else {
        console.warn('🔵 [DEBUG NEXT ROUND] ⚠️ Modal não encontrado no DOM!');
    }
}

// Mostra modal final do jogo
async function showGameEndModal(gameResult) {
    try {
        const modal = document.getElementById('gameEndModal');
        const winnerEl = document.getElementById('gameEndWinner');
        const statsEl = document.getElementById('gameEndStats');
        
        if (!modal || !winnerEl || !statsEl) {
            debugLog('Elementos do modal final não encontrados');
            return;
        }

        // Encontra o vencedor (jogador com mais fichas)
        let winner = null;
        let maxStack = -1;
        const players = [];
        
        if (gameResult && typeof gameResult === 'object') {
            // gameResult pode ter diferentes formatos
            // Tenta obter informações dos players
            if (gameResult.players && Array.isArray(gameResult.players)) {
                gameResult.players.forEach(player => {
                    const stack = typeof player.stack === 'number' ? player.stack : 0;
                    players.push({
                        name: player.name || 'Unknown',
                        stack: stack,
                        uuid: player.uuid || null
                    });
                    if (stack > maxStack) {
                        maxStack = stack;
                        winner = player.name || 'Unknown';
                    }
                });
            } else if (gameResult.seats && Array.isArray(gameResult.seats)) {
                gameResult.seats.forEach(seat => {
                    const stack = typeof seat.stack === 'number' ? seat.stack : 0;
                    players.push({
                        name: seat.name || 'Unknown',
                        stack: stack,
                        uuid: seat.uuid || null
                    });
                    if (stack > maxStack) {
                        maxStack = stack;
                        winner = seat.name || 'Unknown';
                    }
                });
            }
        }

        // Se não encontrou winner, tenta do último round (obtém do servidor)
        if (!winner || players.length === 0) {
            try {
                const currentGameState = await getGameState();
                if (currentGameState && currentGameState.current_round && currentGameState.current_round.final_stacks) {
                    const finalStacks = currentGameState.current_round.final_stacks;
                    Object.values(finalStacks).forEach(player => {
                        if (player && typeof player === 'object') {
                            const stack = typeof player.stack === 'number' ? player.stack : 0;
                            players.push({
                                name: player.name || 'Unknown',
                                stack: stack
                            });
                            if (stack > maxStack) {
                                maxStack = stack;
                                winner = player.name || 'Unknown';
                            }
                        }
                    });
                }
            } catch (e) {
                debugLog('Erro ao obter gameState no showGameEndModal', e);
            }
        }

        // Mostra vencedor
        if (winner) {
            winnerEl.textContent = `🏆 Vencedor: ${winner} 🏆`;
        } else {
            winnerEl.textContent = 'Jogo Finalizado!';
        }

        // Mostra estatísticas
        statsEl.innerHTML = '';
        
        // Ordena players por stack (maior primeiro)
        players.sort((a, b) => b.stack - a.stack);
        
        const statsTitle = document.createElement('div');
        statsTitle.style.fontSize = '20px';
        statsTitle.style.fontWeight = 'bold';
        statsTitle.style.marginBottom = '15px';
        statsTitle.textContent = 'Estatísticas Finais:';
        statsEl.appendChild(statsTitle);

        players.forEach((player, index) => {
            const playerDiv = document.createElement('div');
            playerDiv.style.display = 'flex';
            playerDiv.style.justifyContent = 'space-between';
            playerDiv.style.padding = '10px';
            playerDiv.style.marginBottom = '8px';
            playerDiv.style.background = index === 0 ? 'rgba(58, 159, 117, 0.2)' : 'rgba(255, 255, 255, 0.05)';
            playerDiv.style.borderRadius = '4px';
            playerDiv.style.border = index === 0 ? '2px solid #3a9f75' : '1px solid rgba(255, 255, 255, 0.1)';
            
            const nameSpan = document.createElement('span');
            nameSpan.textContent = `${index + 1}. ${player.name}`;
            nameSpan.style.fontSize = '18px';
            
            const stackSpan = document.createElement('span');
            stackSpan.textContent = `$${player.stack}`;
            stackSpan.style.fontSize = '18px';
            stackSpan.style.fontWeight = 'bold';
            stackSpan.style.color = index === 0 ? '#3a9f75' : '#ffffff';
            
            playerDiv.appendChild(nameSpan);
            playerDiv.appendChild(stackSpan);
            statsEl.appendChild(playerDiv);
        });

        // Adiciona informação sobre rounds
        const roundsInfo = document.createElement('div');
        roundsInfo.style.marginTop = '15px';
        roundsInfo.style.fontSize = '16px';
        roundsInfo.style.color = '#fa8c01';
        roundsInfo.textContent = `Total de Rounds: 10/10`;
        statsEl.appendChild(roundsInfo);

        modal.style.display = 'flex';
    } catch (e) {
        console.error('Erro em showGameEndModal:', e);
        debugLog('Erro em showGameEndModal', e);
    }
}

// Esconde modal final do jogo
function hideGameEndModal() {
    const modal = document.getElementById('gameEndModal');
    if (modal) modal.style.display = 'none';
}

// Função auxiliar para criar hash do gameState (campos críticos)
function createGameStateHash(gameState) {
    if (!gameState || typeof gameState !== 'object') return null;
    
    try {
        const criticalFields = {
            active: gameState.active,
            player_uuid: gameState.player_uuid,
            thinking_uuid: gameState.thinking_uuid,
            round_ended: gameState.round_ended,
            current_round: gameState.current_round ? {
                round_count: gameState.current_round.round_count,
                round_ended: gameState.current_round.round_ended,
                is_player_turn: gameState.current_round.is_player_turn,
                round_state: gameState.current_round.round_state ? {
                    seats: gameState.current_round.round_state.seats,
                    current_player_uuid: gameState.current_round.round_state.current_player_uuid,
                    pot: gameState.current_round.round_state.pot
                } : null
            } : null
        };
        return JSON.stringify(criticalFields);
    } catch (e) {
        debugLog('Erro ao criar hash do gameState', e);
        return null;
    }
}

// Inicia polling do estado do jogo (com throttle baseado em PyPokerGUI)
function startGamePolling() {
    if (gameInterval) clearInterval(gameInterval);
    
    // Reseta sistema de inicialização quando novo jogo começa
    isInitializing = true;
    initializationCount = 0;
    playerNotFoundCount = 0;
    lastGameStateHash = null;
    lastSeatsState = null;
    lastCurrentPlayerUuid = null;

    gameInterval = setInterval(async () => {
        try {
            const gameState = await getGameState();

            if (!gameState || typeof gameState !== 'object') {
                debugLog('gameState inválido no polling');
                return;
            }

            if (gameState.error) {
                console.error('Erro no jogo:', gameState.error);
                debugLog('Erro no jogo recebido do servidor', gameState.error);
                // Não para o polling, apenas loga o erro
                return;
            }

            // Atualiza playerUuid se disponível
            if (gameState.player_uuid && typeof gameState.player_uuid === 'string' && !playerUuid) {
                playerUuid = gameState.player_uuid;
                debugLog('playerUuid atualizado', playerUuid);
            }

            // Throttle: só processa se estado realmente mudou (exceto durante inicialização)
            const currentHash = createGameStateHash(gameState);
            const stateChanged = currentHash !== lastGameStateHash;
            
            if (stateChanged || isInitializing) {
                lastGameStateHash = currentHash;
                
                if (gameState.current_round) {
                    updateGameInfo(gameState);
                }
            } else {
                debugLog('Estado não mudou, pulando atualização (throttle)');
            }

            if (gameState.game_result && gameState.active === false) {
                clearInterval(gameInterval);
                gameInterval = null;
                hideRoundEndModal(); // Fecha modal de round se estiver aberto
                setTimeout(async () => {
                    await showGameEndModal(gameState.game_result);
                }, 500);
            }
        } catch (error) {
            console.error('Erro ao obter estado do jogo:', error);
            debugLog('Erro crítico no polling', error);
            // Continua o polling mesmo com erro para não quebrar o jogo
        }
    }, 500);
}

// Reinicia e recomeça o jogo
async function resetAndRestart() {
    await resetGame();
    playerUuid = null;
    lastRoundCount = 0;
    lastRoundEnded = null;
    modalDismissedForRound = null;
    // Reseta sistema de inicialização
    isInitializing = false;
    initializationCount = 0;
    playerNotFoundCount = 0;
    lastSeatsState = null;
    lastCurrentPlayerUuid = null;
    lastGameStateHash = null;
    hideRoundEndModal();
    await startGame(playerName);
    startGamePolling();
}

// Inicialização e Event listeners
document.addEventListener('DOMContentLoaded', async () => {
    // Event listeners
    const foldBtn = document.getElementById('foldBtn');
    if (foldBtn) {
        foldBtn.addEventListener('click', async () => {
            try {
                const result = await sendPlayerAction('fold', 0);
                if (result.error) {
                    console.error('Erro ao enviar fold:', result.error);
                    alert(`Erro ao fazer fold: ${result.error}`);
                }
            } catch (error) {
                console.error('Erro ao enviar fold:', error);
                alert(`Erro ao fazer fold: ${error.message || 'Erro desconhecido'}`);
            }
        });
    }

    const callBtn = document.getElementById('callBtn');
    if (callBtn) {
        callBtn.addEventListener('click', async () => {
            const gameState = await getGameState();
            const amount = gameState.current_round?.valid_actions?.[1]?.amount || 0;
            await sendPlayerAction('call', amount);
        });
    }

    const exitGameBtn = document.getElementById('exitGameBtn');
    if (exitGameBtn) {
        exitGameBtn.addEventListener('click', async () => {
            if (confirm('Deseja sair da partida?')) {
                try {
                    await resetGame();
                } catch (e) {
                    console.error('Erro ao resetar jogo:', e);
                }
                window.location.href = '/';
            }
        });
    }

    const raiseBtn = document.getElementById('raiseBtn');
    if (raiseBtn) {
        raiseBtn.addEventListener('click', () => {
            const raiseInput = document.getElementById('raiseInput');
            if (raiseInput) raiseInput.style.display = 'flex';
        });
    }

    const confirmRaiseBtn = document.getElementById('confirmRaiseBtn');
    if (confirmRaiseBtn) {
        confirmRaiseBtn.addEventListener('click', async () => {
            const raiseAmount = document.getElementById('raiseAmount');
            if (raiseAmount) {
                const amount = parseInt(raiseAmount.value);
                await sendPlayerAction('raise', amount);
                const raiseInput = document.getElementById('raiseInput');
                if (raiseInput) raiseInput.style.display = 'none';
            }
        });
    }

    const allinBtn = document.getElementById('allinBtn');
    if (allinBtn) {
        allinBtn.addEventListener('click', async () => {
            if (!playerUuid) {
                debugLog('playerUuid não definido ao clicar all-in');
                const gameState = await getGameState();
                if (gameState && gameState.player_uuid) {
                    playerUuid = gameState.player_uuid;
                } else {
                    console.error('Não foi possível obter playerUuid');
                    return;
                }
            }
            
            const gameState = await getGameState();
            const roundState = gameState.current_round?.round_state || {};
            const seats = roundState.seats || [];
            const playerSeat = seats.find(s => s && s.uuid === playerUuid);
            
            if (!playerSeat) {
                debugLog('playerSeat não encontrado para all-in', { playerUuid, seats });
                console.error('Não foi possível encontrar seu assento');
                return;
            }
            
            const allinAmount = typeof playerSeat.stack === 'number' ? playerSeat.stack : 0;
            
            if (allinAmount <= 0) {
                console.error('Stack inválido para all-in:', allinAmount);
                return;
            }
            
            debugLog('Enviando all-in', { action: 'raise', amount: allinAmount, playerUuid });
            const result = await sendPlayerAction('raise', allinAmount);
            if (result.error) {
                console.error('Erro ao enviar all-in:', result.error);
            }
        });
    }

    const nextRoundBtn = document.getElementById('nextRoundBtn');
    if (nextRoundBtn) {
        nextRoundBtn.addEventListener('click', async () => {
            console.log('🔵 [DEBUG NEXT ROUND] ============================================');
            console.log('🔵 [DEBUG NEXT ROUND] Botão nextRoundBtn CLICADO');
            console.log('🔵 [DEBUG NEXT ROUND] Timestamp:', new Date().toISOString());
            debugLog('Botão nextRoundBtn clicado');
            
            // Obtém o round_count atual antes de fechar
            let currentRoundCount = null;
            let currentRoundEnded = null;
            try {
                console.log('🔵 [DEBUG NEXT ROUND] Obtendo gameState...');
                const gameState = await getGameState();
                console.log('🔵 [DEBUG NEXT ROUND] gameState recebido:', {
                    hasGameState: !!gameState,
                    hasCurrentRound: !!(gameState && gameState.current_round),
                    currentRound: gameState?.current_round
                });
                
                if (gameState && gameState.current_round) {
                    currentRoundCount = gameState.current_round.round_count;
                    currentRoundEnded = gameState.current_round.round_ended;
                    console.log('🔵 [DEBUG NEXT ROUND] Estado atual do round:', {
                        currentRoundCount: currentRoundCount,
                        currentRoundEnded: currentRoundEnded,
                        round_state: gameState.current_round.round_state,
                        final_stacks: gameState.current_round.final_stacks,
                        winners: gameState.current_round.winners
                    });
                } else {
                    console.warn('🔵 [DEBUG NEXT ROUND] ⚠️ gameState ou current_round não encontrado!');
                }
            } catch (e) {
                console.error('🔵 [DEBUG NEXT ROUND] ❌ Erro ao obter round_count ao fechar modal:', e);
                debugLog('Erro ao obter round_count ao fechar modal', e);
            }
            
            // Fecha a modal
            console.log('🔵 [DEBUG NEXT ROUND] Fechando modal...');
            hideRoundEndModal();
            console.log('🔵 [DEBUG NEXT ROUND] Modal fechada');
            
            // Marca que a modal foi fechada para este round
            if (currentRoundCount !== null) {
                modalDismissedForRound = currentRoundCount;
                console.log('🔵 [DEBUG NEXT ROUND] Modal fechada para round:', { 
                    round_count: currentRoundCount,
                    round_ended: currentRoundEnded,
                    modalDismissedForRound: modalDismissedForRound
                });
                debugLog('Modal fechada para round', { 
                    round_count: currentRoundCount,
                    round_ended: currentRoundEnded,
                    modalDismissedForRound: modalDismissedForRound
                });
            } else {
                // Se não conseguiu obter o round_count, usa o lastRoundCount
                if (lastRoundCount > 0) {
                    modalDismissedForRound = lastRoundCount;
                    console.log('🔵 [DEBUG NEXT ROUND] Modal fechada usando lastRoundCount:', { 
                        round_count: lastRoundCount,
                        modalDismissedForRound: modalDismissedForRound
                    });
                    debugLog('Modal fechada usando lastRoundCount', { 
                        round_count: lastRoundCount,
                        modalDismissedForRound: modalDismissedForRound
                    });
                } else {
                    console.warn('🔵 [DEBUG NEXT ROUND] ⚠️ Não foi possível determinar round_count!');
                }
            }
            
            // Força limpeza de dados de fim de round no servidor
            console.log('🔵 [DEBUG NEXT ROUND] Chamando forceNextRound para limpar dados de fim de round...');
            let forceSuccess = false;
            try {
                const forceResult = await forceNextRound();
                if (forceResult.error) {
                    console.error('🔵 [DEBUG NEXT ROUND] ❌ Erro ao chamar forceNextRound:', forceResult.error);
                } else {
                    console.log('🔵 [DEBUG NEXT ROUND] ✅ forceNextRound executado com sucesso:', forceResult);
                    forceSuccess = true;
                    
                    // Verifica imediatamente se os dados foram limpos
                    const verifyState = await getGameState();
                    if (verifyState && verifyState.current_round) {
                        const hasFinalStacks = !!verifyState.current_round.final_stacks;
                        const hasWinners = !!verifyState.current_round.winners;
                        console.log('🔵 [DEBUG NEXT ROUND] Verificação imediata após forceNextRound:', {
                            hasFinalStacks: hasFinalStacks,
                            hasWinners: hasWinners,
                            roundEnded: verifyState.current_round.round_ended
                        });
                        
                        if (!hasFinalStacks && !hasWinners) {
                            console.log('🔵 [DEBUG NEXT ROUND] ✅ Dados limpos com sucesso!');
                        } else {
                            console.warn('🔵 [DEBUG NEXT ROUND] ⚠️ Dados ainda presentes após forceNextRound!');
                        }
                    }
                }
            } catch (e) {
                console.error('🔵 [DEBUG NEXT ROUND] ❌ Exceção ao chamar forceNextRound:', e);
            }
            
            // Aguarda e verifica quando o novo round começar
            // O servidor iniciará o próximo round automaticamente, mas pode levar um momento
            let checkCount = 0;
            const maxChecks = 10; // Verifica por até 5 segundos (10 * 500ms)
            console.log('🔵 [DEBUG NEXT ROUND] Iniciando verificação de novo round...');
            console.log('🔵 [DEBUG NEXT ROUND] Configuração:', {
                maxChecks: maxChecks,
                interval: '500ms',
                currentRoundCount: currentRoundCount,
                currentRoundEnded: currentRoundEnded
            });
            
            const checkForNewRound = setInterval(async () => {
                checkCount++;
                console.log(`🔵 [DEBUG NEXT ROUND] Verificação #${checkCount}/${maxChecks}`);
                
                try {
                    const gameState = await getGameState();
                    console.log(`🔵 [DEBUG NEXT ROUND] Verificação #${checkCount} - gameState obtido:`, {
                        hasGameState: !!gameState,
                        hasCurrentRound: !!(gameState && gameState.current_round)
                    });
                    
                    if (gameState && gameState.current_round) {
                        const newRound = gameState.current_round;
                        const newRoundCount = newRound.round_count;
                        const newRoundEnded = newRound.round_ended;
                        const newFinalStacks = newRound.final_stacks;
                        const newWinners = newRound.winners;
                        const newRoundState = newRound.round_state || {};
                        const newSeats = Array.isArray(newRoundState.seats) ? newRoundState.seats : [];
                        
                        console.log(`🔵 [DEBUG NEXT ROUND] Verificação #${checkCount} - Estado do round:`, {
                            newRoundCount: newRoundCount,
                            newRoundEnded: newRoundEnded,
                            hasNewFinalStacks: !!newFinalStacks,
                            finalStacksKeys: newFinalStacks ? Object.keys(newFinalStacks).length : 0,
                            hasNewWinners: !!newWinners,
                            winnersLength: Array.isArray(newWinners) ? newWinners.length : 'N/A',
                            newSeatsLength: newSeats.length,
                            roundState: newRoundState
                        });
                        
                        // Detecta novo round usando múltiplos sinais
                        const roundCountIncreased = newRoundCount && newRoundCount !== currentRoundCount;
                        const roundEndedChanged = currentRoundEnded === true && newRoundEnded === false;
                        const finalStacksDisappeared = !newFinalStacks || (typeof newFinalStacks === 'object' && Object.keys(newFinalStacks).length === 0);
                        const winnersDisappeared = !newWinners || (Array.isArray(newWinners) && newWinners.length === 0);
                        const hasUpdatedSeats = newSeats.length > 0;
                        
                        // Sinais adicionais para detecção melhorada
                        const hasHoleCard = newRound.hole_card && Array.isArray(newRound.hole_card) && newRound.hole_card.length > 0;
                        const potReset = newRoundState.pot && typeof newRoundState.pot === 'object';
                        const potAmount = potReset ? (newRoundState.pot.main?.amount || 0) : 0;
                        const potIsLow = potAmount < 50; // Pot baixo indica início de novo round
                        
                        // Verifica se os stacks dos seats foram atualizados (não são os mesmos do round anterior)
                        let stacksUpdated = false;
                        if (hasUpdatedSeats && newSeats.length > 0) {
                            // Se pelo menos um seat tem stack diferente de 0 e não está folded, pode ser novo round
                            const activeSeats = newSeats.filter(s => {
                                const state = s.state || (s.get && s.get('state')) || 'participating';
                                return state !== 'folded' && (s.stack || 0) > 0;
                            });
                            stacksUpdated = activeSeats.length > 0;
                        }
                        
                        // Se forceNextRound foi chamado, considera que dados devem estar limpos
                        const forceWasCalled = forceSuccess;
                        
                        console.log(`🔵 [DEBUG NEXT ROUND] Verificação #${checkCount} - Sinais de detecção:`, {
                            roundCountIncreased: roundCountIncreased,
                            roundEndedChanged: roundEndedChanged,
                            finalStacksDisappeared: finalStacksDisappeared,
                            winnersDisappeared: winnersDisappeared,
                            hasUpdatedSeats: hasUpdatedSeats,
                            hasHoleCard: hasHoleCard,
                            potReset: potReset,
                            potAmount: potAmount,
                            potIsLow: potIsLow,
                            stacksUpdated: stacksUpdated,
                            forceWasCalled: forceWasCalled,
                            oldRoundCount: currentRoundCount,
                            newRoundCount: newRoundCount,
                            oldRoundEnded: currentRoundEnded,
                            newRoundEnded: newRoundEnded
                        });
                        
                        // Novo round detectado se qualquer um dos sinais indicar
                        // Após forceNextRound, final_stacks e winners devem desaparecer
                        const dataCleaned = finalStacksDisappeared && winnersDisappeared;
                        const newRoundSignals = hasUpdatedSeats && (hasHoleCard || potIsLow || stacksUpdated) && !newRoundEnded;
                        
                        // Se forceNextRound foi chamado, considera dados limpos mesmo se ainda aparecerem
                        // (pode haver delay na sincronização ou dados sendo restaurados)
                        // Após 3 verificações, assume que dados foram limpos se forceNextRound foi chamado
                        const considerDataCleaned = dataCleaned || (forceWasCalled && checkCount >= 3);
                        
                        // Se forceNextRound foi chamado E temos sinais de novo round (seats atualizados, pot baixo, etc)
                        // E não há round_ended, considera novo round mesmo se dados ainda aparecerem
                        const forceWithSignals = forceWasCalled && hasUpdatedSeats && !newRoundEnded && (potIsLow || stacksUpdated || hasHoleCard);
                        
                        if (roundCountIncreased || 
                            (roundEndedChanged && !newRoundEnded) ||
                            (considerDataCleaned && newRoundSignals) ||
                            (considerDataCleaned && hasUpdatedSeats && !newRoundEnded && checkCount >= 2) ||
                            (forceWithSignals && checkCount >= 2)) {
                            console.log('🔵 [DEBUG NEXT ROUND] ✅ NOVO ROUND DETECTADO!', {
                                oldRoundCount: currentRoundCount,
                                newRoundCount: newRoundCount,
                                oldRoundEnded: currentRoundEnded,
                                newRoundEnded: newRoundEnded,
                                roundCountIncreased: roundCountIncreased,
                                roundEndedChanged: roundEndedChanged,
                                finalStacksDisappeared: finalStacksDisappeared,
                                winnersDisappeared: winnersDisappeared,
                                hasUpdatedSeats: hasUpdatedSeats,
                                hasHoleCard: hasHoleCard,
                                potIsLow: potIsLow,
                                stacksUpdated: stacksUpdated,
                                dataCleaned: dataCleaned,
                                checks: checkCount
                            });
                            
                            debugLog('Novo round detectado após fechar modal (múltiplos sinais)', {
                                oldRoundCount: currentRoundCount,
                                newRoundCount: newRoundCount,
                                oldRoundEnded: currentRoundEnded,
                                newRoundEnded: newRoundEnded,
                                roundCountIncreased: roundCountIncreased,
                                roundEndedChanged: roundEndedChanged,
                                finalStacksDisappeared: finalStacksDisappeared,
                                winnersDisappeared: winnersDisappeared,
                                hasUpdatedSeats: hasUpdatedSeats,
                                checks: checkCount
                            });
                            
                            // Reseta a flag e atualiza o estado
                            console.log('🔵 [DEBUG NEXT ROUND] Resetando flags e atualizando jogo...');
                            modalDismissedForRound = null;
                            lastRoundCount = newRoundCount || currentRoundCount;
                            
                            // Força atualização do jogo
                            console.log('🔵 [DEBUG NEXT ROUND] Chamando updateGameInfo...');
                            updateGameInfo(gameState);
                            console.log('🔵 [DEBUG NEXT ROUND] updateGameInfo concluído');
                            
                            clearInterval(checkForNewRound);
                            console.log('🔵 [DEBUG NEXT ROUND] Intervalo limpo. Novo round iniciado com sucesso!');
                            console.log('🔵 [DEBUG NEXT ROUND] ============================================');
                            return;
                        } else {
                            console.log(`🔵 [DEBUG NEXT ROUND] Verificação #${checkCount} - Nenhum sinal de novo round ainda`);
                        }
                    } else {
                        console.warn(`🔵 [DEBUG NEXT ROUND] Verificação #${checkCount} - ⚠️ gameState ou current_round não encontrado!`);
                    }
                } catch (e) {
                    console.error(`🔵 [DEBUG NEXT ROUND] Verificação #${checkCount} - ❌ Erro ao verificar novo round:`, e);
                    debugLog('Erro ao verificar novo round', e);
                }
                
                // Se excedeu o número máximo de verificações, mostra erro
                if (checkCount >= maxChecks) {
                    console.error('🔵 [DEBUG NEXT ROUND] ❌ TIMEOUT ao aguardar novo round!', { checks: checkCount });
                    debugLog('Timeout ao aguardar novo round', { checks: checkCount });
                    clearInterval(checkForNewRound);
                    
                    // Mostra mensagem de erro ao usuário
                    const errorMsg = document.createElement('div');
                    errorMsg.id = 'roundStartError';
                    errorMsg.style.position = 'fixed';
                    errorMsg.style.top = '50%';
                    errorMsg.style.left = '50%';
                    errorMsg.style.transform = 'translate(-50%, -50%)';
                    errorMsg.style.background = 'rgba(220, 53, 69, 0.95)';
                    errorMsg.style.color = 'white';
                    errorMsg.style.padding = '20px 30px';
                    errorMsg.style.borderRadius = '8px';
                    errorMsg.style.zIndex = '10000';
                    errorMsg.style.textAlign = 'center';
                    errorMsg.style.fontSize = '18px';
                    errorMsg.style.fontWeight = 'bold';
                    errorMsg.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
                    errorMsg.textContent = 'Erro: O próximo round não iniciou automaticamente. Por favor, recarregue a página.';
                    
                    document.body.appendChild(errorMsg);
                    
                    // Remove a mensagem após 5 segundos
                    setTimeout(() => {
                        if (errorMsg.parentNode) {
                            errorMsg.parentNode.removeChild(errorMsg);
                        }
                    }, 5000);
                    
                    console.log('🔵 [DEBUG NEXT ROUND] ============================================');
                }
            }, 500); // Verifica a cada 500ms
        });
    } else {
        console.error('🔵 [DEBUG NEXT ROUND] ❌ Botão nextRoundBtn NÃO ENCONTRADO no DOM!');
    }

    const playAgainBtn = document.getElementById('playAgainBtn');
    if (playAgainBtn) {
        playAgainBtn.addEventListener('click', async () => {
            hideGameEndModal();
            await resetAndRestart();
        });
    }

    // Inicialização do jogo
    if (!playerName || playerName === 'Jogador') {
        alert('Por favor, configure seu nome primeiro!');
        window.location.href = 'config.html';
        return;
    }

    await startGame(playerName);
    startGamePolling();
});
