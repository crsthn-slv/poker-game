# Documentação Completa - Sistema de Poker com Múltiplos Bots

## Índice

1. [Visão Geral do Projeto](#visão-geral-do-projeto)
2. [Estrutura do Projeto](#estrutura-do-projeto)
3. [Componentes Principais](#componentes-principais)
4. [Sistema de Jogadores (Bots)](#sistema-de-jogadores-bots)
5. [Sistema de Aprendizado](#sistema-de-aprendizado)
6. [Interface Web](#interface-web)
7. [Servidor Flask](#servidor-flask)
8. [Fluxo do Jogo](#fluxo-do-jogo)
9. [Sistema de Memória Persistente](#sistema-de-memória-persistente)
10. [Modos de Jogo](#modos-de-jogo)

---

## Visão Geral do Projeto

Este é um sistema completo de jogo de poker Texas Hold'em que permite:
- Jogar contra múltiplos bots com diferentes estratégias
- Interface web moderna com visualização de cartas
- Sistema de aprendizado adaptativo para os bots
- Memória persistente entre partidas
- Múltiplos modos de jogo (web, console, AI vs AI)

### Tecnologias Utilizadas

- **Backend**: Python 3 com Flask
- **Motor de Jogo**: PyPokerEngine
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Persistência**: Arquivos JSON para memória dos bots

---

## Estrutura do Projeto

```
poker_test/
├── data/                     # Dados do sistema
│   └── memory/              # Memórias centralizadas dos bots
│       ├── tight_player_memory.json
│       ├── aggressive_player_memory.json
│       └── ...
│
├── docs/                     # Documentação
│   ├── DOCUMENTACAO_COMPLETA.md
│   ├── DEBUGGING.md
│   └── README.md
│
├── game/                     # Scripts de execução do jogo
│   ├── game.py              # Jogo básico AI vs AI
│   ├── game_advanced.py     # Jogo avançado com todas as IAs
│   └── play_console.py      # Jogo interativo no terminal
│
├── players/                  # Todos os bots disponíveis
│   ├── memory_utils.py      # Utilitários para memória centralizada
│   ├── tight_player.py      # Jogador conservador
│   ├── aggressive_player.py  # Jogador agressivo
│   ├── random_player.py     # Jogador aleatório
│   ├── smart_player.py      # Jogador inteligente
│   ├── balanced_player.py   # Jogador balanceado
│   ├── adaptive_player.py   # Jogador adaptativo
│   ├── conservative_aggressive_player.py
│   ├── opportunistic_player.py
│   ├── hybrid_player.py
│   ├── learning_player.py
│   └── console_player.py    # Jogador humano (terminal)
│
├── web/                     # Interface web
│   ├── server.py           # Servidor Flask
│   ├── templates/          # Templates HTML
│   │   ├── index.html
│   │   ├── config.html
│   │   └── game.html
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── api.js          # Comunicação com API
│   │   ├── config.js
│   │   └── game.js         # Lógica do jogo no frontend
│   └── images/             # Link para imagens
│
├── images/                 # Imagens de cartas
├── tests/                  # Testes automatizados
├── requirements.txt        # Dependências Python
└── *_memory.json          # Arquivos de memória dos bots
```

---

## Componentes Principais

### 1. Motor de Jogo (PyPokerEngine)

O projeto utiliza a biblioteca **PyPokerEngine** que gerencia:
- Distribuição de cartas
- Regras do Texas Hold'em
- Gerenciamento de apostas
- Determinação de vencedores
- Ciclo de rounds (preflop, flop, turn, river)

### 2. Sistema de Jogadores

Todos os bots herdam de `BasePokerPlayer` e implementam:
- `declare_action()`: Decide a ação (fold, call, raise)
- `receive_game_start_message()`: Inicialização do jogo
- `receive_round_start_message()`: Início de cada round
- `receive_street_start_message()`: Mudança de street
- `receive_game_update_message()`: Atualização após cada ação
- `receive_round_result_message()`: Resultado do round

---

## Sistema de Jogadores (Bots)

### TightPlayer (Jogador Conservador)

**Características:**
- Blefe: 8% das vezes
- Estratégia: Joga apenas com mãos fortes
- Threshold inicial: 25 pontos de força de mão

**Sistema de Aprendizado:**
- Ajusta threshold quando win rate < 30%
- Reduz blefe após 3+ perdas consecutivas
- Mantém histórico das últimas 10 rodadas

**Quando Joga:**
- Mão muito forte (≥50): Faz raise
- Mão forte (≥threshold ajustado): Faz call
- Mão fraca: Faz fold

### AggressivePlayer (Jogador Agressivo)

**Características:**
- Blefe: 35% das vezes
- Estratégia: Joga muitas mãos, prefere raise
- Nível de agressão inicial: 70%

**Sistema de Aprendizado:**
- Aumenta agressão quando win rate > 60%
- Reduz agressão quando win rate < 30%
- Ajusta baseado no stack (reduz se stack < 70% do inicial)
- Rastreia padrões de blefe dos oponentes
- Mantém histórico das últimas 20 rodadas

**Quando Joga:**
- Sempre tenta fazer raise se possível
- Ajusta valor do raise baseado no nível de agressão aprendido
- Faz call apenas se agressão muito baixa

### RandomPlayer (Jogador Aleatório)

**Características:**
- Blefe: 25% das vezes
- Estratégia: Decisões aleatórias com probabilidades aprendidas

**Sistema de Aprendizado:**
- Ajusta probabilidades de ações (fold/call/raise) baseado em resultados
- Rastreia win rate por tipo de ação
- Aumenta probabilidade de ações que funcionam
- Mantém probabilidades normalizadas (soma = 1)

**Quando Joga:**
- Escolhe ação aleatória baseada em probabilidades aprendidas
- Valor do raise é totalmente aleatório dentro dos limites

### SmartPlayer (Jogador Inteligente)

**Características:**
- Blefe base: 15% (ajusta dinamicamente)
- Estratégia: Análise sofisticada do contexto

**Sistema de Aprendizado Avançado:**
- Ajusta blefe baseado em performance (stack atual vs inicial)
- Rastreia performance por street (preflop, flop, turn, river)
- Analisa sucesso de blefes
- Estratégia por tamanho de pot (small/medium/large)
- Mantém histórico das últimas 50 rodadas

**Quando Joga:**
- Avalia força da mão considerando cartas comunitárias
- Pot grande: blefe mais conservador (CALL)
- Pot pequeno: blefe mais agressivo (RAISE)
- Poucos jogadores: mais agressivo

### BalancedPlayer (Jogador Balanceado)

**Características:**
- Combina Tight (seletividade) + Aggressive (agressão moderada)
- Blefe: 15% das vezes
- Threshold: 30 pontos
- Nível de agressão: 60%

**Sistema de Aprendizado:**
- Ajusta threshold e agressão baseado em win rate
- Se win rate > 50%: aumenta agressão
- Se win rate < 30%: aumenta seletividade (threshold)
- Mantém histórico das últimas 15 rodadas

### AdaptivePlayer (Jogador Adaptativo)

**Características:**
- Combina Smart (análise) + Random (exploração)
- Blefe: 20% inicial
- Sistema de exploração vs exploração (epsilon-greedy)

**Sistema de Aprendizado:**
- 15% de exploração inicial (escolhe aleatoriamente)
- Reduz exploração com o tempo (decay = 0.99)
- Ajusta blefe baseado em performance por street
- Mantém histórico das últimas 30 rodadas

**Quando Joga:**
- 15% das vezes: exploração (ação aleatória)
- 85% das vezes: exploração (usa análise)

### Outros Players

- **ConservativeAggressivePlayer**: Começa conservador, fica agressivo
- **OpportunisticPlayer**: Identifica oportunidades específicas
- **HybridPlayer**: Alterna entre todas as estratégias
- **LearningPlayer**: Sistema de aprendizado avançado
- **ConsolePlayer**: Permite jogador humano no terminal

---

## Sistema de Aprendizado

### Componentes Comuns

Todos os bots implementam:

1. **Histórico de Resultados**
   - Armazena resultados das últimas N rodadas
   - Rastreia vitórias e derrotas
   - Calcula win rate

2. **Ajuste de Parâmetros**
   - Probabilidade de blefe
   - Threshold de força de mão
   - Nível de agressão
   - Probabilidades de ações

3. **Análise Contextual**
   - Performance por street
   - Estratégia por tamanho de pot
   - Padrões dos oponentes
   - Stack atual vs inicial

### Fluxo de Aprendizado

```
1. Jogador recebe cartas
2. Avalia força da mão
3. Decide ação (com ou sem blefe)
4. Executa ação
5. Recebe resultado do round
6. Analisa resultado
7. Ajusta parâmetros baseado em:
   - Win rate recente
   - Performance por contexto
   - Sucesso de blefes
   - Stack atual
8. Salva memória
```

---

## Interface Web

### Estrutura HTML

**game.html:**
- Painel lateral esquerdo: Estatísticas (round, pot, fichas, aposta)
- Área central: Mesa com jogadores e cartas comunitárias
- Botões de ação: Fold, Call, Raise, All-in
- Modais: Fim de round, Fim de jogo

### JavaScript (game.js)

**Funções Principais:**

1. **Renderização:**
   - `renderPlayers()`: Renderiza jogadores na mesa
   - `updateCommunityCards()`: Atualiza cartas comunitárias
   - `updatePlayerCards()`: Atualiza cartas do jogador
   - `updateGameInfo()`: Atualiza todas as informações do jogo

2. **Gerenciamento de Estado:**
   - `startGamePolling()`: Polling do estado do jogo (500ms)
   - `updateTurnMessage()`: Mostra mensagem de turno
   - `showPlayerActions()`: Habilita/desabilita botões de ação

3. **Modais:**
   - `showRoundEndModal()`: Mostra resultado do round
   - `showGameEndModal()`: Mostra resultado final
   - `hideRoundEndModal()`: Esconde modal de round

4. **Ações do Jogador:**
   - Event listeners para botões (fold, call, raise, all-in)
   - Validação de ações
   - Envio para servidor via API

### JavaScript (api.js)

**Funções de API:**

- `startGame(playerName)`: Inicia novo jogo
- `sendPlayerAction(action, amount)`: Envia ação do jogador
- `getGameState()`: Obtém estado atual do jogo
- `resetGame()`: Reseta o jogo

**Tratamento de Erros:**
- Validação de respostas JSON
- Tratamento de erros de rede
- Validação de estrutura de dados

### CSS (style.css)

**Estilos Principais:**
- Layout responsivo
- Dark mode
- Animações de cartas
- Estilos para jogadores (bot vs humano)
- Modais estilizados
- Botões de ação com cores temáticas

---

## Servidor Flask

### Arquivo: web/server.py

**Rotas Principais:**

1. **`/` e `/config.html`**
   - Página de configuração do nome do jogador

2. **`/game.html`**
   - Página principal do jogo

3. **`/api/start_game` (POST)**
   - Inicia novo jogo
   - Cria WebPlayer para jogador humano
   - Seleciona bots aleatórios (6 bots)
   - Inicia jogo em thread separada

4. **`/api/player_action` (POST)**
   - Recebe ação do jogador
   - Notifica WebPlayer para continuar

5. **`/api/game_state` (GET)**
   - Retorna estado atual do jogo
   - Serializa round_state para JSON

6. **`/api/reset_game` (POST)**
   - Reseta estado do jogo

7. **`/api/reset_memory` (POST)**
   - Deleta arquivos de memória dos bots

**Classes Principais:**

### WebPlayer
- Representa o jogador humano na web
- Espera ações via API
- Serializa estado do jogo para frontend
- Gerencia turnos do jogador

**Métodos Importantes:**
- `declare_action()`: Espera ação do jogador via threading.Event
- `_serialize_round_state()`: Converte round_state para JSON
- `_serialize_winners()`: Serializa vencedores
- `_serialize_hand_info()`: Serializa informações de mãos

### BotWrapper
- Wrapper para bots com delay simulado
- Adiciona tempo de "pensamento" (1-3 segundos)
- Indica qual bot está pensando

**Estado do Jogo:**
```python
game_state = {
    'active': False,              # Jogo está ativo?
    'current_round': None,         # Estado do round atual
    'player_name': 'Jogador',     # Nome do jogador
    'player_uuid': None,           # UUID do jogador
    'game_result': None,           # Resultado final
    'thinking_uuid': None          # UUID do bot pensando
}
```

**Threading:**
- Jogo roda em thread separada para não bloquear servidor
- WebPlayer usa threading.Event para esperar ações
- game_lock protege acesso ao game_state

---

## Fluxo do Jogo

### 1. Inicialização

```
1. Jogador acessa /config.html
2. Configura nome
3. Acessa /game.html
4. Frontend chama /api/start_game
5. Servidor:
   - Cria WebPlayer
   - Seleciona 6 bots aleatórios
   - Configura jogo (10 rounds, stack inicial 100, small blind 5)
   - Inicia jogo em thread separada
6. PyPokerEngine inicia primeiro round
```

### 2. Durante o Round

```
1. PyPokerEngine chama declare_action() do próximo jogador
2. Se for bot:
   - BotWrapper adiciona delay
   - Bot decide ação
   - Retorna ação
3. Se for WebPlayer:
   - WebPlayer serializa estado
   - Atualiza game_state['current_round']
   - Espera ação via threading.Event
   - Frontend faz polling, vê que é sua vez
   - Jogador clica em ação
   - Frontend chama /api/player_action
   - WebPlayer recebe ação e continua
4. PyPokerEngine processa ação
5. Chama receive_game_update_message() de todos
6. WebPlayer atualiza game_state
7. Frontend faz polling e atualiza UI
8. Repete até round terminar
```

### 3. Fim do Round

```
1. PyPokerEngine determina vencedor
2. Chama receive_round_result_message() de todos
3. WebPlayer:
   - Serializa winners e hand_info
   - Calcula final_stacks
   - Atualiza game_state['current_round'] com round_ended=True
4. Frontend detecta round_ended
5. Mostra modal de fim de round
6. Bots aprendem e ajustam parâmetros
7. Bots salvam memória
```

### 4. Fim do Jogo

```
1. Após 10 rounds, PyPokerEngine finaliza
2. Retorna game_result
3. Servidor atualiza game_state['game_result']
4. Frontend detecta game_result e active=False
5. Mostra modal de fim de jogo
6. Jogador pode jogar novamente
```

---

## Sistema de Memória Persistente

### Arquivos de Memória

Todos os arquivos de memória estão centralizados em `data/memory/`:
- `data/memory/tight_player_memory.json`
- `data/memory/aggressive_player_memory.json`
- `data/memory/smart_player_memory.json`
- etc.

**Localização Centralizada:**
- Todas as memórias (terminal e web) são salvas no mesmo local
- Facilita backup e gerenciamento
- Evita duplicação de dados

### Estrutura da Memória

Exemplo (TightPlayer):
```json
{
  "bluff_probability": 0.08,
  "tightness_threshold": 25,
  "total_rounds": 150,
  "wins": 45,
  "consecutive_losses": 0
}
```

### Carregamento e Salvamento

**Carregamento:**
- No `__init__()` de cada bot
- Se arquivo existe, carrega parâmetros aprendidos
- Se não existe, usa valores padrão

**Salvamento:**
- Após cada round (em `receive_round_result_message()`)
- Periodicamente (a cada 5 rounds em `receive_round_start_message()`)
- Em caso de erro, falha silenciosamente (não quebra jogo)

### Persistência Entre Partidas

- Bots mantêm aprendizado entre partidas
- Evoluem com o tempo
- Adaptam-se ao estilo de jogo do jogador humano

---

## Modos de Jogo

### 1. Modo Web (Recomendado)

**Como usar:**
```bash
cd web
python3 server.py
# Acesse http://localhost:5002 (ou a porta configurada na variável de ambiente PORT)
```

**Configuração:**
O servidor pode ser configurado através de variáveis de ambiente ou arquivo `.env`:
- `PORT`: Porta do servidor (padrão: 5002)
- `HOST`: Host do servidor (padrão: 0.0.0.0)
- `ALLOWED_ORIGINS`: Origens permitidas para CORS (padrão: *)
- `POKER_DEBUG`: Ativa modo debug (padrão: false)

**Características:**
- Interface visual completa
- Imagens de cartas
- Estatísticas em tempo real
- Modais informativos
- Jogador humano vs 6 bots

### 2. Modo Terminal Interativo

**Como usar:**
```bash
python3 -m game.play_console
```

**Características:**
- Jogador humano no terminal
- 3 bots (Tight, Aggressive, Smart)
- Comandos: 'f' (fold), 'c' (call), 'r' (raise)
- Output textual do jogo

### 3. Modo AI vs AI Básico

**Como usar:**
```bash
python3 -m game.game
```

**Características:**
- 3 FishPlayers jogando entre si
- Output textual
- Sem interação humana

### 4. Modo AI vs AI Avançado

**Como usar:**
```bash
python3 -m game.game_advanced
```

**Características:**
- 5 bots diferentes (Tight, Aggressive, Random, Smart, Learning)
- Todas as estratégias
- Output textual detalhado

---

## Detalhes Técnicos

### Serialização de Dados

**Desafio:** PyPokerEngine retorna objetos Python que não são JSON nativos.

**Solução:**
- `_serialize_round_state()`: Converte round_state para dict
- `_serialize_winners()`: Converte winners para lista de dicts
- `_serialize_hand_info()`: Converte hand_info para lista de dicts
- Tratamento de diferentes tipos (dict, objeto, etc.)

### Threading e Concorrência

**WebPlayer:**
- Usa `threading.Event` para esperar ações
- Thread principal do jogo bloqueia até ação chegar
- Frontend envia ação via API
- Event é setado e jogo continua

**BotWrapper:**
- Adiciona delay aleatório (1-3s) para simular pensamento
- Atualiza `game_state['thinking_uuid']` durante delay

**game_lock:**
- Protege acesso ao `game_state`
- Evita condições de corrida
- Usado em todas as atualizações do estado

### Polling do Frontend

**Frequência:** 500ms (2 vezes por segundo)

**O que faz:**
1. Chama `/api/game_state`
2. Atualiza UI com novo estado
3. Verifica se é vez do jogador
4. Habilita/desabilita botões
5. Atualiza cartas, pot, stacks
6. Detecta fim de round/jogo

**Otimizações:**
- Não recria elementos desnecessariamente
- Mantém referências
- Atualiza apenas o que mudou

### Avaliação de Força de Mão

**Método comum usado pelos bots:**

```python
def _evaluate_hand_strength(hole_card):
    # Par: 50-62 pontos (baseado no rank)
    # Duas cartas altas: 40-45 pontos
    # Uma carta alta: 25-30 pontos
    # Mesmo naipe: 15-20 pontos
    # Cartas baixas: 5-10 pontos
```

**SmartPlayer considera:**
- Cartas comunitárias
- Possibilidade de trinca, dois pares, flush
- Ajusta força baseado em combinações possíveis

### Sistema de Blefe

**Decisão de Blefe:**
1. Calcula probabilidade base
2. Ajusta baseado em:
   - Performance recente
   - Contexto da mesa (pot, jogadores)
   - Street atual
   - Stack atual vs inicial
3. Gera número aleatório
4. Se < probabilidade ajustada: blefa

**Tipo de Blefe:**
- CALL: Blefe conservador
- RAISE: Blefe agressivo
- Decisão baseada em contexto (pot, jogadores)

---

## Extensibilidade

### Adicionar Novo Bot

1. Criar arquivo em `players/novo_bot.py`
2. Herdar de `BasePokerPlayer`
3. Implementar métodos obrigatórios
4. Adicionar sistema de aprendizado (opcional)
5. Registrar em `web/server.py` se quiser usar na web

**Exemplo mínimo:**
```python
from pypokerengine.players import BasePokerPlayer

class NovoBot(BasePokerPlayer):
    def declare_action(self, valid_actions, hole_card, round_state):
        # Lógica de decisão
        return 'fold', 0
    
    def receive_game_start_message(self, game_info):
        pass
    
    # ... outros métodos obrigatórios
```

### Modificar Interface Web

1. Editar `web/templates/game.html` para HTML
2. Editar `web/css/style.css` para estilos
3. Editar `web/js/game.js` para lógica
4. Adicionar novas rotas em `web/server.py` se necessário

### Adicionar Novos Modos de Jogo

1. Criar arquivo em `game/novo_modo.py`
2. Importar bots desejados
3. Configurar jogo com `setup_config()`
4. Iniciar com `start_poker()`

---

## Testes

### Estrutura de Testes

```
tests/
├── test_game_flow.py      # Testes de fluxo do jogo
├── test_serialization.py  # Testes de serialização
└── test_server.py         # Testes do servidor
```

### Executar Testes

```bash
# Todos os testes
python3 -m pytest tests/ -v

# Teste específico
python3 -m pytest tests/test_serialization.py -v
```

---

## Debugging

### Modo Debug Backend

```bash
export POKER_DEBUG=true
python3 web/server.py
```

**O que ativa:**
- Logs detalhados de todas as operações
- Stack traces completos
- Informações de serialização

### Modo Debug Frontend

Editar `web/js/game.js`:
```javascript
const DEBUG_MODE = true; // Mude para true
```

**O que ativa:**
- Logs no console do navegador
- Validações detalhadas
- Informações de estado

### Logs Importantes

**Backend:**
- `[TIMESTAMP] ERROR: ...` - Erros críticos
- `[TIMESTAMP] DEBUG: ...` - Informações de debug

**Frontend:**
- `[TIMESTAMP] DEBUG: ...` - Logs de debug
- Erros no console do navegador

---

## Conclusão

Este sistema implementa um jogo de poker completo com:

✅ Múltiplos bots com estratégias diferentes  
✅ Sistema de aprendizado adaptativo  
✅ Memória persistente entre partidas  
✅ Interface web moderna e responsiva  
✅ Múltiplos modos de jogo  
✅ Sistema robusto de serialização  
✅ Threading seguro para concorrência  
✅ Tratamento de erros abrangente  

O código é extensível e permite adicionar novos bots, modificar estratégias e personalizar a interface facilmente.

---

## Referências

- **PyPokerEngine**: Biblioteca Python para jogos de poker
- **Flask**: Framework web Python
- **Texas Hold'em**: Variante de poker implementada

---

*Documentação gerada em: 2024*

