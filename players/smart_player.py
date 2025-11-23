from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.hand_utils import evaluate_hand_strength
from utils.action_analyzer import analyze_current_round_actions, analyze_possible_bluff

class SmartPlayer(BasePokerPlayer):
    """Jogador inteligente que ajusta estratégia dinamicamente. Usa sistema de memória unificado."""
    
    def __init__(self, memory_file="smart_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.16,  # Nivelado: ligeiramente acima da média
            default_aggression=0.56,  # Nivelado: ligeiramente acima da média
            default_tightness=27  # Nivelado: média
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.initial_stack = None
        self.current_stack = None
        self.current_street = 'preflop'
        self.last_bluff_round = None
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        # NOVO: Analisa ações do round atual
        current_actions = analyze_current_round_actions(round_state, self.uuid) if hasattr(self, 'uuid') and self.uuid else None
        
        # Atualiza stack atual
        self._update_stack(round_state)
        
        # Ajusta probabilidade de blefe baseado na performance
        self._adjust_bluff_probability()
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        
        # NOVO: Analisa possível blefe dos oponentes
        bluff_analysis = None
        if hasattr(self, 'uuid') and self.uuid:
            bluff_analysis = analyze_possible_bluff(
                round_state, self.uuid, hand_strength, self.memory_manager
            )
        should_bluff = self._should_bluff()
        
        # NOVO: Ajusta blefe baseado em ações atuais
        if current_actions and current_actions['has_raises']:
            if current_actions['raise_count'] >= 2:
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
    
    def _should_bluff(self):
        """Decide se deve blefar baseado na probabilidade ajustada dinamicamente."""
        return random.random() < self.bluff_probability
    
    def _adjust_bluff_probability(self):
        """Ajusta probabilidade de blefe baseado na performance (evolução lenta e sutil)."""
        if self.initial_stack is None or self.current_stack is None:
            return
        
        # Calcula performance (stack atual vs inicial)
        if self.initial_stack > 0:
            performance_ratio = self.current_stack / self.initial_stack
            
            # Evolução lenta e sutil: ajustes de 0.2% por vez
            if performance_ratio > 1.2:
                self.memory['bluff_probability'] = min(0.20, self.memory['bluff_probability'] * 1.002)
            elif performance_ratio > 1.0:
                self.memory['bluff_probability'] = min(0.20, self.memory['bluff_probability'] * 1.001)
            elif performance_ratio < 0.8:
                self.memory['bluff_probability'] = max(0.12, self.memory['bluff_probability'] * 0.998)
            elif performance_ratio < 1.0:
                self.memory['bluff_probability'] = max(0.12, self.memory['bluff_probability'] * 0.999)
    
    def _update_stack(self, round_state):
        """Atualiza informações do stack."""
        for seat in round_state['seats']:
            if seat['uuid'] == self.uuid:
                if self.initial_stack is None:
                    self.initial_stack = seat['stack']
                self.current_stack = seat['stack']
                break
    
    def _bluff_action(self, valid_actions, round_state):
        """Executa blefe inteligente baseado no contexto."""
        context = self._analyze_table_context(round_state)
        
        # Análise sofisticada: pot grande = CALL, pot pequeno = RAISE
        if context['pot_size'] > 100:
            # Pot grande: 60% CALL (blefe mais conservador)
            bluff_choice = random.random() < 0.40  # 40% RAISE
        else:
            # Pot pequeno: 70% RAISE (blefe mais agressivo)
            bluff_choice = random.random() < 0.70
        
        # Considera número de jogadores
        if context['active_players'] <= 2:
            # Poucos jogadores: mais agressivo
            bluff_choice = bluff_choice or random.random() < 0.20
        
        if bluff_choice and valid_actions[2]['amount']['min'] != -1:
            # Faz RAISE
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            # Raise moderado
            amount = random.randint(min_amount, min(max_amount, min_amount + 25))
            return raise_action['action'], amount
        else:
            # Faz CALL
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _analyze_table_context(self, round_state):
        """Análise sofisticada do contexto da mesa."""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([s for s in round_state['seats'] if s['state'] == 'participating'])
        street = round_state['street']
        
        # Calcula stack médio dos outros jogadores
        other_stacks = [s['stack'] for s in round_state['seats'] if s['uuid'] != self.uuid and s['state'] == 'participating']
        avg_stack = sum(other_stacks) / len(other_stacks) if other_stacks else 100
        
        return {
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street,
            'avg_stack': avg_stack
        }
    
    def _evaluate_hand_strength(self, hole_card, round_state):
        """Avalia força da mão usando utilitário compartilhado."""
        community_cards = round_state.get('community_card', []) if round_state else None
        return evaluate_hand_strength(hole_card, community_cards)
    
    def _normal_action(self, valid_actions, hand_strength, round_state, current_actions=None, bluff_analysis=None):
        """Ação normal baseada na força da mão, contexto e ações atuais."""
        context = self._analyze_table_context(round_state)
        adjusted_threshold = self.tightness_threshold
        
        # NOVO: Ajusta threshold baseado em ações do round atual
        if current_actions:
            if current_actions['has_raises']:
                # Se alguém fez raise, fica mais seletivo
                adjusted_threshold += 5 + (current_actions['raise_count'] * 2)
            elif current_actions['last_action'] == 'raise':
                # Se última ação foi raise, aumenta threshold
                adjusted_threshold += 3
        
        # NOVO: Campo passivo reduz threshold e aumenta agressão
        if current_actions and current_actions.get('is_passive', False):
            passive_score = current_actions.get('passive_opportunity_score', 0.0)
            # Reduz threshold quando campo está passivo (joga mais mãos)
            adjusted_threshold = max(20, adjusted_threshold - int(passive_score * 5))
        
        # Mão muito forte: raise agressivo
        if hand_strength >= 70:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + 25))
                return raise_action['action'], amount
        
        # Mão forte: raise moderado ou call (baseado em threshold)
        if hand_strength >= 50:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1 and context['pot_size'] < 80:
                return raise_action['action'], raise_action['amount']['min']
            else:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # NOVO: Com campo passivo, até mãos médias podem fazer raise
        if current_actions and current_actions.get('is_passive', False):
            passive_score = current_actions.get('passive_opportunity_score', 0.0)
            if hand_strength >= 35 and passive_score > 0.5:
                raise_action = valid_actions[2]
                if raise_action['amount']['min'] != -1:
                    return raise_action['action'], raise_action['amount']['min']
        
        # Mão média: call se acima do threshold, fold caso contrário
        if hand_strength >= adjusted_threshold:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
        
        # NOVO: Se análise indica possível blefe e deve pagar, considera call mesmo com mão média
        if bluff_analysis and bluff_analysis['should_call_bluff']:
            if hand_strength >= 28:  # Smart: paga blefe com mão razoável
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # Mão fraca: fold apenas se for MUITO fraca
        if hand_strength < (adjusted_threshold - 6):
            fold_action = valid_actions[0]
            return fold_action['action'], fold_action['amount']
        
        # Mão média-fraca: call (não desiste tão fácil)
        call_action = valid_actions[1]
        return call_action['action'], call_action['amount']
    
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
        """Salva memória periodicamente e armazena cartas no registry."""
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
        """Registra mudança de street."""
        self.current_street = street
    
    def receive_game_update_message(self, action, round_state):
        """Registra ações dos oponentes."""
        player_uuid = action.get('uuid') or action.get('player_uuid')
        if player_uuid and player_uuid != self.uuid:
            self.memory_manager.record_opponent_action(player_uuid, action, round_state)
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado lento e sutil: ajusta baseado em win rate recente."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Atualiza stack
        self._update_stack(round_state)
        
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

