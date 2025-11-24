# Como Criar um Novo Bot

Guia rápido para criar um novo bot de poker usando a **arquitetura refatorada baseada em configuração**.

## 🎯 Nova Arquitetura (Simplificada)

Com a refatoração, criar um novo bot é **muito mais simples**: apenas **15 linhas de código**!

A lógica está toda em `PokerBotBase`, você só precisa definir a **configuração**.

## Template Mínimo

Crie um arquivo `players/meu_novo_bot_player.py`:

```python
"""
Meu novo bot - apenas configuração, ZERO lógica.
Toda lógica está em PokerBotBase.
"""
from players.base.poker_bot_base import PokerBotBase
from players.base.bot_config import BotConfig


def _create_config(memory_file: str = "meu_novo_bot_memory.json") -> BotConfig:
    """Cria configuração para meu novo bot"""
    return BotConfig(
        # Identificação do bot
        name="MeuNovoBot",
        memory_file=memory_file,
        
        # Parâmetros de personalidade base
        default_bluff=0.20,
        default_aggression=0.55,
        default_tightness=25,
        
        # Thresholds de decisão
        fold_threshold_base=18,
        raise_threshold=25,
        strong_hand_threshold=30,
        
        # Ajustes de valor de raise
        raise_multiplier_min=15,
        raise_multiplier_max=20,
        
        # Comportamento de blefe
        bluff_call_ratio=0.50,
        bluff_raise_prob_few_players=0.50,
        bluff_raise_prob_many_players=0.50,
        
        # Reação a ações dos oponentes
        raise_count_sensitivity=2.0,
        raise_threshold_adjustment_base=5,
        raise_threshold_adjustment_per_raise=2,
        
        # Detecção e pagamento de blefe
        bluff_detection_threshold=25,
        
        # Comportamento em campo passivo
        passive_aggression_boost=0.15,
        passive_threshold_reduction_factor=4.0,
        passive_threshold_min=20,
        passive_raise_threshold=25,
        passive_raise_score_threshold=0.4,
        
        # Sistema de aprendizado
        learning_speed=0.001,
        win_rate_threshold_high=0.60,
        win_rate_threshold_low=0.30,
        rounds_before_learning=10,
    )


class MeuNovoBotPlayer(PokerBotBase):
    """Descrição do bot."""
    
    def __init__(self, memory_file="meu_novo_bot_memory.json"):
        config = _create_config(memory_file)
        super().__init__(config)
```

**Pronto!** Seu bot está funcionando. Apenas **15 linhas de código**!

## O que o PokerBotBase já faz automaticamente

O `PokerBotBase` já implementa **TUDO** para você:

✅ **Análise de ações do round atual** (`analyze_current_round_actions`)
✅ **Análise de possível blefe** (`analyze_possible_bluff`)
✅ **Decisão de blefe** baseada em configuração
✅ **Ação normal** com todos os ajustes contextuais
✅ **Detecção de campo passivo** e aumento de agressão
✅ **Pagamento de blefes** baseado em threshold configurado
✅ **Todos os métodos `receive_*`** (game_start, round_start, etc.)
✅ **Sistema de aprendizado** baseado em configuração
✅ **Gerenciamento de memória** completo

**Você não precisa implementar nada disso!** Apenas configure os parâmetros.

## Parâmetros de Configuração

O `BotConfig` define todos os parâmetros do bot. Principais campos:

### Parâmetros de Personalidade
- `default_bluff`: Probabilidade inicial de blefe (0.0-1.0)
- `default_aggression`: Nível inicial de agressão (0.0-1.0)
- `default_tightness`: Threshold inicial de seletividade (0-100)

### Thresholds de Decisão
- `fold_threshold_base`: Threshold base para fold
- `raise_threshold`: Threshold mínimo para considerar raise
- `strong_hand_threshold`: Threshold para mão muito forte

### Comportamento de Blefe
- `bluff_call_ratio`: Probabilidade de fazer call vs raise no blefe
- `bluff_raise_prob_few_players`: Prob de raise no blefe com poucos jogadores
- `bluff_raise_prob_many_players`: Prob de raise no blefe com muitos jogadores

### Ajustes Contextuais
- `passive_aggression_boost`: Quanto aumenta agressão em campo passivo
- `raise_count_sensitivity`: Sensibilidade a raises (multiplicador)
- `bluff_detection_threshold`: Threshold para pagar blefe detectado

### Aprendizado
- `learning_speed`: Velocidade de aprendizado (0.001 = lento, 0.01 = rápido)
- `win_rate_threshold_high`: Win rate alto para aumentar agressão
- `win_rate_threshold_low`: Win rate baixo para reduzir agressão
- `rounds_before_learning`: Rodadas mínimas antes de aprender

**Veja `players/base/bot_config.py` para todos os campos disponíveis.**

## Estrutura de Memória

O `UnifiedMemoryManager` (gerenciado automaticamente pelo `PokerBotBase`) gerencia:

```python
{
    'bluff_probability': float,      # 0.0-1.0 (atualizado pelo aprendizado)
    'aggression_level': float,        # 0.0-1.0 (atualizado pelo aprendizado)
    'tightness_threshold': int,       # 0-100 (atualizado pelo aprendizado)
    'total_rounds': int,
    'wins': int,
    'opponents': {},                  # Histórico de oponentes
    'round_history': []                # Últimos rounds
}
```

**Campos personalizados:** Se precisar, você pode adicionar campos customizados no preset, mas a maioria dos casos não precisa.

## Aprendizado Automático

O `PokerBotBase` já implementa aprendizado automático baseado na configuração:

- **Ajusta agressão e blefe** quando win rate > `win_rate_threshold_high`
- **Reduz agressão e aumenta threshold** quando win rate < `win_rate_threshold_low`
- **Velocidade de aprendizado** controlada por `learning_speed`
- **Aprende apenas após** `rounds_before_learning` rodadas

**Você não precisa implementar aprendizado manualmente!** Apenas configure os parâmetros no preset.

### Personalizando Aprendizado

Se precisar de aprendizado customizado, você pode sobrescrever `receive_round_result_message()`:

```python
class MeuNovoBotPlayer(PokerBotBase):
    def __init__(self, memory_file="meu_novo_bot_memory.json"):
        config = _create_config(memory_file)
        super().__init__(config)
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        # Chama aprendizado padrão
        super().receive_round_result_message(winners, hand_info, round_state)
        
        # Adiciona lógica customizada se necessário
        # (geralmente não é necessário)
        pass
```

**Nota:** Na maioria dos casos, o aprendizado padrão é suficiente. Apenas sobrescreva se precisar de comportamento muito específico.

## Registrando o Bot

### Modo Web

Adicione em `web/server.py`:

```python
from players.meu_bot import MeuBot

AVAILABLE_BOTS = [
    # ... outros bots ...
    MeuBot,
]
```

## Funcionalidades Avançadas

### Reação em Tempo Real às Ações

Todos os bots devem analisar ações do round atual e possível blefe:

```python
# 1. Analisa ações do round atual
current_actions = analyze_current_round_actions(round_state, self.uuid)

# 2. Analisa possível blefe dos oponentes
bluff_analysis = analyze_possible_bluff(
    round_state, self.uuid, hand_strength, self.memory_manager
)

# 3. Usa nas decisões
# - Ajusta threshold baseado em current_actions
# - Paga blefe baseado em bluff_analysis
```

### Escolhendo o Threshold para Pagar Blefe

O threshold deve refletir a personalidade do bot:

- **Conservadores** (Tight, Cautious): 28-32 (mais seletivos)
- **Agressivos** (Aggressive, Opportunistic): 22-24 (pagam mais facilmente)
- **Inteligentes** (Smart, Learning): 27-28 (análise balanceada)
- **Balanceados** (Balanced, Moderate): 25-26 (valores médios)

## Checklist Simplificado

Com a nova arquitetura, criar um bot é muito mais simples:

- [ ] Criar arquivo `players/meu_novo_bot_player.py`
- [ ] Criar função `_create_config()` com todos os parâmetros de `BotConfig`
- [ ] Criar classe que herda de `PokerBotBase` (não de `BasePokerPlayer`)
- [ ] Implementar apenas `__init__()` que chama `_create_config()` e `super().__init__(config)`
- [ ] Registrar em `web/server.py` (se usar modo web)

**Isso é tudo!** O `PokerBotBase` já implementa:
- ✅ `declare_action()` com toda a lógica
- ✅ Análise de ações do round atual
- ✅ Análise de possível blefe
- ✅ Detecção de campo passivo
- ✅ Todos os métodos `receive_*`
- ✅ Sistema de aprendizado
- ✅ Gerenciamento de memória

## Escolhendo Valores de Configuração

### Por Personalidade

**Bots Agressivos:**
- `default_bluff`: 0.18-0.25
- `default_aggression`: 0.58-0.65
- `default_tightness`: 25-26
- `bluff_detection_threshold`: 22-24
- `passive_aggression_boost`: 0.25-0.35
- `passive_raise_threshold`: 20-25

**Bots Conservadores:**
- `default_bluff`: 0.12-0.15
- `default_aggression`: 0.48-0.54
- `default_tightness`: 29-35
- `bluff_detection_threshold`: 28-32
- `passive_aggression_boost`: 0.08-0.15
- `passive_raise_threshold`: 45-50

**Bots Balanceados:**
- `default_bluff`: 0.15-0.17
- `default_aggression`: 0.52-0.57
- `default_tightness`: 27-28
- `bluff_detection_threshold`: 25-28
- `passive_aggression_boost`: 0.15-0.20
- `passive_raise_threshold`: 28-35

**Veja exemplos em `players/aggressive_player.py`, `players/balanced_player.py`, etc. para referência.**

## Recursos

- **Exemplos de bots:** `players/aggressive_player.py`, `players/balanced_player.py`, `players/cautious_player.py` (todos ~140-170 linhas com configuração completa)
- **Classe base:** `players/base/poker_bot_base.py` (toda a lógica)
- **Configuração:** `players/base/bot_config.py` (todos os parâmetros)
- **Sistema de memória:** `utils/memory_manager.py` (gerenciado automaticamente)
- **Análise de ações:** `utils/action_analyzer.py` (usado automaticamente)
- **Documentação completa:** 
  - `docs/FUNCIONAMENTO_BOTS.md` - Funcionamento detalhado
  - `docs/ARQUITETURA_BOTS.md` - Arquitetura refatorada

## Funcionalidades Automáticas

Todas essas funcionalidades são **implementadas automaticamente** pelo `PokerBotBase`:

✅ **Análise de ações em tempo real** - Usa `analyze_current_round_actions()` automaticamente
✅ **Detecção de campo passivo** - Ajusta comportamento automaticamente baseado em `passive_aggression_boost`
✅ **Análise de possível blefe** - Usa `analyze_possible_bluff()` automaticamente
✅ **Pagamento de blefes** - Baseado em `bluff_detection_threshold` configurado
✅ **Avaliação de força da mão** - Usa `evaluate_hand_strength()` automaticamente
✅ **Ajuste de threshold** - Baseado em `raise_count_sensitivity` e `raise_threshold_adjustment_*`
✅ **Sistema de aprendizado** - Baseado em `learning_speed` e `win_rate_threshold_*`

**Você não precisa implementar nada disso!** Apenas configure os parâmetros no preset.

### Como Funciona Internamente

O `PokerBotBase.declare_action()` já faz tudo:

1. Analisa ações do round atual
2. Avalia força da mão
3. Analisa possível blefe dos oponentes
4. Ajusta threshold baseado em ações
5. Decide se deve blefar
6. Escolhe ação (fold/call/raise)
7. Registra ação na memória

Tudo baseado na configuração do `BotConfig` que você definiu no preset.

### Personalizando Comportamento

Se precisar de comportamento muito específico, você pode:

1. **Ajustar parâmetros no preset** (recomendado)
2. **Sobrescrever métodos específicos** em seu bot (avançado)

**Exemplo de sobrescrita (geralmente não necessário):**

```python
class MeuNovoBotPlayer(PokerBotBase):
    def _normal_action(self, valid_actions, hand_strength, round_state,
                       current_actions=None, bluff_analysis=None):
        # Chama lógica padrão
        result = super()._normal_action(valid_actions, hand_strength, round_state,
                                        current_actions, bluff_analysis)
        
        # Adiciona lógica customizada se necessário
        # (geralmente não é necessário)
        return result
```

**Nota:** Na maioria dos casos, ajustar os parâmetros do preset é suficiente.
