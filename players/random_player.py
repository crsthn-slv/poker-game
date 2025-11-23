from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.action_analyzer import analyze_current_round_actions

class RandomPlayer(BasePokerPlayer):
    """Jogador que faz decisões aleatórias. Blefa 25% das vezes. Aprendizado estocástico básico com memória persistente."""
    
    def __init__(self, memory_file="random_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.16,  # Nivelado: ligeiramente abaixo da média
            default_aggression=0.55,  # Nivelado: média
            default_tightness=27  # Nivelado: média
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.bluff_call_ratio = 0.50  # 50% CALL / 50% RAISE quando blefar
        self.last_action = None
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        # NOVO: Analisa ações do round atual
        current_actions = analyze_current_round_actions(round_state, self.uuid) if hasattr(self, 'uuid') and self.uuid else None
        
        hand_strength = self._evaluate_hand_strength(hole_card)
        should_bluff = self._should_bluff()
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        
        # NOVO: Ajusta blefe baseado em ações atuais
        if current_actions and current_actions['has_raises'] and current_actions['raise_count'] >= 2:
            should_bluff = False  # Não blefa se muito agressão
        
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state)
        else:
            action, amount = self._normal_action(valid_actions, hand_strength, round_state, current_actions)
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
    def _should_bluff(self):
        """Decide se deve blefar baseado na probabilidade configurada."""
        return random.random() < self.bluff_probability
    
    def _bluff_action(self, valid_actions, round_state):
        """Executa blefe: escolhe aleatoriamente entre CALL ou RAISE."""
        # 50% CALL / 50% RAISE (totalmente aleatório)
        bluff_choice = random.random() < 0.50
        
        if bluff_choice and valid_actions[2]['amount']['min'] != -1:
            # Faz RAISE aleatório
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, max_amount)
            return raise_action['action'], amount
        else:
            # Faz CALL
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _analyze_table_context(self, round_state):
        """Analisa o contexto da mesa (não usado, mas mantido para consistência)."""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([s for s in round_state['seats'] if s['state'] == 'participating'])
        street = round_state['street']
        
        return {
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street
        }
    
    def _evaluate_hand_strength(self, hole_card):
        """Avalia a força das cartas (não usado muito, pois é aleatório)."""
        if not hole_card or len(hole_card) < 2:
            return 0
        
        card_ranks = [card[1] for card in hole_card]
        
        # Par
        if card_ranks[0] == card_ranks[1]:
            return 30
        
        # Cartas altas
        high_cards = ['A', 'K', 'Q']
        if any(rank in high_cards for rank in card_ranks):
            return 20
        
        return 10
    
    def _normal_action(self, valid_actions, hand_strength, round_state, current_actions=None):
        """Ação normal: aleatória, mas ajustada por ações atuais."""
        # NOVO: Se houver muitos raises, aumenta chance de fold
        fold_prob = 0.33
        if current_actions and current_actions['has_raises']:
            fold_prob = min(0.60, 0.33 + (current_actions['raise_count'] * 0.15))
        
        # Escolhe ação aleatoriamente (ajustado)
        rand = random.random()
        if rand < fold_prob:
            action_choice = 'fold'
        elif rand < 0.66:
            action_choice = 'call'
        else:
            action_choice = 'raise'
        
        # Armazena última ação
        self.last_action = action_choice
        
        if action_choice == 'fold':
            fold_action = valid_actions[0]
            return fold_action['action'], fold_action['amount']
        elif action_choice == 'call':
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
        else:  # raise
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, max_amount)
                return raise_action['action'], amount
            else:
                # Se não pode fazer raise, faz call
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
    
    def receive_game_start_message(self, game_info):
        pass
    
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
        """Aprendizado estocástico: ajusta probabilidades baseado em resultados."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprendizado estocástico simples: ajusta blefe baseado em resultados
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 10:
            recent_rounds = round_history[-10:]
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Ajusta blefe baseado em win rate (evolução muito lenta)
            if win_rate > 0.5:
                self.memory['bluff_probability'] = min(0.20, self.memory['bluff_probability'] * 1.001)
            elif win_rate < 0.3:
                self.memory['bluff_probability'] = max(0.12, self.memory['bluff_probability'] * 0.999)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        
        # Salva memória após ajustes
        self.memory_manager.save()

