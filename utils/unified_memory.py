"""
Módulo compartilhado para estrutura de memória unificada dos bots.

Todos os bots usam a mesma estrutura de memória, diferenciando-se apenas
nos valores iniciais e na forma como evoluem/aprendem.
"""

from typing import Dict, List, Optional, Any
from .memory_utils import get_memory_path
from .error_handling import safe_memory_save, safe_memory_load
from .hand_utils import normalize_hole_cards, evaluate_hand_strength


def create_default_memory(bluff_probability: float = 0.17, 
                         aggression_level: float = 0.55,
                         tightness_threshold: int = 27,
                         my_bot_name: str = None) -> Dict[str, Any]:
    """Cria estrutura de memória padrão unificada.
    
    Args:
        bluff_probability: Probabilidade inicial de blefe (0.15-0.20)
        aggression_level: Nível inicial de agressão (0.50-0.60)
        tightness_threshold: Threshold inicial de seletividade (25-30)
        my_bot_name: Nome do bot (para pré-registrar todos os outros bots)
    
    Returns:
        Dicionário com estrutura de memória padrão
    """
    memory = {
        'bluff_probability': bluff_probability,
        'aggression_level': aggression_level,
        'tightness_threshold': tightness_threshold,
        'total_rounds': 0,
        'wins': 0,
        'opponents': {},
        'round_history': []
    }
    
    # Pré-registra todos os bots conhecidos (exceto o próprio bot)
    if my_bot_name:
        from .uuid_utils import get_all_known_bot_names, get_bot_class_uuid_from_name
        all_bot_names = get_all_known_bot_names()
        my_uuid = get_bot_class_uuid_from_name(my_bot_name)
        
        for bot_name in all_bot_names:
            bot_uuid = get_bot_class_uuid_from_name(bot_name)
            if bot_uuid and bot_uuid != my_uuid:
                # Pré-registra o bot (será atualizado quando realmente jogar juntos)
                if bot_uuid not in memory['opponents']:
                    memory['opponents'][bot_uuid] = {
                        'name': bot_name,
                        'first_seen_round': 0,  # 0 indica que ainda não jogou juntos
                        'last_seen_round': 0,
                        'total_rounds_against': 0,
                        'rounds_against': [],
                        # Parâmetros específicos inicializados com valores globais
                        'bluff_probability': bluff_probability,
                        'aggression_level': aggression_level,
                        'tightness_threshold': tightness_threshold
                    }
    
    return memory


def register_new_opponent(memory: Dict[str, Any], opp_uuid: str, 
                          opp_name: str, current_round: int) -> None:
    """Registra novo oponente na memória.
    
    Args:
        memory: Estrutura de memória do bot
        opp_uuid: UUID do oponente
        opp_name: Nome do oponente
        current_round: Número do round atual
    """
    if opp_uuid not in memory['opponents']:
        # Inicializa parâmetros específicos com os valores globais atuais
        memory['opponents'][opp_uuid] = {
            'name': opp_name,
            'first_seen_round': current_round,
            'last_seen_round': current_round,
            'total_rounds_against': 0,
            'rounds_against': [],
            # Parâmetros específicos para este oponente (inicializados com valores globais)
            'bluff_probability': memory.get('bluff_probability', 0.17),
            'aggression_level': memory.get('aggression_level', 0.55),
            'tightness_threshold': memory.get('tightness_threshold', 27)
        }


def parse_hand_info(hand_info: Any, round_state: Dict[str, Any]) -> Dict[str, Any]:
    """Extrai hand_info em formato dicionário {uuid: info}.
    
    Args:
        hand_info: hand_info do PyPokerEngine (pode ser dict, list ou None)
        round_state: Estado do round
    
    Returns:
        Dicionário {uuid: hand_info_item}
    """
    hand_info_dict = {}
    
    if not hand_info:
        return hand_info_dict
    
    seats = round_state.get('seats', [])
    
    if isinstance(hand_info, dict):
        for key, value in hand_info.items():
            if isinstance(value, dict):
                uuid = value.get('uuid', key if isinstance(key, str) else None)
                if uuid:
                    hand_info_dict[uuid] = value
    elif isinstance(hand_info, list):
        for item in hand_info:
            if isinstance(item, dict):
                uuid = item.get('uuid', '')
                if uuid:
                    hand_info_dict[uuid] = item
                # Tenta encontrar UUID pelo nome se não tiver uuid
                elif 'name' in item:
                    for seat in seats:
                        if isinstance(seat, dict):
                            seat_name = seat.get('name', '').strip()
                            item_name = item.get('name', '').strip()
                            if seat_name and item_name and seat_name == item_name:
                                seat_uuid = seat.get('uuid', '')
                                if seat_uuid:
                                    hand_info_dict[seat_uuid] = item
                                break
    
    return hand_info_dict


def extract_hole_cards(hand_info_item: Dict[str, Any]) -> Optional[List[str]]:
    """Extrai hole_cards de um item do hand_info.
    
    Args:
        hand_info_item: Item do hand_info
    
    Returns:
        Lista de cartas normalizadas ou None
    """
    if isinstance(hand_info_item, dict):
        hole_card = hand_info_item.get('hole_card', None)
        if hole_card:
            return normalize_hole_cards(hole_card)
    return None


def record_opponent_round(memory: Dict[str, Any], opp_uuid: str,
                         round_number: int, opponent_actions: List[Dict[str, Any]],
                         reached_showdown: bool, hole_cards: Optional[List[str]],
                         hand_strength: Optional[int], opp_won: bool, i_won: bool,
                         community_cards: Optional[List[str]] = None) -> None:
    """Registra informações de um round contra um oponente.
    
    Args:
        memory: Estrutura de memória do bot
        opp_uuid: UUID do oponente
        round_number: Número do round
        opponent_actions: Lista de ações do oponente neste round
        reached_showdown: Se o oponente chegou ao showdown
        hole_cards: Cartas do oponente (se chegou ao showdown)
        hand_strength: Força da mão do oponente (se chegou ao showdown)
        opp_won: Se o oponente ganhou
        i_won: Se o bot ganhou
        community_cards: Cartas comunitárias (para análise)
    """
    if opp_uuid not in memory['opponents']:
        return
    
    opp = memory['opponents'][opp_uuid]
    
    # Análise simples baseada em observações
    analysis = None
    if reached_showdown and hole_cards and hand_strength is not None:
        # Se tinha mão ruim mas ganhou, pode ter sido blefe
        if hand_strength < 25 and opp_won:
            # Verifica se fez ações agressivas
            aggressive_actions = [a for a in opponent_actions if a.get('action') == 'raise']
            if len(aggressive_actions) > 0:
                analysis = "blefe_sucesso"
        # Se tinha mão boa mas perdeu
        elif hand_strength >= 50 and not opp_won:
            analysis = "mao_forte_perdeu"
        # Se tinha mão ruim e perdeu, mas fez ações agressivas
        elif hand_strength < 25 and not opp_won:
            aggressive_actions = [a for a in opponent_actions if a.get('action') == 'raise']
            if len(aggressive_actions) > 0:
                analysis = "blefe_falhou"
    
    # Cria entrada do round
    round_entry = {
        'round': round_number,
        'opponent_actions': opponent_actions.copy(),
        'reached_showdown': reached_showdown,
        'hole_cards': hole_cards.copy() if hole_cards else None,
        'hand_strength': hand_strength,
        'final_result': {
            'won_against_me': opp_won and not i_won,
            'i_won': i_won
        }
    }
    
    if analysis:
        round_entry['analysis'] = analysis
    
    # Adiciona ao histórico (mantém últimos 10 rounds)
    opp['rounds_against'].append(round_entry)
    if len(opp['rounds_against']) > 10:
        opp['rounds_against'] = opp['rounds_against'][-10:]
    
    # Atualiza estatísticas
    opp['last_seen_round'] = round_number
    opp['total_rounds_against'] += 1


def record_my_action(current_round_actions: List[Dict[str, Any]], street: str,
                     action: str, amount: int, hand_strength: int,
                     pot_size: int, active_players: int, was_bluff: bool) -> None:
    """Registra uma ação do bot durante o round.
    
    Args:
        current_round_actions: Lista de ações do round atual
        street: Street atual (preflop, flop, turn, river)
        action: Ação tomada (fold, call, raise)
        amount: Valor da ação
        hand_strength: Força da mão naquele momento
        pot_size: Tamanho do pot
        active_players: Número de jogadores ativos
        was_bluff: Se foi blefe
    """
    current_round_actions.append({
        'street': street,
        'action': action,
        'amount': amount,
        'hand_strength': hand_strength,
        'pot_size': pot_size,
        'active_players': active_players,
        'was_bluff': was_bluff,
        'result': None  # Será preenchido após o round
    })


def evaluate_action_result(action_record: Dict[str, Any], won: bool,
                          stack_change: int) -> str:
    """Avalia se uma ação foi boa, ruim ou neutra.
    
    Args:
        action_record: Registro da ação
        won: Se ganhou o round
        stack_change: Mudança no stack
    
    Returns:
        'good', 'bad' ou 'neutral'
    """
    if won:
        if action_record['action'] == 'raise' and not action_record['was_bluff']:
            return 'good'
        elif action_record['action'] == 'call' and action_record['hand_strength'] >= 40:
            return 'good'
        elif action_record['was_bluff']:
            return 'good'  # Blefe que funcionou
        else:
            return 'neutral'
    else:
        # Se perdeu, ações agressivas com mão fraca foram ruins
        if action_record['was_bluff']:
            return 'bad'  # Blefe que não funcionou
        elif action_record['action'] == 'raise' and action_record['hand_strength'] < 30:
            return 'bad'
        elif action_record['action'] == 'call' and action_record['hand_strength'] < 20:
            return 'bad'
        else:
            return 'neutral'


def learn_from_opponent_result(memory: Dict[str, Any], opp_uuid: str, 
                                i_won: bool, opp_won: bool,
                                learning_speed: float = 0.01,
                                win_rate_threshold_high: float = 0.6,
                                win_rate_threshold_low: float = 0.4) -> None:
    """Aprende e atualiza parâmetros específicos para um oponente baseado em resultados.
    
    Args:
        memory: Estrutura de memória do bot
        opp_uuid: UUID do oponente
        i_won: Se o bot ganhou o round
        opp_won: Se o oponente ganhou o round
        learning_speed: Velocidade de aprendizado (padrão 0.01 = 1%)
        win_rate_threshold_high: Taxa de vitória considerada alta (padrão 60%)
        win_rate_threshold_low: Taxa de vitória considerada baixa (padrão 40%)
    """
    if opp_uuid not in memory['opponents']:
        return
    
    opp = memory['opponents'][opp_uuid]
    
    # Garante que os parâmetros específicos existem
    if 'bluff_probability' not in opp:
        opp['bluff_probability'] = memory.get('bluff_probability', 0.17)
    if 'aggression_level' not in opp:
        opp['aggression_level'] = memory.get('aggression_level', 0.55)
    if 'tightness_threshold' not in opp:
        opp['tightness_threshold'] = memory.get('tightness_threshold', 27)
    
    # Calcula taxa de vitória contra este oponente (últimos 10 rounds)
    recent_rounds = opp.get('rounds_against', [])
    if len(recent_rounds) >= 5:  # Precisa de pelo menos 5 rounds para aprender
        wins_against = sum(
            1 for r in recent_rounds[-10:]
            if r.get('final_result', {}).get('i_won', False)
        )
        win_rate = wins_against / min(len(recent_rounds[-10:]), 10)
        
        learning_factor = 1 + learning_speed
        
        # Se está ganhando bem contra este oponente: aumenta agressão e blefe
        if win_rate > win_rate_threshold_high:
            opp['aggression_level'] = min(0.75, opp['aggression_level'] * learning_factor)
            opp['bluff_probability'] = min(0.22, opp['bluff_probability'] * learning_factor)
        # Se está perdendo contra este oponente: reduz agressão, aumenta seletividade
        elif win_rate < win_rate_threshold_low:
            opp['tightness_threshold'] = min(35, opp['tightness_threshold'] + 1)
            opp['aggression_level'] = max(0.35, opp['aggression_level'] / learning_factor)
            opp['bluff_probability'] = max(0.10, opp['bluff_probability'] / learning_factor)
    
    # Ajuste baseado no resultado do round atual
    if i_won and not opp_won:
        # Ganhou contra este oponente: pequeno boost em agressão
        opp['aggression_level'] = min(0.75, opp['aggression_level'] * (1 + learning_speed * 0.5))
    elif not i_won and opp_won:
        # Perdeu para este oponente: pequena redução em agressão
        opp['aggression_level'] = max(0.35, opp['aggression_level'] * (1 - learning_speed * 0.5))


def save_unified_memory(memory_file: str, memory: Dict[str, Any]) -> bool:
    """Salva memória unificada de forma segura.
    
    Args:
        memory_file: Caminho do arquivo de memória
        memory: Estrutura de memória
    
    Returns:
        True se salvou com sucesso
    """
    return safe_memory_save(memory_file, memory)


def load_unified_memory(memory_file: str, default_bluff: float = 0.17,
                       default_aggression: float = 0.55,
                       default_tightness: int = 27,
                       my_bot_name: str = None) -> Dict[str, Any]:
    """Carrega memória unificada de forma segura.
    
    Args:
        memory_file: Caminho do arquivo de memória
        default_bluff: Probabilidade padrão de blefe
        default_aggression: Nível padrão de agressão
        default_tightness: Threshold padrão de seletividade
        my_bot_name: Nome do bot (para pré-registrar todos os outros bots)
    
    Returns:
        Estrutura de memória carregada ou padrão
    """
    default_memory = create_default_memory(
        default_bluff, default_aggression, default_tightness, my_bot_name
    )
    loaded = safe_memory_load(memory_file, default_memory)
    
    # Garante que todos os campos obrigatórios existem
    if 'opponents' not in loaded:
        loaded['opponents'] = {}
    if 'round_history' not in loaded:
        loaded['round_history'] = []
    
    # Pré-registra todos os bots conhecidos que ainda não estão na memória
    if my_bot_name:
        from .uuid_utils import get_all_known_bot_names, get_bot_class_uuid_from_name
        all_bot_names = get_all_known_bot_names()
        my_uuid = get_bot_class_uuid_from_name(my_bot_name)
        
        for bot_name in all_bot_names:
            bot_uuid = get_bot_class_uuid_from_name(bot_name)
            if bot_uuid and bot_uuid != my_uuid:
                # Pré-registra o bot se ainda não estiver na memória
                if bot_uuid not in loaded['opponents']:
                    loaded['opponents'][bot_uuid] = {
                        'name': bot_name,
                        'first_seen_round': 0,  # 0 indica que ainda não jogou juntos
                        'last_seen_round': 0,
                        'total_rounds_against': 0,
                        'rounds_against': [],
                        # Parâmetros específicos inicializados com valores globais
                        'bluff_probability': loaded.get('bluff_probability', default_bluff),
                        'aggression_level': loaded.get('aggression_level', default_aggression),
                        'tightness_threshold': loaded.get('tightness_threshold', default_tightness)
                    }
                # Garante que bots existentes tenham os parâmetros específicos (migração)
                elif 'bluff_probability' not in loaded['opponents'][bot_uuid]:
                    loaded['opponents'][bot_uuid]['bluff_probability'] = loaded.get('bluff_probability', default_bluff)
                    loaded['opponents'][bot_uuid]['aggression_level'] = loaded.get('aggression_level', default_aggression)
                    loaded['opponents'][bot_uuid]['tightness_threshold'] = loaded.get('tightness_threshold', default_tightness)
    
    return loaded

