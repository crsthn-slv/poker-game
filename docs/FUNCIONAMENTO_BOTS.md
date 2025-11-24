# Funcionamento dos Bots e Sistema de Memória

Esta documentação explica em detalhes como os bots funcionam, suas estruturas, estratégias e como o sistema de memória persistente opera.

## ⚠️ Arquitetura Refatorada

**IMPORTANTE:** Os bots foram refatorados para usar uma arquitetura baseada em configuração que elimina ~85% de código duplicado.

- **Nova arquitetura:** Todos os bots herdam de `PokerBotBase` e usam `BotConfig` para configuração
- **Lógica compartilhada:** Toda a lógica está em `PokerBotBase`, bots concretos são apenas configuração (~15 linhas)
- **Documentação da arquitetura:** Veja `docs/ARQUITETURA_BOTS.md` para detalhes completos
- **Como criar novo bot:** Veja `docs/COMO_CRIAR_NOVO_BOT.md` (agora muito mais simples!)

**Esta documentação explica o funcionamento interno e as funcionalidades disponíveis. Para criar novos bots, veja a documentação de arquitetura.**

## Índice

1. [Estrutura Base dos Bots](#estrutura-base-dos-bots)
2. [Sistema de Memória Persistente](#sistema-de-memória-persistente)
3. [Tipos de Bots e Estratégias](#tipos-de-bots-e-estratégias)
4. [Ciclo de Vida de um Bot](#ciclo-de-vida-de-um-bot)
5. [Sistema de Aprendizado](#sistema-de-aprendizado)
6. [Reação em Tempo Real às Ações dos Oponentes](#reação-em-tempo-real-às-ações-dos-oponentes)
7. [Análise de Blefe em Tempo Real](#análise-de-blefe-em-tempo-real)
8. [Componentes Compartilhados](#componentes-compartilhados)

---

## Estrutura Base dos Bots

### Arquitetura Refatorada

Todos os bots agora usam uma **arquitetura baseada em configuração** que elimina duplicação de código. A estrutura é:

```
BasePokerPlayer (PyPokerEngine)
    └── PokerBotBase (players/base/poker_bot_base.py)
            ├── AggressivePlayer
            ├── BalancedPlayer
            ├── CautiousPlayer
            └── ... (18 bots mais)
```

### Componentes Principais

#### 1. PokerBotBase

Classe base que contém **TODA a lógica compartilhada**. Todos os bots herdam desta classe.

```python
from players.base.poker_bot_base import PokerBotBase
from players.base.bot_config import BotConfig

def _create_config(memory_file: str = "meu_bot_memory.json") -> BotConfig:
    """Cria configuração para meu bot"""
    return BotConfig(
        name="MeuBot",
        memory_file=memory_file,
        default_bluff=0.16,
        # ... todos os parâmetros
    )

class MeuBot(PokerBotBase):
    def __init__(self, memory_file="meu_bot_memory.json"):
        config = _create_config(memory_file)
        super().__init__(config)
```

#### 2. BotConfig

Dataclass que contém toda a configuração de um bot (sem lógica).

#### 3. Função `_create_config()`

Cada bot tem sua própria função `_create_config()` que retorna um `BotConfig` pré-configurado.

**Nota:** Para mais detalhes sobre a arquitetura, veja `docs/ARQUITETURA_BOTS.md`.

### Métodos Implementados Automaticamente

O `PokerBotBase` já implementa **TODOS** os métodos obrigatórios do `BasePokerPlayer`. Você não precisa implementá-los!

#### 1. `declare_action(valid_actions, hole_card, round_state)`

**Implementado por:** `PokerBotBase`

**O que faz automaticamente:**
- Analisa ações do round atual
- Avalia força da mão
- Analisa possível blefe dos oponentes
- Decide se deve blefar (baseado em `config.bluff_probability`)
- Escolhe ação (fold/call/raise) baseado em configuração
- Registra ação na memória

**Você não precisa implementar isso!** Apenas configure os parâmetros no preset.

#### 2. `receive_game_start_message(game_info)`

**Implementado por:** `PokerBotBase`

**O que faz:** Inicializa stack inicial automaticamente.

#### 3. `receive_round_start_message(round_count, hole_card, seats)`

**Implementado por:** `PokerBotBase`

**O que faz:**
- Salva memória periodicamente (a cada 5 rounds)
- Armazena cartas no registry para exibição

#### 4. `receive_street_start_message(street, round_state)`

**Implementado por:** `PokerBotBase`

**O que faz:** Hook vazio (pode ser sobrescrito se necessário).

#### 5. `receive_game_update_message(action, round_state)`

**Implementado por:** `PokerBotBase`

**O que faz:** Registra ações dos oponentes na memória automaticamente.

#### 6. `receive_round_result_message(winners, hand_info, round_state)`

**Implementado por:** `PokerBotBase`

**O que faz:**
- Processa resultado do round
- Atualiza estatísticas
- Executa aprendizado baseado em configuração
- Salva memória

**Nota:** Se precisar de aprendizado customizado, você pode sobrescrever este método, mas geralmente o aprendizado padrão é suficiente.

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
      "bluff_probability": 0.15,
      "aggression_level": 0.52,
      "tightness_threshold": 28,
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

Todos os bots usam a mesma estrutura e lógica (via `PokerBotBase`), mas com **valores de configuração diferentes** definidos em `BotPresets`:

| Bot | bluff_probability | aggression_level | tightness_threshold |
|-----|-------------------|------------------|---------------------|
| TightPlayer | 0.15 | 0.54 | 29 |
| AggressivePlayer | 0.18 | 0.58 | 26 |
| SmartPlayer | 0.16 | 0.56 | 27 |
| LearningPlayer | 0.17 | 0.55 | 28 |
| BalancedPlayer | 0.16 | 0.57 | 28 |
| CautiousPlayer | 0.12 | 0.48 | 29 |

**A diferença está em:**
1. **Valores iniciais** (definidos em `BotPresets`)
2. **Parâmetros de comportamento** (thresholds, multiplicadores, etc.)
3. **Evolução/aprendizado**: cada bot ajusta esses parâmetros de forma diferente baseado em seus resultados

**Importante:** A lógica de decisão é **idêntica** para todos os bots (está em `PokerBotBase`). A personalidade vem apenas da configuração.

### Carregamento de Memória

A memória é carregada automaticamente pelo `PokerBotBase` no `__init__()` usando `UnifiedMemoryManager`:

```python
# Em PokerBotBase.__init__()
self.memory_manager = UnifiedMemoryManager(
    config.memory_file,
    config.default_bluff,
    config.default_aggression,
    config.default_tightness
)
self.memory = self.memory_manager.get_memory()
```

**Para bots concretos:** A configuração é feita através de `BotPresets`, que define os valores padrão:

```python
# Exemplo: AggressivePlayer
class AggressivePlayer(PokerBotBase):
    def __init__(self, memory_file="aggressive_player_memory.json"):
        config = BotPresets.aggressive()  # Define default_bluff=0.18, etc.
        config.memory_file = memory_file
        super().__init__(config)  # PokerBotBase carrega memória automaticamente
```

O `UnifiedMemoryManager`:
1. Carrega memória anterior se existir
2. Se não existir, cria estrutura padrão usando valores do `BotConfig`
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

### Reação em Tempo Real

**NOVO:** Durante `declare_action()`, os bots também:

1. **Analisam ações do round atual** antes de decidir:
```python
def declare_action(self, valid_actions, hole_card, round_state):
    # Analisa ações que já aconteceram nesta street
    current_actions = analyze_current_round_actions(round_state, self.uuid)
    
    # Ajusta comportamento baseado nas ações observadas
    if current_actions['has_raises']:
        # Fica mais conservador
        adjusted_threshold = self.tightness_threshold + 5 + (current_actions['raise_count'] * 2)
        # Evita blefe se muita agressão
        if current_actions['raise_count'] >= 2:
            should_bluff = False
```

Isso permite que os bots **reajam imediatamente** às ações dos oponentes, não apenas aprendam após o round.

### Sistema de Identificação de Oponentes (UUIDs Fixos)

**IMPORTANTE:** O sistema usa UUIDs determinísticos baseados na classe do bot para garantir rastreamento consistente.

**Como Funciona:**
- Cada tipo de bot tem um UUID fixo baseado em sua classe (não no nome)
- O mesmo tipo de bot sempre tem o mesmo UUID, independente do nome ou da partida
- Isso garante que os bots reconheçam corretamente os mesmos oponentes entre partidas
- Todos os 21 bots conhecidos são pré-registrados na memória desde o início

**Vantagens:**
- Rastreamento consistente: um bot sempre reconhece o mesmo oponente
- Memória não cresce infinitamente: máximo de 20 oponentes por bot (21 bots totais - 1 próprio)
- Aprendizado acumulado: parâmetros específicos por oponente são mantidos entre partidas

**Exemplo:**
```python
# TightPlayer sempre tem o mesmo UUID (baseado em sua classe)
# Mesmo que seja chamado de "Tight", "Blaze" ou qualquer outro nome
# Todos os outros bots reconhecem TightPlayer pelo mesmo UUID fixo
```

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
- **Parâmetros específicos** (`bluff_probability`, `aggression_level`, `tightness_threshold`) - aprendidos especificamente para este oponente
- **Ações observadas** durante cada round
- **Cartas** (quando o oponente chega ao showdown)
- **Força da mão** calculada a partir das cartas
- **Resultado** contra esse oponente
- **Análise simples** (ex: "blefe_sucesso" se tinha mão ruim mas ganhou)

Isso permite que o bot aprenda padrões observados sem inferir valores abstratos.

**Nota:** O histórico de oponentes é usado para aprendizado de longo prazo. Para reação em tempo real, os bots usam `analyze_current_round_actions()` que analisa apenas as ações do round atual.

### Parâmetros Específicos por Oponente

**NOVO:** Cada bot mantém parâmetros de estratégia específicos para cada oponente que já enfrentou:

- **`bluff_probability`**: Probabilidade de blefe contra este oponente específico
- **`aggression_level`**: Nível de agressão contra este oponente específico
- **`tightness_threshold`**: Threshold de seletividade contra este oponente específico

**Inicialização:**
- Quando um oponente é registrado pela primeira vez, seus parâmetros específicos são inicializados com os valores globais do bot
- Conforme o bot joga mais rounds contra o oponente, os parâmetros evoluem independentemente

**Uso na Decisão:**
- Durante `declare_action()`, o bot identifica o oponente principal no round
- Usa os parâmetros específicos desse oponente para tomar decisões (com fallback para parâmetros globais se não houver parâmetros específicos)
- Isso permite que o bot adapte sua estratégia para cada oponente individualmente

**Exemplo:**
```python
# Bot pode ter estratégia diferente contra cada oponente
# Parâmetros globais: bluff=0.17, aggression=0.55, tightness=27
# Contra TightPlayer: bluff=0.15, aggression=0.52, tightness=28 (mais conservador)
# Contra AggressivePlayer: bluff=0.20, aggression=0.60, tightness=25 (mais agressivo)
```

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

**Com a nova arquitetura:**

```python
# Em seu bot (ex: AggressivePlayer)
def __init__(self, memory_file="aggressive_player_memory.json"):
    config = BotPresets.aggressive()  # Obtém configuração
    config.memory_file = memory_file
    super().__init__(config)  # PokerBotBase faz todo o resto
```

**O que o `PokerBotBase.__init__()` faz automaticamente:**
1. Armazena configuração em `self.config`
2. Inicializa `UnifiedMemoryManager` com valores do config
3. Carrega memória anterior (se existir) ou cria nova
4. Carrega parâmetros da memória (`bluff_probability`, `aggression_level`, etc.)
5. Inicializa estado interno (`initial_stack`, `current_stack`)

**Você não precisa fazer nada disso!** Apenas chame `super().__init__(config)`.

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

**Implementado por:** `PokerBotBase`

**Fluxo automático:**
1. Identifica oponentes
2. Identifica oponente principal no round (para usar parâmetros específicos)
3. Analisa ações do round atual (`analyze_current_round_actions`)
4. Avalia força da mão (`evaluate_hand_strength`)
5. Analisa possível blefe dos oponentes (`analyze_possible_bluff`)
6. Carrega parâmetros atualizados da memória (específicos do oponente principal ou globais)
7. Decide se deve blefar (baseado em parâmetros específicos ou globais)
8. Escolhe ação (blefe ou normal) baseado em configuração e parâmetros específicos
9. Registra ação na memória
10. Retorna ação e valor

**Você não precisa implementar isso!** Tudo é automático baseado na configuração.

#### 4.2. Atualização de Estado (`receive_game_update_message`)

**Implementado por:** `PokerBotBase`

**O que faz automaticamente:**
- Registra ações dos oponentes na memória
- Atualiza histórico de oponentes

**Você não precisa implementar isso!**

#### 4.3. Mudança de Street (`receive_street_start_message`)

**Implementado por:** `PokerBotBase`

**O que faz:** Hook vazio (pode ser sobrescrito se necessário).

### 5. Fim de Round (`receive_round_result_message`)

**Implementado por:** `PokerBotBase`

**O que faz automaticamente:**
1. Processa resultado usando `memory_manager.process_round_result()`
   - Registra round contra cada oponente
   - **Aprende parâmetros específicos para cada oponente** (após 5+ rounds)
2. Atualiza stack atual
3. Atualiza estatísticas (`total_rounds`, `wins`)
4. Executa aprendizado global baseado em configuração:
   - Ajusta agressão/blefe quando win rate > `win_rate_threshold_high`
   - Reduz agressão/aumenta threshold quando win rate < `win_rate_threshold_low`
   - Velocidade controlada por `learning_speed`
5. Salva memória atualizada (incluindo parâmetros específicos por oponente)

**Você não precisa implementar isso!** O aprendizado padrão é suficiente para a maioria dos casos.

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

#### 5. Aprendizado por Oponente Específico (Todos os Bots)

**NOVO:** Todos os bots agora aprendem parâmetros específicos para cada oponente individualmente.

**Características:**
- Cada bot mantém parâmetros de estratégia (`bluff_probability`, `aggression_level`, `tightness_threshold`) específicos para cada oponente
- Parâmetros evoluem independentemente baseado na performance contra cada oponente
- Aprendizado ativo após 5+ rounds contra um oponente
- Decisões usam parâmetros específicos do oponente principal no round

**Como Funciona:**

1. **Inicialização:**
   - Quando um oponente é registrado pela primeira vez, seus parâmetros específicos são inicializados com os valores globais do bot
   - Todos os 21 bots conhecidos são pré-registrados na memória (mesmo que ainda não tenham jogado juntos)

2. **Aprendizado:**
   ```python
   # Após cada round, o bot aprende com o resultado contra cada oponente
   def learn_from_opponent_result(memory, opp_uuid, i_won, opp_won):
       # Calcula taxa de vitória contra este oponente (últimos 10 rounds)
       recent_rounds = opp['rounds_against'][-10:]
       win_rate = wins_against / len(recent_rounds)
       
       # Se está ganhando bem (>60%): aumenta agressão e blefe
       if win_rate > 0.6:
           opp['aggression_level'] *= 1.01  # +1%
           opp['bluff_probability'] *= 1.01
       
       # Se está perdendo (<40%): reduz agressão, aumenta seletividade
       elif win_rate < 0.4:
           opp['tightness_threshold'] += 1
           opp['aggression_level'] /= 1.01  # -1%
           opp['bluff_probability'] /= 1.01
   ```

3. **Uso na Decisão:**
   ```python
   def declare_action(self, valid_actions, hole_card, round_state):
       # Identifica oponente principal no round
       primary_opponent_uuid = self._get_primary_opponent_uuid(round_state)
       
       # Carrega parâmetros específicos deste oponente (ou globais se não houver)
       self._load_parameters_from_memory(primary_opponent_uuid)
       
       # Usa parâmetros específicos para tomar decisão
       # ...
   ```

**Vantagens:**
- Bots adaptam estratégia para cada oponente individualmente
- Aprendizado mais preciso e contextualizado
- Estratégias diferentes para oponentes diferentes (ex: mais conservador contra Tight, mais agressivo contra Aggressive)

**Exemplo Prático:**
```python
# Bot LearningPlayer tem:
# Parâmetros globais: bluff=0.17, aggression=0.55, tightness=27

# Após jogar 20 rounds contra TightPlayer:
# Parâmetros vs Tight: bluff=0.15, aggression=0.52, tightness=28
# (aprendeu que precisa ser mais conservador contra Tight)

# Após jogar 15 rounds contra AggressivePlayer:
# Parâmetros vs Aggressive: bluff=0.20, aggression=0.60, tightness=25
# (aprendeu que pode ser mais agressivo contra Aggressive)
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

## Reação em Tempo Real às Ações dos Oponentes

### Visão Geral

Todos os bots agora **reagem em tempo real** às ações dos oponentes no mesmo round antes de tomar sua decisão. Isso torna o jogo mais dinâmico e realista, pois os bots ajustam seu comportamento baseado no que está acontecendo na mesa.

### Como Funciona

#### 1. Análise de Ações do Round Atual

Antes de decidir sua ação, cada bot analisa as ações que já aconteceram na street atual usando a função `analyze_current_round_actions()`:

```python
from utils.action_analyzer import analyze_current_round_actions

def declare_action(self, valid_actions, hole_card, round_state):
    # Analisa ações do round atual
    current_actions = analyze_current_round_actions(round_state, self.uuid)
    
    # current_actions contém:
    # - has_raises: bool (se alguém fez raise)
    # - raise_count: int (quantos raises)
    # - call_count: int (quantos calls)
    # - last_action: str ('raise', 'call', 'fold' ou None)
    # - total_aggression: float (0.0 a 1.0)
    # - is_passive: bool (se campo está passivo - muitos calls, nenhum raise)
    # - passive_opportunity_score: float (0.0 a 1.0, oportunidade de agressão)
```

#### 2. Ajuste de Comportamento

Baseado nas ações observadas, os bots ajustam:

**Quando detectam raises:**
- **Aumentam threshold de seletividade** (ficam mais conservadores)
- **Reduzem ou evitam blefe** (especialmente com 2+ raises)
- **Ajustam agressão** (reduzem quando há muita agressão na mesa)

**Exemplo de ajuste:**
```python
# TightPlayer: muito conservador quando há raises
if current_actions['has_raises']:
    adjusted_threshold = self.tightness_threshold + 8 + (current_actions['raise_count'] * 3)
    if current_actions['raise_count'] >= 2:
        should_bluff = False  # Não blefa com 2+ raises

# AggressivePlayer: ainda agressivo, mas um pouco mais seletivo
if current_actions['has_raises']:
    adjusted_threshold = 20 + 3 + (current_actions['raise_count'] * 2)
    # Reduz agressão em 10% se muitos raises
    if current_actions['raise_count'] >= 2:
        adjusted_aggression = self.aggression_level * 0.9
```

#### 3. Análise por Street

A análise funciona em todas as streets (preflop, flop, turn, river):
- Cada street é analisada **independentemente**
- Ações de streets anteriores não afetam a análise da street atual
- O bot reage apenas às ações que aconteceram na street atual

### Comportamento por Tipo de Bot

#### Bots Conservadores (TightPlayer, ConservativeAggressivePlayer, CautiousPlayer)
- **Reação forte a raises**: Aumentam threshold significativamente (+8 a +17 pontos)
- **Evitam blefe completamente** quando há 2+ raises
- **Ficam ainda mais seletivos** em situações agressivas

#### Bots Agressivos (AggressivePlayer, SteadyAggressivePlayer)
- **Reação moderada**: Aumentam threshold, mas mantêm agressão
- **Reduzem agressão em 10%** quando há 2+ raises
- **Ainda tentam raise**, mas com mais seletividade

#### Bots Inteligentes (SmartPlayer, LearningPlayer, AdaptivePlayer)
- **Análise balanceada**: Ajustam threshold baseado em contexto
- **Evitam blefe** quando há muita agressão (2+ raises)
- **Ajustam estratégia** considerando múltiplos fatores

#### Bots Balanceados (BalancedPlayer, ModeratePlayer)
- **Reação equilibrada**: Ajustam threshold moderadamente (+5 a +9 pontos)
- **Evitam blefe** com 2+ raises
- **Mantêm estilo balanceado** mesmo com agressão

### Exemplos Práticos

#### Cenário 1: Sem Raises (Situação Normal)
```
Ações observadas: [CALL, CALL]
- has_raises: False
- raise_count: 0
- Comportamento: Normal, sem ajustes
```

#### Cenário 2: 1 Raise (Situação Moderada)
```
Ações observadas: [RAISE]
- has_raises: True
- raise_count: 1
- Comportamento: 
  - TightPlayer: threshold +11 (35 → 46)
  - AggressivePlayer: threshold +5 (20 → 25)
  - SmartPlayer: threshold +7 (27 → 34)
```

#### Cenário 3: 2+ Raises (Situação Agressiva)
```
Ações observadas: [RAISE, RAISE]
- has_raises: True
- raise_count: 2
- Comportamento:
  - Todos os bots: threshold aumenta significativamente
  - Blefe DESABILITADO (should_bluff = False)
  - Muito mais seletivos
```

### Implementação Técnica

#### Módulo: `utils/action_analyzer.py`

Função principal:
```python
def analyze_current_round_actions(round_state, my_uuid):
    """
    Analisa ações do round atual antes da decisão do bot.
    
    Args:
        round_state: Estado atual do round (do PyPokerEngine)
        my_uuid: UUID do bot que está analisando
    
    Returns:
        dict com informações sobre ações dos oponentes
    """
```

#### Integração nos Bots

Todos os bots seguem este padrão:
```python
def declare_action(self, valid_actions, hole_card, round_state):
    # 1. Analisa ações do round atual
    current_actions = analyze_current_round_actions(round_state, self.uuid)
    
    # 2. Ajusta comportamento baseado nas ações
    if current_actions['has_raises']:
        adjusted_threshold = self.tightness_threshold + 5 + (current_actions['raise_count'] * 2)
        if current_actions['raise_count'] >= 2:
            should_bluff = False
    
    # 3. Usa threshold ajustado na decisão
    # ...
```

### Diferença do Sistema Anterior

**Antes:**
- Bots decidiam apenas baseado em:
  - Força da mão
  - Parâmetros aprendidos (blefe, agressão, threshold)
  - Contexto geral (pot size, número de jogadores)
  - Histórico de rounds anteriores

**Agora:**
- Bots também consideram:
  - **Ações que aconteceram no round atual**
  - **Quantidade de raises observados**
  - **Última ação dos oponentes**
  - **Nível de agressão na mesa**

### Vantagens

1. **Jogo mais dinâmico**: Bots reagem ao que está acontecendo agora
2. **Mais realista**: Comportamento similar a jogadores humanos
3. **Adaptação imediata**: Não precisa esperar fim do round para ajustar
4. **Reação a todos os oponentes**: Analisa ações de bots e jogador humano igualmente

### Detecção de Campo Passivo

**NOVO:** Os bots agora detectam quando o campo está passivo (muitos calls, nenhum raise) e aumentam sua agressão para aproveitar a oportunidade.

#### O que é Campo Passivo?

Campo passivo é detectado quando:
- Há **muitos calls/checks** na street atual
- **Nenhum raise** foi feito
- Isso indica que os oponentes estão jogando de forma conservadora

#### Como Funciona

A função `analyze_current_round_actions()` agora retorna:
- `is_passive`: `True` quando campo está passivo (raises == 0 e calls >= 2)
- `passive_opportunity_score`: Score de 0.0 a 1.0 indicando a oportunidade de agressão
  - Baseado no número de calls (mais calls = mais oportunidade)
  - Aumentado se pot é pequeno (< 100)
  - Aumentado em streets iniciais (preflop/flop)

#### Reação dos Bots a Campo Passivo

**Bots Agressivos** (AggressivePlayer, OpportunisticPlayer, SteadyAggressivePlayer):
- **Reduzem threshold significativamente** (jogam mais mãos)
- **Aumentam agressão temporariamente** (+20% a +30%)
- **Fazem raise com mãos médias** (hand_strength >= 20-25) quando score > 0.4-0.5

**Bots Moderados** (SmartPlayer, BalancedPlayer, ModeratePlayer):
- **Reduzem threshold moderadamente** (jogam mais mãos)
- **Aumentam agressão temporariamente** (+15% a +20%)
- **Fazem raise com mãos médias-fortes** (hand_strength >= 30-35) quando score > 0.4-0.5

**Bots Conservadores** (TightPlayer, CautiousPlayer, PatientPlayer):
- **Reduzem threshold levemente** (jogam um pouco mais mãos)
- **Fazem raise apenas com mãos fortes** (hand_strength >= 45-50) quando score > 0.6-0.7

#### Exemplo de Implementação

```python
def _normal_action(self, valid_actions, hand_strength, round_state, 
                   current_actions=None, bluff_analysis=None):
    adjusted_threshold = self.tightness_threshold
    
    # Campo passivo reduz threshold e aumenta agressão
    adjusted_aggression = self.aggression_level
    if current_actions and current_actions.get('is_passive', False):
        passive_score = current_actions.get('passive_opportunity_score', 0.0)
        # Reduz threshold quando campo está passivo
        adjusted_threshold = max(20, adjusted_threshold - int(passive_score * 5))
        # Aumenta agressão temporariamente
        adjusted_aggression = min(0.80, adjusted_aggression + (passive_score * 0.2))
    
    # Com campo passivo, até mãos médias podem fazer raise
    if current_actions and current_actions.get('is_passive', False):
        passive_score = current_actions.get('passive_opportunity_score', 0.0)
        if hand_strength >= 25 and passive_score > 0.5:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                return raise_action['action'], raise_action['amount']['min']
    
    # ... resto da lógica normal ...
```

#### Cenários Práticos

**Cenário 1: Campo Passivo (apenas calls)**
```
Ações observadas: [CALL, CALL, CALL]
- is_passive: True
- passive_opportunity_score: ~0.8 (alto)
- Comportamento:
  - AggressivePlayer: threshold reduzido, faz raise com mão >= 20
  - SmartPlayer: threshold reduzido, faz raise com mão >= 35
  - TightPlayer: threshold reduzido levemente, faz raise com mão >= 45
```

**Cenário 2: Campo Agressivo (com raises)**
```
Ações observadas: [RAISE, CALL]
- is_passive: False
- passive_opportunity_score: 0.0
- Comportamento: Normal, sem ajustes de campo passivo
```

### Limitações

- Análise é **por street**: Não considera ações de streets anteriores no mesmo round
- Análise é **simples**: Não considera valores dos raises, apenas a presença
- Não diferencia **quem** fez raise: Trata todos os oponentes igualmente
- Campo passivo é detectado apenas quando há **2+ calls e 0 raises**

### Testes

A funcionalidade é testada automaticamente:
- `tests/test_action_reaction.py`: Testes básicos da função
- `tests/test_action_reaction_integration.py`: Testes de integração com bots

Para executar:
```bash
python3 tests/test_action_reaction.py
python3 tests/test_action_reaction_integration.py
```

---

## Análise de Blefe em Tempo Real

### Visão Geral

Todos os bots agora **analisam se os oponentes podem estar blefando** antes de tomar sua decisão. Isso permite que os bots paguem blefes quando têm mãos razoáveis, tornando o jogo mais estratégico e realista.

### Como Funciona

#### 1. Análise de Possível Blefe

Antes de decidir sua ação, cada bot analisa se os oponentes podem estar blefando usando a função `analyze_possible_bluff()`:

```python
from utils.action_analyzer import analyze_possible_bluff

def declare_action(self, valid_actions, hole_card, round_state):
    hand_strength = self._evaluate_hand_strength(hole_card, round_state)
    
    # Analisa possível blefe dos oponentes
    bluff_analysis = analyze_possible_bluff(
        round_state, self.uuid, hand_strength, self.memory_manager
    )
    
    # bluff_analysis contém:
    # - possible_bluff_probability: float (0.0 a 1.0)
    # - should_call_bluff: bool (se deve pagar possível blefe)
    # - bluff_confidence: float (confiança na análise)
    # - analysis_factors: dict (fatores que indicam blefe)
```

#### 2. Fatores que Indicam Possível Blefe

A análise considera múltiplos fatores:

**Múltiplos raises (2+):**
- Alta probabilidade de blefe (+0.4)
- Indica que oponente pode estar tentando intimidar

**Alta agressão (>60% raises vs calls):**
- Probabilidade moderada de blefe (+0.2)
- Muitos raises em relação a calls

**Street inicial (preflop/flop):**
- Probabilidade baixa de blefe (+0.1)
- Mais comum blefar em streets iniciais

**Pot pequeno (<50):**
- Probabilidade baixa de blefe (+0.1)
- Mais fácil blefar em pots pequenos

**Histórico de blefes do oponente:**
- Se oponente tem histórico de blefes bem-sucedidos (+0.1)
- Usa memória para identificar oponentes que blefam frequentemente

#### 3. Decisão de Pagar Blefe

A análise recomenda pagar blefe quando:

```python
# Com mão forte (≥40): sempre paga
if hand_strength >= 40:
    should_call = True

# Com mão média (≥30) + alta probabilidade (>0.5): paga
elif hand_strength >= 30 and bluff_prob > 0.5:
    should_call = True

# Com mão média-fraca (≥25) + muito alta probabilidade (>0.7): paga
elif hand_strength >= 25 and bluff_prob > 0.7:
    should_call = True
```

#### 4. Integração na Lógica do Bot

A análise é usada na lógica de `_normal_action()`:

```python
def _normal_action(self, valid_actions, hand_strength, round_state, 
                   current_actions=None, bluff_analysis=None):
    # Se análise indica possível blefe e deve pagar, considera call
    if bluff_analysis and bluff_analysis['should_call_bluff']:
        if hand_strength >= threshold_personalizado:  # Threshold por personalidade
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    # ... resto da lógica normal ...
```

### Valores por Personalidade

Cada bot tem um **threshold personalizado** para pagar blefe, refletindo sua personalidade:

#### Conservadores (mais seletivos)
- **TightPlayer**: 32
- **CautiousPlayer**: 30
- **PatientPlayer**: 28
- **ConservativeAggressivePlayer**: 29

#### Agressivos (pagam blefe mais facilmente)
- **AggressivePlayer**: 22
- **SteadyAggressivePlayer**: 24
- **OpportunisticPlayer**: 23
- **RandomPlayer**: 24
- **FishPlayer**: 23

#### Inteligentes (análise balanceada)
- **SmartPlayer**: 28
- **LearningPlayer**: 27
- **CalculatedPlayer**: 28
- **ThoughtfulPlayer**: 27
- **CalmPlayer**: 27

#### Balanceados (valores médios)
- **BalancedPlayer**: 26
- **ModeratePlayer**: 26
- **FlexiblePlayer**: 25
- **SteadyPlayer**: 26
- **ObservantPlayer**: 26

#### Outros
- **AdaptivePlayer**: 25
- **HybridPlayer**: 25

### Exemplos Práticos

#### Cenário 1: Múltiplos Raises (Alta Probabilidade de Blefe)
```
Ações: [RAISE, RAISE]
- possible_bluff_probability: ~0.6-0.8
- should_call_bluff: True (se mão ≥ threshold personalizado)
- Comportamento: Bot paga blefe se tiver mão razoável
```

#### Cenário 2: Um Raise (Probabilidade Moderada)
```
Ações: [RAISE]
- possible_bluff_probability: ~0.2-0.4
- should_call_bluff: True (se mão forte ≥40)
- Comportamento: Bot paga apenas com mão forte
```

#### Cenário 3: Sem Raises (Baixa Probabilidade)
```
Ações: [CALL, CALL]
- possible_bluff_probability: ~0.0-0.2
- should_call_bluff: False
- Comportamento: Segue lógica normal
```

### Diferença da Análise de Ações

**Análise de Ações (`analyze_current_round_actions`):**
- Detecta **quantos raises** foram feitos
- Ajusta **threshold de seletividade** do bot
- Reduz **probabilidade de blefe** do próprio bot

**Análise de Blefe (`analyze_possible_bluff`):**
- Detecta se **oponentes podem estar blefando**
- Calcula **probabilidade de blefe** dos oponentes
- Recomenda se deve **pagar o blefe** baseado na mão própria

### Vantagens

1. **Jogo mais estratégico**: Bots pagam blefes quando têm mão razoável
2. **Mais realista**: Comportamento similar a jogadores humanos experientes
3. **Personalidade preservada**: Cada bot tem threshold diferente
4. **Aprende com histórico**: Usa memória de blefes anteriores dos oponentes

### Limitações

- Análise é **probabilística**: Não garante que oponente está blefando
- Não considera **valores dos raises**: Apenas quantidade
- Não diferencia **quem** fez raise: Trata todos igualmente
- Histórico é **limitado**: Apenas últimos 5 rounds por oponente

### Testes

A funcionalidade é testada automaticamente:
- `tests/test_bluff_analysis.py`: Testes básicos da função
- `tests/test_bluff_analysis_complete.py`: Testes completos de integração
- `tests/test_bluff_personality_values.py`: Validação de valores por personalidade

Para executar:
```bash
python3 tests/test_bluff_analysis.py
python3 tests/test_bluff_analysis_complete.py
python3 tests/test_bluff_personality_values.py
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

### 5. `action_analyzer.py`

Utilitário para análise de ações do round atual e possível blefe:

- `analyze_current_round_actions(round_state, my_uuid)`: Analisa ações dos oponentes na street atual
  - Retorna informações sobre raises, calls, e nível de agressão
  - **NOVO:** Detecta campo passivo (`is_passive`, `passive_opportunity_score`)
  - Exclui ações próprias da análise
  - Funciona em todas as streets (preflop, flop, turn, river)

- `analyze_possible_bluff(round_state, my_uuid, my_hand_strength, memory_manager)`: Analisa se oponentes podem estar blefando
  - Calcula probabilidade de blefe baseado em múltiplos fatores
  - Considera histórico de blefes dos oponentes (se disponível)
  - Recomenda se deve pagar blefe baseado na força da mão própria
  - Retorna: probabilidade, recomendação, confiança e fatores analisados

---

## Resumo do Fluxo de Decisão

Para entender como um bot decide sua ação, siga este fluxo:

1. **Recebe `declare_action`** com estado atual
2. **Atualiza informações internas** (stack, contexto)
3. **NOVO: Analisa ações do round atual** usando `analyze_current_round_actions()`
   - Detecta se há raises na street atual
   - Conta quantos raises foram feitos
   - Identifica última ação dos oponentes
4. **Avalia força da mão** usando `evaluate_hand_strength()`
5. **NOVO: Analisa possível blefe dos oponentes** usando `analyze_possible_bluff()`
   - Calcula probabilidade de blefe baseado em múltiplos fatores
   - Determina se deve pagar blefe baseado na mão própria
6. **Ajusta threshold baseado em ações atuais**
   - Se há raises: aumenta threshold (fica mais seletivo)
   - Se 2+ raises: aumenta threshold significativamente
7. **Analisa contexto** (pot size, jogadores ativos, street)
8. **Decide se deve blefar** baseado em probabilidade
   - **NOVO: Se 2+ raises, evita blefe completamente**
9. **Se blefar:**
   - Analisa contexto da mesa
   - Escolhe entre CALL ou RAISE
   - Retorna ação
10. **Se não blefar:**
    - **NOVO: Se análise indica possível blefe e deve pagar:**
      - Compara mão com threshold personalizado
      - Se mão ≥ threshold: faz CALL (paga blefe)
    - Caso contrário:
      - Compara força da mão com **threshold ajustado**
      - Escolhe FOLD, CALL ou RAISE
    - Retorna ação
11. **Após o round:**
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
- **Oponentes rastreados**: Máximo de 20 oponentes por bot (21 bots totais - 1 próprio)
- **Parâmetros específicos por oponente**: Mantidos indefinidamente e evoluem com aprendizado
- **UUIDs fixos**: Garantem rastreamento consistente e evitam duplicação de oponentes
- Operações de arquivo falham silenciosamente para não quebrar o jogo

### Debugging

- Use `POKER_PLAYER_LOG_LEVEL=DEBUG` para ver logs detalhados
- Logs aparecem no console/terminal
- Memórias podem ser inspecionadas diretamente nos arquivos JSON

