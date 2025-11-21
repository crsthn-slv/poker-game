// Carrega nome salvo
const playerNameInput = document.getElementById('playerName');
const savedName = localStorage.getItem('playerName');
if (savedName) {
    playerNameInput.value = savedName;
}

// Salva nome e vai para o jogo
document.getElementById('saveBtn').addEventListener('click', () => {
    const name = playerNameInput.value.trim();
    if (name) {
        localStorage.setItem('playerName', name);
        window.location.href = 'game.html';
    } else {
        alert('Por favor, digite um nome!');
        playerNameInput.focus();
    }
});

// Volta para início
document.getElementById('backBtn').addEventListener('click', () => {
    window.location.href = 'index.html';
});

// Resetar memória dos bots
document.getElementById('resetMemoryBtn').addEventListener('click', async () => {
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

