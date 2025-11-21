// Usa origem relativa para evitar problemas de CORS
const API_BASE = '/api';

// Função auxiliar para validar e parsear respostas JSON
async function parseJSONResponse(response) {
    try {
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Erro HTTP ${response.status}: ${errorText}`);
            return {
                error: `HTTP ${response.status}: ${errorText || response.statusText}`,
                status: response.status
            };
        }

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Resposta não é JSON:', text);
            return {
                error: 'Resposta do servidor não é JSON válido',
                rawResponse: text
            };
        }

        const data = await response.json();
        
        // Valida que a resposta é um objeto
        if (typeof data !== 'object' || data === null) {
            console.error('Resposta JSON inválida:', data);
            return {
                error: 'Resposta JSON inválida: não é um objeto',
                data: data
            };
        }

        return data;
    } catch (error) {
        console.error('Erro ao parsear resposta JSON:', error);
        return {
            error: `Erro ao processar resposta: ${error.message}`,
            exception: error
        };
    }
}

async function startGame(playerName) {
    try {
        if (!playerName || typeof playerName !== 'string') {
            return { error: 'Nome do jogador inválido' };
        }

        const response = await fetch(`${API_BASE}/start_game`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ player_name: playerName })
        });
        
        return await parseJSONResponse(response);
    } catch (error) {
        console.error('Erro em startGame:', error);
        return { error: `Erro de rede: ${error.message}` };
    }
}

async function sendPlayerAction(action, amount = 0) {
    try {
        if (!action || typeof action !== 'string') {
            return { error: 'Ação inválida' };
        }

        if (typeof amount !== 'number' || amount < 0) {
            amount = 0;
        }

        const response = await fetch(`${API_BASE}/player_action`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action, amount })
        });
        
        return await parseJSONResponse(response);
    } catch (error) {
        console.error('Erro em sendPlayerAction:', error);
        return { error: `Erro de rede: ${error.message}` };
    }
}

async function getGameState() {
    try {
        const response = await fetch(`${API_BASE}/game_state`);
        const data = await parseJSONResponse(response);
        
        // Valida estrutura básica do gameState
        if (!data.error && typeof data === 'object') {
            // Garante que propriedades esperadas existem
            if (data.active === undefined) {
                data.active = false;
            }
            if (data.current_round === undefined) {
                data.current_round = null;
            }
            if (data.thinking_uuid === undefined) {
                data.thinking_uuid = null;
            }
        }
        
        // Log detalhado para debug
        if (typeof DEBUG_MODE !== 'undefined' && DEBUG_MODE) {
            console.log('[API] getGameState retornou:', {
                active: data.active,
                hasCurrentRound: !!data.current_round,
                thinking_uuid: data.thinking_uuid,
                player_uuid: data.player_uuid,
                round_ended: data.current_round?.round_ended,
                is_player_turn: data.current_round?.is_player_turn
            });
        }
        
        return data;
    } catch (error) {
        console.error('Erro em getGameState:', error);
        return { 
            error: `Erro de rede: ${error.message}`,
            active: false,
            current_round: null,
            thinking_uuid: null
        };
    }
}

async function resetGame() {
    try {
        const response = await fetch(`${API_BASE}/reset_game`, {
            method: 'POST'
        });
        
        return await parseJSONResponse(response);
    } catch (error) {
        console.error('Erro em resetGame:', error);
        return { error: `Erro de rede: ${error.message}` };
    }
}

async function forceNextRound() {
    try {
        console.log('🔵 [API] Chamando force_next_round...');
        const response = await fetch(`${API_BASE}/force_next_round`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await parseJSONResponse(response);
        
        if (data.error) {
            console.error('🔵 [API] Erro em forceNextRound:', data.error);
        } else {
            console.log('🔵 [API] forceNextRound sucesso:', data);
        }
        
        return data;
    } catch (error) {
        console.error('🔵 [API] Erro em forceNextRound:', error);
        return { error: `Erro de rede: ${error.message}` };
    }
}

