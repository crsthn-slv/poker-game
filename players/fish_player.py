from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.hand_utils import evaluate_hand_strength

class FishPlayer(BasePokerPlayer):
    """Jogador 'peixe' que aprende lentamente. Começa sempre fazendo call, mas aprende quando foldar. Usa sistema de memória unificado."""
    
    def __init__(self, memory_file="fish_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.10,  # Baixo blefe (peixe não blefa muito)
            default_aggression=0.30,  # Baixa agressão (peixe é passivo)
            default_tightness=20  # Muito baixo threshold (joga muitas mãos)
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.initial_stack = None
        # Probabilidade de fazer call (começa alta, peixe sempre faz call)
        self.call_probability = self.memory.get('call_probability', 0.95)
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.call_probability = self.memory.get('call_probability', 0.95)
        
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        
        # Peixe: prefere call, mas aprende quando foldar
        if hand_strength < 10 and random.random() > self.call_probability:
            # Mão muito fraca e probabilidade de fold
            action, amount = valid_actions[0]['action'], valid_actions[0]['amount']
        else:
            # Sempre faz call (comportamento de peixe)
            call_action = valid_actions[1]
            action, amount = call_action['action'], call_action['amount']
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            was_bluff = False  # Peixe não blefa
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, was_bluff
            )
        
        return action, amount
    
    def _evaluate_hand_strength(self, hole_card, round_state=None):
        """Avalia força da mão usando utilitário compartilhado."""
        community_cards = round_state.get('community_card', []) if round_state else None
        return evaluate_hand_strength(hole_card, community_cards)
    
    def receive_game_start_message(self, game_info):
        """Inicializa stack."""
        seats = game_info.get('seats', [])
        if isinstance(seats, list):
            for player in seats:
                if player.get('uuid') == self.uuid:
                    self.initial_stack = player.get('stack', 100)
                    if not hasattr(self.memory_manager, 'initial_stack'):
                        self.memory_manager.initial_stack = self.initial_stack
                    break
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        """Salva memória periodicamente."""
        if round_count % 5 == 0:
            self.memory_manager.save()
        # Armazena cartas no registry global para exibição no final do round
        if hole_card and hasattr(self, 'uuid') and self.uuid:
            from utils.cards_registry import store_player_cards
            from utils.hand_utils import normalize_hole_cards
            hole_cards = normalize_hole_cards(hole_card)
            if hole_cards:
                store_player_cards(self.uuid, hole_cards)
    
    def receive_street_start_message(self, street, round_state):
        pass
    
    def receive_game_update_message(self, action, round_state):
        """Registra ações dos oponentes."""
        player_uuid = action.get('uuid') or action.get('player_uuid')
        if player_uuid and player_uuid != self.uuid:
            self.memory_manager.record_opponent_action(player_uuid, action, round_state)
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado lento: peixe aprende quando foldar."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprendizado lento: se está perdendo muito, aprende a foldar mais
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 20:
            recent_rounds = round_history[-20:]
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Se está perdendo muito, reduz probabilidade de call (aprende a foldar)
            if win_rate < 0.25:
                self.memory['call_probability'] = max(0.70, self.memory.get('call_probability', 0.95) - 0.05)
            # Se está ganhando, mantém comportamento de call
            elif win_rate > 0.50:
                self.memory['call_probability'] = min(0.95, self.memory.get('call_probability', 0.95) + 0.01)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.call_probability = self.memory.get('call_probability', 0.95)
        
        # Salva memória após ajustes
        self.memory_manager.save()

