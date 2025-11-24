"""
Módulo dedicado para cálculo de bet sizing.
Centraliza toda lógica de sizing para facilitar ajustes e testes.
"""
import random
from typing import Optional, Dict, Tuple


class BetSizingCalculator:
    """Calculadora de tamanho de apostas baseada em contexto."""
    
    def __init__(self, config=None):
        """
        Inicializa calculadora de sizing.
        
        Args:
            config: Configuração do bot (opcional, para personalidade)
        """
        self.config = config
    
    def get_sizing_ranges(self, street: str) -> Dict[str, Tuple[float, float]]:
        """
        Retorna ranges de sizing por street.
        
        Ranges (não valores fixos) para evitar comportamentos repetitivos:
        - Preflop: ranges em BB
        - Pós-flop: ranges em percentagem do pote
        
        Args:
            street: 'preflop', 'flop', 'turn', 'river'
        
        Returns:
            dict: Ranges por categoria {'small': (min, max), 'medium': (min, max), 'large': (min, max)}
        """
        sizing_ranges = {
            'preflop': {
                'small': (0.25, 0.35),   # 2.5-3.5x BB
                'medium': (0.45, 0.55),  # 4.5-5.5x BB
                'large': (0.70, 0.80)     # 7-8x BB
            },
            'flop': {
                'small': (0.20, 0.30),   # 20-30% do pote
                'medium': (0.45, 0.55),  # 45-55% do pote
                'large': (0.70, 0.80)    # 70-80% do pote
            },
            'turn': {
                'small': (0.45, 0.55),   # 45-55% do pote
                'medium': (0.65, 0.75),  # 65-75% do pote
                'large': (0.95, 1.05)    # 95-105% do pote (pot-sized)
            },
            'river': {
                'small': (0.45, 0.55),   # 45-55% do pote
                'medium': (0.65, 0.75),  # 65-75% do pote
                'large': (0.95, 1.05)    # 95-105% do pote (pot-sized)
            }
        }
        
        return sizing_ranges.get(street, sizing_ranges['flop'])
    
    def get_sizing_preference(self) -> str:
        """
        Retorna preferência de sizing baseada na personalidade.
        
        Returns:
            str: 'aggressive', 'balanced' ou 'cautious'
        """
        if not self.config:
            return 'balanced'
        
        if self.config.name == "Cautious":
            return 'cautious'
        elif self.config.name == "Aggressive":
            return 'aggressive'
        else:
            return 'balanced'
    
    def select_sizing_category(self, hand_strength: int, round_state: Dict, 
                              strong_hand_threshold: int = 50, 
                              raise_threshold: int = 27) -> str:
        """
        Seleciona categoria de sizing (small/mid/large) baseado em força da mão.
        
        Args:
            hand_strength: Força da mão (0-100)
            round_state: Estado do round (para multiway)
            strong_hand_threshold: Threshold para mão muito forte
            raise_threshold: Threshold mínimo para raise
        
        Returns:
            str: 'small', 'medium' ou 'large'
        """
        # Determina categoria base por força da mão
        if hand_strength >= strong_hand_threshold:
            base_category = 'large'
        elif hand_strength >= raise_threshold:
            base_category = 'medium'
        else:
            base_category = 'small'
        
        # Multiway: mãos fortes continuam agressivas, mas sizing moderado
        active_players = self._count_active_players(round_state)
        if active_players > 2 and base_category == 'large':
            # Em multiway, mesmo mãos fortes usam sizing medium
            return 'medium'
        
        return base_category
    
    def _count_active_players(self, round_state: Dict) -> int:
        """
        Conta jogadores ativos no pote (multiway).
        
        Returns:
            int: Número de jogadores ativos (mínimo 2)
        """
        active_count = 0
        for seat in round_state.get('seats', []):
            if seat.get('stack', 0) > 0:
                active_count += 1
        return max(2, active_count)  # Mínimo 2 (heads-up)
    
    def calculate_spr(self, my_stack: int, pot_size: int) -> float:
        """
        Calcula Stack-to-Pot Ratio (SPR).
        
        Args:
            my_stack: Stack atual do jogador
            pot_size: Tamanho do pote
        
        Returns:
            float: SPR atual (infinito se pot_size == 0)
        """
        if pot_size == 0:
            return float('inf')
        return my_stack / pot_size
    
    def get_street(self, round_state: Dict) -> str:
        """
        Identifica a street atual (flop, turn, river).
        
        Returns:
            str: 'flop', 'turn', 'river' ou 'preflop'
        """
        community_cards = round_state.get('community_card', [])
        
        if len(community_cards) == 0:
            return 'preflop'
        elif len(community_cards) == 3:
            return 'flop'
        elif len(community_cards) == 4:
            return 'turn'
        else:  # len == 5
            return 'river'
    
    def calculate_bet_size(self, min_amount: int, max_amount: int, 
                           round_state: Dict, hand_strength: int,
                           my_stack: int,
                           strong_hand_threshold: int = 50,
                           raise_threshold: int = 27) -> int:
        """
        Calcula tamanho da aposta usando SPR, street e ranges estocásticos.
        
        Sistema que:
        1. Calcula SPR
        2. Identifica street
        3. Seleciona categoria de sizing (small/mid/large) por força da mão
        4. Seleciona range correspondente
        5. Aplica variação estocástica mínima dentro do range
        6. Ajusta por SPR (limites rígidos)
        7. Garante limites do engine (clamp)
        
        Args:
            min_amount: Mínimo permitido pelo engine
            max_amount: Máximo permitido pelo engine
            round_state: Estado do round
            hand_strength: Força da mão (0-100)
            my_stack: Stack atual do jogador
            strong_hand_threshold: Threshold para mão muito forte
            raise_threshold: Threshold mínimo para raise
        
        Returns:
            int: Tamanho da aposta calculado (clamped entre min_amount e max_amount)
        """
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        
        if pot_size == 0 or my_stack == 0:
            return self._clamp_amount(min_amount, max_amount, min_amount)
        
        # Calcula SPR
        spr = self.calculate_spr(my_stack, pot_size)
        
        # Identifica street
        street = self.get_street(round_state)
        
        # Seleciona categoria de sizing
        sizing_category = self.select_sizing_category(
            hand_strength, round_state, strong_hand_threshold, raise_threshold
        )
        
        # Obtém ranges de sizing
        sizing_ranges = self.get_sizing_ranges(street)
        range_min, range_max = sizing_ranges[sizing_category]
        
        # Aplica variação estocástica mínima dentro do range
        # Personalidade afeta preferência (upper/lower end do range)
        personality_preference = self.get_sizing_preference()
        
        if personality_preference == 'aggressive':
            # Prefere upper end do range (70-100% do range)
            target_ratio = range_min + (range_max - range_min) * random.uniform(0.70, 1.0)
        elif personality_preference == 'cautious':
            # Prefere lower end do range (0-30% do range)
            target_ratio = range_min + (range_max - range_min) * random.uniform(0.0, 0.30)
        else:  # balanced
            # Prefere meio do range (40-60% do range)
            target_ratio = range_min + (range_max - range_min) * random.uniform(0.40, 0.60)
        
        # Calcula amount baseado em % do pote
        base_amount = int(pot_size * target_ratio)
        
        # Ajuste por SPR: limites rígidos para evitar all-ins arbitrários
        if spr < 3.0:  # SPR baixo: situação de all-in
            max_stack_bet = int(my_stack * 0.30)  # Máximo 30% do stack
            base_amount = min(base_amount, max_stack_bet)
        elif spr < 10.0:  # SPR médio: jogo normal
            max_stack_bet = int(my_stack * 0.40)  # Máximo 40% do stack
            base_amount = min(base_amount, max_stack_bet)
        # SPR alto (> 10): sem limite de stack, usa apenas % do pote
        
        # CLAMP: Garante limites do engine (MELHORIA #1)
        final_amount = self._clamp_amount(min_amount, max_amount, base_amount)
        
        return final_amount
    
    def _clamp_amount(self, min_amount: int, max_amount: int, amount: int) -> int:
        """
        Aplica clamp de valores no sizing.
        
        Elimina raises inválidos e evita erros silenciosos da engine.
        
        Args:
            min_amount: Valor mínimo permitido
            max_amount: Valor máximo permitido
            amount: Valor a ser clampado
        
        Returns:
            int: Valor clampado entre min_amount e max_amount
        """
        return max(min_amount, min(max_amount, amount))
    
    def is_raise_available(self, valid_actions: list) -> bool:
        """
        Verifica se raise está disponível.
        
        Impede blefe ou raise normal quando min == -1 ou quando o raise é ilegal.
        
        Args:
            valid_actions: Lista de ações válidas do PyPokerEngine
        
        Returns:
            bool: True se raise está disponível, False caso contrário
        """
        if not valid_actions or len(valid_actions) < 3:
            return False
        
        raise_action = valid_actions[2]
        if not isinstance(raise_action, dict):
            return False
        
        amount_info = raise_action.get('amount', {})
        if not isinstance(amount_info, dict):
            return False
        
        min_amount = amount_info.get('min', -1)
        return min_amount != -1

