"""
Sistema de histórico de jogos para análise estatística.

Captura dados brutos de cada jogo para análise posterior.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from .hand_utils import get_community_cards, normalize_hole_cards
from .cards_registry import get_player_cards


def get_history_path(filename: str) -> str:
    """
    Retorna o caminho completo para o arquivo de histórico.
    Centraliza todos os históricos em data/history/
    
    Args:
        filename: Nome do arquivo de histórico (ex: 'game_2024-01-15_10-30-00.json')
    
    Returns:
        Caminho completo para o arquivo de histórico
    """
    # Obtém o diretório raiz do projeto (poker_test/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Cria diretório de histórico se não existir
    history_dir = os.path.join(project_root, 'data', 'history')
    os.makedirs(history_dir, exist_ok=True)
    
    # Retorna caminho completo
    return os.path.join(history_dir, filename)


class GameHistory:
    """Gerenciador de histórico de jogos."""
    
    def __init__(self, player_uuid: str, initial_stack: int = 100):
        """
        Inicializa histórico de jogo.
        
        Args:
            player_uuid: UUID do jogador humano
            initial_stack: Stack inicial do jogador
        """
        self.player_uuid = player_uuid
        self.initial_stack = initial_stack
        self.start_time = datetime.now()
        
        # Gera game_id determinístico baseado em timestamp + player_uuid
        timestamp_str = self.start_time.isoformat()
        game_id_source = f"{player_uuid}_{timestamp_str}"
        GAME_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        self.game_id = str(uuid.uuid5(GAME_NAMESPACE, game_id_source))
        
        # Estrutura do histórico
        self.history = {
            "game_id": self.game_id,
            "timestamp": self.start_time.isoformat(),
            "player_uuid": self.player_uuid,
            "game_config": {
                "initial_stack": initial_stack,
                "small_blind": 0,  # Será preenchido quando disponível
                "big_blind": 0,    # Será preenchido quando disponível
                "max_rounds": 0,   # Será preenchido quando disponível
                "num_players": 0   # Será preenchido quando disponível
            },
            "players": [],  # Lista de UUIDs dos jogadores
            "rounds": []
        }
        
        self.current_round = None
        self.current_street = None
        self.current_street_actions = []
        
    def set_game_config(self, small_blind: int, big_blind: int, max_rounds: int, num_players: int):
        """Define configurações do jogo."""
        self.history["game_config"]["small_blind"] = small_blind
        self.history["game_config"]["big_blind"] = big_blind
        self.history["game_config"]["max_rounds"] = max_rounds
        self.history["game_config"]["num_players"] = num_players
    
    def register_players(self, seats: List[Dict[str, Any]]):
        """
        Registra todos os jogadores do jogo.
        
        Args:
            seats: Lista de seats com informações dos jogadores
        """
        self.history["players"] = []
        for seat in seats:
            if isinstance(seat, dict):
                player_uuid = seat.get('uuid')
                if player_uuid:
                    self.history["players"].append(player_uuid)
    
    def start_round(self, round_count: int, seats: List[Dict[str, Any]], 
                   button_position: int = 0):
        """
        Inicia um novo round.
        
        Args:
            round_count: Número do round
            seats: Lista de seats com informações dos jogadores
            button_position: Posição do botão (índice no array de seats)
        """
        # Finaliza round anterior se existir
        if self.current_round:
            self._finalize_current_round()
        
        # Encontra small blind e big blind
        small_blind_uuid = None
        big_blind_uuid = None
        if seats and len(seats) >= 2:
            sb_index = (button_position + 1) % len(seats)
            bb_index = (button_position + 2) % len(seats)
            if sb_index < len(seats) and isinstance(seats[sb_index], dict):
                small_blind_uuid = seats[sb_index].get('uuid')
            if bb_index < len(seats) and isinstance(seats[bb_index], dict):
                big_blind_uuid = seats[bb_index].get('uuid')
        
        # Captura stacks iniciais
        initial_stacks = {}
        for seat in seats:
            if isinstance(seat, dict):
                seat_uuid = seat.get('uuid')
                stack = seat.get('stack', 0)
                if seat_uuid:
                    initial_stacks[seat_uuid] = stack
        
        self.current_round = {
            "round_number": round_count,
            "timestamp": datetime.now().isoformat(),
            "button_position": button_position,
            "small_blind_player": small_blind_uuid,
            "big_blind_player": big_blind_uuid,
            "initial_stacks": initial_stacks,
            "streets": [],
            "result": None
        }
        self.current_street = None
        self.current_street_actions = []
    
    def start_street(self, street: str, round_state: Dict[str, Any]):
        """
        Inicia uma nova street (preflop, flop, turn, river).
        
        Args:
            street: Nome da street ('preflop', 'flop', 'turn', 'river')
            round_state: Estado do round
        """
        if not self.current_round:
            return
        
        # Finaliza street anterior se existir
        if self.current_street:
            self._finalize_current_street()
        
        # Obtém cartas comunitárias
        community_cards = get_community_cards(round_state)
        
        self.current_street = {
            "street": street,
            "community_cards": community_cards,
            "actions": []
        }
        self.current_street_actions = []
    
    def record_action(self, player_uuid: str, action: str, amount: int,
                     round_state: Dict[str, Any], my_hole_cards: Optional[List[str]] = None,
                     my_win_probability: Optional[float] = None):
        """
        Registra uma ação de um jogador.
        
        Args:
            player_uuid: UUID do jogador que fez a ação
            action: Tipo de ação ('FOLD', 'CALL', 'RAISE', 'SMALLBLIND', 'BIGBLIND', 'CHECK')
            amount: Valor da ação
            round_state: Estado do round
            my_hole_cards: Cartas do jogador humano (se for ele)
            my_win_probability: Probabilidade de vitória do jogador humano (se for ele)
        """
        if not self.current_street:
            return
        
        # Obtém pot antes e depois
        pot_before = 0
        pot_after = 0
        if isinstance(round_state.get('pot'), dict):
            pot_before = round_state.get('pot', {}).get('main', {}).get('amount', 0)
            pot_after = pot_before  # Será atualizado após a ação
        
        # Obtém stack antes e depois
        stack_before = 0
        stack_after = 0
        seats = round_state.get('seats', [])
        for seat in seats:
            if isinstance(seat, dict) and seat.get('uuid') == player_uuid:
                stack_before = seat.get('stack', 0)
                # Estima stack depois (aproximado)
                if action == 'FOLD':
                    stack_after = stack_before
                elif action in ['SMALLBLIND', 'BIGBLIND', 'CALL', 'RAISE']:
                    stack_after = stack_before - amount
                else:
                    stack_after = stack_before
                break
        
        # Calcula pot odds (se for ação do jogador humano)
        pot_odds = None
        if player_uuid == self.player_uuid and amount > 0:
            # Pot odds = amount_to_call / (pot + amount_to_call)
            pot_after = pot_before + amount
            if pot_after > 0:
                pot_odds = amount / pot_after
        
        # Conta número de oponentes ativos
        num_active_players = sum(
            1 for seat in seats
            if isinstance(seat, dict) and seat.get('state') == 'participating'
        )
        
        # Cria registro de ação
        action_record = {
            "player_uuid": player_uuid,
            "action": action,
            "amount": amount,
            "pot_before": pot_before,
            "pot_after": pot_after,
            "stack_before": stack_before,
            "stack_after": stack_after,
            "num_active_players": num_active_players
        }
        
        # Adiciona informações específicas do jogador humano
        if player_uuid == self.player_uuid:
            if my_hole_cards:
                action_record["my_hole_cards"] = my_hole_cards
            if my_win_probability is not None:
                action_record["my_win_probability"] = my_win_probability
            if pot_odds is not None:
                action_record["pot_odds"] = pot_odds
        
        self.current_street_actions.append(action_record)
        self.current_street["actions"] = self.current_street_actions
    
    def record_round_result(self, winners: List[Any], hand_info: Any, 
                            round_state: Dict[str, Any]):
        """
        Registra resultado do round.
        
        Args:
            winners: Lista de vencedores
            hand_info: Informações das mãos
            round_state: Estado do round
        """
        if not self.current_round:
            return
        
        # Finaliza street atual
        if self.current_street:
            self._finalize_current_street()
        
        # Processa winners
        winner_uuids = []
        for winner in winners:
            if isinstance(winner, dict):
                winner_uuids.append(winner.get('uuid', winner))
            else:
                winner_uuids.append(winner)
        
        # Obtém pot final
        pot_amount = 0
        if isinstance(round_state.get('pot'), dict):
            pot_amount = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        
        # Obtém stacks finais
        final_stacks = {}
        seats = round_state.get('seats', [])
        for seat in seats:
            if isinstance(seat, dict):
                seat_uuid = seat.get('uuid')
                stack = seat.get('stack', 0)
                if seat_uuid:
                    final_stacks[seat_uuid] = stack
        
        # Determina se chegou ao showdown
        reached_showdown = len(winner_uuids) > 0 and hand_info is not None
        
        # Processa hand_info para obter informações do showdown
        showdown_info = None
        if reached_showdown:
            showdown_info = self._process_hand_info(hand_info, round_state)
        
        # Resultado do jogador humano
        my_result = None
        my_won = self.player_uuid in winner_uuids
        my_seat = next(
            (s for s in seats if isinstance(s, dict) and s.get('uuid') == self.player_uuid),
            None
        )
        
        if my_seat:
            initial_stack = self.current_round["initial_stacks"].get(self.player_uuid, self.initial_stack)
            final_stack = my_seat.get('stack', 0)
            stack_change = final_stack - initial_stack
            
            my_result = {
                "won": my_won,
                "pot_won": pot_amount if my_won else 0,
                "stack_change": stack_change,
                "final_stack": final_stack,
                "reached_showdown": reached_showdown
            }
            
            # Adiciona informações de mão se chegou ao showdown
            if reached_showdown and showdown_info:
                my_showdown = showdown_info.get(self.player_uuid)
                if my_showdown:
                    # Só adiciona se a informação estiver disponível (não None)
                    if my_showdown.get("hand") is not None:
                        my_result["final_hand"] = my_showdown.get("hand")
                    if my_showdown.get("hand_strength") is not None:
                        my_result["final_hand_strength"] = my_showdown.get("hand_strength")
                    if my_showdown.get("hole_cards"):
                        my_result["my_hole_cards"] = my_showdown.get("hole_cards")
                    
                    # Obtém informações dos oponentes no showdown
                    opponents_at_showdown = []
                    for opp_uuid, opp_info in showdown_info.items():
                        if opp_uuid != self.player_uuid:
                            opp_data = {"uuid": opp_uuid}
                            # Só adiciona campos se estiverem disponíveis (não None)
                            if opp_info.get("hole_cards"):
                                opp_data["hole_cards"] = opp_info.get("hole_cards")
                            if opp_info.get("hand") is not None:
                                opp_data["hand"] = opp_info.get("hand")
                            if opp_info.get("hand_strength") is not None:
                                opp_data["hand_strength"] = opp_info.get("hand_strength")
                            opponents_at_showdown.append(opp_data)
                    if opponents_at_showdown:
                        my_result["opponents_at_showdown"] = opponents_at_showdown
        
        self.current_round["result"] = {
            "winners": winner_uuids,
            "pot_amount": pot_amount,
            "final_stacks": final_stacks,
            "showdown": reached_showdown,
            "my_result": my_result
        }
    
    def _process_hand_info(self, hand_info: Any, round_state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Processa hand_info para extrair informações do showdown.
        
        Returns:
            Dict com {uuid: {hole_cards, hand, hand_strength}}
        """
        result = {}
        community_cards = get_community_cards(round_state)
        
        # Importa HandEvaluator para calcular hand_strength quando necessário
        try:
            from .hand_evaluator import HandEvaluator
            hand_evaluator = HandEvaluator()
        except ImportError:
            hand_evaluator = None
        
        # Processa hand_info (pode ser dict ou list)
        if isinstance(hand_info, dict):
            for key, value in hand_info.items():
                if isinstance(value, dict):
                    player_uuid = value.get('uuid', key if isinstance(key, str) else None)
                    if not player_uuid:
                        continue
                    
                    # Extrai hole_cards - tenta múltiplos formatos
                    hole_cards_raw = value.get('hole_card') or value.get('hole_cards') or value.get('cards')
                    if not hole_cards_raw and isinstance(key, str):
                        # Se key é o UUID, tenta obter do value diretamente
                        hole_cards_raw = value.get('hole_card') or value.get('hole_cards')
                    
                    hole_cards = normalize_hole_cards(hole_cards_raw) if hole_cards_raw else []
                    
                    # Se não encontrou cartas no hand_info, tenta obter do registry
                    if not hole_cards and player_uuid:
                        hole_cards = get_player_cards(player_uuid) or []
                    
                    # Tenta obter hand_strength do hand_info (NÃO usa valores padrão)
                    hand_strength = None
                    hand_dict = value.get('hand', {})
                    if isinstance(hand_dict, dict):
                        hand_strength = hand_dict.get('strength')
                    elif isinstance(hand_dict, (int, float)):
                        hand_strength = int(hand_dict)
                    
                    # Se hand_strength não está disponível no hand_info, tenta calcular usando HandEvaluator
                    # APENAS se tiver as cartas necessárias
                    if hand_strength is None and hand_evaluator and hole_cards and len(hole_cards) >= 2 and community_cards:
                        try:
                            hand_strength = hand_evaluator.evaluate(hole_cards, community_cards)
                        except Exception:
                            hand_strength = None
                    
                    # Obtém nome da mão APENAS se hand_strength estiver disponível
                    hand_name = None
                    if hand_strength is not None:
                        try:
                            from .hand_utils import score_to_hand_name
                            hand_name = score_to_hand_name(hand_strength)
                        except Exception:
                            pass
                    
                    result[player_uuid] = {
                        "hole_cards": hole_cards,
                        "hand": hand_name,
                        "hand_strength": hand_strength
                    }
        elif isinstance(hand_info, list):
            for item in hand_info:
                if not isinstance(item, dict):
                    continue
                
                player_uuid = item.get('uuid', '')
                if not player_uuid:
                    continue
                
                # Extrai hole_cards - tenta múltiplos formatos
                hole_cards_raw = item.get('hole_card') or item.get('hole_cards') or item.get('cards')
                hole_cards = normalize_hole_cards(hole_cards_raw) if hole_cards_raw else []
                
                # Se não encontrou cartas no hand_info, tenta obter do registry
                if not hole_cards and player_uuid:
                    hole_cards = get_player_cards(player_uuid) or []
                
                # Tenta obter hand_strength do hand_info (NÃO usa valores padrão)
                hand_strength = None
                hand_dict = item.get('hand', {})
                if isinstance(hand_dict, dict):
                    hand_strength = hand_dict.get('strength')
                elif isinstance(hand_dict, (int, float)):
                    hand_strength = int(hand_dict)
                
                # Se hand_strength não está disponível no hand_info, tenta calcular usando HandEvaluator
                # APENAS se tiver as cartas necessárias
                if hand_strength is None and hand_evaluator and hole_cards and len(hole_cards) >= 2 and community_cards:
                    try:
                        hand_strength = hand_evaluator.evaluate(hole_cards, community_cards)
                    except Exception:
                        hand_strength = None
                
                # Obtém nome da mão APENAS se hand_strength estiver disponível
                hand_name = None
                if hand_strength is not None:
                    try:
                        from .hand_utils import score_to_hand_name
                        hand_name = score_to_hand_name(hand_strength)
                    except Exception:
                        pass
                
                result[player_uuid] = {
                    "hole_cards": hole_cards,
                    "hand": hand_name,
                    "hand_strength": hand_strength
                }
        
        return result
    
    def _finalize_current_street(self):
        """Finaliza a street atual e adiciona ao round."""
        if self.current_street and self.current_round:
            self.current_round["streets"].append(self.current_street)
            self.current_street = None
            self.current_street_actions = []
    
    def _finalize_current_round(self):
        """Finaliza o round atual e adiciona ao histórico."""
        if self.current_round:
            self.history["rounds"].append(self.current_round)
            self.current_round = None
            self.current_street = None
            self.current_street_actions = []
    
    def save(self, filename: Optional[str] = None) -> str:
        """
        Salva histórico em arquivo JSON.
        
        Args:
            filename: Nome do arquivo (opcional, gera automaticamente se None)
        
        Returns:
            Caminho do arquivo salvo
        """
        # Finaliza round atual se existir
        if self.current_round:
            self._finalize_current_round()
        
        # Gera nome do arquivo se não fornecido
        if not filename:
            timestamp = self.start_time.strftime('%Y-%m-%d_%H-%M-%S')
            filename = f"game_{timestamp}_{self.game_id[:8]}.json"
        
        # Garante que é .json
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Salva arquivo
        filepath = get_history_path(filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
        
        return filepath

