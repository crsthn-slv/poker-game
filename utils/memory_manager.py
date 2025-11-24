"""
Gerenciador de memória unificada para bots.

Facilita o uso da estrutura de memória unificada pelos bots.
"""

from typing import Dict, List, Optional, Any
from .unified_memory import (
    create_default_memory, register_new_opponent, parse_hand_info,
    extract_hole_cards, record_opponent_round, record_my_action,
    evaluate_action_result, save_unified_memory, load_unified_memory
)
from .hand_utils import evaluate_hand_strength, get_community_cards


class UnifiedMemoryManager:
    """Gerenciador de memória unificada para bots."""
    
    def __init__(self, memory_file: str, default_bluff: float = 0.17,
                 default_aggression: float = 0.55, default_tightness: int = 27,
                 my_bot_name: str = None):
        """Inicializa gerenciador de memória.
        
        Args:
            memory_file: Nome do arquivo de memória
            default_bluff: Probabilidade padrão de blefe
            default_aggression: Nível padrão de agressão
            default_tightness: Threshold padrão de seletividade
            my_bot_name: Nome do bot (para pré-registrar todos os outros bots)
        """
        from .memory_utils import get_memory_path
        self.memory_file = get_memory_path(memory_file)
        self.memory = load_unified_memory(
            self.memory_file, default_bluff, default_aggression, default_tightness, my_bot_name
        )
        self._current_round_actions = []
        self._current_round_opponent_actions = {}
    
    def get_memory(self) -> Dict[str, Any]:
        """Retorna a estrutura de memória."""
        return self.memory
    
    def identify_opponents(self, round_state: Dict[str, Any], my_uuid: str) -> None:
        """Identifica e registra oponentes no round atual.
        
        Args:
            round_state: Estado do round
            my_uuid: UUID do bot
        """
        from utils.uuid_utils import get_bot_class_uuid_from_name
        
        seats = round_state.get('seats', [])
        current_round = self.memory['total_rounds'] + 1
        
        # Obtém UUID fixo do próprio bot (para comparação correta)
        my_seat = next((s for s in seats if isinstance(s, dict) and s.get('uuid') == my_uuid), None)
        my_name = my_seat.get('name', 'Unknown') if my_seat else None
        my_uuid_fixed = get_bot_class_uuid_from_name(my_name) if my_name else my_uuid
        
        for seat in seats:
            if isinstance(seat, dict):
                opp_uuid_from_seat = seat.get('uuid')
                if opp_uuid_from_seat and opp_uuid_from_seat != my_uuid:
                    opp_name = seat.get('name', 'Unknown')
                    
                    # Obtém UUID fixo do oponente
                    opp_uuid_fixed = get_bot_class_uuid_from_name(opp_name)
                    opp_uuid = opp_uuid_fixed if opp_uuid_fixed else opp_uuid_from_seat
                    
                    # Compara UUIDs fixos para evitar rastrear a si mesmo
                    if opp_uuid != my_uuid_fixed:
                        register_new_opponent(self.memory, opp_uuid, opp_name, current_round)
    
    def record_opponent_action(self, opp_uuid: str, action: Dict[str, Any],
                              round_state: Dict[str, Any]) -> None:
        """Registra ação de um oponente durante o round.
        
        Args:
            opp_uuid: UUID do oponente
            action: Ação do oponente
            round_state: Estado do round
        """
        if opp_uuid not in self._current_round_opponent_actions:
            self._current_round_opponent_actions[opp_uuid] = []
        
        self._current_round_opponent_actions[opp_uuid].append({
            'street': round_state.get('street', 'preflop'),
            'action': action.get('action'),
            'amount': action.get('amount', 0)
        })
    
    def record_my_action(self, street: str, action: str, amount: int,
                        hand_strength: int, round_state: Dict[str, Any],
                        was_bluff: bool) -> None:
        """Registra uma ação do bot.
        
        Args:
            street: Street atual
            action: Ação tomada
            amount: Valor da ação
            hand_strength: Força da mão
            round_state: Estado do round
            was_bluff: Se foi blefe
        """
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        active_players = len([
            s for s in round_state.get('seats', [])
            if isinstance(s, dict) and s.get('state') == 'participating'
        ])
        
        record_my_action(
            self._current_round_actions, street, action, amount,
            hand_strength, pot_size, active_players, was_bluff
        )
    
    def process_round_result(self, winners: List[Any], hand_info: Any,
                           round_state: Dict[str, Any], my_uuid: str) -> None:
        """Processa resultado do round e atualiza memória.
        
        Args:
            winners: Lista de vencedores
            hand_info: Informações das mãos
            round_state: Estado do round
            my_uuid: UUID do bot
        """
        self.memory['total_rounds'] += 1
        won = any(
            (w.get('uuid') if isinstance(w, dict) else getattr(w, 'uuid', None)) == my_uuid
            for w in winners
        )
        
        if won:
            self.memory['wins'] += 1
        
        # Processa hand_info
        hand_info_dict = parse_hand_info(hand_info, round_state)
        community_cards = get_community_cards(round_state)
        
        # Identifica oponentes
        opponents_uuids = [
            s.get('uuid') for s in round_state.get('seats', [])
            if isinstance(s, dict) and s.get('uuid') != my_uuid and s.get('state') == 'participating'
        ]
        
        # Processa cada oponente
        for opp_uuid in opponents_uuids:
            if opp_uuid not in self.memory['opponents']:
                continue
            
            # Verifica se chegou ao showdown
            reached_showdown = opp_uuid in hand_info_dict
            
            # Obtém cartas se chegou ao showdown
            hole_cards = None
            hand_strength = None
            if reached_showdown:
                hand_info_item = hand_info_dict[opp_uuid]
                hole_cards = extract_hole_cards(hand_info_item)
                if hole_cards:
                    hand_strength = evaluate_hand_strength(hole_cards, community_cards)
            
            # Obtém ações do oponente
            opponent_actions = self._current_round_opponent_actions.get(opp_uuid, [])
            
            # Determina resultado
            opp_won = any(
                (w.get('uuid') if isinstance(w, dict) else getattr(w, 'uuid', None)) == opp_uuid
                for w in winners
            )
            
            # Registra round contra este oponente
            record_opponent_round(
                self.memory, opp_uuid, self.memory['total_rounds'],
                opponent_actions, reached_showdown, hole_cards, hand_strength,
                opp_won, won, community_cards
            )
        
        # Avalia ações do bot
        my_seat = next(
            (s for s in round_state.get('seats', [])
             if isinstance(s, dict) and s.get('uuid') == my_uuid),
            None
        )
        stack_change = 0
        final_stack = 0
        if my_seat:
            final_stack = my_seat.get('stack', 0)
            if hasattr(self, 'initial_stack') and self.initial_stack:
                stack_change = final_stack - self.initial_stack
        
        # Avalia cada ação
        for action_record in self._current_round_actions:
            action_record['result'] = evaluate_action_result(
                action_record, won, stack_change
            )
        
        # Salva histórico do round
        round_history_entry = {
            'round': self.memory['total_rounds'],
            'opponents_uuids': opponents_uuids,
            'my_actions': self._current_round_actions.copy(),
            'final_result': {
                'won': won,
                'pot_won': round_state.get('pot', {}).get('main', {}).get('amount', 0) if won else 0,
                'stack_change': stack_change,
                'final_stack': final_stack
            }
        }
        
        # Adiciona ao histórico (mantém últimos 20 rounds)
        self.memory['round_history'].append(round_history_entry)
        if len(self.memory['round_history']) > 20:
            self.memory['round_history'] = self.memory['round_history'][-20:]
        
        # Limpa ações do round atual
        self._current_round_actions = []
        self._current_round_opponent_actions = {}
    
    def save(self) -> bool:
        """Salva memória em arquivo.
        
        Returns:
            True se salvou com sucesso
        """
        return save_unified_memory(self.memory_file, self.memory)
    
    def get_opponent_info(self, opp_uuid: str) -> Optional[Dict[str, Any]]:
        """Obtém informações de um oponente.
        
        Args:
            opp_uuid: UUID do oponente
        
        Returns:
            Informações do oponente ou None
        """
        return self.memory['opponents'].get(opp_uuid)

