from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.hand_utils import evaluate_hand_strength
from utils.action_analyzer import analyze_current_round_actions, analyze_possible_bluff

class FlexiblePlayer(BasePokerPlayer):
    """Jogador flexível que adapta estratégia conforme a situação. Usa sistema de memória unificado."""
    
    def __init__(self, memory_file="flexible_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.16,  # Flexível
            default_aggression=0.55,  # Médio-alto
            default_tightness=26  # Flexível
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.initial_stack = None
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # NOVO: Analisa ações do round atual
        current_actions = analyze_current_round_actions(round_state, self.uuid) if hasattr(self, "uuid") and self.uuid else None
        
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        
        # NOVO: Analisa possível blefe dos oponentes
        bluff_analysis = None
        if hasattr(self, 'uuid') and self.uuid:
            bluff_analysis = analyze_possible_bluff(
                round_state, self.uuid, hand_strength, self.memory_manager
            )
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Adapta estratégia baseado em contexto
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        active_players = len([
            s for s in round_state.get('seats', [])
            if isinstance(s, dict) and s.get('state') == 'participating'
        ])
        street = round_state.get('street', 'preflop')
        
        # Probabilidade de blefe adaptada
        should_bluff = self._adaptive_bluff_decision(pot_size, active_players, street)
        
        # NOVO: Ajusta blefe baseado em ações atuais
        if current_actions and current_actions['has_raises'] and current_actions['raise_count'] >= 2:
            should_bluff = False  # Não blefa se muito agressão
        
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state)
        else:
            action, amount = self._normal_action(valid_actions, hand_strength, round_state, pot_size, active_players, current_actions, bluff_analysis)
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
    def _adaptive_bluff_decision(self, pot_size, active_players, street):
        """Decisão de blefe adaptada ao contexto."""
        base_prob = self.bluff_probability
        
        # Adapta baseado em múltiplos fatores
        if pot_size < 50:
            base_prob *= 1.2  # Pot pequeno, mais flexível
        elif pot_size > 80:
            base_prob *= 0.9  # Pot grande, mais cauteloso
        
        if active_players <= 2:
            base_prob *= 1.15  # Poucos jogadores, mais agressivo
        elif active_players > 4:
            base_prob *= 0.85  # Muitos jogadores, mais conservador
        
        if street in ['preflop', 'flop']:
            base_prob *= 1.1  # Streets iniciais
        
        return random.random() < min(0.21, base_prob)
    
    def _bluff_action(self, valid_actions, round_state):
        """Blefe flexível: adapta ao contexto."""
        if valid_actions[2]['amount']['min'] != -1 and random.random() < 0.5:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, min(max_amount, min_amount + 15))
            return raise_action['action'], amount
        else:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state, pot_size, active_players, current_actions=None, bluff_analysis=None):
        """Ação flexível: adapta ao contexto e ações atuais."""
        adjusted_threshold = self.tightness_threshold
        
        # Ajusta threshold baseado em contexto
        if active_players > 4:
            adjusted_threshold += 2  # Mais seletivo com muitos jogadores
        
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
            # Reduz threshold quando campo está passivo
            adjusted_threshold = max(22, adjusted_threshold - int(passive_score * 5))
            # Aumenta agressão temporariamente
            adjusted_aggression = min(0.75, adjusted_aggression + (passive_score * 0.2))
        
        # Mão muito forte: raise flexível
        if hand_strength >= 50:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + int(17 * adjusted_aggression)))
                return raise_action['action'], amount
        
        # Mão forte: call ou raise pequeno
        if hand_strength >= adjusted_threshold:
            # NOVO: Com campo passivo, aumenta chance de raise
            if current_actions and current_actions.get('is_passive', False):
                passive_score = current_actions.get('passive_opportunity_score', 0.0)
                if passive_score > 0.4 and valid_actions[2]['amount']['min'] != -1:
                    return valid_actions[2]['action'], valid_actions[2]['amount']['min']
            
            if adjusted_aggression > 0.55 and valid_actions[2]['amount']['min'] != -1:
                return valid_actions[2]['action'], valid_actions[2]['amount']['min']
            else:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
                # NOVO: Se análise indica possível blefe e deve pagar, considera call mesmo com mão média
        if bluff_analysis and bluff_analysis['should_call_bluff']:
            if hand_strength >= 25:  # Flexible: paga blefe com mão razoável
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # Mão fraca: fold apenas se for MUITO fraca
        if hand_strength < (adjusted_threshold - 7):
            fold_action = valid_actions[0]
            return fold_action['action'], fold_action['amount']
        
        if bluff_analysis and bluff_analysis['should_call_bluff']:
            threshold = 25
            if hand_strength >= threshold:  # Mão razoável: paga possível blefe
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # Mão média-fraca: call (não desiste tão fácil)
        call_action = valid_actions[1]
        return call_action['action'], call_action['amount']
    
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
        """Aprendizado flexível: adapta estratégia baseado em resultados."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprendizado flexível: adapta baseado em resultados
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 10:
            recent_rounds = round_history[-10:]
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Ajustes flexíveis
            if win_rate > 0.60:
                self.memory['aggression_level'] = min(0.70, self.memory['aggression_level'] * 1.004)
                self.memory['bluff_probability'] = min(0.20, self.memory['bluff_probability'] * 1.004)
            elif win_rate < 0.30:
                self.memory['tightness_threshold'] = min(30, self.memory['tightness_threshold'] + 1)
                self.memory['aggression_level'] = max(0.42, self.memory['aggression_level'] * 0.996)
                self.memory['bluff_probability'] = max(0.12, self.memory['bluff_probability'] * 0.996)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Salva memória após ajustes
        self.memory_manager.save()

