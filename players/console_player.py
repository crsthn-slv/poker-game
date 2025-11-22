from pypokerengine.players import BasePokerPlayer
from .console_formatter import ConsoleFormatter
from .cards_registry import store_player_cards, get_all_cards, clear_registry
from .win_probability_calculator import calculate_win_probability_for_player


class QuitGameException(Exception):
    """Exceção levantada quando o jogador digita 'q' para sair."""
    pass


class ConsolePlayer(BasePokerPlayer):

    def __init__(self, input_receiver=None, initial_stack=100):
        self.input_receiver = input_receiver if input_receiver else self.__gen_raw_input_wrapper()
        self.formatter = ConsoleFormatter()
        self.initial_stack = initial_stack
        self.last_pot_printed = 0  # Rastreia último pot impresso para evitar repetições
        self.my_hole_cards = None  # Cache das cartas do jogador atual
        self.players_hole_cards = {}  # Cache de cartas de todos os jogadores (UUID -> cartas)

    def declare_action(self, valid_actions, hole_card, round_state):
        """Exibe HUD completo fixo e solicita ação do jogador."""
        # Estrutura fixa minimalista do HUD
        
        print("\n–––– SUA VEZ ––––")
        
        # 1. Cartas do jogador com força da mão
        current_street = round_state.get('street', 'preflop')
        community_cards = round_state.get('community_card', [])
        
        # Atualiza cache das cartas do jogador e armazena no registro global
        if hole_card:
            self.my_hole_cards = hole_card
            if hasattr(self, 'uuid') and self.uuid:
                self.players_hole_cards[self.uuid] = hole_card
                store_player_cards(self.uuid, hole_card)
        
        if hole_card:
            cards_display = self.formatter.format_cards_display_with_color(hole_card)
            hand_strength = self.formatter.get_hand_strength_heuristic(hole_card, community_cards, current_street)
            # Calcula nível semântico da força da mão (educativo)
            hand_strength_level = self.formatter.get_hand_strength_level(hole_card, community_cards)
            hand_strength_with_level = f"{hand_strength} [{hand_strength_level}]"
            
            # Calcula probabilidade de vitória
            win_probability = None
            try:
                if hasattr(self, 'uuid') and self.uuid:
                    win_prob = calculate_win_probability_for_player(
                        player_uuid=self.uuid,
                        round_state=round_state
                    )
                    if win_prob is not None:
                        win_probability = round(win_prob * 100, 1)  # Converte para percentual
            except Exception as e:
                # Silenciosamente ignora erros no cálculo (não deve quebrar o jogo)
                pass
            
            # Formata saída com probabilidade se disponível
            if win_probability is not None:
                print(f"Suas cartas: {cards_display} | Mão: {hand_strength_with_level} | Probabilidade de vitória: {win_probability}%")
            else:
                print(f"Suas cartas: {cards_display} | Mão: {hand_strength_with_level}")
        
        # 2. Cartas comunitárias (quando existirem)
        if community_cards:
            community_display = self.formatter.format_cards_display_with_color(community_cards)
            print(f"Cartas comunitárias: {community_display}")
        
        # 3. Pot com composição e stack do jogador
        action_histories = round_state.get('action_histories', {})
        pot_amount, pot_composition = self.formatter.calculate_pot_composition(round_state, action_histories)
        
        seats = round_state.get('seats', [])
        my_stack = 0
        for seat in seats:
            if isinstance(seat, dict) and seat.get('uuid') == self.uuid:
                my_stack = seat.get('stack', 0)
                break
        
        # Se pot inicial, mostra composição; senão mostra valor
        if pot_amount <= 15 and current_street == 'preflop' and len(action_histories.get('preflop', [])) <= 2:
            pot_display = f"{pot_composition} = {pot_amount}"
        else:
            pot_display = self.formatter.format_pot_with_color(pot_amount)
        
        # Atualiza último pot impresso
        self.last_pot_printed = pot_amount
        
        stack_display = self.formatter.format_stack_with_color(my_stack, self.initial_stack, is_current=True)
        print(f"Pot: {pot_display} | Suas fichas: {stack_display}")
        
        # 4. Stacks dos outros jogadores numa única linha
        stacks_line = self.formatter.format_player_stacks(seats, self.uuid, self.initial_stack)
        if stacks_line:
            # Remove ":" do formato para simplificar
            stacks_line_clean = stacks_line.replace(': ', ' ')
            print(stacks_line_clean)
        
        # 5. Histórico sintético da street atual em linha única
        if action_histories:
            compact_history = self.formatter.format_compact_history(action_histories, current_street)
            if compact_history:
                # Extrai apenas a parte das ações (sem prefixo de street)
                if ':' in compact_history:
                    _, actions_part = compact_history.split(':', 1)
                    print(f"Ações anteriores: {actions_part.strip()}")
                else:
                    print(f"Ações anteriores: {compact_history}")
        
        # 6. Ações disponíveis com prefixos [f], [c], [r] numa única linha
        actions_display = self.formatter.format_action_costs(valid_actions)
        action_prefixes = ['f', 'c', 'r']
        action_line_parts = []
        for i, action_text in enumerate(actions_display):
            if i < len(action_prefixes):
                action_line_parts.append(f"[{action_prefixes[i]}] {action_text}")
        
        # Adiciona opção de sair
        action_line_parts.append("[q] Sair")
        
        if action_line_parts:
            print(f"Ações disponíveis: {' | '.join(action_line_parts)}")
        
        # Solicitar ação
        print()
        action, amount = self.__receive_action_from_console(valid_actions)
        return action, amount

    def receive_game_start_message(self, game_info):
        """Não imprime nada (ou apenas linha inicial mínima)."""
        # Silencioso - HUD será mostrado no turno do jogador
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        """Não imprime nada - HUD será mostrado no turno do jogador."""
        # Silencioso - informações aparecerão no HUD do declare_action
        # Reseta pot impresso para novo round
        self.last_pot_printed = 0
        # Limpa registro de cartas do round anterior
        clear_registry()
        # Armazena cartas do jogador em cache e no registro global
        if hole_card:
            self.my_hole_cards = hole_card
            if hasattr(self, 'uuid') and self.uuid:
                self.players_hole_cards[self.uuid] = hole_card
                store_player_cards(self.uuid, hole_card)
        # Tenta obter cartas dos outros jogadores dos seats se disponíveis
        if seats:
            for seat in seats:
                if isinstance(seat, dict):
                    seat_uuid = seat.get('uuid', '')
                    seat_hole_cards = seat.get('hole_card', None)
                    if seat_uuid and seat_hole_cards:
                        self.players_hole_cards[seat_uuid] = seat_hole_cards
                        store_player_cards(seat_uuid, seat_hole_cards)
        pass

    def receive_street_start_message(self, street, round_state):
        """Imprime bloco novo para nova street sem repetir dados estáticos."""
        street_pt = self.formatter.format_street_pt(street)
        print(f"\n–– {street_pt.upper()} ––")
        
        # Mostra apenas cartas comunitárias se existirem
        community_cards = round_state.get('community_card', [])
        if community_cards:
            community_display = self.formatter.format_cards_display_with_color(community_cards)
            print(f"Cartas comunitárias: {community_display}")
        
        # Mostra pot atualizado e atualiza último pot impresso
        action_histories = round_state.get('action_histories', {})
        pot_amount, _ = self.formatter.calculate_pot_composition(round_state, action_histories)
        pot_display = self.formatter.format_pot_with_color(pot_amount)
        print(f"Pot {pot_display}")
        self.last_pot_printed = pot_amount

    def receive_game_update_message(self, new_action, round_state):
        """Exibe apenas delta: quem agiu, ação, montante, novo pot, novo stack."""
        if not isinstance(new_action, dict):
            return
        
        # Quem agiu
        player_name = self.formatter.clean_player_name(new_action.get('player', ''))
        action_type = new_action.get('action', '')
        
        # Formata ação em português
        action_names = {
            'SMALLBLIND': 'SB',
            'BIGBLIND': 'BB',
            'FOLD': 'desistiu',
            'CALL': 'igualou' if new_action.get('paid', 0) > 0 else 'passou',
            'RAISE': 'aumentou',
            'CHECK': 'passou'
        }
        action_name = action_names.get(action_type, action_type.lower())
        
        # Montante
        amount = new_action.get('amount', 0)
        paid = new_action.get('paid', 0)
        
        # Novo pot
        pot = round_state.get('pot', {}).get('main', {}).get('amount', 0) if isinstance(round_state.get('pot'), dict) else 0
        
        # Novo stack do jogador afetado e todos os jogadores
        player_uuid = new_action.get('uuid', '')
        seats = round_state.get('seats', [])
        player_stack = None
        
        # Se não tem UUID no new_action, busca pelo nome
        if not player_uuid:
            for seat in seats:
                if isinstance(seat, dict):
                    seat_name = self.formatter.clean_player_name(seat.get('name', ''))
                    if seat_name == player_name:
                        player_uuid = seat.get('uuid', '')
                        break
        
        # Busca stack do jogador afetado
        for seat in seats:
            if isinstance(seat, dict) and seat.get('uuid') == player_uuid:
                player_stack = seat.get('stack', 0)
                break
        
        # Formata delta em formato compacto
        delta_parts = []
        
        # Ação básica
        if action_type in ['SMALLBLIND', 'BIGBLIND']:
            delta_parts.append(f"{player_name} {action_name} {amount}")
        elif action_type == 'FOLD':
            delta_parts.append(f"{player_name} {action_name}")
            # NOTA: Não removemos cartas do registry quando dá fold
            # As cartas são mantidas para histórico futuro, apenas não são exibidas no resultado
        elif action_type == 'CALL':
            if paid > 0:
                delta_parts.append(f"{player_name} {action_name} {paid}")
            else:
                delta_parts.append(f"{player_name} {action_name}")
        elif action_type == 'RAISE':
            delta_parts.append(f"{player_name} {action_name} {amount}")
        elif action_type == 'CHECK':
            delta_parts.append(f"{player_name} {action_name}")
        
        # Novo pot - só mostra se mudou
        if pot > 0 and pot != self.last_pot_printed:
            pot_display = self.formatter.format_pot_with_color(pot)
            delta_parts.append(f"Pot {pot_display}")
            self.last_pot_printed = pot
        
        # Stacks de todos os jogadores numa linha
        all_stacks = []
        for seat in seats:
            if isinstance(seat, dict):
                name = self.formatter.clean_player_name(seat.get('name', ''))
                stack = seat.get('stack', 0)
                stack_display = self.formatter.format_stack_with_color(stack, self.initial_stack, is_current=(seat.get('uuid') == self.uuid))
                all_stacks.append(f"{name} {stack_display}")
        
        if all_stacks:
            delta_parts.append(" | ".join(all_stacks))
        
        if delta_parts:
            print(" | ".join(delta_parts))

    def receive_round_result_message(self, winners, hand_info, round_state):
        """Mostra resultado final humanizado sem JSON bruto."""
        pot = round_state.get('pot', {}).get('main', {}).get('amount', 0) if isinstance(round_state.get('pot'), dict) else 0
        seats = round_state.get('seats', [])
        community_cards = round_state.get('community_card', [])
        current_street = round_state.get('street', 'river')
        
        # Processa winners (pode ser lista de dicts ou lista de strings/UUIDs)
        winner_uuids = []
        if winners:
            for winner in winners:
                if isinstance(winner, dict):
                    winner_uuids.append(winner.get('uuid', winner))
                else:
                    winner_uuids.append(winner)
        
        # Processa hand_info (pode ser dict ou lista)
        hand_info_dict = {}
        if isinstance(hand_info, dict):
            hand_info_dict = hand_info
        elif isinstance(hand_info, list):
            for item in hand_info:
                if isinstance(item, dict):
                    uuid = item.get('uuid', '')
                    hand_info_dict[uuid] = item
        
        if winner_uuids or seats:
            print("\n–––– RESULTADO DO ROUND ––––")
            
            # Mostra cartas dos participantes que não desistiram
            print("\nCartas dos participantes:")
            # Busca cartas do registro global uma única vez para eficiência
            all_cards = get_all_cards()
            
            for seat in seats:
                if isinstance(seat, dict):
                    seat_uuid = seat.get('uuid', '')
                    name = self.formatter.clean_player_name(seat.get('name', ''))
                    state = seat.get('state', '')
                    
                    # Determina se deve mostrar as cartas deste jogador
                    is_winner = seat_uuid in winner_uuids
                    is_folded = state == 'folded'
                    
                    # Se o jogador deu fold, mostra apenas o nome com "desistiu" (sem cartas)
                    # As cartas permanecem no registry para histórico futuro
                    if is_folded:
                        print(f"  {name}: desistiu")
                        continue
                    
                    # Verifica se o jogador tem cartas no registry
                    # Se tem cartas registradas, significa que participou do round até o final
                    # (não desistiu antes, mesmo que tenha feito all-in)
                    hole_cards = all_cards.get(seat_uuid)
                    has_cards = hole_cards is not None
                    
                    # Mostra cartas se:
                    # 1. O jogador é um vencedor (independente do estado)
                    # 2. OU o jogador tem cartas no registry (participou até o final, mesmo que tenha perdido)
                    #    (isso inclui jogadores que fizeram all-in e perderam)
                    if is_winner or has_cards:
                        if hole_cards:
                            cards_display = self.formatter.format_cards_display_with_color(hole_cards)
                            hand_desc = self.formatter.get_hand_strength_heuristic(hole_cards, community_cards, current_street)
                            print(f"  {name}: {cards_display} | {hand_desc}")
                        else:
                            # Se não encontrou no registry (não deveria acontecer), mostra erro
                            print(f"  {name}: [erro: cartas não encontradas no registry]")
                    else:
                        # Caso raro: jogador não é vencedor, não tem cartas no registry e não deu fold
                        # (não deveria acontecer, mas por segurança mostra "desistiu")
                        print(f"  {name}: desistiu")
            
            # Limpa cache de cartas para próximo round (registry será limpo no próximo round_start)
            self.players_hole_cards.clear()
            self.my_hole_cards = None
            
            # Mostra ganhador(es)
            if winner_uuids:
                winner_names = []
                for winner_uuid in winner_uuids:
                    for seat in seats:
                        if isinstance(seat, dict) and seat.get('uuid') == winner_uuid:
                            name = self.formatter.clean_player_name(seat.get('name', ''))
                            
                            # Tenta obter mão do ganhador do registro global
                            all_cards = get_all_cards()
                            hole_cards = all_cards.get(winner_uuid)
                            hand_desc = ""
                            if hole_cards:
                                hand_desc = self.formatter.get_hand_strength_heuristic(hole_cards, community_cards, current_street)
                            
                            if hand_desc:
                                winner_names.append(f"{name} ({hand_desc})")
                            else:
                                winner_names.append(name)
                            break
                
                if winner_names:
                    winner_line = " | ".join(winner_names)
                    pot_display = self.formatter.format_pot_with_color(pot)
                    print(f"\nGanhador(es): {winner_line} | Pot: {pot_display}")
            
            # Mostra stacks finais
            final_stacks = []
            for seat in seats:
                if isinstance(seat, dict):
                    name = self.formatter.clean_player_name(seat.get('name', ''))
                    stack = seat.get('stack', 0)
                    final_stacks.append(f"{name} {stack}")
            
            if final_stacks:
                print(f"\nStacks finais:")
                print(" | ".join(final_stacks))
            
            # Pausa para aguardar input antes de continuar
            print()
            self.__wait_for_continue()
            
            # Reseta pot impresso para próximo round
            self.last_pot_printed = 0
            # Limpa cache de cartas (já foi limpo acima, mas garantindo)
            self.players_hole_cards.clear()
            self.my_hole_cards = None

    def __wait_until_input(self):
        """Método não utilizado mais - mantido para compatibilidade."""
        pass
    
    def __wait_for_continue(self):
        """Aguarda input do usuário antes de continuar."""
        try:
            user_input = input("Pressione Enter para continuar (ou 'q' para sair)... ")
            if user_input.strip().lower() == 'q':
                raise QuitGameException()
        except (EOFError, KeyboardInterrupt):
            # Se não houver input disponível (ex: em testes), continua silenciosamente
            pass

    def __gen_raw_input_wrapper(self):
        return lambda msg: input(msg)

    def __receive_action_from_console(self, valid_actions):
        """Solicita ação do jogador de forma limpa."""
        try:
            flg = self.input_receiver('>> ').strip().lower()
            # Verifica se o jogador quer sair
            if flg == 'q':
                raise QuitGameException()
            
            if flg in self.__gen_valid_flg(valid_actions):
                if flg == 'f':
                    return valid_actions[0]['action'], valid_actions[0]['amount']
                elif flg == 'c':
                    return valid_actions[1]['action'], valid_actions[1]['amount']
                elif flg == 'r':
                    valid_amounts = valid_actions[2]['amount']
                    raise_amount = self.__receive_raise_amount_from_console(valid_amounts['min'], valid_amounts['max'])
                    return valid_actions[2]['action'], raise_amount
            else:
                print("Ação inválida. Use [f], [c], [r] ou [q] para sair")
                return self.__receive_action_from_console(valid_actions)
        except QuitGameException:
            # Re-raise para ser capturado no nível superior
            raise

    def __gen_valid_flg(self, valid_actions):
        flgs = ['f', 'c']
        is_raise_possible = valid_actions[2]['amount']['min'] != -1
        if is_raise_possible:
            flgs.append('r')
        return flgs

    def __receive_raise_amount_from_console(self, min_amount, max_amount):
        try:
            raw_amount = self.input_receiver(f"Valor ({min_amount}-{max_amount}) ou 'q' para sair: ").strip().lower()
            # Verifica se o jogador quer sair
            if raw_amount == 'q':
                raise QuitGameException()
            
            try:
                amount = int(raw_amount)
                if min_amount <= amount and amount <= max_amount:
                    return amount
                else:
                    print(f"Valor inválido. Use {min_amount}-{max_amount}")
                    return self.__receive_raise_amount_from_console(min_amount, max_amount)
            except ValueError:
                print("Entrada inválida. Digite um número ou 'q' para sair.")
                return self.__receive_raise_amount_from_console(min_amount, max_amount)
        except QuitGameException:
            # Re-raise para ser capturado no nível superior
            raise

