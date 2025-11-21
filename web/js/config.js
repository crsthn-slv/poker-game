// Carrega configurações salvas
const playerNameInput = document.getElementById('playerName');
const playerCountInput = document.getElementById('playerCount');
const initialStackInput = document.getElementById('initialStack');
const smallBlindInput = document.getElementById('smallBlind');

// Carrega valores salvos do localStorage
const savedName = localStorage.getItem('playerName');
const savedPlayerCount = localStorage.getItem('playerCount');
const savedInitialStack = localStorage.getItem('initialStack');
const savedSmallBlind = localStorage.getItem('smallBlind');

if (savedName) playerNameInput.value = savedName;
if (savedPlayerCount) playerCountInput.value = savedPlayerCount;
if (savedInitialStack) initialStackInput.value = savedInitialStack;
if (savedSmallBlind) smallBlindInput.value = savedSmallBlind;

// Validação de configuração
function validateConfiguration() {
    const name = playerNameInput.value.trim();
    const playerCount = parseInt(playerCountInput.value) || 5;
    const initialStack = parseInt(initialStackInput.value) || 10000;
    const smallBlind = parseInt(smallBlindInput.value) || 25;

    if (!name) {
        alert('Por favor, digite um nome!');
        playerNameInput.focus();
        return false;
    }

    if (playerCount < 2 || playerCount > 9) {
        alert('Número de bots deve ser entre 2 e 9!');
        playerCountInput.focus();
        return false;
    }

    if (initialStack <= 0) {
        alert('Stack inicial deve ser maior que zero!');
        initialStackInput.focus();
        return false;
    }

    if (smallBlind <= 0 || smallBlind >= initialStack) {
        alert('Small blind deve ser maior que zero e menor que o stack inicial!');
        smallBlindInput.focus();
        return false;
    }

    return true;
}

// Função para iniciar jogo
async function startGame() {
    if (!validateConfiguration()) return;

    const playBtn = document.getElementById('playBtn');
    const originalText = playBtn.textContent;
    
    // Desabilita botão para evitar múltiplas chamadas simultâneas
    playBtn.disabled = true;
    playBtn.textContent = 'Iniciando...';

    // Valida e converte valores numéricos
    const playerCount = parseInt(playerCountInput.value, 10);
    const initialStackRaw = initialStackInput.value.trim();
    const initialStack = parseInt(initialStackRaw, 10);
    const smallBlindRaw = smallBlindInput.value.trim();
    const smallBlind = parseInt(smallBlindRaw, 10);
    
    // Log para debug
    console.log('[CONFIG] Valores antes de enviar:', {
        initialStackRaw: initialStackRaw,
        initialStack: initialStack,
        smallBlindRaw: smallBlindRaw,
        smallBlind: smallBlind,
        playerCount: playerCount
    });
    
    // Validação adicional
    if (isNaN(initialStack) || initialStack <= 0) {
        alert('Stack inicial inválido! Por favor, digite um número válido maior que zero.');
        initialStackInput.focus();
        playBtn.disabled = false;
        playBtn.textContent = originalText;
        return;
    }
    
    if (isNaN(smallBlind) || smallBlind <= 0) {
        alert('Small blind inválido! Por favor, digite um número válido maior que zero.');
        smallBlindInput.focus();
        playBtn.disabled = false;
        playBtn.textContent = originalText;
        return;
    }
    
    const config = {
        player_name: playerNameInput.value.trim(),
        player_count: isNaN(playerCount) ? 5 : playerCount,
        initial_stack: initialStack,
        small_blind: smallBlind,
        statistics_visible: true // Mantém sempre true, checkbox removido
    };
    
    // Log final antes de enviar
    console.log('[CONFIG] Configuração final a ser enviada:', config);

    // Salva no localStorage
    localStorage.setItem('playerName', config.player_name);
    localStorage.setItem('playerCount', config.player_count.toString());
    localStorage.setItem('initialStack', config.initial_stack.toString());
    localStorage.setItem('smallBlind', config.small_blind.toString());
    localStorage.setItem('statisticsVisible', 'true');

    // Envia configuração para o servidor
    try {
        // Performance measurement: T026 - Game start within 2 seconds
        const startTime = performance.now();
        
        const response = await fetch('/api/start_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        const data = await response.json();
        const apiTime = performance.now() - startTime;

        if (response.ok && data.status === 'started') {
            // Measure total time until redirect
            const totalTime = performance.now() - startTime;
            
            // Performance validation: should be < 2000ms
            if (totalTime > 2000) {
                console.warn(`[T026] Game start took ${totalTime.toFixed(2)}ms (target: < 2000ms)`);
            } else {
                console.log(`[T026] Game start completed in ${totalTime.toFixed(2)}ms ✓`);
            }
            
            // Store timing for validation
            localStorage.setItem('lastGameStartTime', totalTime.toString());
            
            // Redireciona para o jogo
            window.location.href = 'game.html';
        } else {
            // Reabilita botão em caso de erro
            playBtn.disabled = false;
            playBtn.textContent = originalText;
            alert('Erro ao iniciar jogo: ' + (data.message || 'Erro desconhecido'));
        }
    } catch (error) {
        // Reabilita botão em caso de erro
        playBtn.disabled = false;
        playBtn.textContent = originalText;
        console.error('Erro ao iniciar jogo:', error);
        alert('Erro ao conectar com o servidor');
    }
}

// Botão Jogar - Inicia nova partida
document.getElementById('playBtn').addEventListener('click', startGame);

// Botão Retomar - Retoma partida anterior
document.getElementById('resumeBtn').addEventListener('click', async () => {
    // Verifica se há um jogo ativo
    try {
        const response = await fetch('/api/game_state');
        const data = await response.json();
        
        if (data.active) {
            // Se há jogo ativo, redireciona para o jogo
            window.location.href = 'game.html';
        } else {
            alert('Não há partida anterior para retomar.');
        }
    } catch (error) {
        console.error('Erro ao verificar estado do jogo:', error);
        alert('Erro ao conectar com o servidor');
    }
});

// Botão Histórico - Mostra histórico de partidas
document.getElementById('historyBtn').addEventListener('click', () => {
    // Por enquanto mostra mensagem de desenvolvimento
    alert('Histórico de partidas em desenvolvimento.');
});

// Botão Reset Bots - Reseta memória dos bots
document.getElementById('resetBotsBtn').addEventListener('click', async () => {
    if (confirm('Tem certeza? Isso apagará todo o aprendizado dos bots!')) {
        try {
            const response = await fetch('/api/reset_memory', { method: 'POST' });
            const data = await response.json();
            if (data.status === 'success') {
                alert('Memória dos bots resetada com sucesso!');
            } else {
                alert('Erro ao resetar memória: ' + data.message);
            }
        } catch (error) {
            alert('Erro ao conectar com o servidor');
            console.error(error);
        }
    }
});
