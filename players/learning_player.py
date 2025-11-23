from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.hand_utils import evaluate_hand_strength
from utils.action_analyzer import analyze_current_round_actions

class LearningPlayer(BasePokerPlayer):
    """IA que aprende e se adapta baseado no histórico de jogos. Usa sistema de memória unificado."""
    
    def __init__(self, learning_rate=0.01, memory_file="learning_player_memory.json"):
        # Parâmetros de aprendizado (muito lento)
        self.learning_rate = learning_rate
        
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.17,  # Nivelado: média
            default_aggression=0.55,  # Nivelado: média
            default_tightness=28  # Nivelado: ligeiramente acima da média
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
        
        # Avalia força da mão
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Decide se deve blefar baseado no aprendizado
        should_bluff = self._should_bluff_with_learning(round_state, current_actions)
        
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state)
        else:
            action, amount = self._normal_action_with_learning(valid_actions, hand_strength, round_state, current_actions)
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
    def _should_bluff_with_learning(self, round_state, current_actions=None):
        """Decide se deve blefar considerando o aprendizado e ações atuais."""
        base_probability = self.bluff_probability
        
        # NOVO: Ajusta baseado em ações do round atual
        if current_actions:
            if current_actions['has_raises']:
                # Se alguém fez raise, reduz chance de blefe
                if current_actions['raise_count'] >= 2:
                    base_probability *= 0.5  # Muito agressão: reduz bastante
                else:
                    base_probability *= 0.8  # Um raise: reduz moderadamente
        
        # Ajusta baseado nos oponentes (análise simples)
        active_opponents = [s for s in round_state['seats'] 
                           if s['uuid'] != self.uuid and s['state'] == 'participating']
        
        # Se oponentes são muito agressivos, blefa menos (ajuste sutil)
        if len(active_opponents) > 0:
            # Análise simples baseada em histórico
            opp_uuids = [opp['uuid'] for opp in active_opponents]
            aggressive_count = 0
            for opp_uuid in opp_uuids:
                opp_info = self.memory_manager.get_opponent_info(opp_uuid)
                if opp_info:
                    # Analisa ações recentes
                    recent_rounds = opp_info.get('rounds_against', [])[-5:]
                    if recent_rounds:
                        raise_count = sum(1 for r in recent_rounds 
                                         for a in r.get('opponent_actions', [])
                                         if a.get('action') == 'raise')
                        if raise_count > len(recent_rounds) * 0.5:
                            aggressive_count += 1
            
            if aggressive_count > len(active_opponents) * 0.5:
                base_probability *= 0.95  # Reduz levemente
        
        return random.random() < base_probability
    
    def _normal_action_with_learning(self, valid_actions, hand_strength, round_state, current_actions=None):
        """Ação normal considerando aprendizado e ações atuais."""
        adjusted_threshold = self.tightness_threshold
        
        # NOVO: Ajusta threshold baseado em ações do round atual
        if current_actions:
            if current_actions['has_raises']:
                # Se alguém fez raise, fica mais seletivo
                adjusted_threshold += 5 + (current_actions['raise_count'] * 2)
            elif current_actions['last_action'] == 'raise':
                # Se última ação foi raise, aumenta threshold
                adjusted_threshold += 3
        
        # Mão muito forte: raise
        if hand_strength >= 60:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                return raise_action['action'], raise_action['amount']['min']
        
        # Mão forte: call ou raise moderado
        if hand_strength >= 40:
            if self.aggression_level > 0.55 and valid_actions[2]['amount']['min'] != -1:
                return valid_actions[2]['action'], valid_actions[2]['amount']['min']
            else:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # Mão média: depende do threshold
        if hand_strength >= adjusted_threshold:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
        
        # Mão fraca: fold apenas se for MUITO fraca
        if hand_strength < (adjusted_threshold - 7):
            fold_action = valid_actions[0]
            return fold_action['action'], fold_action['amount']
        
        # Mão média-fraca: call (não desiste tão fácil)
        call_action = valid_actions[1]
        return call_action['action'], call_action['amount']
    
    def _bluff_action(self, valid_actions, round_state):
        """Executa blefe considerando aprendizado."""
        context = self._analyze_table_context(round_state)
        
        # Blefe moderado
        if valid_actions[2]['amount']['min'] != -1 and random.random() < 0.5:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, min(max_amount, min_amount + 20))
            return raise_action['action'], amount
        else:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _analyze_table_context(self, round_state):
        """Analisa contexto da mesa."""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([s for s in round_state['seats'] if s['state'] == 'participating'])
        street = round_state['street']
        
        return {
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street
        }
    
    def _evaluate_hand_strength(self, hole_card, round_state):
        """Avalia força da mão usando utilitário compartilhado."""
        community_cards = round_state.get('community_card', []) if round_state else None
        return evaluate_hand_strength(hole_card, community_cards)
    
    def receive_game_start_message(self, game_info):
        """Inicializa stack inicial."""
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
        """Aprende com o resultado da rodada (evolução lenta e sutil)."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprendizado lento e sutil: ajusta baseado em win rate recente
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 10:
            recent_rounds = round_history[-10:]
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Evolução muito lenta: ajustes de 0.1% por vez
            if win_rate > 0.6:
                self.memory['bluff_probability'] = min(0.20, self.memory['bluff_probability'] * 1.001)
                self.memory['aggression_level'] = min(0.70, self.memory['aggression_level'] * 1.001)
            elif win_rate < 0.3:
                self.memory['bluff_probability'] = max(0.12, self.memory['bluff_probability'] * 0.999)
                self.memory['aggression_level'] = max(0.40, self.memory['aggression_level'] * 0.999)
                self.memory['tightness_threshold'] = min(35, self.memory['tightness_threshold'] + 1)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Salva memória após ajustes
        self.memory_manager.save()
