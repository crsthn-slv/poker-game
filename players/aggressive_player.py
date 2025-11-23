from pypokerengine.players import BasePokerPlayer
import random
from .memory_manager import UnifiedMemoryManager

class AggressivePlayer(BasePokerPlayer):
    """Jogador agressivo que joga muitas mãos e blefa frequentemente (35%). Aprendizado agressivo intermediário com memória persistente."""
    
    def __init__(self, memory_file="aggressive_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.18,  # Nivelado: ligeiramente acima da média
            default_aggression=0.58,  # Nivelado: ligeiramente acima da média
            default_tightness=26  # Nivelado: ligeiramente abaixo da média
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.bluff_call_ratio = 0.40  # 40% CALL / 60% RAISE quando blefar
        self.initial_stack = None
        self.current_stack = None
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        hand_strength = self._evaluate_hand_strength(hole_card)
        should_bluff = self._should_bluff()
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        
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
    
    def _should_bluff(self):
        """Decide se deve blefar baseado na probabilidade configurada."""
        return random.random() < self.bluff_probability
    
    def _bluff_action(self, valid_actions, round_state):
        """Executa blefe agressivo: prefere RAISE."""
        context = self._analyze_table_context(round_state)
        
        # Blefe mais agressivo quando há poucos jogadores ativos
        if context['active_players'] <= 2:
            # Poucos jogadores: mais RAISE (80%)
            bluff_choice = random.random() < 0.80
        else:
            # Muitos jogadores: ainda prefere RAISE (50%)
            bluff_choice = random.random() < 0.50
        
        if bluff_choice and valid_actions[2]['amount']['min'] != -1:
            # Faz RAISE agressivo
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            # Raise mais alto que o mínimo
            amount = random.randint(min_amount, min(max_amount, min_amount + 30))
            return raise_action['action'], amount
        else:
            # Faz CALL
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _analyze_table_context(self, round_state):
        """Analisa o contexto da mesa."""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([s for s in round_state['seats'] if s['state'] == 'participating'])
        street = round_state['street']
        
        return {
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street
        }
    
    def _evaluate_hand_strength(self, hole_card):
        """Avalia a força das cartas (mais permissivo que TightPlayer)."""
        if not hole_card or len(hole_card) < 2:
            return 0
        
        card_ranks = [card[1] for card in hole_card]
        card_suits = [card[0] for card in hole_card]
        
        # Par
        if card_ranks[0] == card_ranks[1]:
            return 40
        
        # Qualquer carta alta
        high_cards = ['A', 'K', 'Q', 'J', 'T']
        if any(rank in high_cards for rank in card_ranks):
            return 30
        
        # Mesmo naipe
        if card_suits[0] == card_suits[1]:
            return 20
        
        # Qualquer coisa
        return 10
    
    def _normal_action(self, valid_actions, hand_strength, round_state):
        """Ação normal: ajusta agressão baseado no aprendizado."""
        # Ajusta agressão baseado no aprendizado
        adjusted_aggression = self.aggression_level
        
        # Sempre tenta fazer raise se possível (ajustado pelo aprendizado)
        raise_action = valid_actions[2]
        if raise_action['amount']['min'] != -1:
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            
            # Se tem mão forte, raise maior
            if hand_strength >= 30:
                # Ajusta baseado no nível de agressão aprendido
                raise_multiplier = 15 + (adjusted_aggression * 20)
                amount = random.randint(min_amount, min(max_amount, min_amount + int(raise_multiplier)))
            else:
                # Ainda faz raise, mas menor se agressão foi reduzida
                if adjusted_aggression > 0.5:
                    amount = min_amount
                else:
                    # Se agressão muito baixa, pode fazer call
                    call_action = valid_actions[1]
                    return call_action['action'], call_action['amount']
            return raise_action['action'], amount
        
        # Se não pode fazer raise, faz call
        call_action = valid_actions[1]
        return call_action['action'], call_action['amount']
    
    def receive_game_start_message(self, game_info):
        pass
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        """Salva memória periodicamente e armazena cartas no registry."""
        if round_count % 5 == 0:
            self.memory_manager.save()
        # Armazena cartas no registry global para exibição no final do round
        if hole_card and hasattr(self, 'uuid') and self.uuid:
            from .cards_registry import store_player_cards
            from .hand_utils import normalize_hole_cards
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
        """Aprendizado agressivo: ajusta rapidamente baseado em resultados."""
        # Atualiza stack
        for seat in round_state['seats']:
            if seat['uuid'] == self.uuid:
                if self.initial_stack is None:
                    self.initial_stack = seat['stack']
                    self.memory_manager.initial_stack = self.initial_stack
                self.current_stack = seat['stack']
                break
        
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprendizado agressivo: ajusta rapidamente
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 5:
            recent_rounds = round_history[-10:] if len(round_history) >= 10 else round_history
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Aumenta agressão quando ganha (evolução muito lenta)
            if win_rate > 0.6:
                self.memory['aggression_level'] = min(0.70, self.memory['aggression_level'] * 1.001)
                self.memory['bluff_probability'] = min(0.20, self.memory['bluff_probability'] * 1.001)
            # Reduz agressão quando perde muito (evolução muito lenta)
            elif win_rate < 0.3:
                self.memory['aggression_level'] = max(0.40, self.memory['aggression_level'] * 0.999)
                self.memory['bluff_probability'] = max(0.12, self.memory['bluff_probability'] * 0.999)
            
            # Ajusta baseado em stack (evolução muito lenta)
            if self.initial_stack and self.current_stack:
                stack_ratio = self.current_stack / self.initial_stack
                if stack_ratio < 0.7:
                    # Stack baixo: reduz agressão
                    self.memory['aggression_level'] = max(0.40, self.memory['aggression_level'] * 0.999)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        
        # Salva memória após ajustes
        self.memory_manager.save()
    
    def receive_game_start_message(self, game_info):
        """Inicializa stack."""
        seats = game_info.get('seats', [])
        if isinstance(seats, list):
            for player in seats:
                if player.get('uuid') == self.uuid:
                    self.initial_stack = player.get('stack', 100)
                    self.memory_manager.initial_stack = self.initial_stack
                    break

