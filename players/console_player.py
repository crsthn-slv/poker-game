from typing import Tuple
import re
import os

from pypokerengine.players import BasePokerPlayer  # type: ignore[reportMissingImports]
from utils.console_formatter import ConsoleFormatter
from utils.cards_registry import store_player_cards, get_all_cards, clear_registry
from utils.win_probability_calculator import calculate_win_probability_for_player
from utils.hand_utils import get_community_cards, normalize_hole_cards
from utils.game_history import GameHistory


class QuitGameException(Exception):
    """Exceção levantada quando o jogador digita 'q' para sair."""
    pass


class ConsolePlayer(BasePokerPlayer):

    def __init__(self, input_receiver=None, initial_stack=100, small_blind=None, big_blind=None, show_win_probability=False):
        self.input_receiver = input_receiver if input_receiver else self.__gen_raw_input_wrapper()
        self.formatter = ConsoleFormatter()
        self.initial_stack = initial_stack
        self.small_blind = small_blind  # Blind pequeno (pode ser None)
        self.big_blind = big_blind  # Blind grande (pode ser None)
        self.show_win_probability = show_win_probability  # Se deve mostrar probabilidade de vitória
        self.last_pot_printed = 0  # Rastreia último pot impresso para evitar repetições
        self.pot_line_printed = False  # Indica se já imprimiu linha de pot atual
        self.pot_updates = []  # Lista de atualizações do pot para exibir na mesma linha
        self.my_hole_cards = None  # Cache das cartas do jogador atual
        self.players_hole_cards = {}  # Cache de cartas de todos os jogadores (UUID -> cartas)
        self.i_folded = False  # Flag para rastrear se o jogador deu fold no round atual
        # Cache de probabilidade de vitória: {cache_key: win_probability_data}
        self.win_probability_cache = {}
        self.last_cache_key = None  # Chave de cache usada na última vez
        self.preflop_active_count = None  # Número de jogadores ativos no preflop (para garantir estabilidade)
        # Sistema de histórico
        self.game_history = None  # Será inicializado quando UUID for definido
        self._player_name = None
    
    def set_uuid(self, uuid):
        """
        Define UUID fixo baseado no nome do jogador.
        Ignora o UUID do PyPokerEngine e usa UUID determinístico baseado no nome.
        Isso garante que o mesmo jogador sempre tenha o mesmo UUID.
        """
        # Por padrão, usa "You" como nome do jogador humano
        from utils.uuid_utils import get_player_uuid
        fixed_uuid = get_player_uuid("You")
        if fixed_uuid:
            self.uuid = fixed_uuid
            self._player_name = "You"
            debug_mode = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'
            if debug_mode:
                print(f"[DEBUG] ConsolePlayer UUID: PyPokerEngine={uuid} -> Fixed={fixed_uuid} (You)")
        else:
            # Fallback: usa UUID do PyPokerEngine se não conseguir gerar fixo
            self.uuid = uuid

    def _get_win_probability_cache_key(self, round_state):
        """Gera chave de cache baseada em street, número de jogadores ativos e cartas comunitárias.
        
        A probabilidade só muda quando:
        - A street muda (preflop -> flop -> turn -> river)
        - O número de jogadores ativos muda (alguém desiste/fold)
        - As cartas comunitárias mudam (que já acontece quando a street muda)
        
        IMPORTANTE: No preflop, a chave deve ser estável entre ações do mesmo round,
        mudando apenas quando alguém desiste (fold).
        
        Args:
            round_state: Estado do round atual
        
        Returns:
            str: Chave de cache única
        """
        street = round_state.get('street', 'preflop')
        
        # Conta jogadores ativos (participating) - apenas estes contam para probabilidade
        seats = round_state.get('seats', [])
        active_players_count = sum(
            1 for seat in seats
            if isinstance(seat, dict) and seat.get('state') == 'participating'
        )
        
        # Obtém cartas comunitárias (ordenadas para garantir consistência)
        community_cards = get_community_cards(round_state)
        community_cards_str = ','.join(sorted(community_cards)) if community_cards else ''
        
        # Gera chave única
        # No preflop, a chave deve ser estável: só muda quando número de jogadores muda
        cache_key = f"{street}:{active_players_count}:{community_cards_str}"
        return cache_key

    def declare_action(self, valid_actions, hole_card, round_state):
        """Exibe HUD completo fixo e solicita ação do jogador."""
        # Estrutura fixa minimalista do HUD
        
        print("\n–––– YOUR TURN ––––")
        
        # 1. Cartas do jogador com força da mão
        current_street = round_state.get('street', 'preflop')
        # Padroniza extração de cartas comunitárias
        community_cards = get_community_cards(round_state)
        
        # Normaliza hole_card para hole_cards (padronização)
        hole_cards = normalize_hole_cards(hole_card)
        
        # Atualiza cache das cartas do jogador
        # Obtém seats do round_state uma única vez
        seats = round_state.get('seats', [])
        
        if hole_cards:
            self.my_hole_cards = hole_cards
            # Tenta obter uuid para armazenar cartas no registry
            player_uuid_for_storage = None
            if hasattr(self, 'uuid') and self.uuid:
                player_uuid_for_storage = self.uuid
            else:
                # Fallback: tenta obter uuid do round_state
                for seat in seats:
                    if isinstance(seat, dict):
                        seat_hole_card = seat.get('hole_card', None)
                        if seat_hole_card:
                            seat_hole_cards = normalize_hole_cards(seat_hole_card)
                            if seat_hole_cards == hole_cards:
                                player_uuid_for_storage = seat.get('uuid')
                                # Armazena uuid para uso futuro
                                if not hasattr(self, 'uuid'):
                                    self.uuid = player_uuid_for_storage
                                break
            
            # Armazena cartas no registry se tiver uuid
            # IMPORTANTE: Usa UUID fixo (self.uuid já é fixo para ConsolePlayer)
            if player_uuid_for_storage:
                # Usa UUID fixo se disponível, senão usa o UUID do PyPokerEngine
                uuid_to_store = self.uuid if hasattr(self, 'uuid') and self.uuid else player_uuid_for_storage
                self.players_hole_cards[uuid_to_store] = hole_cards
                # Busca nome do jogador nos seats para mapear
                player_name = None
                if seats:
                    for seat in seats:
                        if isinstance(seat, dict) and seat.get('uuid') == player_uuid_for_storage:
                            player_name = seat.get('name', '')
                            break
                store_player_cards(uuid_to_store, hole_cards, player_name)
                import os
                if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
                    from utils.cards_registry import get_all_cards
                    all_cards_after = get_all_cards()
                    print(f"[DEBUG] Cartas armazenadas: uuid={player_uuid_for_storage}, hole_cards={hole_cards}, registry_has={player_uuid_for_storage in all_cards_after}")
        
        if hole_cards:
            cards_display = self.formatter.format_cards_display_with_color(hole_cards)
            hand_strength = self.formatter.get_hand_strength_heuristic(hole_cards, community_cards, current_street)
            # Calcula nível semântico da força da mão (educativo)
            hand_strength_level = self.formatter.get_hand_strength_level(hole_cards, community_cards)
            hand_strength_with_level = f"{hand_strength} [{hand_strength_level}]"
            
            # Calcula probabilidade de vitória usando simulação Monte Carlo
            # O cálculo simula múltiplas rodadas onde:
            # 1. Completa as cartas comunitárias faltantes aleatoriamente do deck restante
            # 2. Simula cartas dos oponentes (se não conhecidas) do deck restante
            # 3. Avalia todas as mãos usando PokerKit
            # 4. Conta quantas vezes o jogador venceu
            # 5. Retorna a porcentagem de vitórias (wins / num_simulations)
            # No preflop, mostra intervalo de confiança para indicar margem de erro
            # 
            # Cache: A probabilidade é calculada apenas quando a street muda ou o número
            # de jogadores ativos muda, para evitar recalcular a cada ação do jogador.
            win_probability = None
            win_probability_display = None
            
            # Só calcula probabilidade se estiver habilitado
            if self.show_win_probability:
                try:
                    import os
                    debug_mode = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'
                    
                    if debug_mode:
                        print(f"[DEBUG] Iniciando cálculo de probabilidade - hole_cards={hole_cards}, street={current_street}")
                    
                    # Tenta obter uuid do self primeiro, senão tenta obter do round_state
                    player_uuid = None
                    if hasattr(self, 'uuid') and self.uuid:
                        player_uuid = self.uuid
                        if debug_mode:
                            print(f"[DEBUG] UUID obtido de self.uuid: {player_uuid}")
                    else:
                        if debug_mode:
                            print(f"[DEBUG] self.uuid não disponível, tentando obter do round_state...")
                        # Fallback: tenta obter uuid do round_state procurando pelo jogador que tem as cartas
                        seats = round_state.get('seats', [])
                        for seat in seats:
                            if isinstance(seat, dict):
                                seat_hole_card = seat.get('hole_card', None)
                                # Se o seat tem as mesmas cartas que recebemos, é o nosso uuid
                                if seat_hole_card and hole_cards:
                                    seat_hole_cards = normalize_hole_cards(seat_hole_card)
                                    if seat_hole_cards == hole_cards:
                                        player_uuid = seat.get('uuid')
                                        if debug_mode:
                                            print(f"[DEBUG] UUID encontrado no round_state: {player_uuid}")
                                        # Armazena para uso futuro
                                        if not hasattr(self, 'uuid'):
                                            self.uuid = player_uuid
                                        break
                        if not player_uuid and debug_mode:
                            print(f"[DEBUG] UUID não encontrado no round_state!")
                    
                    if player_uuid:
                        if debug_mode:
                            print(f"[DEBUG] Calculando probabilidade para uuid={player_uuid}")
                        # Gera chave de cache
                        cache_key = self._get_win_probability_cache_key(round_state)
                        
                        # No preflop, garante que a probabilidade seja estável entre ações
                        # A probabilidade só deve mudar quando alguém desiste (fold)
                        if current_street == 'preflop':
                            seats = round_state.get('seats', [])
                            current_active_count = sum(
                                1 for seat in seats
                                if isinstance(seat, dict) and seat.get('state') == 'participating'
                            )
                            
                            # Se já temos um número de jogadores ativos registrado e não mudou,
                            # usa a chave de cache anterior (garante estabilidade)
                            if (self.preflop_active_count is not None and 
                                current_active_count == self.preflop_active_count and
                                self.last_cache_key and
                                self.last_cache_key in self.win_probability_cache):
                                cache_key = self.last_cache_key
                            else:
                                # Atualiza o número de jogadores ativos registrado
                                self.preflop_active_count = current_active_count
                        
                        # Verifica se já temos no cache
                        if cache_key in self.win_probability_cache:
                            # Usa valor do cache
                            cached_data = self.win_probability_cache[cache_key]
                            win_probability = cached_data.get('prob_pct')
                            win_probability_display = cached_data.get('display')
                            if debug_mode:
                                print(f"[DEBUG] Usando cache: {win_probability_display}")
                        else:
                            if debug_mode:
                                print(f"[DEBUG] Cache miss, calculando nova probabilidade...")
                            # Calcula nova probabilidade
                            # No preflop, retorna intervalo de confiança
                            if current_street == 'preflop':
                                if debug_mode:
                                    print(f"[DEBUG] Chamando calculate_win_probability_for_player (preflop)...")
                                win_prob_data = calculate_win_probability_for_player(
                                    player_uuid=player_uuid,
                                    round_state=round_state,
                                    return_confidence=True
                                )
                                if debug_mode:
                                    print(f"[DEBUG] Resultado: {win_prob_data}")
                                if win_prob_data is not None:
                                    # Formata intervalo de confiança (ex: 25-30%)
                                    min_pct = int(round(win_prob_data['min'] * 100))
                                    max_pct = int(round(win_prob_data['max'] * 100))
                                    win_probability = int(round(win_prob_data['prob'] * 100))
                                    win_probability_display = f"{min_pct}–{max_pct}%"
                                    if debug_mode:
                                        print(f"[DEBUG] Probabilidade formatada: {win_probability_display}")
                                    
                                    # Armazena no cache
                                    self.win_probability_cache[cache_key] = {
                                        'prob_pct': win_probability,
                                        'display': win_probability_display,
                                        'data': win_prob_data
                                    }
                                elif debug_mode:
                                    print(f"[DEBUG] calculate_win_probability_for_player retornou None!")
                            else:
                                # Em outras streets, mostra apenas o valor único
                                if debug_mode:
                                    print(f"[DEBUG] Chamando calculate_win_probability_for_player (street={current_street})...")
                                win_prob = calculate_win_probability_for_player(
                                    player_uuid=player_uuid,
                                    round_state=round_state,
                                    return_confidence=False
                                )
                                if debug_mode:
                                    print(f"[DEBUG] Resultado: {win_prob}")
                                if win_prob is not None:
                                    win_probability = int(round(win_prob * 100))
                                    win_probability_display = f"{win_probability}%"
                                    if debug_mode:
                                        print(f"[DEBUG] Probabilidade formatada: {win_probability_display}")
                                    
                                    # Armazena no cache
                                    self.win_probability_cache[cache_key] = {
                                        'prob_pct': win_probability,
                                        'display': win_probability_display,
                                        'data': {'prob': win_prob}
                                    }
                                elif debug_mode:
                                    print(f"[DEBUG] calculate_win_probability_for_player retornou None!")
                        
                        # Atualiza última chave usada
                        self.last_cache_key = cache_key
                    elif debug_mode:
                        print(f"[DEBUG] player_uuid é None, não calculando probabilidade")
                except Exception as e:
                    # Log de erro mais informativo
                    debug_mode = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'
                    if debug_mode:
                        print(f"[DEBUG] Erro ao calcular probabilidade: {type(e).__name__}: {e}")
                        import traceback
                        traceback.print_exc()
                    # Silenciosamente ignora erros no cálculo (não deve quebrar o jogo)
                    # win_probability_display será None e não será exibido
                    win_probability_display = None
            
            # Formata saída com probabilidade se disponível
            if win_probability_display is not None:
                print(f"Your cards: {cards_display} | Hand: {hand_strength_with_level} | Win probability: {win_probability_display}")
            else:
                # Log temporário para debug - sempre mostra se probabilidade não foi calculada
                import os
                if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
                    print(f"[DEBUG] win_probability_display é None - probabilidade não calculada")
                print(f"Your cards: {cards_display} | Hand: {hand_strength_with_level}")
        
        # 2. Cartas comunitárias (quando existirem)
        if community_cards:
            community_display = self.formatter.format_cards_display_with_color(community_cards)
            print(f"Community cards: {community_display}")
        
        # 3. Pot e stack do jogador apenas
        action_histories = round_state.get('action_histories', {})
        pot_amount, pot_composition = self.formatter.calculate_pot_composition(round_state, action_histories)
        
        seats = round_state.get('seats', [])
        my_stack = 0
        debug_mode = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'
        
        # Estratégia múltipla para encontrar o seat do jogador
        player_seat = None
        
        if debug_mode:
            print(f"\n[DEBUG] === Buscando seat do jogador ===")
            print(f"[DEBUG] self.uuid: {getattr(self, 'uuid', 'NÃO DEFINIDO')}")
            print(f"[DEBUG] self.initial_stack: {self.initial_stack}")
            print(f"[DEBUG] hole_cards: {hole_cards}")
            print(f"[DEBUG] Seats disponíveis ({len(seats)}):")
            for i, seat in enumerate(seats):
                if isinstance(seat, dict):
                    print(f"[DEBUG]   Seat {i}: name='{seat.get('name')}', uuid={seat.get('uuid')}, stack={seat.get('stack')}, state={seat.get('state')}")
                    if seat.get('hole_card'):
                        seat_cards = normalize_hole_cards(seat.get('hole_card'))
                        print(f"[DEBUG]     hole_card: {seat_cards}")
        
        # 1. Tenta encontrar pelo UUID
        if hasattr(self, 'uuid') and self.uuid:
            for seat in seats:
                if isinstance(seat, dict) and seat.get('uuid') == self.uuid:
                    player_seat = seat
                    if debug_mode:
                        print(f"[DEBUG] ✓ Seat encontrado pelo UUID: {self.uuid}")
                    break
        
        # 2. Se não encontrou, tenta pelo nome "You"
        if not player_seat:
            for seat in seats:
                if isinstance(seat, dict) and seat.get('name', '').lower() == 'you':
                    player_seat = seat
                    # Atualiza self.uuid se não estava definido
                    if not hasattr(self, 'uuid') or not self.uuid:
                        self.uuid = seat.get('uuid')
                        if debug_mode:
                            print(f"[DEBUG] ✓ UUID atualizado: {self.uuid}")
                    if debug_mode:
                        print(f"[DEBUG] ✓ Seat encontrado pelo nome 'You', UUID: {seat.get('uuid')}")
                    break
        
        # 3. Se ainda não encontrou, tenta pelas cartas (fallback)
        if not player_seat and hole_cards:
            for seat in seats:
                if isinstance(seat, dict):
                    seat_hole_card = seat.get('hole_card', None)
                    if seat_hole_card:
                        seat_hole_cards = normalize_hole_cards(seat_hole_card)
                        if seat_hole_cards == hole_cards:
                            player_seat = seat
                            # Atualiza self.uuid se não estava definido
                            if not hasattr(self, 'uuid') or not self.uuid:
                                self.uuid = seat.get('uuid')
                                if debug_mode:
                                    print(f"[DEBUG] ✓ UUID atualizado pelas cartas: {self.uuid}")
                            if debug_mode:
                                print(f"[DEBUG] ✓ Seat encontrado pelas cartas, UUID: {seat.get('uuid')}")
                            break
        
        # Obtém stack do seat encontrado
        if player_seat:
            my_stack = player_seat.get('stack', 0)
            if debug_mode:
                print(f"[DEBUG] ✓ Stack encontrado: {my_stack} (initial_stack: {self.initial_stack})")
                if my_stack == 0:
                    print(f"[DEBUG] ⚠️  ATENÇÃO: Stack é 0! Isso pode indicar um problema.")
        else:
            if debug_mode:
                print(f"[DEBUG] ❌ ERRO: Seat do jogador não encontrado!")
                print(f"[DEBUG] self.uuid: {getattr(self, 'uuid', 'NÃO DEFINIDO')}")
                print(f"[DEBUG] Tentou buscar por: UUID, nome 'You', e cartas")
            # Fallback: tenta usar o primeiro seat se houver apenas um (caso edge)
            if len(seats) == 1 and isinstance(seats[0], dict):
                player_seat = seats[0]
                my_stack = player_seat.get('stack', 0)
                if debug_mode:
                    print(f"[DEBUG] ⚠️  Fallback: usando único seat disponível, stack: {my_stack}")
        
        if debug_mode:
            print(f"[DEBUG] === Fim da busca ===\n")
        
        # IMPORTANTE: Jogador com 0 fichas não pode fazer ações (apenas fold)
        # Mas jogador com stack baixo (> 0) pode continuar jogando normalmente
        # O PyPokerEngine tratará all-in parcial automaticamente quando necessário
        if my_stack == 0:
            print(f"\n⚠️  Você foi eliminado (0 fichas). Apenas FOLD disponível.")
            # Força fold automaticamente
            return 'fold', 0
        
        # NOTA: Jogador com stack baixo (> 0) continua jogando normalmente
        # - Se tentar fazer CALL/RAISE com stack insuficiente, será all-in parcial
        # - Side pots serão criados automaticamente pelo PyPokerEngine
        # - Não há eliminação durante a mão atual, mesmo com stack muito baixo
        
        # Mostra pot atualizado
        pot_display = self.formatter.format_pot_with_color(pot_amount)
        stack_display = self.formatter.format_stack_with_color(my_stack, self.initial_stack, is_current=True)
        print(f"Pot {pot_display} | Your chips {stack_display}")
        
        # Atualiza último pot impresso
        self.last_pot_printed = pot_amount
        
        # 5. Tabela de status dos jogadores e histórico
        status_table = self.formatter.format_player_status_table(round_state, action_histories, current_street, valid_actions)
        if status_table:
            print(status_table)
        
        # 6. Ações disponíveis com prefixos [f], [c], [r] numa única linha
        # Passa round_state e player_uuid para calcular valor adicional de call corretamente
        player_uuid_for_call = None
        if hasattr(self, 'uuid') and self.uuid:
            player_uuid_for_call = self.uuid
        actions_display = self.formatter.format_action_costs(valid_actions, round_state, player_uuid_for_call)
        # Mapeia ações por tipo para garantir correspondência correta
        # IMPORTANTE: Raise sempre aparece, mas pode estar esmaecido quando não disponível
        action_map = {}
        display_index = 0
        for action_data in valid_actions:
            action_type = action_data.get('action', '')
            if action_type == 'fold':
                action_map['f'] = {'index': display_index, 'available': True}
                display_index += 1
            elif action_type == 'call':
                action_map['c'] = {'index': display_index, 'available': True}
                display_index += 1
            elif action_type == 'raise':
                # Verifica se raise é possível
                raise_amount = action_data.get('amount', {})
                is_available = False
                if isinstance(raise_amount, dict):
                    min_raise = raise_amount.get('min', -1)
                    is_available = (min_raise >= 0)
                elif isinstance(raise_amount, (int, float)) and raise_amount > 0:
                    is_available = True
                # Sempre adiciona raise ao mapa, mesmo se não disponível
                action_map['r'] = {'index': display_index, 'available': is_available}
                display_index += 1
        
        action_line_parts = []
        action_prefix_order = ['f', 'c', 'r']
        
        for prefix in action_prefix_order:
            if prefix in action_map:
                action_info = action_map[prefix]
                idx = action_info['index']
                is_available = action_info['available']
                
                if idx < len(actions_display):
                    action_text, action_available = actions_display[idx]
                    # Se a ação não está disponível, aplica formatação esmaecida
                    if not action_available or not is_available:
                        dimmed_text = f"{self.formatter.DIM}[{prefix}] {action_text}{self.formatter.RESET}"
                        action_line_parts.append(dimmed_text)
                    else:
                        action_line_parts.append(f"[{prefix}] {action_text}")
        
        # Adiciona All In sempre disponível (é sempre a última ação na lista)
        if actions_display:
            all_in_text = actions_display[-1][0]  # All In é sempre o último
            action_line_parts.append(f"[a] {all_in_text}")
        
        # Adiciona opção de sair
        action_line_parts.append("[q] Quit")
        
        if action_line_parts:
            print(f"Available actions: {' | '.join(action_line_parts)}")
        
        
        # Solicitar ação - passa round_state E player_stack para permitir all-in correto
        # IMPORTANTE: Passa o stack que foi calculado e exibido ao usuário para garantir consistência
        print()
        action, amount = self.__receive_action_from_console(valid_actions, round_state, my_stack)  # type: ignore[assignment]

        
        # Marca se o jogador deu fold
        if action == 'fold':
            self.i_folded = True
        else:
            self.i_folded = False
        
        # Registra ação no histórico
        if self.game_history and hasattr(self, 'uuid') and self.uuid:
            # Obtém probabilidade de vitória se disponível
            win_prob = None
            if win_probability_display is not None:
                # Tenta extrair valor numérico da probabilidade
                try:
                    if '-' in win_probability_display:
                        # Intervalo de confiança (ex: "25–30%")
                        parts = win_probability_display.replace('%', '').split('–')
                        if len(parts) == 2:
                            win_prob = (float(parts[0]) + float(parts[1])) / 2 / 100
                    else:
                        # Valor único (ex: "45%")
                        win_prob = float(win_probability_display.replace('%', '')) / 100
                except (ValueError, AttributeError):
                    pass
            
            # Sanitiza round_state para usar UUIDs fixos
            sanitized_round_state = self._sanitize_round_state(round_state)
            
            self.game_history.record_action(
                player_uuid=self.uuid,
                action=action,
                amount=amount,
                round_state=sanitized_round_state,
                my_hole_cards=hole_cards if hole_cards else None,
                my_win_probability=win_prob
            )
        
        return action, amount

    def receive_game_start_message(self, game_info):
        """Não imprime nada (ou apenas linha inicial mínima)."""
        # Silencioso - HUD será mostrado no turno do jogador
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        # Reseta flag de linha de pot no início de novo round
        self.pot_line_printed = False
        """Mostra divisor de round e inicializa novo round."""
        
        # UUID é sempre fixo, não precisa de atualização
        # Mostra divisor de round de forma destacada
        print("\n" + self.formatter.format_round_divider(round_count))
        print()
        
        # Reseta pot impresso para novo round
        self.last_pot_printed = 0
        self.pot_line_printed = False  # Reseta flag de linha de pot
        self.pot_updates = []  # Limpa atualizações acumuladas do pot
        # Limpa todos os caches para novo round
        self._clear_all_caches()
        # Limpa registro de cartas do round anterior
        clear_registry()
        # Armazena cartas do jogador em cache e no registro global
        # UUID é sempre fixo
        if hole_card:
            hole_cards = normalize_hole_cards(hole_card)
            self.my_hole_cards = hole_cards
            if hasattr(self, 'uuid') and self.uuid:
                self.players_hole_cards[self.uuid] = hole_cards
                store_player_cards(self.uuid, hole_cards, self._player_name)
        # Tenta obter cartas dos outros jogadores dos seats se disponíveis
        # Nota: PyPokerEngine geralmente não fornece cartas dos oponentes aqui,
        # mas tentamos capturar se estiverem disponíveis
        # IMPORTANTE: Armazena com UUID fixo para garantir consistência
        if seats:
            for seat in seats:
                if isinstance(seat, dict):
                    seat_uuid = seat.get('uuid', '')
                    seat_hole_cards = seat.get('hole_card', None)
                    if seat_uuid and seat_hole_cards:
                        # Normaliza as cartas antes de armazenar
                        normalized_cards = normalize_hole_cards(seat_hole_cards)
                        if normalized_cards:
                            # Mapeia para UUID fixo antes de armazenar
                            fixed_uuid = self._get_fixed_uuid_from_seat(seat, False)
                            uuid_to_store = fixed_uuid if fixed_uuid else seat_uuid
                            self.players_hole_cards[uuid_to_store] = normalized_cards
                            store_player_cards(uuid_to_store, normalized_cards)
        
        # Garante que histórico está inicializado
        self._ensure_game_history_initialized(seats)
        
        # Inicia novo round no histórico
        if self.game_history and seats:
            # Tenta encontrar posição do botão (geralmente é o primeiro seat ou pode ser calculado)
            button_position = 0  # Default, pode ser ajustado se houver informação disponível
            
            # Sanitiza seats para usar UUIDs fixos no histórico
            sanitized_seats = []
            for seat in seats:
                if isinstance(seat, dict):
                    sanitized_seat = seat.copy()
                    fixed_uuid = self._get_fixed_uuid_from_seat(seat, False)
                    if fixed_uuid:
                        sanitized_seat['uuid'] = fixed_uuid
                    sanitized_seats.append(sanitized_seat)
                else:
                    sanitized_seats.append(seat)
            
            self.game_history.start_round(round_count, sanitized_seats, button_position)
        
        # Reseta flag de fold no início de cada round
        self.i_folded = False
        pass

    def receive_street_start_message(self, street, round_state):
        """Imprime bloco novo para nova street sem repetir dados estáticos."""
        street_pt = self.formatter.format_street_pt(street)
        if street_pt:
            print(f"\n–– {street_pt.upper()} ––")
        else:
            print(f"\n–– {street.upper() if street else 'UNKNOWN'} ––")
        
        # Limpa cache de probabilidade quando a street muda
        # (a probabilidade mudará porque as cartas comunitárias mudaram)
        self.win_probability_cache = {}
        self.last_cache_key = None
        # Reseta contador de jogadores ativos no preflop quando a street muda
        if street != 'preflop':
            self.preflop_active_count = None
        
        # Mostra apenas cartas comunitárias se existirem
        community_cards = get_community_cards(round_state)
        if community_cards:
            community_display = self.formatter.format_cards_display_with_color(community_cards)
            print(f"Community cards: {community_display}")
        
        # Mostra pot apenas quando a street muda
        # Se já tinha pot na linha anterior, quebra linha antes de nova street
        if self.pot_line_printed:
            # Se há atualizações acumuladas do pot, exibe todas antes de quebrar linha
            if self.pot_updates:
                pot_line = " -> ".join([f"Pot {p}" for p in self.pot_updates])
                print(pot_line)  # Quebra linha após mostrar todas as atualizações
            else:
                print()  # Quebra linha
            self.pot_line_printed = False
        
        # Limpa atualizações acumuladas e inicia nova lista para a nova street
        self.pot_updates = []
        
        action_histories = round_state.get('action_histories', {})
        pot_amount, _ = self.formatter.calculate_pot_composition(round_state, action_histories)
        pot_display = self.formatter.format_pot_with_color(pot_amount)
        # Adiciona à lista de atualizações
        self.pot_updates.append(pot_display)
        self.last_pot_printed = pot_amount
        
        # Exibe pot inicial da street (sem quebrar linha)
        print(f"Pot {pot_display}", end='', flush=True)
        self.pot_line_printed = True  # Marca que pot está na linha atual
        
        # Registra início de nova street no histórico
        if self.game_history:
            # Sanitiza round_state para usar UUIDs fixos
            sanitized_round_state = self._sanitize_round_state(round_state)
            self.game_history.start_street(street, sanitized_round_state)

    def receive_game_update_message(self, new_action, round_state):
        """Exibe apenas quem agiu e a ação, de forma simplificada."""
        if not isinstance(new_action, dict):
            return
        
        # Quem agiu
        player_name = self.formatter.clean_player_name(new_action.get('player', ''))
        action_type = new_action.get('action', '')
        
        # Formata ação em inglês
        action_names = {
            'SMALLBLIND': 'SB',
            'BIGBLIND': 'BB',
            'FOLD': 'folded',
            'CALL': 'called' if new_action.get('paid', 0) > 0 else 'checked',
            'RAISE': 'raised',
            'CHECK': 'checked'
        }
        action_name = action_names.get(action_type, action_type.lower())
        
        # Montante
        amount = new_action.get('amount', 0)
        paid = new_action.get('paid', 0)
        
        # Detecta all-in: verifica se o jogador tem stack 0 após esta ação
        is_all_in = False
        if round_state:
            seats = round_state.get('seats', [])
            action_uuid = new_action.get('uuid')
            if action_uuid:
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('uuid') == action_uuid:
                        current_stack = seat.get('stack', 0)
                        # Se o stack é 0 após CALL ou RAISE, é all-in
                        if current_stack == 0 and action_type in ['CALL', 'RAISE']:
                            is_all_in = True
                        break
        
        # Formata ação de forma compacta
        action_parts = []
        
        # Se o jogador fez fold, torna o nome opaco
        if action_type == 'FOLD':
            dim_name = f"{self.formatter.DIM}{player_name}{self.formatter.RESET}"
            action_parts.append(f"{dim_name} {action_name}")
        # Ação básica
        elif action_type in ['SMALLBLIND', 'BIGBLIND']:
            action_parts.append(f"{player_name} {action_name} {amount}")
        elif action_type == 'CALL':
            if paid > 0:
                if is_all_in:
                    action_parts.append(f"{player_name} all-in({paid})")
                else:
                    action_parts.append(f"{player_name} {action_name} {paid}")
            else:
                action_parts.append(f"{player_name} {action_name}")
        elif action_type == 'RAISE':
            if is_all_in:
                action_parts.append(f"{player_name} all-in({amount})")
            else:
                action_parts.append(f"{player_name} {action_name} {amount}")
        elif action_type == 'CHECK':
            action_parts.append(f"{player_name} {action_name}")
        
        # Imprime ações primeiro (se houver)
        if action_parts:
            # Se já tinha pot na linha, quebra linha antes das ações
            if self.pot_line_printed:
                # Se há atualizações acumuladas do pot, exibe todas antes de quebrar linha
                if self.pot_updates:
                    pot_line = " -> ".join([f"Pot {p}" for p in self.pot_updates])
                    print(pot_line)  # Quebra linha após mostrar todas as atualizações
                    self.pot_updates = []  # Limpa após exibir
                else:
                    print()  # Quebra linha
                self.pot_line_printed = False
            print(" | ".join(action_parts))
        
        # Atualiza pot na mesma linha (sempre que mudar)
        pot = round_state.get('pot', {}).get('main', {}).get('amount', 0) if isinstance(round_state.get('pot'), dict) else 0
        if pot > 0 and pot != self.last_pot_printed:
            pot_display = self.formatter.format_pot_with_color(pot)
            # Adiciona à lista de atualizações
            self.pot_updates.append(pot_display)
            self.last_pot_printed = pot
            
            # Exibe atualização na mesma linha
            if self.pot_line_printed:
                # Continua na mesma linha, adicionando mais atualizações
                print(f" -> Pot {pot_display}", end='', flush=True)
            else:
                # Primeira vez, imprime todas as atualizações acumuladas (sem quebrar linha)
                pot_line = " -> ".join([f"Pot {p}" for p in self.pot_updates])
                print(f"{pot_line}", end='', flush=True)
                self.pot_line_printed = True
        
        # Registra ação no histórico (de outros jogadores)
        if self.game_history:
            import os
            debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
            
            # Obtém UUID do PyPokerEngine da ação
            pypoker_uuid = new_action.get('player_uuid')
            
            if debug_mode:
                print(f"[HISTORY DEBUG] pypoker_uuid from new_action: {pypoker_uuid[:8] if pypoker_uuid else 'None'}")
            
            # Encontra o seat correspondente e converte para UUID fixo
            fixed_player_uuid = None
            seat_name = 'Unknown'
            seats = round_state.get('seats', [])
            
            if pypoker_uuid:
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('uuid') == pypoker_uuid:
                        # Converte para UUID fixo
                        fixed_player_uuid = self._get_fixed_uuid_from_seat(seat, False)
                        seat_name = seat.get('name', 'Unknown')
                        if debug_mode:
                            print(f"[HISTORY DEBUG] ✓ Found seat: name='{seat_name}', fixed_uuid={fixed_player_uuid[:8] if fixed_player_uuid else 'None'}")
                        break
            
            if not fixed_player_uuid and debug_mode:
                print(f"[HISTORY DEBUG] ❌ Could not find seat for pypoker_uuid: {pypoker_uuid[:8] if pypoker_uuid else 'None'}")
                print(f"[HISTORY DEBUG] Available seats:")
                for i, seat in enumerate(seats):
                    if isinstance(seat, dict):
                        print(f"[HISTORY DEBUG]   Seat {i}: uuid={seat.get('uuid', '')[:8] if seat.get('uuid') else 'None'}, name='{seat.get('name', '')}'")
            
            if fixed_player_uuid:
                # Usa 'paid' para CALL, 'amount' para outras ações
                action_amount = paid if action_type == 'CALL' and paid > 0 else amount
                
                # Evita duplicidade: se a ação for do próprio jogador (Hero), ignora
                # pois já foi registrada em declare_action com mais detalhes (win_prob, etc)
                if hasattr(self, 'uuid') and self.uuid and fixed_player_uuid == self.uuid:
                    if debug_mode:
                        print(f"[HISTORY] Skipping duplicate Hero action in update: {action_type} {action_amount}")
                else:
                    # Sanitiza round_state para usar UUIDs fixos
                    sanitized_round_state = self._sanitize_round_state(round_state)
                    
                    self.game_history.record_action(
                        player_uuid=fixed_player_uuid,
                        action=action_type,
                        amount=action_amount,
                        round_state=sanitized_round_state
                    )
                    
                    if debug_mode:
                        print(f"[HISTORY] Recorded action: {seat_name} ({fixed_player_uuid[:8]}) {action_type} {action_amount}")
            else:
                # Se não conseguiu obter UUID, loga warning
                if debug_mode:
                    print(f"[HISTORY] WARNING: Could not resolve UUID for player {seat_name}, action not recorded")
                
                # Atualiza configurações de blinds se detectar SMALLBLIND ou BIGBLIND
                # Melhorado: captura de qualquer jogador e atualiza se necessário
                if action_type == 'SMALLBLIND' and amount > 0:
                    # Só atualiza se ainda não foi definido ou se o valor é maior (blind structure)
                    current_sb = self.game_history.history["game_config"]["small_blind"]
                    if current_sb == 0 or amount > current_sb:
                        self.game_history.history["game_config"]["small_blind"] = amount
                elif action_type == 'BIGBLIND' and amount > 0:
                    # Só atualiza se ainda não foi definido ou se o valor é maior (blind structure)
                    current_bb = self.game_history.history["game_config"]["big_blind"]
                    if current_bb == 0 or amount > current_bb:
                        self.game_history.history["game_config"]["big_blind"] = amount

    def _get_fixed_uuid_from_seat(self, seat, debug_mode=False):
        """
        Mapeia UUID do PyPokerEngine para UUID fixo usando o nome do jogador.
        
        Args:
            seat: Dict com informações do seat (deve ter 'name' e 'uuid')
            debug_mode: Se True, imprime debug
        
        Returns:
            UUID fixo se encontrado, senão retorna o UUID original
        """
        if not isinstance(seat, dict):
            return None
        
        seat_name = seat.get('name', '')
        seat_uuid_pypoker = seat.get('uuid', '')
        
        if not seat_name:
            return seat_uuid_pypoker
        
        from utils.uuid_utils import get_bot_class_uuid_from_name, get_player_uuid
        
        # Tenta UUID fixo do bot primeiro
        fixed_uuid = get_bot_class_uuid_from_name(seat_name)
        if fixed_uuid:
            if debug_mode:
                print(f"[DEBUG]   UUID mapeado: {seat_uuid_pypoker} -> {fixed_uuid} (bot: {seat_name})")
            return fixed_uuid
        
        # Se não encontrou, tenta UUID fixo do jogador humano
        player_fixed_uuid = get_player_uuid(seat_name)
        if player_fixed_uuid:
            if debug_mode:
                print(f"[DEBUG]   UUID mapeado: {seat_uuid_pypoker} -> {player_fixed_uuid} (jogador: {seat_name})")
            return player_fixed_uuid
        
        # Se não encontrou nenhum, retorna UUID original (pode ser jogador sem nome fixo)
        if debug_mode:
            print(f"[DEBUG]   UUID não mapeado (mantendo original): {seat_uuid_pypoker}")
        return seat_uuid_pypoker

    def _sanitize_round_state(self, round_state):
        """
        Cria uma cópia do round_state com todos os UUIDs de seats convertidos para UUIDs fixos.
        Isso garante consistência no histórico.
        """
        if not round_state or not isinstance(round_state, dict):
            return round_state
            
        sanitized = round_state.copy()
        seats = round_state.get('seats', [])
        
        if seats:
            sanitized_seats = []
            for seat in seats:
                if isinstance(seat, dict):
                    sanitized_seat = seat.copy()
                    fixed_uuid = self._get_fixed_uuid_from_seat(seat, False)
                    if fixed_uuid:
                        sanitized_seat['uuid'] = fixed_uuid
                    sanitized_seats.append(sanitized_seat)
                else:
                    sanitized_seats.append(seat)
            sanitized['seats'] = sanitized_seats
            
        return sanitized
    


    def _get_player_cards(self, fixed_uuid, seat, all_cards, winners_with_cards, hand_info_dict, hand_info, seats, name, debug_mode=False):
        """
        Obtém cartas de um jogador usando múltiplas fontes em ordem de prioridade.
        
        Args:
            fixed_uuid: UUID fixo do jogador
            seat: Dict com informações do seat
            all_cards: Dict com todas as cartas do registry
            winners_with_cards: Dict com cartas dos winners
            hand_info_dict: Dict processado do hand_info
            hand_info: hand_info original (pode ser dict ou list)
            seats: Lista de seats
            name: Nome do jogador
            debug_mode: Se True, imprime debug
        
        Returns:
            Lista de cartas normalizadas ou None
        """
        if not fixed_uuid:
            return None
        
        # 1. Do registry global usando UUID fixo (mais confiável)
        hole_cards = all_cards.get(fixed_uuid)
        if hole_cards:
            if debug_mode:
                print(f"[DEBUG]   Cartas encontradas no registry: {fixed_uuid}")
            return normalize_hole_cards(hole_cards)
        
        # 1.5. Do registry global usando UUID do seat (engine UUID)
        # Bots atualizam seu UUID para o do engine e armazenam cartas com ele
        if seat and isinstance(seat, dict):
            seat_uuid = seat.get('uuid')
            if seat_uuid and seat_uuid != fixed_uuid:
                hole_cards = all_cards.get(seat_uuid)
                if hole_cards:
                    if debug_mode:
                        print(f"[DEBUG]   Cartas encontradas no registry (seat uuid): {seat_uuid}")
                    return normalize_hole_cards(hole_cards)
        
        # 2. Dos winners se este jogador é vencedor
        if fixed_uuid in winners_with_cards:
            if debug_mode:
                print(f"[DEBUG]   Cartas encontradas nos winners: {fixed_uuid}")
            hole_cards = normalize_hole_cards(winners_with_cards[fixed_uuid])
            if hole_cards:
                store_player_cards(fixed_uuid, hole_cards, name)
            return hole_cards
        
        # 3. Do hand_info_dict usando UUID fixo
        if fixed_uuid in hand_info_dict:
            if debug_mode:
                print(f"[DEBUG]   Cartas encontradas no hand_info_dict: {fixed_uuid}")
            hand_info_item = hand_info_dict[fixed_uuid]
            if isinstance(hand_info_item, dict):
                # Tenta múltiplos formatos possíveis
                hole_card_from_info = (
                    hand_info_item.get('hole_card') or 
                    hand_info_item.get('hole_cards') or
                    (hand_info_item.get('hand', {}).get('hole_card') if isinstance(hand_info_item.get('hand'), dict) else None)
                )
                if hole_card_from_info:
                    hole_cards = normalize_hole_cards(hole_card_from_info)
                    if hole_cards:
                        store_player_cards(fixed_uuid, hole_cards, name)
                    return hole_cards
        
        # 4. Busca direta no hand_info (caso não esteja no dicionário processado)
        if hand_info and isinstance(hand_info, list):
            from utils.uuid_utils import get_bot_class_uuid_from_name, get_player_uuid
            for item in hand_info:
                if isinstance(item, dict):
                    item_uuid = item.get('uuid')
                    item_name = item.get('name', '')
                    
                    # Mapeia UUID do item para UUID fixo
                    item_fixed_uuid = None
                    if item_name:
                        item_fixed_uuid = get_bot_class_uuid_from_name(item_name)
                        if not item_fixed_uuid:
                            item_fixed_uuid = get_player_uuid(item_name)
                    
                    # Compara com UUID fixo do seat
                    if item_fixed_uuid == fixed_uuid or (not item_fixed_uuid and item_uuid == fixed_uuid):
                        if debug_mode:
                            print(f"[DEBUG]   Cartas encontradas na busca direta do hand_info: {fixed_uuid}")
                        hole_card_from_info = (
                            item.get('hole_card') or 
                            item.get('hole_cards') or
                            (item.get('hand', {}).get('hole_card') if isinstance(item.get('hand'), dict) else None)
                        )
                        if hole_card_from_info:
                            hole_cards = normalize_hole_cards(hole_card_from_info)
                            if hole_cards:
                                store_player_cards(fixed_uuid, hole_cards, name)
                            return hole_cards
        
        # 5. Do cache local do jogador
        hole_cards = self.players_hole_cards.get(fixed_uuid)
        if hole_cards:
            if debug_mode:
                print(f"[DEBUG]   Cartas encontradas no cache local: {fixed_uuid}")
            return normalize_hole_cards(hole_cards)
        
        # 6. Do seat diretamente
        hole_cards = seat.get('hole_card') or seat.get('hole_cards')
        if hole_cards:
            if debug_mode:
                print(f"[DEBUG]   Cartas encontradas no seat: {fixed_uuid}")
            hole_cards = normalize_hole_cards(hole_cards)
            if hole_cards and fixed_uuid:
                store_player_cards(fixed_uuid, hole_cards, name)
            return hole_cards
        
        return None
    
    def _process_winners(self, winners, seats):
        """
        Processa winners e mapeia para UUIDs fixos.
        
        Args:
            winners: Lista de winners (pode ser dicts ou UUIDs)
            seats: Lista de seats
        
        Returns:
            Tuple (winner_uuids, winners_with_cards)
        """
        winner_uuids = []
        winners_with_cards = {}
        
        if not winners:
            return winner_uuids, winners_with_cards
        
        from utils.uuid_utils import get_bot_class_uuid_from_name, get_player_uuid
        
        for winner in winners:
            winner_uuid = None
            winner_name = None
            
            if isinstance(winner, dict):
                winner_uuid = winner.get('uuid')
                winner_name = winner.get('name', '')
                # Mapeia para UUID fixo usando o nome
                if winner_name:
                    fixed_uuid = get_bot_class_uuid_from_name(winner_name)
                    if not fixed_uuid:
                        fixed_uuid = get_player_uuid(winner_name)
                    if fixed_uuid:
                        winner_uuid = fixed_uuid
                
                if not winner_uuid:
                    winner_uuid = winner
                
                # Verifica se o winner tem cartas diretamente
                winner_cards = winner.get('hole_card') or winner.get('hole_cards')
                if winner_cards and winner_uuid:
                    winners_with_cards[winner_uuid] = winner_cards
            else:
                winner_uuid = winner
            
            if winner_uuid:
                winner_uuids.append(winner_uuid)
        
        return winner_uuids, winners_with_cards
    
    def _process_hand_info(self, hand_info, seats, debug_mode=False):
        """
        Processa hand_info e mapeia para UUIDs fixos.
        
        Args:
            hand_info: hand_info original (pode ser dict ou list)
            seats: Lista de seats
            debug_mode: Se True, imprime debug
        
        Returns:
            Dict com {fixed_uuid: hand_info_item}
        """
        hand_info_dict = {}
        
        if not hand_info:
            return hand_info_dict
        
        from utils.uuid_utils import get_bot_class_uuid_from_name, get_player_uuid
        
        if isinstance(hand_info, dict):
            for key, value in hand_info.items():
                if isinstance(value, dict):
                    uuid_from_info = value.get('uuid')
                    name_from_info = value.get('name', '')
                    
                    # Mapeia para UUID fixo usando o nome
                    fixed_uuid = None
                    if name_from_info:
                        fixed_uuid = get_bot_class_uuid_from_name(name_from_info)
                        if not fixed_uuid:
                            fixed_uuid = get_player_uuid(name_from_info)
                    
                    uuid_to_use = fixed_uuid if fixed_uuid else (uuid_from_info or (key if isinstance(key, str) and key else None))
                    if uuid_to_use:
                        hand_info_dict[uuid_to_use] = value
                        if debug_mode and fixed_uuid:
                            print(f"[DEBUG]   hand_info mapeado: {uuid_from_info} -> {fixed_uuid} ({name_from_info})")
                elif isinstance(value, (list, tuple)):
                    # Se value é lista/tuple, pode conter cartas diretamente
                    if isinstance(key, str) and key:
                        # Tenta encontrar o nome do jogador nos seats para mapear
                        fixed_uuid = None
                        for seat in seats:
                            if isinstance(seat, dict) and seat.get('uuid') == key:
                                seat_name = seat.get('name', '')
                                if seat_name:
                                    fixed_uuid = get_bot_class_uuid_from_name(seat_name)
                                    if not fixed_uuid:
                                        fixed_uuid = get_player_uuid(seat_name)
                                break
                        uuid_to_use = fixed_uuid if fixed_uuid else key
                        hand_info_dict[uuid_to_use] = {'hole_card': value}
        
        elif isinstance(hand_info, list):
            for item in hand_info:
                if isinstance(item, dict):
                    uuid_from_info = item.get('uuid')
                    name_from_info = item.get('name', '')
                    
                    # Se não tem nome no item, tenta buscar nos seats usando UUID
                    if not name_from_info and uuid_from_info:
                        for seat in seats:
                            if isinstance(seat, dict) and seat.get('uuid') == uuid_from_info:
                                name_from_info = seat.get('name', '')
                                if debug_mode:
                                    print(f"[DEBUG]   Nome encontrado nos seats para UUID {uuid_from_info}: {name_from_info}")
                                break
                    
                    # Mapeia para UUID fixo usando o nome
                    fixed_uuid = None
                    if name_from_info:
                        fixed_uuid = get_bot_class_uuid_from_name(name_from_info)
                        if not fixed_uuid:
                            fixed_uuid = get_player_uuid(name_from_info)
                        if debug_mode and fixed_uuid:
                            print(f"[DEBUG]   hand_info mapeado: {uuid_from_info} -> {fixed_uuid} ({name_from_info})")
                    
                    uuid_to_use = fixed_uuid if fixed_uuid else uuid_from_info
                    if uuid_to_use:
                        hand_info_dict[uuid_to_use] = item
        
        return hand_info_dict
    
    def _ensure_game_history_initialized(self, seats):
        """
        Garante que o histórico seja inicializado, mesmo sem UUID inicial.
        
        Args:
            seats: Lista de seats
        """
        if self.game_history:
            return
        
        # Tenta obter UUID de várias fontes
        player_uuid = None
        if hasattr(self, 'uuid') and self.uuid:
            player_uuid = self.uuid
        elif hasattr(self, '_fixed_uuid') and self._fixed_uuid:
            player_uuid = self._fixed_uuid
        else:
            # Tenta encontrar nos seats pelo nome "You"
            for seat in seats:
                if isinstance(seat, dict) and seat.get('name', '').lower() == 'you':
                    player_uuid = seat.get('uuid')
                    if not hasattr(self, 'uuid'):
                        self.uuid = player_uuid
                    break
        
        if player_uuid:
            try:
                self.game_history = GameHistory(player_uuid, self.initial_stack)
                if seats:
                    self.game_history.register_players(seats)
                    num_players = len([s for s in seats if isinstance(s, dict)])
                    
                    # Tenta obter blinds
                    small_blind_value = self.small_blind or 0
                    big_blind_value = self.big_blind or 0
                    
                    if small_blind_value == 0 or big_blind_value == 0:
                        try:
                            from game.blind_manager import BlindManager
                            blind_manager = BlindManager(initial_reference_stack=self.initial_stack)
                            calculated_sb, calculated_bb = blind_manager.get_blinds()
                            if small_blind_value == 0:
                                small_blind_value = calculated_sb
                            if big_blind_value == 0:
                                big_blind_value = calculated_bb
                        except Exception:
                            pass
                    
                    # Garante que os valores são int antes de passar para set_game_config
                    small_blind_final = int(small_blind_value) if small_blind_value is not None else 0
                    big_blind_final = int(big_blind_value) if big_blind_value is not None else 0
                    
                    self.game_history.set_game_config(
                        small_blind=small_blind_final,
                        big_blind=big_blind_final,
                        max_rounds=10,
                        num_players=num_players
                    )
            except Exception as e:
                # Log erro mas não quebra o jogo
                debug_mode = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'
                if debug_mode:
                    print(f"[DEBUG] Erro ao inicializar histórico: {type(e).__name__}: {e}")
    
    def _clear_all_caches(self):
        """Limpa todos os caches do jogador."""
        self.win_probability_cache = {}
        self.last_cache_key = None
        self.preflop_active_count = None
        self.players_hole_cards.clear()
        self.my_hole_cards = None

    def receive_round_result_message(self, winners, hand_info, round_state):
        """Mostra resultado final humanizado sem JSON bruto."""
        try:
            debug_mode = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'
            
            if debug_mode:
                print(f"[DEBUG] ========== receive_round_result_message CALLED ==========")
                print(f"[DEBUG] Player UUID: {self.uuid}")
                print(f"[DEBUG] Player Name: {self.name}")
            
            # Evita mostrar showdown duplicado (quando chamado manualmente após fold)
            round_id = f"{round_state.get('round_count', 0)}_{round_state.get('street', '')}"
            if hasattr(self, '_last_showdown_displayed') and self._last_showdown_displayed == round_id:
                if debug_mode:
                    print(f"[DEBUG] Showdown already displayed for round {round_id}, skipping")
                return
            self._last_showdown_displayed = round_id
            
            
            # Calcula pot total incluindo side pots
            pot = 0
            pot_data = round_state.get('pot', {})
            if isinstance(pot_data, dict):
                # Adiciona pot principal
                main_pot = pot_data.get('main', {})
                if isinstance(main_pot, dict):
                    pot += main_pot.get('amount', 0)
                
                # Adiciona side pots
                side_pots = pot_data.get('side', [])
                if isinstance(side_pots, list):
                    for side_pot in side_pots:
                        if isinstance(side_pot, dict):
                            pot += side_pot.get('amount', 0)
            
            seats = round_state.get('seats', [])
            community_cards = get_community_cards(round_state)
            current_street = round_state.get('street', 'river')
            debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
            
            # Garante que histórico está inicializado
            self._ensure_game_history_initialized(seats)
            
            # IMPORTANTE: Registra cartas de TODOS os jogadores no showdown, não apenas os que não foldaram
            if seats:
                if debug_mode:
                    print(f"[DEBUG] Processing {len(seats)} seats for card registration")
                for seat in seats:
                    if isinstance(seat, dict):
                        seat_uuid = seat.get('uuid', '')
                        seat_name = seat.get('name', '')
                        # Registra cartas se existirem, independente do estado
                        if seat_uuid:
                            seat_hole_cards = (
                                seat.get('hole_card') or 
                                seat.get('hole_cards') or
                                (getattr(seat, 'hole_card', None) if hasattr(seat, 'hole_card') else None)
                            )
                            if debug_mode:
                                print(f"[DEBUG] Seat {seat_name} ({seat_uuid[:8]}): hole_cards={seat_hole_cards}")
                            if seat_hole_cards:
                                try:
                                    normalized_cards = normalize_hole_cards(seat_hole_cards)
                                    if normalized_cards:
                                        fixed_uuid = self._get_fixed_uuid_from_seat(seat, False)
                                        if fixed_uuid:
                                            store_player_cards(fixed_uuid, normalized_cards, seat_name)
                                            if debug_mode:
                                                print(f"[DEBUG] Cartas armazenadas do seat: {fixed_uuid} -> {normalized_cards}")
                                except Exception as e:
                                    if debug_mode:
                                        print(f"[DEBUG] Erro ao armazenar cartas do seat: {e}")
            
            # Processa winners e hand_info usando métodos auxiliares
            winner_uuids, winners_with_cards = self._process_winners(winners, seats)
            
            # DEBUG: Mostra conteúdo bruto do hand_info
            if debug_mode:
                print(f"[DEBUG] ========== RAW hand_info ==========")
                print(f"[DEBUG] Type: {type(hand_info)}")
                print(f"[DEBUG] Content: {hand_info}")
                print(f"[DEBUG] ====================================")
            
            hand_info_dict = self._process_hand_info(hand_info, seats, debug_mode)
            
            # IMPORTANTE: Extrai e armazena cartas dos bots do hand_info no registry global
            # Isso garante que as cartas estejam disponíveis no showdown
            if hand_info_dict:
                for fixed_uuid, info in hand_info_dict.items():
                    if isinstance(info, dict):
                        # Tenta obter cartas de múltiplos formatos possíveis
                        bot_hole_cards = (
                            info.get('hole_card') or 
                            info.get('hole_cards') or
                            (info.get('hand', {}).get('hole_card') if isinstance(info.get('hand'), dict) else None)
                        )
                        if bot_hole_cards:
                            try:
                                normalized_cards = normalize_hole_cards(bot_hole_cards)
                                if normalized_cards:
                                    # Obtém nome do jogador para o registro
                                    player_name = info.get('name', '')
                                    if not player_name:
                                        # Tenta encontrar nome nos seats
                                        for seat in seats:
                                            if isinstance(seat, dict):
                                                seat_uuid = seat.get('uuid', '')
                                                seat_fixed_uuid = self._get_fixed_uuid_from_seat(seat, False)
                                                if seat_uuid == fixed_uuid or seat_fixed_uuid == fixed_uuid:
                                                    player_name = seat.get('name', '')
                                                    break
                                    
                                    store_player_cards(fixed_uuid, normalized_cards, player_name)
                                    if debug_mode:
                                        print(f"[DEBUG] Cartas armazenadas do hand_info: {fixed_uuid} ({player_name}) -> {normalized_cards}")
                            except Exception as e:
                                if debug_mode:
                                    print(f"[DEBUG] Erro ao armazenar cartas do hand_info: {e}")
            
            # === FIX: Ensure all participating players are in hand_info_dict for history ===
            # Iterate through all seats to find players who reached showdown but might be missing from hand_info
            all_cards = get_all_cards()
            for seat in seats:
                if isinstance(seat, dict):
                    seat_uuid = seat.get('uuid', '')
                    seat_state = seat.get('state', '')
                    
                    # Skip folded players (unless we want to show their cards if known, but usually not for history if folded)
                    if seat_state == 'folded':
                        continue
                        
                    fixed_uuid = self._get_fixed_uuid_from_seat(seat, False)
                    uuid_to_use = fixed_uuid if fixed_uuid else seat_uuid
                    
                    # If not already in hand_info_dict, try to add it if we have cards
                    if uuid_to_use and uuid_to_use not in hand_info_dict:
                        # Check if we have cards in registry
                        hole_cards = all_cards.get(uuid_to_use)
                        if hole_cards:
                            # Create a synthetic hand_info entry
                            hand_info_dict[uuid_to_use] = {
                                'uuid': uuid_to_use,
                                'name': seat.get('name', ''),
                                'hole_cards': hole_cards,
                                # We might not have hand strength here, but GameHistory will try to calculate it
                            }
                            if debug_mode:
                                print(f"[DEBUG] Added synthetic hand_info for {uuid_to_use} with cards {hole_cards}")
            # ==============================================================================

            if debug_mode:
                print(f"[DEBUG] Registry tem {len(get_all_cards())} jogadores")
                print(f"[DEBUG] hand_info_dict tem {len(hand_info_dict)} jogadores")
                print(f"[DEBUG] winner_uuids: {winner_uuids}")
                print(f"[DEBUG] ========== REGISTRY CONTENT ==========")
                all_cards_debug = get_all_cards()
                for uuid, cards in all_cards_debug.items():
                    print(f"[DEBUG]   {uuid}: {cards}")
                print(f"[DEBUG] ========================================")
            
            if winner_uuids or seats:
                # Mostra última street e community cards antes do resultado
                street_pt = self.formatter.format_street_pt(current_street)
                if street_pt:
                    print(f"\n–– {street_pt.upper()} ––")
                else:
                    print(f"\n–– {current_street.upper() if current_street else 'UNKNOWN'} ––")
                
                # Mostra community cards
                if community_cards:
                    community_display = self.formatter.format_cards_display_with_color(community_cards)
                    print(f"Community cards: {community_display}")
                
                print("\n–– SHOWDOWN ––")
                
                # Mostra community cards novamente no resultado
                if community_cards:
                    community_display = self.formatter.format_cards_display_with_color(community_cards)
                    print(f"\nCommunity cards: {community_display}")
                
                # Mostra cartas dos participantes
                print("\nParticipant cards:")
                all_cards = get_all_cards()
                
                for seat in seats:
                    if not isinstance(seat, dict):
                        continue
                    
                    try:
                        seat_uuid = seat.get('uuid', '')
                        name = self.formatter.clean_player_name(seat.get('name', ''))
                        state = seat.get('state', '')
                        seat_stack = seat.get('stack', 0)
                        
                        # Obtém posição do jogador
                        position = self.formatter.get_player_position(seat, round_state)
                        position_indicator = f" ({position})" if position else ""
                        
                        # Mapeia UUID e determina flags
                        fixed_uuid = self._get_fixed_uuid_from_seat(seat, debug_mode)
                        is_winner = fixed_uuid in winner_uuids if fixed_uuid else (seat_uuid in winner_uuids)
                        is_player = hasattr(self, 'uuid') and self.uuid and (seat_uuid == self.uuid or fixed_uuid == self.uuid)
                        is_eliminated = seat_stack == 0
                        
                        # IMPORTANTE: Verifica se realmente deu fold checando o histórico de ações
                        # Não confiar apenas no state, pois all-in players podem ter state='folded' após perder
                        is_folded = False
                        did_all_in = False
                        action_histories = round_state.get('action_histories', {})
                        
                        # Calcula o total apostado pelo jogador neste round
                        total_bet_this_round = 0
                        
                        # Verifica todas as ações do jogador neste round
                        for street_history in action_histories.values():
                            if isinstance(street_history, list):
                                for action in street_history:
                                    if isinstance(action, dict):
                                        action_uuid = action.get('uuid', '')
                                        if action_uuid == seat_uuid or action_uuid == fixed_uuid:
                                            action_type = action.get('action', '').lower()
                                            action_amount = action.get('amount', 0)
                                            
                                            if action_type == 'fold':
                                                is_folded = True
                                                break
                                            elif action_type in ['raise', 'call']:
                                                total_bet_this_round += action_amount
                                if is_folded:
                                    break
                        
                        # Jogador fez all-in se:
                        # 1. Ficou com 0 chips (is_eliminated), OU
                        # 2. Apostou todo o seu stack inicial (total_bet >= stack inicial)
                        # Para calcular stack inicial: stack_atual + total_apostado
                        initial_stack = seat_stack + total_bet_this_round
                        if not is_folded and (is_eliminated or (total_bet_this_round > 0 and total_bet_this_round >= initial_stack)):
                            did_all_in = True
                        
                        
                        # IMPORTANTE: Verifica se o jogador participou do round
                        # Um jogador participou se:
                        # 1. Tem cartas no hand_info ou no registry, OU
                        # 2. Tem ações no action_histories do round
                        action_histories = round_state.get('action_histories', {})
                        participated_in_round = False
                        
                        # Verifica se tem ações no histórico
                        for street_history in action_histories.values():
                            if isinstance(street_history, list):
                                for action in street_history:
                                    if isinstance(action, dict):
                                        action_uuid = action.get('uuid', '')
                                        if action_uuid == seat_uuid or action_uuid == fixed_uuid:
                                            participated_in_round = True
                                            break
                                if participated_in_round:
                                    break
                        
                        # Se não participou do round e não é vencedor, mostra mensagem apropriada
                        if not participated_in_round and not is_winner:
                            # Verifica se é porque não tem fichas suficientes para os blinds
                            if seat_stack > 0:
                                # Tem fichas mas não participou (pode ser porque não consegue pagar blinds)
                                full_line = f"  {name}{position_indicator}: (Out of chips - cannot pay blinds)"
                            else:
                                # Sem fichas
                                full_line = f"  {name}{position_indicator}: (Out of chips)"
                            dim_line = f"{self.formatter.DIM}{full_line}{self.formatter.RESET}"
                            print(dim_line)
                            continue
                        
                        # Se jogador deu fold e não é o jogador humano, mostra apenas "folded"
                        if is_folded and not is_player:
                            full_line = f"  {name}{position_indicator}: folded"
                            dim_line = f"{self.formatter.DIM}{full_line}{self.formatter.RESET}"
                            print(dim_line)
                            continue
                        
                        # IMPORTANTE: Jogadores eliminados (stack == 0) ainda mostram cartas se participaram do showdown
                        # Só não mostra cartas se deu fold
                        
                        # Obtém cartas usando método centralizado
                        hole_cards = self._get_player_cards(
                            fixed_uuid, seat, all_cards, winners_with_cards, 
                            hand_info_dict, hand_info, seats, name, debug_mode
                        )
                        
                        # Exibe cartas ou mensagem de erro
                        if hole_cards and len(hole_cards) >= 2:
                            cards_display = self.formatter.format_cards_display_with_color(hole_cards)
                            hand_desc = self.formatter.get_hand_strength_heuristic(hole_cards, community_cards, current_street)
                            
                            # Determina indicadores
                            folded_indicator = " (Folded)" if is_folded else ""
                            all_in_indicator = " (all-in)" if did_all_in or (is_eliminated and not is_folded) else ""
                            
                            if is_folded:
                                # Jogador que deu fold - mostra cartas com indicador (Folded)
                                cards_display_no_color = re.sub(r'\033\[[0-9;]*m', '', cards_display)
                                full_line = f"  {name}{position_indicator}: {cards_display_no_color} | {hand_desc}{folded_indicator}"
                                dim_line = f"{self.formatter.DIM}{full_line}{self.formatter.RESET}"
                                print(dim_line)
                            else:
                                # Jogador que chegou ao showdown (com ou sem all-in) - mostra normalmente
                                # Se fez all-in, mostra indicador, mas não esmaece
                                print(f"  {name}{position_indicator}: {cards_display} | {hand_desc}{all_in_indicator}")
                        else:
                            # Mensagem de erro mais informativa
                            error_msg = f"  {name}{position_indicator}: [erro: cartas não encontradas"
                            if debug_mode:
                                error_msg += f" (UUID: {seat_uuid}, fixed: {fixed_uuid})"
                            error_msg += "]"
                            if is_folded and is_player:
                                error_msg = f"  {name}: folded (cartas não encontradas)"
                                dim_line = f"{self.formatter.DIM}{error_msg}{self.formatter.RESET}"
                                print(dim_line)
                            else:
                                print(error_msg)
                    except Exception as e:
                        # Tratamento de erro robusto
                        error_msg = f"  {name}: [erro ao processar: {type(e).__name__}]"
                        if debug_mode:
                            error_msg += f" - {str(e)}"
                            import traceback
                            traceback.print_exc()
                        print(error_msg)
            
                # Mostra ganhador(es)
                if winner_uuids:
                    try:
                        winner_names = []
                        player_won = False
                        player_hand_desc = None
                        num_winners = len(winner_uuids)
                        all_cards = get_all_cards()
                        
                        for winner_uuid in winner_uuids:
                            # Verifica se o jogador humano venceu
                            if hasattr(self, 'uuid') and self.uuid and winner_uuid == self.uuid:
                                player_won = True
                                hole_cards = all_cards.get(winner_uuid)
                                if hole_cards:
                                    player_hand_desc = self.formatter.get_hand_strength_heuristic(
                                        hole_cards, community_cards, current_street
                                    )
                            
                            # Encontra nome do winner nos seats
                            for seat in seats:
                                if isinstance(seat, dict):
                                    seat_uuid = seat.get('uuid', '')
                                    fixed_uuid = self._get_fixed_uuid_from_seat(seat, False)
                                    if seat_uuid == winner_uuid or fixed_uuid == winner_uuid:
                                        name = self.formatter.clean_player_name(seat.get('name', ''))
                                        hole_cards = all_cards.get(winner_uuid)
                                        hand_desc = ""
                                        if hole_cards:
                                            hand_desc = self.formatter.get_hand_strength_heuristic(
                                                hole_cards, community_cards, current_street
                                            )
                                        
                                        if hand_desc:
                                            # Bold the hand name for emphasis
                                            hand_desc_bold = self.formatter.format_hand_name_bold(hand_desc)
                                            winner_names.append(f"{name} ({hand_desc_bold})")
                                        else:
                                            winner_names.append(name)
                                        break
                        
                        if winner_names:
                            winner_line = " | ".join(winner_names)
                            pot_display = self.formatter.format_pot_with_color(pot)
                            print(f"\nWinner(s): {winner_line} | Pot: {pot_display}")
                        
                        # Mostra mensagem destacada se o jogador humano venceu
                        if player_won:
                            player_pot = pot // num_winners if num_winners > 0 else pot
                            round_number = 0
                            if self.game_history and self.game_history.current_round:
                                round_number = self.game_history.current_round.get("round_number", 0)
                            print()
                            print(self.formatter.format_round_winner(round_number, "You", player_pot, player_hand_desc))
                            print()
                    except Exception as e:
                        if debug_mode:
                            print(f"[DEBUG] Erro ao processar winners: {type(e).__name__}: {e}")
                            import traceback
                            traceback.print_exc()
                        print(f"\n[Erro ao processar winners]")
                
                # Mostra stacks finais
                # Jogadores que chegaram ao showdown não aparecem esmaecidos, mesmo com stack 0 (all-in)
                # Apenas jogadores que deram fold ou não participaram aparecem esmaecidos
                try:
                    final_stacks = []
                    all_cards = get_all_cards()
                    for seat in seats:
                        if isinstance(seat, dict):
                            name = self.formatter.clean_player_name(seat.get('name', ''))
                            stack = seat.get('stack', 0)
                            seat_uuid = seat.get('uuid', '')
                            state = seat.get('state', '')
                            
                            # Verifica se o jogador chegou ao showdown (tem cartas ou não deu fold)
                            fixed_uuid = self._get_fixed_uuid_from_seat(seat, False)
                            uuid_to_check = fixed_uuid if fixed_uuid else seat_uuid
                            has_cards = uuid_to_check in all_cards if uuid_to_check else False
                            reached_showdown = has_cards or (state != 'folded' and stack == 0)
                            
                            # Só esmaece se não chegou ao showdown (deu fold ou não participou)
                            if stack == 0 and not reached_showdown:
                                dim_line = f"{self.formatter.DIM}{name} {stack}{self.formatter.RESET}"
                                final_stacks.append(dim_line)
                            else:
                                final_stacks.append(f"{name} {stack}")
                    
                    if final_stacks:
                        print(f"\nFinal stacks:")
                        print(" | ".join(final_stacks))
                except Exception as e:
                    if debug_mode:
                        print(f"[DEBUG] Erro ao mostrar stacks finais: {type(e).__name__}: {e}")
                
                # Registra resultado do round no histórico
                if self.game_history:
                    try:
                        # Sanitiza round_state para usar UUIDs fixos
                        sanitized_round_state = self._sanitize_round_state(round_state)
                        
                        # Processa winners para usar UUIDs fixos
                        fixed_winners = []
                        for winner in winners:
                            if isinstance(winner, dict):
                                winner_copy = winner.copy()
                                winner_name = winner.get('name', '')
                                if winner_name:
                                    fixed_uuid = None
                                    from utils.uuid_utils import get_bot_class_uuid_from_name, get_player_uuid
                                    fixed_uuid = get_bot_class_uuid_from_name(winner_name)
                                    if not fixed_uuid:
                                        fixed_uuid = get_player_uuid(winner_name)
                                    
                                    if fixed_uuid:
                                        winner_copy['uuid'] = fixed_uuid
                                fixed_winners.append(winner_copy)
                            else:
                                # Se for apenas UUID string, tenta encontrar o nome nos seats para converter
                                fixed_uuid = winner
                                for seat in seats:
                                    if isinstance(seat, dict) and seat.get('uuid') == winner:
                                        fixed = self._get_fixed_uuid_from_seat(seat, False)
                                        if fixed:
                                            fixed_uuid = fixed
                                        break
                                fixed_winners.append(fixed_uuid)

                        # Sanitiza hand_info para usar UUIDs fixos
                        sanitized_hand_info = {}
                        if hand_info_dict:
                            for fixed_uuid, info in hand_info_dict.items():
                                if isinstance(info, dict):
                                    info_copy = info.copy()
                                    info_copy['uuid'] = fixed_uuid # Garante UUID fixo dentro do dict
                                    sanitized_hand_info[fixed_uuid] = info_copy

                        self.game_history.record_round_result(fixed_winners, sanitized_hand_info, sanitized_round_state)
                        
                        # Salva histórico ao final do jogo (não apenas no round 10)
                        round_number = 0
                        if self.game_history.current_round:
                            round_number = self.game_history.current_round.get("round_number", 0)
                        
                        # Tenta salvar histórico (pode falhar se jogo terminar antes do round 10)
                        if round_number >= 10:
                            try:
                                history_file = self.game_history.save()
                                print(f"\n[Histórico salvo em: {history_file}]")
                            except Exception as e:
                                if debug_mode:
                                    print(f"[DEBUG] Erro ao salvar histórico: {type(e).__name__}: {e}")
                                print(f"\n[Aviso: não foi possível salvar histórico]")
                    except Exception as e:
                        if debug_mode:
                            print(f"[DEBUG] Erro ao registrar resultado: {type(e).__name__}: {e}")
                            import traceback
                            traceback.print_exc()
                
                # Pausa para aguardar input antes de continuar
                print()
                self.__wait_for_continue()
                
                # Limpa todos os caches para próximo round
                self._clear_all_caches()
                self.last_pot_printed = 0
        
        except QuitGameException:
            # Re-lança QuitGameException para ser capturada no nível superior
            # Limpa caches antes de sair
            self._clear_all_caches()
            raise
        except Exception as e:
            # Tratamento de erro geral para não quebrar o jogo
            debug_mode = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'
            print(f"\n[Erro ao processar resultado do round: {type(e).__name__}]")
            if debug_mode:
                print(f"[DEBUG] Detalhes: {e}")
                import traceback
                traceback.print_exc()
            # Limpa caches mesmo em caso de erro
            self._clear_all_caches()

    def __wait_until_input(self):
        """Método não utilizado mais - mantido para compatibilidade."""
        pass
    
    def __wait_for_continue(self):
        """Aguarda input do usuário antes de continuar."""
        try:
            user_input = input("Press Enter to continue (or 'q' to quit)... ")
            if user_input.strip().lower() == 'q':
                raise QuitGameException()
        except (EOFError, KeyboardInterrupt):
            # Se não houver input disponível (ex: em testes), continua silenciosamente
            pass

    def __gen_raw_input_wrapper(self):
        return lambda msg: input(msg)

    def _get_current_street_bet(self, round_state):
        """Calcula o total apostado pelo jogador na street atual."""
        if not round_state:
            return 0
            
        street = round_state.get('street', '')
        action_histories = round_state.get('action_histories', {})
        
        street_key = street.lower()
        if street_key not in action_histories:
            return 0
            
        street_actions = action_histories.get(street_key, [])
        if not street_actions:
            return 0
            
        # Procura pela última ação do jogador nesta street
        my_uuid = getattr(self, 'uuid', None)
        if not my_uuid:
            return 0
            
        # Cria um mapa de UUID original -> UUID fixo usando os seats
        uuid_map = {}
        seats = round_state.get('seats', [])
        for seat in seats:
            if isinstance(seat, dict):
                orig_uuid = seat.get('uuid')
                if orig_uuid:
                    # Usa o método existente que depende do nome no seat
                    fixed = self._get_fixed_uuid_from_seat(seat, False)
                    if fixed:
                        uuid_map[orig_uuid] = fixed
        
        # Itera de trás para frente para encontrar a última ação válida
        for i in range(len(street_actions) - 1, -1, -1):
            action = street_actions[i]
            if isinstance(action, dict):
                action_uuid = action.get('uuid')
                
                # Tenta obter o UUID fixo do mapa
                fixed_uuid = uuid_map.get(action_uuid, action_uuid)
                
                if action_uuid == my_uuid or fixed_uuid == my_uuid:
                    action_type = action.get('action', '').lower()
                    if action_type in ['call', 'raise']:
                        return action.get('amount', 0)
                    elif action_type == 'fold':
                        return 0 
                        
        # Se não encontrou ações nesta street, verifica se é preflop e se pagou blind
        if street_key == 'preflop':
            for action in street_actions:
                if isinstance(action, dict):
                    action_uuid = action.get('uuid')
                    fixed_uuid = uuid_map.get(action_uuid, action_uuid)
                    
                    if action_uuid == my_uuid or fixed_uuid == my_uuid:
                        action_type = action.get('action', '').upper()
                        if action_type in ['SMALLBLIND', 'BIGBLIND']:
                            return action.get('amount', 0)
                            
        return 0
                            
        if debug_mode:
            print(f"[DEBUG] _get_current_street_bet: No matching action found, returning 0")
        return 0

    def __receive_action_from_console(self, valid_actions, round_state=None, cached_player_stack=None) -> Tuple[str, int]:
        """Solicita ação do jogador de forma limpa.
        
        Args:
            valid_actions: Lista de ações válidas
            round_state: Estado do round (opcional, necessário para all-in)
            cached_player_stack: Stack do jogador já calculado (opcional, evita recalcular)
        
        Returns:
            tuple[str, int]: Tupla com (action, amount)
        """
        def _get_player_stack(round_state):
            """Obtém stack do jogador usando múltiplas estratégias (mesma lógica de declare_action)."""
            import os
            debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
            
            if not round_state:
                if debug_mode:
                    print(f"[DEBUG] _get_player_stack: round_state is None, returning 0")
                return 0
            
            seats = round_state.get('seats', [])
            player_seat = None
            
            if debug_mode:
                print(f"[DEBUG] _get_player_stack: Searching for player stack...")
                print(f"[DEBUG]   self.uuid: {getattr(self, 'uuid', 'NOT SET')}")
                print(f"[DEBUG]   Number of seats: {len(seats)}")
            
            # 1. Tenta encontrar pelo UUID
            if hasattr(self, 'uuid') and self.uuid:
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('uuid') == self.uuid:
                        player_seat = seat
                        if debug_mode:
                            print(f"[DEBUG]   ✓ Found by UUID: stack={seat.get('stack', 0)}")
                        break
            
            # 2. Se não encontrou, tenta pelo nome "You"
            if not player_seat:
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('name', '').lower() == 'you':
                        player_seat = seat
                        # Atualiza self.uuid se não estava definido
                        if not hasattr(self, 'uuid') or not self.uuid:
                            self.uuid = seat.get('uuid')
                            if debug_mode:
                                print(f"[DEBUG]   ✓ Found by name 'You', updated UUID: {self.uuid}")
                        if debug_mode:
                            print(f"[DEBUG]   ✓ Found by name: stack={seat.get('stack', 0)}")
                        break
            
            # 3. Se ainda não encontrou, tenta pelas cartas (fallback)
            if not player_seat and hasattr(self, 'my_hole_cards') and self.my_hole_cards:
                from utils.hand_utils import normalize_hole_cards
                for seat in seats:
                    if isinstance(seat, dict):
                        seat_hole_card = seat.get('hole_card', None)
                        if seat_hole_card:
                            seat_hole_cards = normalize_hole_cards(seat_hole_card)
                            if seat_hole_cards == self.my_hole_cards:
                                player_seat = seat
                                if not hasattr(self, 'uuid') or not self.uuid:
                                    self.uuid = seat.get('uuid')
                                if debug_mode:
                                    print(f"[DEBUG]   ✓ Found by hole cards: stack={seat.get('stack', 0)}")
                                break
            
            # 4. Fallback: usa o primeiro seat se houver apenas um
            if not player_seat and len(seats) == 1 and isinstance(seats[0], dict):
                player_seat = seats[0]
                if debug_mode:
                    print(f"[DEBUG]   ⚠️  Using single seat fallback: stack={seats[0].get('stack', 0)}")
            
            if player_seat:
                stack = player_seat.get('stack', 0)
                if debug_mode:
                    print(f"[DEBUG]   Final stack: {stack}")
                return stack
            
            if debug_mode:
                print(f"[DEBUG]   ❌ ERROR: Could not find player seat! Returning 0")
                print(f"[DEBUG]   Available seats:")
                for i, seat in enumerate(seats):
                    if isinstance(seat, dict):
                        print(f"[DEBUG]     Seat {i}: name={seat.get('name')}, uuid={seat.get('uuid')}, stack={seat.get('stack')}")
            return 0
        
        try:
            flg = self.input_receiver('>> ').strip().lower()
            # IMPORTANTE: Verifica se o jogador quer sair PRIMEIRO, antes de qualquer outra validação
            if flg == 'q':
                raise QuitGameException()
            
            # Se escolheu All In ('a')
            if flg == 'a':
                # Usa stack em cache se disponível, senão calcula
                player_stack = cached_player_stack if cached_player_stack is not None else _get_player_stack(round_state)
                current_bet = self._get_current_street_bet(round_state)
                total_all_in = player_stack + current_bet
                
                import os
                debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
                if debug_mode:
                    print(f"[DEBUG] ALL-IN: player_stack={player_stack} (cached={cached_player_stack is not None}), current_bet={current_bet}, total={total_all_in}")
                
                if player_stack > 0:
                    # Verifica se há ação de raise válida disponível
                    raise_action = None
                    for action_data in valid_actions:
                        if action_data.get('action') == 'raise':
                            raise_action = action_data
                            break
                    
                    if raise_action:
                        # Valida limites do raise
                        raise_amount = raise_action.get('amount', {})
                        if isinstance(raise_amount, dict):
                            min_raise = raise_amount.get('min', 0)
                            max_raise = raise_amount.get('max', float('inf'))
                            
                            # Se max_raise for -1, considera como infinito (sem limite superior imposto pelo engine)
                            effective_max = max_raise if max_raise != -1 else float('inf')
                            # Se min_raise for -1, considera como 0 (sem limite inferior imposto pelo engine)
                            effective_min = min_raise if min_raise != -1 else 0
                            
                            # Garante que o all-in está dentro dos limites válidos
                            final_amount = min(total_all_in, effective_max) if effective_max != float('inf') else total_all_in
                            
                            # Se o stack é menor que min_raise, ainda pode fazer all-in
                            if final_amount >= effective_min or total_all_in <= effective_min:
                                return 'raise', final_amount
                            else:
                                print(f"⚠️  Seu stack total ({total_all_in}) é menor que o raise mínimo ({min_raise}). Fazendo all-in...")
                                return 'raise', total_all_in
                        else:
                            # Formato simples, retorna o stack total
                            return 'raise', total_all_in
                    else:
                        # Se não há raise disponível, tenta call como all-in
                        # (pode acontecer em situações especiais)
                        call_action = None
                        for action_data in valid_actions:
                            if action_data.get('action') == 'call':
                                call_action = action_data
                                break
                        if call_action:
                            return 'call', call_action.get('amount', 0)
                        else:
                            print("Erro: Não há ações válidas para all-in. Use outra ação.")
                            return self.__receive_action_from_console(valid_actions, round_state)
                else:
                    print("Erro: Não foi possível determinar stack para all-in")
                    return self.__receive_action_from_console(valid_actions, round_state)
            
            # Busca ação por tipo ao invés de índice fixo (mais robusto após filtragem)
            # IMPORTANTE: Filtra raise se não for possível (min == -1)
            action_map = {}
            for action_data in valid_actions:
                action_type = action_data.get('action', '')
                if action_type == 'fold':
                    action_map['f'] = action_data
                elif action_type == 'call':
                    action_map['c'] = action_data
                elif action_type == 'raise':
                    # Verifica se raise é possível antes de adicionar ao mapa
                    raise_amount = action_data.get('amount', {})
                    if isinstance(raise_amount, dict):
                        min_raise = raise_amount.get('min', -1)
                        # Só adiciona raise se min_raise for válido (>= 0)
                        if min_raise >= 0:
                            action_map['r'] = action_data
                    elif isinstance(raise_amount, (int, float)) and raise_amount > 0:
                        action_map['r'] = action_data
            
            if flg in self.__gen_valid_flg(valid_actions):
                if flg == 'f' and 'f' in action_map:
                    action_data = action_map['f']
                    return action_data['action'], action_data['amount']
                elif flg == 'c' and 'c' in action_map:
                    action_data = action_map['c']
                    call_amount = action_data['amount']
                    
                    # IMPORTANTE: Verifica se o jogador tem stack suficiente para o call
                    # Se não tiver ou se o call vai usar todas as fichas, converte para all-in automaticamente
                    # Usa stack em cache se disponível (mais confiável que recalcular)
                    player_stack = cached_player_stack if cached_player_stack is not None else _get_player_stack(round_state)
                    
                    # Debug logging para rastrear o problema
                    import os
                    debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
                    if debug_mode:
                        print(f"[DEBUG] CALL Logic: player_stack={player_stack} (cached={cached_player_stack is not None}), call_amount={call_amount}")
                        print(f"[DEBUG] Condition check: player_stack > 0? {player_stack > 0}")
                        print(f"[DEBUG] Condition check: call_amount > 0? {call_amount > 0}")
                        print(f"[DEBUG] Condition check: player_stack <= call_amount? {player_stack <= call_amount}")
                    
                    # Se o stack é menor ou igual ao call_amount, faz all-in
                    # (quando são iguais, o call usa todas as fichas, então é all-in)
                    if player_stack > 0 and call_amount > 0 and player_stack <= call_amount:
                        # Stack insuficiente ou exato - retorna all-in com o stack total
                        # IMPORTANTE: O valor do raise deve ser o total apostado na street (aposta atual + stack restante)
                        current_bet = self._get_current_street_bet(round_state)
                        total_all_in = current_bet + player_stack
                        
                        if debug_mode:
                            print(f"[DEBUG] Converting CALL to ALL-IN: returning ('raise', {total_all_in}) [Stack: {player_stack} + CurrentBet: {current_bet}]")
                        return 'raise', total_all_in
                    else:
                        # Stack suficiente ou call_amount é 0 (check)
                        if debug_mode:
                            print(f"[DEBUG] Normal CALL: returning ('{action_data['action']}', {call_amount})")
                        return action_data['action'], call_amount
                elif flg == 'r' and 'r' in action_map:
                    action_data = action_map['r']
                    valid_amounts = action_data['amount']
                    if isinstance(valid_amounts, dict):
                        # Passa round_state E cached_player_stack para validação de stack
                        raise_amount = self.__receive_raise_amount_from_console(
                            valid_amounts['min'], 
                            valid_amounts['max'],
                            round_state,
                            cached_player_stack
                        )
                        
                        # IMPORTANTE: Garante que o raise_amount não exceda o stack total
                        # (validação adicional caso a função não tenha feito)
                        player_stack = cached_player_stack if cached_player_stack is not None else _get_player_stack(round_state)
                        current_bet = self._get_current_street_bet(round_state)
                        max_possible_bet = player_stack + current_bet
                        
                        # Se o raise_amount exceder o stack total, limita ao stack total (all-in)
                        if player_stack > 0 and raise_amount > max_possible_bet:
                            return 'raise', max_possible_bet
                        
                        return action_data['action'], raise_amount
            
            # Se chegou aqui, a ação é inválida - solicita novamente
            print("Invalid action. Use [f] FOLD, [c] CALL, [r] RAISE, [a] ALL IN or [q] to quit")
            return self.__receive_action_from_console(valid_actions, round_state)
        except QuitGameException:
            # Re-raise para ser capturado no nível superior
            raise

    def __gen_valid_flg(self, valid_actions):
        """Gera lista de flags válidas baseado nas ações disponíveis."""
        flgs = []
        for action_data in valid_actions:
            action_type = action_data.get('action', '')
            if action_type == 'fold':
                flgs.append('f')
            elif action_type == 'call':
                flgs.append('c')
            elif action_type == 'raise':
                # Verifica se raise é possível (min deve ser >= 0)
                amount = action_data.get('amount', {})
                if isinstance(amount, dict):
                    min_raise = amount.get('min', -1)
                    # Só adiciona 'r' se min_raise for válido (>= 0)
                    if min_raise >= 0:
                        flgs.append('r')
                elif isinstance(amount, (int, float)) and amount > 0:
                    flgs.append('r')
        return flgs

    def __receive_raise_amount_from_console(self, min_amount, max_amount, round_state=None, cached_player_stack=None):
        def _get_player_stack(round_state):
            """Obtém stack do jogador usando múltiplas estratégias."""
            import os
            debug_mode = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
            
            if not round_state:
                return 0
            
            seats = round_state.get('seats', [])
            player_seat = None
            
            # 1. Tenta encontrar pelo UUID
            if hasattr(self, 'uuid') and self.uuid:
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('uuid') == self.uuid:
                        player_seat = seat
                        break
            
            # 2. Se não encontrou, tenta pelo nome "You"
            if not player_seat:
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('name', '').lower() == 'you':
                        player_seat = seat
                        if not hasattr(self, 'uuid') or not self.uuid:
                            self.uuid = seat.get('uuid')
                        break
            
            # 3. Fallback: usa o primeiro seat se houver apenas um
            if not player_seat and len(seats) == 1 and isinstance(seats[0], dict):
                player_seat = seats[0]
            
            if player_seat:
                return player_seat.get('stack', 0)
            return 0
        
        try:
            raw_amount = self.input_receiver(f"Amount ({min_amount}-{max_amount}) or 'q' to quit: ").strip().lower()
            # Verifica se o jogador quer sair
            if raw_amount == 'q':
                raise QuitGameException()
            
            try:
                amount = int(raw_amount)
                if min_amount <= amount and amount <= max_amount:
                    # IMPORTANTE: Verifica se o amount não excede o stack do jogador
                    if round_state or cached_player_stack is not None:
                        player_stack = cached_player_stack if cached_player_stack is not None else _get_player_stack(round_state)
                        
                        # Calcula o total disponível para aposta (stack atual + o que já apostou na street)
                        current_bet = self._get_current_street_bet(round_state) if round_state else 0
                        max_possible_bet = player_stack + current_bet
                        
                        if player_stack > 0 and amount > max_possible_bet:
                            print(f"⚠️  Valor excede seu stack total ({max_possible_bet}). Será all-in por {max_possible_bet}.")
                            return max_possible_bet
                            
                    return amount
                else:
                    print(f"Invalid amount. Please enter a value between {min_amount} and {max_amount}")
                    return self.__receive_raise_amount_from_console(min_amount, max_amount, round_state, cached_player_stack)
            except ValueError:
                print("Invalid input. Please enter a number.")
                return self.__receive_raise_amount_from_console(min_amount, max_amount, round_state, cached_player_stack)
        except QuitGameException:
            # Re-raise para ser capturado no nível superior
            raise


    def save_history(self):
        """Salva o histórico do jogo manualmente."""
        if self.game_history:
            try:
                history_file = self.game_history.save()
                print(f"\n[Histórico salvo em: {history_file}]")
                return history_file
            except Exception as e:
                print(f"\n[Erro ao salvar histórico: {e}]")
        return None
