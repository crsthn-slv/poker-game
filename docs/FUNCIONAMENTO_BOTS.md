# Funcionamento dos Bots e Sistema de Memória

Esta documentação explica em detalhes como os bots funcionam, suas estruturas, estratégias e como o sistema de memória persistente opera.

## Índice

1. [Estrutura Base dos Bots](#estrutura-base-dos-bots)
2. [Sistema de Memória Persistente](#sistema-de-memória-persistente)
3. [Tipos de Bots e Estratégias](#tipos-de-bots-e-estratégias)
4. [Ciclo de Vida de um Bot](#ciclo-de-vida-de-um-bot)
5. [Sistema de Aprendizado](#sistema-de-aprendizado)
6. [Componentes Compartilhados](#componentes-compartilhados)

---

## Estrutura Base dos Bots

### Herança de BasePokerPlayer

Todos os bots herdam da classe `BasePokerPlayer` do PyPokerEngine. Esta classe base fornece a interface necessária para interagir com o motor do jogo.

```python
from pypokerengine.players import BasePokerPlayer

class MeuBot(BasePokerPlayer):
    # Implementação do bot
```

### Métodos Obrigatórios

O `BasePokerPlayer` requer que você implemente os seguintes métodos:

#### 1. `declare_action(valid_actions, hole_card, round_state)`

**Quando é chamado:** A cada vez que é a vez do bot jogar.

**Responsabilidade:** Decidir qual ação tomar (FOLD, CALL ou RAISE) e retornar essa decisão.

**Parâmetros:**
- `valid_actions`: Lista de ações válidas `[fold_info, call_info, raise_info]`
- `hole_card`: Lista de 2 cartas do bot (ex: `['SA', 'HK']`)
- `round_state`: Estado completo do round atual

**Retorno:** Tupla `(action, amount)` onde:
- `action`: String `'fold'`, `'call'` ou `'raise'`
- `amount`: Valor inteiro (para raise) ou valor do call

**Exemplo:**
```python
def declare_action(self, valid_actions, hole_card, round_state):
    # Avalia força da mão
    hand_strength = self._evaluate_hand_strength(hole_card, round_state)
    
    # Decide ação baseada na estratégia
    if hand_strength >= 50:
        raise_action = valid_actions[2]
        return raise_action['action'], raise_action['amount']['min']
    elif hand_strength >= 25:
        call_action = valid_actions[1]
        return call_action['action'], call_action['amount']
    else:
        fold_action = valid_actions[0]
        return fold_action['action'], fold_action['amount']
```

#### 2. `receive_game_start_message(game_info)`

**Quando é chamado:** Uma vez, no início do jogo.

**Responsabilidade:** Inicializar variáveis globais do jogo (como stack inicial).

**Parâmetros:**
- `game_info`: Informações sobre o jogo (players, configurações, etc.)

#### 3. `receive_round_start_message(round_count, hole_card, seats)`

**Quando é chamado:** No início de cada round.

**Responsabilidade:** Preparar para um novo round, salvar memória periodicamente.

**Parâmetros:**
- `round_count`: Número do round atual
- `hole_card`: Cartas do bot para este round
- `seats`: Informações sobre todos os jogadores

#### 4. `receive_street_start_message(street, round_state)`

**Quando é chamado:** Quando uma nova street começa (flop, turn, river).

**Responsabilidade:** Atualizar estado interno baseado na nova street.

**Parâmetros:**
- `street`: String `'preflop'`, `'flop'`, `'turn'` ou `'river'`
- `round_state`: Estado atual do round

#### 5. `receive_game_update_message(action, round_state)`

**Quando é chamado:** Após cada ação de qualquer jogador.

**Responsabilidade:** Analisar ações dos oponentes, aprender padrões.

**Parâmetros:**
- `action`: Informações sobre a ação tomada (quem, o quê, quanto)
- `round_state`: Estado atualizado do round

#### 6. `receive_round_result_message(winners, hand_info, round_state)`

**Quando é chamado:** No final de cada round, após determinar o vencedor.

**Responsabilidade:** Aprender com o resultado, ajustar estratégia, salvar memória.

**Parâmetros:**
- `winners`: Lista de jogadores que ganharam o round
- `hand_info`: Informações sobre as mãos dos jogadores
- `round_state`: Estado final do round

---

## Sistema de Memória Persistente Unificada

### Estrutura Unificada

Todos os bots agora usam a **mesma estrutura de memória**, diferenciando-se apenas nos valores iniciais e na forma como evoluem/aprendem. Isso torna o sistema mais consistente e fácil de manter.

### Localização dos Arquivos

Todos os arquivos de memória são armazenados centralmente em `data/memory/`:

```
data/memory/
├── tight_player_memory.json
├── aggressive_player_memory.json
├── smart_player_memory.json
├── learning_player_memory.json
└── ...
```

### Módulo Compartilhado: `unified_memory.py` e `memory_manager.py`

A estrutura de memória é gerenciada pelos módulos compartilhados:

- `unified_memory.py`: Funções utilitárias para criar e manipular memória
- `memory_manager.py`: Classe `UnifiedMemoryManager` que facilita o uso pelos bots

### Estrutura dos Arquivos de Memória

Todos os bots usam a mesma estrutura JSON:

1. **Parâmetros de estratégia** (bluff_probability, aggression_level, tightness_threshold)
2. **Estatísticas** (total_rounds, wins)
3. **Histórico de oponentes** (ações observadas, cartas quando disponíveis, resultados)
4. **Histórico de rounds** (ações do bot, resultados, contexto)

**Exemplo de Estrutura Unificada:**
```json
{
  "bluff_probability": 0.17,
  "aggression_level": 0.55,
  "tightness_threshold": 27,
  "total_rounds": 100,
  "wins": 25,
  "opponents": {
    "uuid-oponente-1": {
      "name": "TightPlayer",
      "first_seen_round": 1,
      "last_seen_round": 10,
      "total_rounds_against": 10,
      "rounds_against": [
        {
          "round": 1,
          "opponent_actions": [
            {"street": "preflop", "action": "fold"},
            {"street": "flop", "action": "call", "amount": 10}
          ],
          "reached_showdown": true,
          "hole_cards": ["SA", "HK"],
          "hand_strength": 45,
          "final_result": {
            "won_against_me": false,
            "i_won": true
          }
        }
      ]
    }
  },
  "round_history": [
    {
      "round": 1,
      "opponents_uuids": ["uuid-1", "uuid-2"],
      "my_actions": [
        {
          "street": "preflop",
          "action": "raise",
          "amount": 15,
          "hand_strength": 45,
          "pot_size": 20,
          "active_players": 4,
          "was_bluff": false,
          "result": "good"
        }
      ],
      "final_result": {
        "won": true,
        "pot_won": 60,
        "stack_change": 30,
        "final_stack": 130
      }
    }
  ]
}
```

### Diferenças entre Bots

Todos os bots usam a mesma estrutura, mas com valores iniciais diferentes:

| Bot | bluff_probability | aggression_level | tightness_threshold |
|-----|-------------------|------------------|---------------------|
| TightPlayer | 0.15 | 0.50 | 30 |
| AggressivePlayer | 0.20 | 0.60 | 25 |
| SmartPlayer | 0.17 | 0.55 | 27 |
| LearningPlayer | 0.18 | 0.55 | 28 |
| RandomPlayer | 0.17 | 0.55 | 27 |

A diferença está na **evolução/aprendizado**: cada bot ajusta esses parâmetros de forma diferente baseado em seus resultados.

### Carregamento de Memória

A memória é carregada no `__init__()` do bot usando `UnifiedMemoryManager`:

```python
from .memory_manager import UnifiedMemoryManager

def __init__(self, memory_file="meu_bot_memory.json"):
    # Inicializa gerenciador de memória unificada
    self.memory_manager = UnifiedMemoryManager(
        memory_file,
        default_bluff=0.17,
        default_aggression=0.55,
        default_tightness=27
    )
    self.memory = self.memory_manager.get_memory()
    
    # Atualiza valores locais
    self.bluff_probability = self.memory['bluff_probability']
    self.aggression_level = self.memory['aggression_level']
    self.tightness_threshold = self.memory['tightness_threshold']
```

O `UnifiedMemoryManager`:
1. Carrega memória anterior se existir
2. Se não existir, cria estrutura padrão
3. Falha silenciosamente (não quebra o jogo)

### Salvamento de Memória

A memória é salva em dois momentos principais:

1. **Periodicamente** (a cada 5 rounds) em `receive_round_start_message()`:
```python
def receive_round_start_message(self, round_count, hole_card, seats):
    if round_count % 5 == 0:
        self.memory_manager.save()
```

2. **Após aprendizado** em `receive_round_result_message()`:
```python
def receive_round_result_message(self, winners, hand_info, round_state):
    # Processa resultado e atualiza memória
    self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
    
    # ... lógica de aprendizado ...
    
    # Salva memória após ajustes
    self.memory_manager.save()
```

O método `save()` do `UnifiedMemoryManager`:
1. Serializa a estrutura de memória completa
2. Escreve no arquivo de memória
3. Falha silenciosamente em caso de erro (não quebra o jogo)

### Registro de Ações e Oponentes

Durante o jogo, os bots registram:

1. **Ações próprias** em `declare_action()`:
```python
def declare_action(self, valid_actions, hole_card, round_state):
    # Identifica oponentes
    self.memory_manager.identify_opponents(round_state, self.uuid)
    
    # ... decide ação ...
    
    # Registra ação
    self.memory_manager.record_my_action(
        street, action, amount, hand_strength, round_state, was_bluff
    )
    
    return action, amount
```

2. **Ações dos oponentes** em `receive_game_update_message()`:
```python
def receive_game_update_message(self, action, round_state):
    player_uuid = action.get('uuid')
    if player_uuid and player_uuid != self.uuid:
        self.memory_manager.record_opponent_action(player_uuid, action, round_state)
```

3. **Resultados e cartas** em `receive_round_result_message()`:
```python
def receive_round_result_message(self, winners, hand_info, round_state):
    # Processa resultado completo (inclui cartas dos oponentes que chegaram ao showdown)
    self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
```

### Histórico de Oponentes

Para cada oponente, o bot registra:
- **Nome** do oponente
- **Ações observadas** durante cada round
- **Cartas** (quando o oponente chega ao showdown)
- **Força da mão** calculada a partir das cartas
- **Resultado** contra esse oponente
- **Análise simples** (ex: "blefe_sucesso" se tinha mão ruim mas ganhou)

Isso permite que o bot aprenda padrões observados sem inferir valores abstratos.

---

## Tipos de Bots e Estratégias

### 1. TightPlayer (Jogador Conservador)

**Filosofia:** Joga apenas com mãos fortes, blefa raramente.

**Características:**
- Blefe: 8% base (pode ser reduzido após perdas)
- Threshold de força: 25-35 (ajustável)
- Prefere CALL quando blefa (70% das vezes)

**Sistema de Aprendizado:**
- Mantém histórico das últimas 10 rodadas
- Aumenta threshold quando win rate < 30%
- Reduz blefe após 3+ perdas consecutivas
- Aprendizado conservador (ajustes lentos)

**Estrutura de Memória:** Usa estrutura unificada com valores iniciais:
- `bluff_probability`: 0.15
- `aggression_level`: 0.50
- `tightness_threshold`: 30

### 2. AggressivePlayer (Jogador Agressivo)

**Filosofia:** Joga muitas mãos, blefa frequentemente, prefere raise.

**Características:**
- Blefe: 35% base (ajustável)
- Nível de agressão: 70% inicial
- Prefere RAISE quando blefa (60% das vezes)

**Sistema de Aprendizado:**
- Mantém histórico das últimas 20 rodadas
- Aumenta agressão quando win rate > 60%
- Reduz agressão quando win rate < 30%
- Rastreia padrões de blefe dos oponentes
- Ajusta baseado no stack (reduz se stack < 70% do inicial)

**Estrutura de Memória:** Usa estrutura unificada com valores iniciais:
- `bluff_probability`: 0.20
- `aggression_level`: 0.60
- `tightness_threshold`: 25

### 3. RandomPlayer (Jogador Aleatório)

**Filosofia:** Decisões estocásticas com probabilidades aprendidas.

**Características:**
- Blefe: 25% base
- Escolhe ações aleatoriamente baseado em probabilidades
- Aprende quais ações funcionam melhor

**Sistema de Aprendizado:**
- Rastreia win rate por tipo de ação (fold/call/raise)
- Ajusta probabilidades de ações baseado em resultados
- Aumenta probabilidade de ações que funcionam
- Mantém probabilidades normalizadas (soma = 1)

**Estrutura de Memória:**
```json
{
  "bluff_probability": float,
  "action_probabilities": {
    "fold": float,
    "call": float,
    "raise": float
  },
  "action_results": {
    "fold": {"wins": int, "total": int},
    "call": {"wins": int, "total": int},
    "raise": {"wins": int, "total": int}
  },
  "total_rounds": int,
  "wins": int
}
```

### 4. SmartPlayer (Jogador Inteligente)

**Filosofia:** Análise sofisticada do contexto, ajuste dinâmico de estratégia.

**Características:**
- Blefe: 15% base, ajustado dinamicamente
- Ajusta blefe baseado na performance (stack atual vs inicial)
- Análise multi-dimensional (street, pot size, contexto)

**Sistema de Aprendizado Avançado:**
- Histórico das últimas 50 rodadas
- Performance por street (preflop, flop, turn, river)
- Taxa de sucesso de blefes
- Estratégia por tamanho de pot
- Ajusta probabilidade baseado em múltiplos fatores

**Estrutura de Memória:** Usa estrutura unificada com valores iniciais:
- `bluff_probability`: 0.17
- `aggression_level`: 0.55
- `tightness_threshold`: 27

### 5. LearningPlayer (Jogador que Aprende)

**Filosofia:** Aprende padrões dos oponentes, adapta estratégia continuamente.

**Características:**
- Blefe: 20% inicial
- Nível de agressão: 50% inicial
- Tightness (seletividade): 50% inicial
- Taxa de aprendizado: 0.1 (10%)

**Sistema de Aprendizado:**
- Rastreia histórico de ações de cada oponente (UUID)
- Calcula padrões de cada oponente (agressão, tightness, frequência de blefe)
- Ajusta estratégia baseado em performance recente
- Ajusta blefe baseado na agressão dos oponentes
- Usa learning rate para suavizar atualizações

**Estrutura de Memória:** Usa estrutura unificada com valores iniciais:
- `bluff_probability`: 0.18
- `aggression_level`: 0.55
- `tightness_threshold`: 28

O histórico de oponentes contém ações observadas e cartas (quando disponíveis), não padrões inferidos.

### 6. HybridPlayer (Jogador Híbrido)

**Filosofia:** Combina múltiplas estratégias, alterna entre elas baseado em contexto.

**Características:**
- Múltiplas estratégias: tight, aggressive, balanced, smart
- Escolhe estratégia baseada em performance
- Alterna estratégias conforme o contexto

**Sistema de Aprendizado:**
- Rastreia performance de cada estratégia
- Escolhe melhor estratégia baseado em contexto
- Mantém histórico de contextos e estratégias usadas

### 7. AdaptivePlayer (Jogador Adaptativo)

**Filosofia:** Combina análise inteligente com exploração aleatória.

**Características:**
- Blefe: 17% inicial (ajustado dinamicamente)
- Epsilon: 10% (probabilidade de exploração, reduzido de 15%)
- Decay de exploração: 0.999 (reduz exploração muito lentamente)

**Sistema de Aprendizado:**
- Exploração vs Exploração (Epsilon-Greedy)
- Rastreia sucesso de estratégias
- Performance por street
- Reduz exploração gradualmente
- Ajusta blefe baseado em win rate recente (evolução lenta)

**Estrutura de Memória:** Usa estrutura unificada com valores iniciais:
- `bluff_probability`: 0.17
- `aggression_level`: 0.56
- `tightness_threshold`: 27

### 8. BalancedPlayer (Jogador Balanceado)

**Filosofia:** Combina Tight (seletividade) + Aggressive (agressão moderada). Equilibra conservadorismo e agressão.

**Características:**
- Blefe: 16% base (nivelado: ligeiramente acima da média)
- Nível de agressão: 57% inicial (nivelado)
- Threshold de seletividade: 28 (nivelado)
- Prefere CALL quando blefa (50% das vezes)

**Sistema de Aprendizado:**
- Mantém histórico das últimas 10 rodadas
- Ajusta parâmetros baseado em win rate recente
- Evolução muito lenta: ajustes de 0.1% por vez
- Aumenta agressão e blefe quando win rate > 60%
- Reduz agressão e aumenta threshold quando win rate < 30%

**Estrutura de Memória:** Usa estrutura unificada com valores iniciais:
- `bluff_probability`: 0.16
- `aggression_level`: 0.57
- `tightness_threshold`: 28

### 9. ConservativeAggressivePlayer (Jogador Conservador-Agressivo)

**Filosofia:** Começa muito conservador, fica agressivo quando está ganhando. Adapta estilo baseado em performance.

**Características:**
- Blefe: 5% inicial (muito conservador)
- Modo conservador: ativo inicialmente
- Threshold de seletividade: 35 inicial (muito seletivo)
- Nível de agressão: 40% inicial (baixo)
- Muda para modo agressivo quando win rate > 60%
- Volta para modo conservador quando win rate < 30%

**Sistema de Aprendizado:**
- Mantém histórico das últimas 5 rodadas
- Alterna entre dois modos:
  - **Modo Conservador:** Blefe raro (5%), threshold alto (35), agressão baixa (40%)
  - **Modo Agressivo:** Blefe mais frequente (até 25%), threshold baixo (25), agressão alta (até 80%)
- Ajusta parâmetros baseado em win rate recente
- Mudanças de modo são graduais mas perceptíveis

**Estrutura de Memória:** Usa estrutura unificada com valores iniciais:
- `bluff_probability`: 0.05
- `aggression_level`: 0.40
- `tightness_threshold`: 35
- `conservative_mode`: True (campo adicional)

### 10. OpportunisticPlayer (Jogador Oportunista)

**Filosofia:** Identifica oportunidades de ataque e ataca agressivamente. Combina análise de contexto com agressão seletiva.

**Características:**
- Blefe: 25% inicial (alto)
- Nível de agressão: 65% inicial (alto)
- Threshold de seletividade: 25 (menos seletivo, oportunista)
- Sistema de análise de oportunidades:
  - Poucos jogadores ativos = oportunidade (+30 pontos)
  - Pot pequeno = oportunidade de blefe (+20 pontos)
  - Street inicial (preflop/flop) = mais oportunidades (+15 pontos)
- Ajusta probabilidade de blefe baseado em score de oportunidade

**Sistema de Aprendizado:**
- Mantém histórico das últimas 10 rodadas
- Aumenta agressão e blefe quando win rate > 50%
- Reduz agressão e blefe quando win rate < 30%
- Aprende quais tipos de oportunidades funcionam melhor
- Ajusta estratégia baseado em performance recente

**Estrutura de Memória:** Usa estrutura unificada com valores iniciais:
- `bluff_probability`: 0.25
- `aggression_level`: 0.65
- `tightness_threshold`: 25

### 11. FishPlayer (Jogador Peixe)

**Filosofia:** Jogador passivo que aprende lentamente. Começa sempre fazendo call, mas aprende quando foldar.

**Características:**
- Blefe: 10% inicial (baixo, peixe não blefa muito)
- Nível de agressão: 30% inicial (baixo, peixe é passivo)
- Threshold de seletividade: 20 (muito baixo, joga muitas mãos)
- Probabilidade de call: 95% inicial (sempre faz call)
- Comportamento típico: prefere call sobre fold
- Aprende a foldar quando está perdendo muito

**Sistema de Aprendizado:**
- Mantém histórico das últimas 20 rodadas
- Aprendizado muito lento: ajusta probabilidade de call baseado em win rate
- Se win rate < 25%: reduz probabilidade de call (aprende a foldar mais)
- Se win rate > 50%: mantém comportamento de call
- Ajustes são graduais (5% por vez)

**Estrutura de Memória:** Usa estrutura unificada com valores iniciais:
- `bluff_probability`: 0.10
- `aggression_level`: 0.30
- `tightness_threshold`: 20
- `call_probability`: 0.95 (campo adicional)

### 12. ConsolePlayer (Jogador de Console)

**Filosofia:** Bot especial para jogador humano. Não usa sistema de aprendizado automático, pois é controlado pelo usuário.

**Características:**
- Interface de console interativa
- HUD completo com informações do jogo
- Calcula probabilidade de vitória usando simulação Monte Carlo
- Mostra cartas, pot, stacks, histórico de ações
- Cache de probabilidades para otimização
- Não possui sistema de aprendizado (jogador humano decide)

**Funcionalidades:**
- Exibe cartas do jogador com força da mão
- Mostra cartas comunitárias quando disponíveis
- Calcula e exibe probabilidade de vitória
- Mostra pot e stacks de todos os jogadores
- Histórico compacto de ações
- Suporte para sair do jogo (tecla 'q')

**Nota:** Este bot não usa sistema de memória unificado, pois é controlado pelo jogador humano através do console.

---

## Ciclo de Vida de um Bot

### 1. Inicialização (`__init__`)

```python
def __init__(self, memory_file="bot_memory.json"):
    # 1. Define arquivo de memória
    self.memory_file = get_memory_path(memory_file)
    
    # 2. Inicializa valores padrão
    self.bluff_probability = 0.15
    self.total_rounds = 0
    self.wins = 0
    
    # 3. Carrega memória anterior
    self.load_memory()
```

**Ordem de execução:**
1. Define caminho do arquivo de memória
2. Inicializa todos os atributos com valores padrão
3. Carrega memória anterior (se existir) e sobrescreve valores padrão

### 2. Início do Jogo (`receive_game_start_message`)

```python
def receive_game_start_message(self, game_info):
    # Encontra nosso stack inicial
    seats = game_info.get('seats', [])
    for player in seats:
        if player.get('uuid') == self.uuid:
            self.initial_stack = player.get('stack', 100)
            break
```

**Quando:** Uma vez, antes do primeiro round.

**Responsabilidade:** Capturar configurações iniciais do jogo (stack inicial, etc.)

### 3. Início de Round (`receive_round_start_message`)

```python
def receive_round_start_message(self, round_count, hole_card, seats):
    # Salva memória periodicamente (a cada 5 rounds)
    if round_count % 5 == 0:
        self.save_memory()
    
    # Armazena cartas no registry para exibição
    if hole_card and hasattr(self, 'uuid') and self.uuid:
        from .cards_registry import store_player_cards
        hole_cards = normalize_hole_cards(hole_card)
        if hole_cards:
            store_player_cards(self.uuid, hole_cards)
```

**Quando:** No início de cada round.

**Responsabilidade:**
- Preparar para novo round
- Salvar memória periodicamente
- Registrar cartas para exibição (web)

### 4. Durante o Round (Múltiplas Chamadas)

#### 4.1. Declaração de Ação (`declare_action`)

```python
def declare_action(self, valid_actions, hole_card, round_state):
    # 1. Avalia situação atual
    hand_strength = self._evaluate_hand_strength(hole_card, round_state)
    
    # 2. Decide se deve blefar
    should_bluff = self._should_bluff()
    
    # 3. Executa ação
    if should_bluff:
        return self._bluff_action(valid_actions, round_state)
    else:
        return self._normal_action(valid_actions, hand_strength, round_state)
```

**Quando:** Toda vez que é a vez do bot jogar.

**Fluxo típico:**
1. Atualiza informações internas (stack, contexto)
2. Avalia força da mão
3. Decide estratégia (blefe ou jogo normal)
4. Retorna ação e valor

#### 4.2. Atualização de Estado (`receive_game_update_message`)

```python
def receive_game_update_message(self, action, round_state):
    # Analisa ações dos oponentes
    player_uuid = action.get('uuid')
    if player_uuid != self.uuid:
        # Registra ação do oponente
        # Atualiza padrões do oponente
        pass
```

**Quando:** Após cada ação de qualquer jogador.

**Responsabilidade:** Aprender padrões dos oponentes em tempo real.

#### 4.3. Mudança de Street (`receive_street_start_message`)

```python
def receive_street_start_message(self, street, round_state):
    # Atualiza street atual
    self.current_street = street
```

**Quando:** Quando uma nova street começa (flop, turn, river).

**Responsabilidade:** Atualizar estado interno para nova fase do round.

### 5. Fim de Round (`receive_round_result_message`)

```python
def receive_round_result_message(self, winners, hand_info, round_state):
    # 1. Atualiza estatísticas
    self.total_rounds += 1
    won = any(w['uuid'] == self.uuid for w in winners)
    if won:
        self.wins += 1
    
    # 2. Registra resultado no histórico
    self.round_results.append({
        'won': won,
        'round': self.total_rounds,
        'stack': self.current_stack
    })
    
    # 3. Aprende e ajusta estratégia
    if len(self.round_results) >= 5:
        self._adapt_strategy()
    
    # 4. Salva memória
    self.save_memory()
```

**Quando:** No final de cada round, após determinar o vencedor.

**Responsabilidade:**
1. Atualizar estatísticas (rodadas, vitórias, stack)
2. Registrar resultado no histórico
3. Executar lógica de aprendizado
4. Salvar memória atualizada

---

## Sistema de Aprendizado

### Tipos de Aprendizado

#### 1. Aprendizado Conservador (TightPlayer)

**Características:**
- Ajustes lentos e cuidadosos
- Só ajusta quando situação está muito ruim
- Mantém histórico curto (10 rodadas)

**Exemplo:**
```python
# Só ajusta quando win rate < 30% OU 3+ perdas seguidas
if win_rate < 0.30:
    self.tightness_threshold = min(35, self.tightness_threshold + 5)

if self.consecutive_losses >= 3:
    self.bluff_probability = max(0.02, self.bluff_probability * 0.7)
```

#### 2. Aprendizado Agressivo (AggressivePlayer)

**Características:**
- Ajustes rápidos baseados em performance recente
- Mantém histórico médio (20 rodadas)
- Ajusta múltiplos parâmetros simultaneamente

**Exemplo:**
```python
# Ajusta agressão e blefe baseado em win rate recente
if win_rate > 0.6:
    self.aggression_level = min(0.90, self.aggression_level + 0.10)
    self.bluff_probability = min(0.45, self.bluff_probability * 1.1)
elif win_rate < 0.3:
    self.aggression_level = max(0.30, self.aggression_level - 0.15)
    self.bluff_probability = max(0.20, self.bluff_probability * 0.9)
```

#### 3. Aprendizado Avançado (SmartPlayer)

**Características:**
- Análise multi-dimensional
- Mantém histórico longo (50 rodadas)
- Rastreia múltiplas métricas (street, pot size, blefe)

**Exemplo:**
```python
# Ajusta baseado em múltiplos fatores
# 1. Sucesso de blefes
if bluff_success_rate > 0.6:
    self.base_bluff_probability = min(0.25, self.base_bluff_probability * 1.1)

# 2. Performance por street
for street, perf in self.street_performance.items():
    if perf['total'] > 5:
        win_rate = perf['wins'] / perf['total']
        if win_rate < 0.2:
            # Ajusta estratégia para essa street
            pass

# 3. Estratégia por tamanho de pot
# (similar ao acima)
```

#### 4. Aprendizado Adaptativo (LearningPlayer)

**Características:**
- Rastreia padrões dos oponentes
- Usa learning rate para suavizar atualizações
- Adapta estratégia baseado em comportamento dos oponentes

**Exemplo:**
```python
# Atualiza padrões de oponente com learning rate
old_aggression = self.opponent_history[uuid]['patterns']['aggression']
new_aggression = raise_count / total_actions
self.opponent_history[uuid]['patterns']['aggression'] = \
    old_aggression * (1 - self.learning_rate) + new_aggression * self.learning_rate

# Ajusta estratégia baseado nos oponentes
avg_opponent_aggression = self._get_avg_opponent_aggression(active_opponents)
if avg_opponent_aggression > 0.7:
    base_probability *= 0.7  # Reduz blefe contra oponentes agressivos
```

### Algoritmos de Aprendizado

#### Epsilon-Greedy (AdaptivePlayer)

```python
def declare_action(self, valid_actions, hole_card, round_state):
    # Exploração: escolhe aleatoriamente (15% das vezes)
    if random.random() < self.epsilon:
        return self._explore_action(valid_actions)
    
    # Exploração: usa análise (85% das vezes)
    return self._normal_action(valid_actions, hand_strength, round_state)
```

#### Ajuste Dinâmico de Probabilidade

```python
# Ajusta blefe baseado na performance
if self.initial_stack > 0:
    performance_ratio = self.current_stack / self.initial_stack
    
    if performance_ratio > 1.2:
        self.current_bluff_probability = self.base_bluff_probability * 1.5
    elif performance_ratio < 0.8:
        self.current_bluff_probability = self.base_bluff_probability * 0.5
```

#### Normalização de Probabilidades

```python
# Normaliza probabilidades para soma = 1
total = sum(self.action_probabilities.values())
for action in self.action_probabilities:
    self.action_probabilities[action] /= total
```

---

## Componentes Compartilhados

### 1. `hand_utils.py`

Fornece funções utilitárias para avaliação de mãos:

- `evaluate_hand_strength(hole_card, community_cards)`: Avalia força básica da mão
- `get_rank_value(rank)`: Converte rank da carta para valor numérico
- `normalize_hole_cards(hole_card)`: Padroniza formato das cartas
- `get_community_cards(round_state)`: Extrai cartas comunitárias

### 2. `constants.py`

Define constantes compartilhadas:

- Probabilidades de blefe padrão
- Thresholds de força de mão
- Níveis de agressão
- Tamanhos de pot
- Taxas de aprendizado

### 3. `error_handling.py`

Fornece tratamento seguro de erros:

- `safe_memory_save(memory_file, memory_data)`: Salva memória com tratamento de erros
- `safe_memory_load(memory_file, default_data)`: Carrega memória com tratamento de erros

### 4. `memory_utils.py`

Utilitários para gerenciamento de memória:

- `get_memory_path(filename)`: Retorna caminho completo para arquivo de memória

---

## Resumo do Fluxo de Decisão

Para entender como um bot decide sua ação, siga este fluxo:

1. **Recebe `declare_action`** com estado atual
2. **Atualiza informações internas** (stack, contexto)
3. **Avalia força da mão** usando `evaluate_hand_strength()`
4. **Analisa contexto** (pot size, jogadores ativos, street)
5. **Decide se deve blefar** baseado em probabilidade
6. **Se blefar:**
   - Analisa contexto da mesa
   - Escolhe entre CALL ou RAISE
   - Retorna ação
7. **Se não blefar:**
   - Compara força da mão com threshold
   - Escolhe FOLD, CALL ou RAISE
   - Retorna ação
8. **Após o round:**
   - Recebe resultado em `receive_round_result_message`
   - Atualiza estatísticas
   - Aprende com resultado
   - Ajusta estratégia
   - Salva memória

---

## Considerações Finais

### Persistência entre Partidas

- Memórias são carregadas no `__init__()` de cada bot
- Memórias são salvas periodicamente e ao fim de cada round
- Bots mantêm aprendizado entre partidas
- Bots evoluem com o tempo

### Thread Safety

- Cada bot é uma instância separada
- Memórias são salvas de forma atômica (escrita completa ou falha)
- Não há compartilhamento de estado entre bots (exceto via `cards_registry`)

### Performance

- Salvamento de memória é feito assincronamente (não bloqueia jogo)
- Históricos são limitados (10-50 rodadas) para evitar crescimento infinito
- Operações de arquivo falham silenciosamente para não quebrar o jogo

### Debugging

- Use `POKER_PLAYER_LOG_LEVEL=DEBUG` para ver logs detalhados
- Logs aparecem no console/terminal
- Memórias podem ser inspecionadas diretamente nos arquivos JSON

