"""
Calculadora de probabilidade de vitória para um jogador.
Usa simulação Monte Carlo para estimar chances de vitória.
Otimizado para velocidade e precisão com intervalo de confiança.
"""

import random
import math
import os
from typing import Optional
from datetime import datetime
try:
    from concurrent.futures import ProcessPoolExecutor, as_completed
    HAS_CONCURRENT = True
except ImportError:
    HAS_CONCURRENT = False
    ProcessPoolExecutor = None
from .cards_registry import get_all_cards
from .hand_utils import get_community_cards

# Tenta importar HandEvaluator, mas não é obrigatório
try:
    from .hand_evaluator import HandEvaluator
    HAS_POKERKIT = True
except ImportError:
    HAS_POKERKIT = False
    HandEvaluator = None

# Lazy loading do HandEvaluator (singleton)
_hand_evaluator_instance: Optional[HandEvaluator] = None

# Modo debug (pode ser ativado via variável de ambiente)
DEBUG_MODE = os.getenv('POKER_DEBUG_PROBABILITY', 'false').lower() == 'true'
DEBUG_LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'logs', 'probability_debug.log')

# Cria diretório de logs se não existir
if DEBUG_MODE:
    log_dir = os.path.dirname(DEBUG_LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)


def _get_hand_evaluator() -> Optional[HandEvaluator]:
    """
    Retorna instância singleton do HandEvaluator com lazy loading.
    Cria apenas quando necessário.
    """
    global _hand_evaluator_instance
    if _hand_evaluator_instance is None and HAS_POKERKIT and HandEvaluator:
        try:
            _hand_evaluator_instance = HandEvaluator()
        except Exception:
            return None
    return _hand_evaluator_instance


def _get_num_simulations_for_street(street):
    """Retorna número de simulações baseado na street.
    
    Otimizado para equilibrar velocidade e precisão:
    - Preflop: 2000 simulações (reduzido de 5000 para 2.5x mais rápido)
    - Flop: 2000 simulações (mantido para precisão)
    - Turn: 1500 simulações (reduzido de 2000)
    - River: 1000 simulações (mantido)
    
    Args:
        street: Street atual ('preflop', 'flop', 'turn', 'river')
    
    Returns:
        Número de simulações a realizar
    """
    street_simulations = {
        'preflop': 2000,  # Reduzido de 5000 para 2.5x mais rápido, ainda preciso
        'flop': 2000,     # Reduzido de 3000, mantém boa precisão
        'turn': 1500,     # Reduzido de 2000
        'river': 1000     # Mantido (máxima precisão com cartas conhecidas)
    }
    return street_simulations.get(street, 2000)  # Default: 2000 se street desconhecida


def _calculate_confidence_interval(wins, total_simulations, confidence_level=0.95):
    """Calcula intervalo de confiança para probabilidade de vitória.
    
    Usa aproximação normal para proporção binomial.
    
    Args:
        wins: Número de vitórias nas simulações
        total_simulations: Número total de simulações
        confidence_level: Nível de confiança (padrão: 0.95 = 95%)
    
    Returns:
        Tupla (probabilidade, margem_erro, min_prob, max_prob)
    """
    if total_simulations == 0:
        return (0.0, 0.0, 0.0, 0.0)
    
    # Probabilidade estimada
    p = wins / total_simulations
    
    # Z-score para nível de confiança (95% = 1.96)
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence_level, 1.96)
    
    # Margem de erro usando aproximação normal
    # margem = z * sqrt(p * (1-p) / n)
    if p > 0 and p < 1 and total_simulations > 1:
        margin = z * math.sqrt(p * (1 - p) / total_simulations)
    else:
        margin = 0.0
    
    # Intervalo de confiança
    min_prob = max(0.0, p - margin)
    max_prob = min(1.0, p + margin)
    
    return (p, margin, min_prob, max_prob)


def _debug_log(message, data=None):
    """Registra mensagem de debug no arquivo de log."""
    if not DEBUG_MODE:
        return
    
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] {message}"
        if data:
            log_entry += f" | {data}"
        log_entry += "\n"
        
        with open(DEBUG_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception:
        pass  # Silenciosamente ignora erros de logging


def _should_early_exit(wins, total_simulations, min_simulations=1000, target_margin=0.02):
    """
    Decide se deve parar a simulação early baseado na margem de erro.
    
    Args:
        wins: Número de vitórias até agora
        total_simulations: Número de simulações realizadas
        min_simulations: Número mínimo de simulações antes de considerar early exit
        target_margin: Margem de erro alvo (padrão: 2%)
    
    Returns:
        True se deve parar early, False caso contrário
    """
    if total_simulations < min_simulations:
        return False
    
    # Calcula margem de erro atual
    _, margin, _, _ = _calculate_confidence_interval(wins, total_simulations)
    
    # Para early se a margem de erro já está abaixo do alvo
    return margin <= target_margin


def _run_simulation_batch(args):
    """
    Executa um batch de simulações. Usado para paralelização.
    
    Args:
        args: Tupla com (batch_size, player_cards, community_cards, remaining_deck,
                         needed_community_cards, opponents)
    
    Returns:
        Número de vitórias neste batch
    """
    (batch_size, player_cards, community_cards, remaining_deck,
     needed_community_cards, opponents) = args
    
    # Cria HandEvaluator local para este processo/thread
    hand_evaluator = _get_hand_evaluator()
    if hand_evaluator is None:
        return 0
    
    wins = 0
    cards_needed_for_opponents = len(opponents) * 2
    
    for _ in range(batch_size):
        if needed_community_cards + cards_needed_for_opponents > len(remaining_deck):
            continue
        
        # Seleciona cartas
        selected_cards = random.sample(remaining_deck, needed_community_cards + cards_needed_for_opponents)
        
        # Completa cartas comunitárias
        simulated_community = list(community_cards)
        simulated_community.extend(selected_cards[:needed_community_cards])
        
        # Avalia mão do jogador
        player_score = hand_evaluator.evaluate(player_cards, simulated_community)
        
        # Verifica oponentes
        # IMPORTANTE: Sempre simula cartas dos oponentes aleatoriamente
        # Não conhecemos as cartas dos oponentes durante o jogo
        player_wins_round = True
        card_index = needed_community_cards
        
        for opponent_uuid in opponents:
            # Sempre distribui cartas aleatoriamente para cada oponente
            opponent_cards = selected_cards[card_index:card_index+2]
            card_index += 2
            
            opponent_score = hand_evaluator.evaluate(opponent_cards, simulated_community)
            
            if opponent_score < player_score:
                player_wins_round = False
                break
        
        if player_wins_round:
            wins += 1
    
    return wins


def calculate_win_probability_for_player(player_uuid, round_state, num_simulations=None, return_confidence=False, use_parallel=False, max_workers=None):
    """Calcula probabilidade de vitória para um jogador usando simulação Monte Carlo.
    
    Versão otimizada com melhor performance e suporte a intervalo de confiança.
    Suporta early exit adaptativo e paralelização opcional.
    
    Args:
        player_uuid: UUID do jogador
        round_state: Estado do round atual
        num_simulations: Número de simulações (padrão: calculado dinamicamente baseado na street)
        return_confidence: Se True, retorna dict com probabilidade e intervalo de confiança
        use_parallel: Se True, usa paralelização para acelerar simulações (padrão: False)
        max_workers: Número máximo de workers para paralelização (padrão: None = auto)
    
    Returns:
        Se return_confidence=False: Float entre 0.0 e 1.0 representando probabilidade de vitória, ou None se erro
        Se return_confidence=True: Dict com {'prob': float, 'min': float, 'max': float, 'margin': float} ou None
    """
    try:
        # Obtém cartas do jogador
        all_cards = get_all_cards()
        player_cards = all_cards.get(player_uuid)
        
        if not player_cards or len(player_cards) < 2:
            return None
        
        # Obtém cartas comunitárias já reveladas (padronizado)
        community_cards = get_community_cards(round_state)
        
        # Obtém street atual para calcular número de simulações
        street = round_state.get('street', 'preflop')
        
        # Obtém todos os jogadores ativos
        seats = round_state.get('seats', [])
        active_players = []
        for seat in seats:
            if isinstance(seat, dict):
                seat_uuid = seat.get('uuid', '')
                state = seat.get('state', '')
                # Jogadores ativos são aqueles que estão participando
                # (consistente com outros players que usam 'participating')
                if state == 'participating' and seat_uuid:
                    active_players.append(seat_uuid)
        
        if len(active_players) < 2:
            # Se só há um jogador ativo, ele ganha
            result = 1.0 if player_uuid in active_players else 0.0
            if return_confidence:
                return {
                    'prob': result,
                    'min': result,
                    'max': result,
                    'margin': 0.0
                }
            else:
                return result
        
        # Calcula número de simulações baseado na street (dinâmico)
        # Pre-flop: 5000, diminuindo até river: 1000
        if num_simulations is None:
            num_simulations = _get_num_simulations_for_street(street)
        
        # Obtém cartas conhecidas (do jogador + comunitárias)
        known_cards = set(player_cards + community_cards)
        
        # Gera deck completo (otimizado: gerado uma vez)
        suits = ['S', 'H', 'D', 'C']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        full_deck = [f"{suit}{rank}" for suit in suits for rank in ranks]
        
        # Remove cartas conhecidas do deck (otimizado: lista comprehension)
        remaining_deck = [card for card in full_deck if card not in known_cards]
        
        # Pré-calcula número de cartas necessárias para oponentes
        num_opponents = len(active_players) - 1  # Exclui o próprio jogador
        cards_needed_for_opponents = num_opponents * 2
        
        # Se não há cartas suficientes no deck, retorna None
        needed_community_cards = 5 - len(community_cards)
        total_cards_needed = needed_community_cards + cards_needed_for_opponents
        if len(remaining_deck) < total_cards_needed:
            return None
        
        # Se PokerKit não estiver disponível, retorna None (probabilidade não calculável)
        if not HAS_POKERKIT or not HandEvaluator:
            return None
        
        # Pré-filtra oponentes (exclui o próprio jogador uma vez)
        opponents = [uuid for uuid in active_players if uuid != player_uuid]
        
        # IMPORTANTE: NÃO usamos cartas conhecidas dos oponentes na simulação Monte Carlo
        # A simulação deve sempre distribuir cartas aleatoriamente dos oponentes,
        # pois no poker real não conhecemos as cartas dos oponentes durante o jogo.
        # O cards_registry é usado apenas para exibição no final do round.
        
        # Simula múltiplas rodadas (otimizado com early exit e paralelização opcional)
        wins = 0
        min_simulations = min(1000, num_simulations)  # Mínimo 1000 simulações
        target_margin = 0.02  # 2% de margem de erro alvo
        
        # Debug: estatísticas para análise
        debug_stats = {
            'opponent_three_of_kind': 0,
            'opponent_two_pair': 0,
            'opponent_one_pair_better': 0,
            'opponent_high_card_better': 0,
            'player_wins': 0
        } if DEBUG_MODE else None
        
        # Debug: registra início da simulação
        if DEBUG_MODE:
            _debug_log("=== INÍCIO SIMULAÇÃO MONTE CARLO ===", {
                'street': street,
                'player_cards': player_cards,
                'community_cards': community_cards,
                'num_opponents': len(opponents),
                'num_simulations': num_simulations,
                'min_simulations': min_simulations,
                'remaining_deck_size': len(remaining_deck),
                'opponent_cards_simulation': 'random',  # Sempre aleatório - não conhecemos cartas dos oponentes
                'remaining_4s': [c for c in remaining_deck if c[1] == '4']
            })
        
        if use_parallel and num_simulations >= 500 and HAS_CONCURRENT and ProcessPoolExecutor:
            # Paralelização: divide simulações em batches
            # Só usa se houver muitas simulações (overhead de paralelização)
            batch_size = max(100, num_simulations // (max_workers or 4))
            num_batches = (num_simulations + batch_size - 1) // batch_size
            
            try:
                with ProcessPoolExecutor(max_workers=max_workers) as executor:
                    batch_args = [
                        (min(batch_size, num_simulations - i * batch_size),
                         player_cards, community_cards, remaining_deck,
                         needed_community_cards, opponents)
                        for i in range(num_batches)
                    ]
                    
                    futures = [executor.submit(_run_simulation_batch, args) for args in batch_args]
                    
                    completed = 0
                    for future in as_completed(futures):
                        batch_wins = future.result()
                        wins += batch_wins
                        completed += 1
                        
                        # Early exit adaptativo: verifica após cada batch
                        if completed >= 2:  # Pelo menos 2 batches completos
                            current_sims = min(completed * batch_size, num_simulations)
                            if DEBUG_MODE and completed % 2 == 0:  # Log a cada 2 batches
                                prob = wins / current_sims if current_sims > 0 else 0
                                _, margin, min_prob, max_prob = _calculate_confidence_interval(wins, current_sims)
                                _debug_log("Progresso simulação (paralelo)", {
                                    'batches_completed': completed,
                                    'simulations': current_sims,
                                    'wins': wins,
                                    'prob': f"{prob:.4f}",
                                    'margin': f"{margin:.4f}",
                                    'interval': f"[{min_prob:.4f}, {max_prob:.4f}]"
                                })
                            if current_sims >= min_simulations:
                                if _should_early_exit(wins, current_sims, min_simulations, target_margin):
                                    if DEBUG_MODE:
                                        prob = wins / current_sims if current_sims > 0 else 0
                                        _, margin, min_prob, max_prob = _calculate_confidence_interval(wins, current_sims)
                                        _debug_log("EARLY EXIT ativado (paralelo)", {
                                            'simulations': current_sims,
                                            'wins': wins,
                                            'prob': f"{prob:.4f}",
                                            'margin': f"{margin:.4f}",
                                            'interval': f"[{min_prob:.4f}, {max_prob:.4f}]"
                                        })
                                    # Cancela batches restantes
                                    for f in futures:
                                        f.cancel()
                                    num_simulations = current_sims
                                    break
            except Exception:
                # Se paralelização falhar, usa método sequencial
                use_parallel = False
        
        if not use_parallel:
            # Método sequencial com early exit
            hand_evaluator = _get_hand_evaluator()
            if hand_evaluator is None:
                return None
            
            for simulation_num in range(num_simulations):
                if needed_community_cards + cards_needed_for_opponents > len(remaining_deck):
                    continue
                
                # Seleciona todas as cartas necessárias de uma vez
                selected_cards = random.sample(remaining_deck, needed_community_cards + cards_needed_for_opponents)
                
                # Completa cartas comunitárias
                simulated_community = list(community_cards)
                simulated_community.extend(selected_cards[:needed_community_cards])
                
                # Avalia mão do jogador
                player_score = hand_evaluator.evaluate(player_cards, simulated_community)
                
                # Verifica oponentes
                player_wins_round = True
                card_index = needed_community_cards
                
                for opponent_uuid in opponents:
                    # IMPORTANTE: Sempre simula cartas dos oponentes aleatoriamente
                    # Não conhecemos as cartas dos oponentes durante o jogo
                    opponent_cards = selected_cards[card_index:card_index+2]
                    card_index += 2
                    
                    opponent_score = hand_evaluator.evaluate(opponent_cards, simulated_community)
                    
                    if opponent_score < player_score:
                        player_wins_round = False
                        # Debug: conta tipos de derrotas
                        if DEBUG_MODE:
                            from .hand_utils import score_to_hand_name
                            opponent_hand = score_to_hand_name(opponent_score)
                            if 'Three of a Kind' in opponent_hand:
                                debug_stats['opponent_three_of_kind'] += 1
                            elif 'Two Pair' in opponent_hand:
                                debug_stats['opponent_two_pair'] += 1
                            elif 'One Pair' in opponent_hand:
                                debug_stats['opponent_one_pair_better'] += 1
                            else:
                                debug_stats['opponent_high_card_better'] += 1
                            
                            # Registra casos especiais (apenas primeiras 10 simulações)
                            if simulation_num < 10:
                                player_hand = score_to_hand_name(player_score)
                                _debug_log(f"Simulação {simulation_num + 1}: Oponente vence", {
                                    'opponent_cards': opponent_cards,
                                    'opponent_hand': opponent_hand,
                                    'opponent_score': opponent_score,
                                    'player_hand': player_hand,
                                    'player_score': player_score
                                })
                        break
                
                if player_wins_round:
                    wins += 1
                    if DEBUG_MODE:
                        debug_stats['player_wins'] += 1
                
                # Early exit: verifica a cada 50 iterações
                if (simulation_num + 1) >= min_simulations and (simulation_num + 1) % 50 == 0:
                    should_exit = _should_early_exit(wins, simulation_num + 1, min_simulations, target_margin)
                    if DEBUG_MODE and (simulation_num + 1) % 200 == 0:  # Log a cada 200 simulações
                        prob = wins / (simulation_num + 1)
                        _, margin, min_prob, max_prob = _calculate_confidence_interval(wins, simulation_num + 1)
                        _debug_log("Progresso simulação", {
                            'simulations': simulation_num + 1,
                            'wins': wins,
                            'prob': f"{prob:.4f}",
                            'margin': f"{margin:.4f}",
                            'interval': f"[{min_prob:.4f}, {max_prob:.4f}]"
                        })
                    if should_exit:
                        if DEBUG_MODE:
                            prob = wins / (simulation_num + 1)
                            _, margin, min_prob, max_prob = _calculate_confidence_interval(wins, simulation_num + 1)
                            _debug_log("EARLY EXIT ativado", {
                                'simulations': simulation_num + 1,
                                'wins': wins,
                                'prob': f"{prob:.4f}",
                                'margin': f"{margin:.4f}",
                                'interval': f"[{min_prob:.4f}, {max_prob:.4f}]"
                            })
                        num_simulations = simulation_num + 1
                        break
        
        # Calcula probabilidade e intervalo de confiança
        if num_simulations == 0:
            result = 0.0
            confidence_data = (0.0, 0.0, 0.0, 0.0)
        else:
            result = wins / num_simulations
            confidence_data = _calculate_confidence_interval(wins, num_simulations)
        
        # Debug: registra resultado final
        if DEBUG_MODE:
            prob, margin, min_prob, max_prob = confidence_data
            
            # Obtém nome da mão do jogador para análise
            player_hand_name = "Unknown"
            try:
                from .hand_utils import score_to_hand_name
                if community_cards:
                    player_score_temp = _get_hand_evaluator().evaluate(player_cards, community_cards)
                    player_hand_name = score_to_hand_name(player_score_temp)
                else:
                    # Preflop - apenas verifica se tem par
                    if player_cards[0][1] == player_cards[1][1]:
                        player_hand_name = "One Pair"
                    else:
                        player_hand_name = "High Card"
            except Exception:
                pass
            
            log_data = {
                'total_simulations': num_simulations,
                'wins': wins,
                'prob': f"{prob:.4f} ({prob*100:.2f}%)",
                'margin': f"{margin:.4f}",
                'interval': f"[{min_prob:.4f}, {max_prob:.4f}]",
                'early_exit': num_simulations < _get_num_simulations_for_street(street),
                'player_hand': player_hand_name,
                'num_opponents': len(opponents)
            }
            
            # Aviso se probabilidade for 100% (não deveria acontecer com simulação correta)
            if prob >= 0.9999:
                log_data['warning'] = 'Probabilidade 100% detectada - verifique se há problema na simulação'
            
            if debug_stats:
                log_data['debug_stats'] = debug_stats
                # Adiciona estatísticas de distribuição de mãos dos oponentes
                total_defeats = (debug_stats.get('opponent_three_of_kind', 0) + 
                                debug_stats.get('opponent_two_pair', 0) +
                                debug_stats.get('opponent_one_pair_better', 0) +
                                debug_stats.get('opponent_high_card_better', 0))
                if total_defeats > 0:
                    log_data['opponent_hand_distribution'] = {
                        'three_of_kind_pct': f"{(debug_stats.get('opponent_three_of_kind', 0) / total_defeats * 100):.1f}%",
                        'two_pair_pct': f"{(debug_stats.get('opponent_two_pair', 0) / total_defeats * 100):.1f}%",
                        'one_pair_better_pct': f"{(debug_stats.get('opponent_one_pair_better', 0) / total_defeats * 100):.1f}%",
                        'high_card_better_pct': f"{(debug_stats.get('opponent_high_card_better', 0) / total_defeats * 100):.1f}%"
                    }
            
            _debug_log("=== RESULTADO FINAL SIMULAÇÃO ===", log_data)
            _debug_log("", None)  # Linha em branco para separar
        
        # Retorna resultado baseado no parâmetro return_confidence
        if return_confidence:
            prob, margin, min_prob, max_prob = confidence_data
            return {
                'prob': prob,
                'min': min_prob,
                'max': max_prob,
                'margin': margin
            }
        else:
            return result
        
    except Exception as e:
        # Em caso de erro, retorna None silenciosamente
        # (não deve quebrar o jogo)
        return None

