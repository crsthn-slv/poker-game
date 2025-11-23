# Como Criar um Novo Bot

Guia rápido para criar um novo bot de poker usando o sistema unificado de memória.

## Template Mínimo

```python
from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.hand_utils import evaluate_hand_strength
from utils.action_analyzer import analyze_current_round_actions, analyze_possible_bluff

class MeuBot(BasePokerPlayer):
    """Descrição do bot."""
    
    def __init__(self, memory_file="meu_bot_memory.json"):
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.20,
            default_aggression=0.55,
            default_tightness=25
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.initial_stack = None
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        # NOVO: Analisa ações do round atual
        current_actions = analyze_current_round_actions(round_state, self.uuid) if hasattr(self, 'uuid') and self.uuid else None
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Avalia força da mão
        hand_strength = evaluate_hand_strength(
            hole_card, 
            round_state.get('community_card', [])
        )
        
        # NOVO: Analisa possível blefe dos oponentes
        bluff_analysis = None
        if hasattr(self, 'uuid') and self.uuid:
            bluff_analysis = analyze_possible_bluff(
                round_state, self.uuid, hand_strength, self.memory_manager
            )
        
        # Decide ação
        should_bluff = random.random() < self.bluff_probability
        
        # NOVO: Ajusta blefe baseado em ações atuais
        if current_actions and current_actions['has_raises'] and current_actions['raise_count'] >= 2:
            should_bluff = False  # Não blefa se muito agressão
        
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state)
        else:
            action, amount = self._normal_action(valid_actions, hand_strength, round_state, current_actions, bluff_analysis)
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
    def _bluff_action(self, valid_actions, round_state):
        """Blefe: CALL ou RAISE."""
        if valid_actions[2]['amount']['min'] != -1 and random.random() < 0.5:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, min(max_amount, min_amount + 20))
            return raise_action['action'], amount
        else:
            return valid_actions[1]['action'], valid_actions[1]['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state, 
                       current_actions=None, bluff_analysis=None):
        """Ação baseada na força da mão, ações atuais e possível blefe."""
        adjusted_threshold = self.tightness_threshold
        
        # NOVO: Ajusta threshold baseado em ações do round atual
        if current_actions:
            if current_actions['has_raises']:
                adjusted_threshold += 5 + (current_actions['raise_count'] * 2)
            elif current_actions['last_action'] == 'raise':
                adjusted_threshold += 3
        
        # NOVO: Campo passivo reduz threshold e aumenta agressão
        adjusted_aggression = self.aggression_level
        if current_actions and current_actions.get('is_passive', False):
            passive_score = current_actions.get('passive_opportunity_score', 0.0)
            # Reduz threshold quando campo está passivo (joga mais mãos)
            adjusted_threshold = max(20, adjusted_threshold - int(passive_score * 5))
            # Aumenta agressão temporariamente
            adjusted_aggression = min(0.80, adjusted_aggression + (passive_score * 0.2))
        
        # NOVO: Se análise indica possível blefe e deve pagar, considera call
        # Ajuste o threshold (25) conforme a personalidade do seu bot
        # Conservadores: 28-32, Agressivos: 22-24, Inteligentes: 27-28, Balanceados: 25-26
        if bluff_analysis and bluff_analysis['should_call_bluff']:
            if hand_strength >= 25:  # Ajuste conforme personalidade do bot
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # Mão muito forte: raise
        if hand_strength >= 50:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                return raise_action['action'], raise_action['amount']['min']
        
        # NOVO: Com campo passivo, até mãos médias podem fazer raise
        if current_actions and current_actions.get('is_passive', False):
            passive_score = current_actions.get('passive_opportunity_score', 0.0)
            # Ajuste os valores conforme personalidade:
            # Agressivos: hand_strength >= 20-25, passive_score > 0.4
            # Moderados: hand_strength >= 30-35, passive_score > 0.5
            # Conservadores: hand_strength >= 45-50, passive_score > 0.6-0.7
            if hand_strength >= 30 and passive_score > 0.5:
                raise_action = valid_actions[2]
                if raise_action['amount']['min'] != -1:
                    return raise_action['action'], raise_action['amount']['min']
        
        # Mão forte: call (threshold ajustado)
        if hand_strength >= adjusted_threshold:
            return valid_actions[1]['action'], valid_actions[1]['amount']
        
        # Mão fraca: fold
        return valid_actions[0]['action'], valid_actions[0]['amount']
    
    def receive_game_start_message(self, game_info):
        seats = game_info.get('seats', [])
        if isinstance(seats, list):
            for player in seats:
                if player.get('uuid') == self.uuid:
                    self.initial_stack = player.get('stack', 100)
                    if not hasattr(self.memory_manager, 'initial_stack'):
                        self.memory_manager.initial_stack = self.initial_stack
                    break
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        if round_count % 5 == 0:
            self.memory_manager.save()
    
    def receive_street_start_message(self, street, round_state):
        pass
    
    def receive_game_update_message(self, action, round_state):
        player_uuid = action.get('uuid') or action.get('player_uuid')
        if player_uuid and player_uuid != self.uuid:
            self.memory_manager.record_opponent_action(player_uuid, action, round_state)
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        # Processa resultado
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprendizado: ajusta parâmetros baseado em win rate
        if self.total_rounds >= 10:
            win_rate = self.wins / self.total_rounds
            if win_rate < 0.3:
                self.memory['tightness_threshold'] = min(35, self.memory['tightness_threshold'] + 2)
            elif win_rate > 0.6:
                self.memory['tightness_threshold'] = max(20, self.memory['tightness_threshold'] - 1)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Salva memória
        self.memory_manager.save()
```

## Estrutura de Memória

O `UnifiedMemoryManager` gerencia automaticamente:

```python
{
    'bluff_probability': float,      # 0.0-1.0
    'aggression_level': float,        # 0.0-1.0
    'tightness_threshold': int,       # 0-100
    'total_rounds': int,
    'wins': int,
    'opponents': {},                  # Histórico de oponentes
    'round_history': []                # Últimos 20 rounds
}
```

**Campos personalizados:** Adicione `self.memory['meu_campo'] = valor` e será salvo automaticamente.

## Aprendizado Avançado

### Com Histórico Recente

```python
def receive_round_result_message(self, winners, hand_info, round_state):
    # ... processa resultado ...
    
    round_history = self.memory.get('round_history', [])
    if len(round_history) >= 5:
        recent_rounds = round_history[-10:]
        win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
        
        if win_rate < 0.3:
            self.memory['tightness_threshold'] = min(35, self.memory['tightness_threshold'] + 3)
            self.memory['bluff_probability'] = max(0.05, self.memory['bluff_probability'] * 0.9)
        elif win_rate > 0.6:
            self.memory['tightness_threshold'] = max(20, self.memory['tightness_threshold'] - 2)
            self.memory['bluff_probability'] = min(0.35, self.memory['bluff_probability'] * 1.1)
    
    # ... atualiza valores locais e salva ...
```

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

## Checklist

- [ ] Criar arquivo `players/meu_bot.py`
- [ ] Herdar de `BasePokerPlayer`
- [ ] Usar `UnifiedMemoryManager` no `__init__`
- [ ] Importar `analyze_current_round_actions` e `analyze_possible_bluff`
- [ ] Implementar `declare_action()` com:
  - [ ] Análise de ações do round atual
  - [ ] Análise de possível blefe dos oponentes
  - [ ] Ajuste de threshold baseado em ações
  - [ ] Lógica de pagar blefe
- [ ] Implementar `_normal_action()` com parâmetros `current_actions` e `bluff_analysis`
- [ ] Implementar detecção de campo passivo (opcional, mas recomendado)
- [ ] Implementar métodos `receive_*` obrigatórios
- [ ] Adicionar aprendizado em `receive_round_result_message()` (opcional)
- [ ] Escolher threshold apropriado para pagar blefe (conforme personalidade)
- [ ] Escolher valores apropriados para reagir a campo passivo (conforme personalidade)
- [ ] Registrar em `web/server.py` (se usar modo web)

## Recursos

- **Exemplos completos:** `players/tight_player.py`, `players/smart_player.py`, `players/balanced_player.py`
- **Sistema de memória:** `utils/memory_manager.py`
- **Análise de ações:** `utils/action_analyzer.py`
- **Documentação completa:** `docs/FUNCIONAMENTO_BOTS.md`

## Funcionalidades Disponíveis

### Análise de Ações em Tempo Real

```python
from utils.action_analyzer import analyze_current_round_actions

current_actions = analyze_current_round_actions(round_state, self.uuid)
# Retorna:
# - has_raises: bool (se alguém fez raise)
# - raise_count: int (quantos raises)
# - call_count: int (quantos calls)
# - last_action: str ('raise', 'call', 'fold' ou None)
# - total_aggression: float (0.0 a 1.0)
# - is_passive: bool (se campo está passivo - muitos calls, nenhum raise)
# - passive_opportunity_score: float (0.0 a 1.0, oportunidade de agressão)
```

#### Usando Detecção de Campo Passivo

```python
# Detecta quando campo está passivo e aumenta agressão
if current_actions and current_actions.get('is_passive', False):
    passive_score = current_actions.get('passive_opportunity_score', 0.0)
    
    # Reduz threshold (joga mais mãos)
    adjusted_threshold = max(20, adjusted_threshold - int(passive_score * 5))
    
    # Aumenta agressão temporariamente
    adjusted_aggression = min(0.80, adjusted_aggression + (passive_score * 0.2))
    
    # Faz raise com mãos médias quando oportunidade é alta
    if hand_strength >= 30 and passive_score > 0.5:
        raise_action = valid_actions[2]
        if raise_action['amount']['min'] != -1:
            return raise_action['action'], raise_action['amount']['min']
```

#### Valores Recomendados por Personalidade

**Bots Agressivos** (AggressivePlayer, OpportunisticPlayer, SteadyAggressivePlayer):
- Reduzir threshold: `passive_score * 5-6`
- Aumentar agressão: `passive_score * 0.2-0.3`
- Raise com mão: `hand_strength >= 20-25` e `passive_score > 0.4-0.5`

**Bots Moderados** (SmartPlayer, BalancedPlayer, ModeratePlayer, LearningPlayer):
- Reduzir threshold: `passive_score * 4-5`
- Aumentar agressão: `passive_score * 0.15-0.2`
- Raise com mão: `hand_strength >= 30-35` e `passive_score > 0.4-0.5`

**Bots Conservadores** (TightPlayer, CautiousPlayer, PatientPlayer, CalmPlayer):
- Reduzir threshold: `passive_score * 2-3`
- Aumentar agressão: `passive_score * 0.1-0.15` (ou não aumentar)
- Raise com mão: `hand_strength >= 45-50` e `passive_score > 0.6-0.7`

### Análise de Possível Blefe

```python
from utils.action_analyzer import analyze_possible_bluff

bluff_analysis = analyze_possible_bluff(
    round_state, self.uuid, hand_strength, self.memory_manager
)
# Retorna: possible_bluff_probability, should_call_bluff, bluff_confidence, analysis_factors
```

### Avaliação de Força da Mão

```python
from utils.hand_utils import evaluate_hand_strength

hand_strength = evaluate_hand_strength(hole_card, community_cards)
# Retorna: int (0-100, onde 100 é a melhor mão possível)
```
