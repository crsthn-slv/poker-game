# Como Criar um Novo Bot

Guia rápido para criar um novo bot de poker usando o sistema unificado de memória.

## Template Mínimo

```python
from pypokerengine.players import BasePokerPlayer
import random
from .memory_manager import UnifiedMemoryManager
from .hand_utils import evaluate_hand_strength

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
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Avalia força da mão
        hand_strength = evaluate_hand_strength(
            hole_card, 
            round_state.get('community_card', [])
        )
        
        # Decide ação
        should_bluff = random.random() < self.bluff_probability
        
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state)
        else:
            action, amount = self._normal_action(valid_actions, hand_strength, round_state)
        
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
    
    def _normal_action(self, valid_actions, hand_strength, round_state):
        """Ação baseada na força da mão."""
        if hand_strength >= 50:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                return raise_action['action'], raise_action['amount']['min']
        
        if hand_strength >= self.tightness_threshold:
            return valid_actions[1]['action'], valid_actions[1]['amount']
        
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

## Checklist

- [ ] Criar arquivo `players/meu_bot.py`
- [ ] Herdar de `BasePokerPlayer`
- [ ] Usar `UnifiedMemoryManager` no `__init__`
- [ ] Implementar `declare_action()` com lógica de decisão
- [ ] Implementar métodos `receive_*` obrigatórios
- [ ] Adicionar aprendizado em `receive_round_result_message()` (opcional)
- [ ] Registrar em `web/server.py` (se usar modo web)

## Recursos

- **Exemplos completos:** `players/tight_player.py`, `players/smart_player.py`, `players/balanced_player.py`
- **Sistema de memória:** `players/memory_manager.py`
- **Documentação completa:** `docs/FUNCIONAMENTO_BOTS.md`
