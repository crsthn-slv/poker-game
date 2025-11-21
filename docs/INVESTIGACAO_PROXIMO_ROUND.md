# Investigação: Próximo Round Não Inicia

## Problema

Após clicar no botão "Próximo Round", o sistema aguarda 5 segundos mas o novo round não inicia automaticamente. O PyPokerEngine não chama `receive_round_start_message`.

## Logs Adicionados

Foram adicionados logs detalhados em vários pontos do sistema para rastrear o problema:

### 1. WebPlayer
- **🔴 [SERVER]** - `receive_round_result_message`: Mostra quando o round termina e quanto tempo leva
- **🟢 [SERVER]** - `receive_round_start_message`: Mostra quando o PyPokerEngine inicia um novo round

### 2. BotWrapper
- **🟡 [SERVER]** - `receive_round_result_message`: Mostra tempo de execução de cada bot
- **🟡 [SERVER]** - `receive_round_start_message`: Mostra quando cada bot recebe notificação de novo round

### 3. Thread do Jogo
- **🟣 [SERVER]** - Thread do jogo: Mostra quando `start_poker()` é chamado e quando retorna

### 4. Salvamento de Memória
- **💾 [MEMORY]** - Mostra tempo de salvamento de memória dos bots (apenas se > 0.1s)

### 5. Estado do Jogo
- **🔵 [SERVER]** - `get_game_state`: Mostra quando o frontend verifica o estado

## Como Testar Isoladamente

### Teste 1: Verificar se o problema é com os bots

**Objetivo**: Verificar se algum bot está bloqueando o fluxo

**Passos**:
1. Modificar `web/server.py` na função `start_game()` para usar menos bots:
   ```python
   # Em vez de 6 bots, usar apenas 1
   selected_bots = random.sample(available_bots, min(1, len(available_bots)))
   ```

2. Executar o jogo e observar os logs:
   - Verificar se `receive_round_result_message` dos bots termina rapidamente
   - Verificar se algum bot demora muito (> 1 segundo)
   - Verificar se há erros nos bots

3. Se o problema persistir com 1 bot, o problema não é quantidade de bots

### Teste 2: Verificar se o problema é com salvamento de memória

**Objetivo**: Verificar se o salvamento de memória está bloqueando

**Passos**:
1. Modificar `players/error_handling.py` na função `safe_memory_save()` para retornar imediatamente:
   ```python
   def safe_memory_save(memory_file, memory_data):
       # Retorna True sem salvar nada (para teste)
       return True
   ```

2. Executar o jogo e observar os logs:
   - Verificar se os bots terminam mais rápido
   - Verificar se o próximo round inicia

3. Se o problema for resolvido, o salvamento de memória está bloqueando

### Teste 3: Verificar se o jogo terminou

**Objetivo**: Verificar se o jogo chegou ao limite de rounds

**Passos**:
1. Verificar nos logs se `Round count: X` onde X >= 10 (DEFAULT_MAX_ROUNDS)
2. Se sim, o jogo terminou e não há mais rounds

### Teste 4: Verificar se há erro silencioso

**Objetivo**: Verificar se há exceção não tratada que está quebrando o fluxo

**Passos**:
1. Verificar logs do servidor por erros (❌)
2. Verificar se `start_poker()` retornou ou se há exceção na thread
3. Verificar se `game_state['active']` está True

## Interpretação dos Logs

### Fluxo Normal Esperado

1. **Round termina**:
   ```
   🔴 [SERVER] WebPlayer.receive_round_result_message CHAMADO
   🟡 [SERVER] BotWrapper.receive_round_result_message - Bot: X
   💾 [MEMORY] Bot X - save_memory: 0.XXXs
   🟡 [SERVER] BotWrapper.receive_round_result_message FINALIZADO
   🔴 [SERVER] WebPlayer.receive_round_result_message FINALIZADO
   🔴 [SERVER] Aguardando PyPokerEngine iniciar próximo round...
   ```

2. **Novo round inicia** (deve acontecer automaticamente):
   ```
   🟢 [SERVER] WebPlayer.receive_round_start_message CHAMADO
   🟢 [SERVER] ✅ NOVO ROUND INICIADO PELO PYPOKERENGINE!
   🟡 [SERVER] BotWrapper.receive_round_start_message - Bot: X
   🟢 [SERVER] Estado do jogo atualizado com novo round
   ```

### Problemas Possíveis

1. **Bots demorando muito**:
   - Se algum bot demora > 1 segundo em `receive_round_result_message`, pode estar bloqueando
   - Verificar logs 💾 [MEMORY] para ver se salvamento está lento

2. **PyPokerEngine não chama receive_round_start_message**:
   - Se não aparecer log 🟢 [SERVER] `receive_round_start_message CHAMADO`, o PyPokerEngine não está iniciando
   - Possíveis causas:
     - Jogo terminou (round_count >= MAX_ROUNDS)
     - Erro silencioso no PyPokerEngine
     - PyPokerEngine esperando algo que nunca acontece

3. **Thread do jogo travada**:
   - Se não aparecer log 🟣 [SERVER] após `start_poker()`, a thread pode ter travado
   - Verificar se há exceção não tratada

## Próximos Passos

Após executar os testes e analisar os logs:

1. **Se o problema for com bots**: Otimizar ou remover salvamento de memória síncrono
2. **Se o problema for com PyPokerEngine**: Investigar por que não está iniciando próximo round
3. **Se o problema for com jogo terminado**: Implementar detecção correta de fim de jogo
4. **Se o problema for com erro silencioso**: Adicionar tratamento de exceção mais robusto

## Comandos Úteis

### Ver logs em tempo real (Linux/Mac)
```bash
tail -f logs/server.log | grep -E "\[SERVER\]|\[MEMORY\]"
```

### Filtrar apenas logs de round
```bash
grep -E "receive_round|Round|round" logs/server.log
```

### Verificar se há erros
```bash
grep "❌\|ERRO\|ERROR" logs/server.log
```

