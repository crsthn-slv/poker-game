"""
Formatador para exibição de informações no console do terminal.
Inclui cores ANSI e formatação de cartas, pot, stacks, etc.
"""

import sys
from .hand_utils import (
    evaluate_hand_strength,
    score_to_hand_name,
    score_to_strength_level,
    score_to_strength_level_heuristic,
    get_community_cards,
    normalize_hole_cards,
)
from .constants import MIN_COMMUNITY_CARDS_FOR_POKERKIT

# Tenta importar HandEvaluator, mas não é obrigatório
try:
    from .hand_evaluator import HandEvaluator
    HAS_POKERKIT = True
except ImportError:
    HAS_POKERKIT = False
    HandEvaluator = None


class ConsoleFormatter:
    """Formatador para exibição no terminal com cores ANSI."""
    
    # Códigos ANSI para cores
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Cores de texto
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    DIM = '\033[2m'  # Texto opaco/desbotado (para jogadores que fizeram fold)
    GRAY = '\033[90m'  # Cinza escuro (alternativa para texto opaco)
    
    # Cores de fundo
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    
    def __init__(self):
        # Tenta inicializar HandEvaluator se PokerKit estiver disponível
        if HAS_POKERKIT and HandEvaluator:
            try:
                self.hand_evaluator = HandEvaluator()
            except Exception:
                self.hand_evaluator = None
        else:
            self.hand_evaluator = None
        # Mapeamento de naipes para símbolos e cores
        self.suit_map = {
            'S': ('♠', self.WHITE),      # Spades (Paus) - branco
            'H': ('♥', self.RED),        # Hearts (Copas) - vermelho
            'D': ('♦', self.RED),        # Diamonds (Ouros) - vermelho
            'C': ('♣', self.WHITE)       # Clubs (Espadas) - branco
        }
        # Mapeamento de ranks
        self.rank_map = {
            '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7',
            '8': '8', '9': '9', 'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'
        }
    
    def format_cards_display_with_color(self, cards):
        """Formata cartas com cores e símbolos de naipes.
        
        Args:
            cards: Lista de cartas no formato PyPokerEngine (ex: ['SA', 'HK'])
        
        Returns:
            String formatada (ex: "A♠ K♥")
        """
        if not cards:
            return ""
        
        formatted_cards = []
        for card in cards:
            if not card or len(card) < 2:
                continue
            
            suit = card[0].upper()
            rank = card[1:].upper()
            
            suit_symbol, suit_color = self.suit_map.get(suit, ('?', self.WHITE))
            rank_display = self.rank_map.get(rank, rank)
            
            # Formata: rank + símbolo do naipe com cor
            formatted_card = f"{suit_color}{rank_display}{suit_symbol}{self.RESET}"
            formatted_cards.append(formatted_card)
        
        return " ".join(formatted_cards)
    
    def format_pot_with_color(self, pot_amount):
        """Formata pot com cor.
        
        Args:
            pot_amount: Valor do pot
        
        Returns:
            String formatada com cor
        """
        if pot_amount <= 0:
            return f"{self.CYAN}0{self.RESET}"
        
        # Pot grande = verde, médio = amarelo, pequeno = ciano
        if pot_amount >= 150:
            color = self.GREEN
        elif pot_amount >= 50:
            color = self.YELLOW
        else:
            color = self.CYAN
        
        return f"{color}{pot_amount}{self.RESET}"
    
    def format_stack_with_color(self, stack, initial_stack, is_current=False):
        """Formata stack com cor baseado no valor relativo ao inicial.
        
        Args:
            stack: Stack atual
            initial_stack: Stack inicial
            is_current: Se é o stack do jogador atual
        
        Returns:
            String formatada com cor
        """
        if is_current:
            # Stack do jogador atual sempre em verde
            return f"{self.GREEN}{stack}{self.RESET}"
        
        # Outros jogadores: verde se acima do inicial, vermelho se abaixo
        if stack > initial_stack:
            color = self.GREEN
        elif stack < initial_stack * 0.7:
            color = self.RED
        else:
            color = self.YELLOW
        
        return f"{color}{stack}{self.RESET}"
    
    def format_player_stacks(self, seats, current_uuid, initial_stack):
        """Formata stacks de todos os jogadores em uma linha.
        
        Args:
            seats: Lista de assentos/jogadores
            current_uuid: UUID do jogador atual
            initial_stack: Stack inicial
        
        Returns:
            String formatada
        """
        if not seats:
            return ""
        
        stack_parts = []
        for seat in seats:
            if not isinstance(seat, dict):
                continue
            
            name = self.clean_player_name(seat.get('name', ''))
            stack = seat.get('stack', 0)
            seat_uuid = seat.get('uuid', '')
            
            is_current = (seat_uuid == current_uuid)
            stack_display = self.format_stack_with_color(stack, initial_stack, is_current)
            stack_parts.append(f"{name}: {stack_display}")
        
        return " | ".join(stack_parts)
    
    def format_compact_history(self, action_histories, current_street, round_state=None):
        """Formata histórico de ações de forma compacta.
        Mostra todas as ações de todas as streets (exceto fold).
        
        Args:
            action_histories: Dict com histórico de ações por street
            current_street: Street atual
            round_state: Estado do round (opcional, para buscar nomes dos jogadores)
        
        Returns:
            String formatada
        """
        if not action_histories:
            return ""
        
        # Cria mapa UUID -> nome dos jogadores se round_state disponível
        uuid_to_name = {}
        if round_state:
            seats = round_state.get('seats', [])
            for seat in seats:
                if isinstance(seat, dict):
                    uuid = seat.get('uuid', '')
                    name = seat.get('name', '')
                    if uuid and name:
                        uuid_to_name[uuid] = self.clean_player_name(name)
        
        # Ordem das streets
        street_order = ['preflop', 'flop', 'turn', 'river']
        
        action_parts = []
        for street in street_order:
            # Só processa streets que já aconteceram (até a street atual)
            if street not in action_histories:
                continue
            
            street_history = action_histories.get(street, [])
            if not street_history:
                continue
            
            for action in street_history:
                if not isinstance(action, dict):
                    continue
                
                action_type = action.get('action', '')
                
                # Pula fold (não mostra)
                if action_type == 'FOLD':
                    continue
                
                # Tenta obter nome do jogador de várias formas
                player_name = action.get('player', '')
                player_uuid = action.get('uuid', '')
                
                # Se não tem nome mas tem UUID, busca no round_state
                if not player_name and player_uuid and uuid_to_name:
                    player_name = uuid_to_name.get(player_uuid, '')
                
                # Se ainda não tem nome, usa UUID ou "Desconhecido"
                if not player_name:
                    if player_uuid:
                        # Tenta usar parte do UUID como fallback (últimos 4 caracteres)
                        player_name = f"Player {player_uuid[-4:]}" if len(player_uuid) >= 4 else "Unknown"
                    else:
                        player_name = "Unknown"
                else:
                    player_name = self.clean_player_name(player_name)
                
                amount = action.get('amount', 0)
                paid = action.get('paid', 0)  # Valor pago no call
                
                # Traduz ação para português com valores quando aplicável
                if action_type == 'SMALLBLIND':
                    action_display = f'SB {amount}'
                elif action_type == 'BIGBLIND':
                    action_display = f'BB {amount}'
                elif action_type == 'CALL':
                    # Mostra valor pago se houver
                    if paid > 0:
                        action_display = f'call {paid}'
                    else:
                        action_display = 'call'
                elif action_type == 'RAISE':
                    action_display = f'raise {amount}'
                elif action_type == 'CHECK':
                    action_display = 'check'
                else:
                    action_display = action_type.lower()
                
                action_parts.append(f"{player_name}: {action_display}")
        
        return ", ".join(action_parts)
    
    def format_history_by_player(self, action_histories, current_street, round_state=None):
        """Formata histórico de ações agrupado por jogador.
        Cada jogador tem uma linha mostrando todas as suas ações.
        
        Args:
            action_histories: Dict com histórico de ações por street
            current_street: Street atual
            round_state: Estado do round (opcional, para buscar nomes dos jogadores)
        
        Returns:
            Lista de strings, uma para cada jogador com suas ações
        """
        if not action_histories:
            return []
        
        # Cria mapa UUID -> nome dos jogadores e UUID -> stack
        uuid_to_name = {}
        uuid_to_stack = {}  # Mapa UUID -> stack atual
        player_order = []  # Mantém ordem de aparição dos jogadores
        if round_state:
            seats = round_state.get('seats', [])
            for seat in seats:
                if isinstance(seat, dict):
                    uuid = seat.get('uuid', '')
                    name = seat.get('name', '')
                    stack = seat.get('stack', 0)
                    if uuid:
                        if name:
                            clean_name = self.clean_player_name(name)
                            uuid_to_name[uuid] = clean_name
                        if stack is not None:
                            uuid_to_stack[uuid] = stack
                        if uuid not in player_order:
                            player_order.append(uuid)
        
        # Agrupa ações por jogador
        player_actions = {}  # {player_uuid: [(street, action_type, amount, paid)]}
        
        # Ordem das streets
        street_order = ['preflop', 'flop', 'turn', 'river']
        
        for street in street_order:
            if street not in action_histories:
                continue
            
            street_history = action_histories.get(street, [])
            if not street_history:
                continue
            
            for action in street_history:
                if not isinstance(action, dict):
                    continue
                
                action_type = action.get('action', '')
                player_uuid = action.get('uuid', '')
                
                # Obtém nome do jogador
                player_name = action.get('player', '')
                if not player_name and player_uuid and uuid_to_name:
                    player_name = uuid_to_name.get(player_uuid, '')
                if not player_name and player_uuid:
                    # Usa UUID como fallback
                    player_name = f"Player {player_uuid[-4:]}" if len(player_uuid) >= 4 else "Unknown"
                    uuid_to_name[player_uuid] = player_name
                    if player_uuid not in player_order:
                        player_order.append(player_uuid)
                
                if not player_uuid:
                    # Se não tem UUID, tenta usar o nome como chave
                    player_uuid = player_name if player_name else "unknown"
                
                # Inicializa lista de ações do jogador se necessário
                if player_uuid not in player_actions:
                    player_actions[player_uuid] = []
                
                amount = action.get('amount', 0)
                paid = action.get('paid', 0)
                
                # Formata ação
                if action_type == 'SMALLBLIND':
                    action_display = f'SB({amount})'
                elif action_type == 'BIGBLIND':
                    action_display = f'BB({amount})'
                elif action_type == 'CALL':
                    if paid > 0:
                        action_display = f'call({paid})'
                    else:
                        action_display = 'check'
                elif action_type == 'RAISE':
                    action_display = f'raise({amount})'
                elif action_type == 'CHECK':
                    action_display = 'check'
                elif action_type == 'FOLD':
                    action_display = 'fold'
                else:
                    action_display = action_type.lower()
                
                player_actions[player_uuid].append(action_display)
        
        # Formata saída: uma linha por jogador
        result = []
        # Usa ordem dos seats primeiro, depois ordem de aparição nas ações
        all_player_uuids = []
        for uuid in player_order:
            if uuid in player_actions:
                all_player_uuids.append(uuid)
        for uuid in player_actions:
            if uuid not in all_player_uuids:
                all_player_uuids.append(uuid)
        
        # Calcula comprimento máximo do nome para alinhar os stacks
        max_name_length = 0
        for player_uuid in all_player_uuids:
            if player_uuid in player_actions:
                player_name = uuid_to_name.get(player_uuid, player_uuid)
                max_name_length = max(max_name_length, len(player_name))
        
        # Formata cada linha com alinhamento
        for player_uuid in all_player_uuids:
            if player_uuid in player_actions:
                player_name = uuid_to_name.get(player_uuid, player_uuid)
                actions_str = ' → '.join(player_actions[player_uuid])
                
                # Obtém stack do jogador (se disponível)
                player_stack = uuid_to_stack.get(player_uuid)
                
                # Alinha o nome e adiciona stack entre parênteses
                padded_name = player_name.ljust(max_name_length)
                if player_stack is not None:
                    name_with_stack = f"{padded_name} ({player_stack})"
                else:
                    name_with_stack = padded_name
                
                # Verifica se o jogador fez fold para tornar a linha inteira opaca
                has_folded = 'fold' in player_actions[player_uuid]
                if has_folded:
                    # Aplica formatação opaca à linha inteira
                    full_line = f"  {name_with_stack}: {actions_str}"
                    formatted_line = f"{self.DIM}{full_line}{self.RESET}"
                    result.append(formatted_line)
                else:
                    result.append(f"  {name_with_stack}: {actions_str}")
        
        return result
    
    def format_action_costs(self, valid_actions):
        """Formata custos das ações disponíveis.
        
        Args:
            valid_actions: Lista de ações válidas do PyPokerEngine
        
        Returns:
            Lista de strings formatadas
        """
        if not valid_actions:
            return []
        
        action_texts = []
        for action in valid_actions:
            action_type = action.get('action', '')
            amount = action.get('amount', 0)
            
            if action_type == 'fold':
                action_texts.append("FOLD")
            elif action_type == 'call':
                if amount > 0:
                    action_texts.append(f"CALL ({amount})")
                else:
                    action_texts.append("CHECK (0)")
            elif action_type == 'raise':
                min_raise = action.get('amount', {}).get('min', 0)
                max_raise = action.get('amount', {}).get('max', 0)
                if min_raise == max_raise:
                    action_texts.append(f"RAISE ({min_raise})")
                else:
                    action_texts.append(f"RAISE ({min_raise}-{max_raise})")
        
        return action_texts
    
    def calculate_pot_composition(self, round_state, action_histories):
        """Calcula valor do pot e sua composição inicial.
        
        Args:
            round_state: Estado do round
            action_histories: Histórico de ações
        
        Returns:
            Tupla (pot_amount, pot_composition_string)
        """
        # Tenta obter pot do round_state
        pot = round_state.get('pot', {})
        if isinstance(pot, dict):
            main_pot = pot.get('main', {})
            if isinstance(main_pot, dict):
                pot_amount = main_pot.get('amount', 0)
            else:
                pot_amount = pot.get('main', 0) if isinstance(pot.get('main'), (int, float)) else 0
        else:
            pot_amount = pot if isinstance(pot, (int, float)) else 0
        
        # Se pot é pequeno e estamos no preflop, mostra composição
        if pot_amount <= 15 and action_histories:
            preflop_actions = action_histories.get('preflop', [])
            if len(preflop_actions) <= 2:
                # Pot inicial: SB + BB
                small_blind = 0
                big_blind = 0
                for action in preflop_actions:
                    if action.get('action') == 'SMALLBLIND':
                        small_blind = action.get('amount', 0)
                    elif action.get('action') == 'BIGBLIND':
                        big_blind = action.get('amount', 0)
                
                if small_blind > 0 or big_blind > 0:
                    pot_composition = f"SB({small_blind})+BB({big_blind})"
                    return pot_amount, pot_composition
        
        return pot_amount, ""
    
    def get_hand_strength_heuristic(self, hole_cards, community_cards, street):
        """Calcula força heurística da mão.
        
        Args:
            hole_cards: Cartas do jogador
            community_cards: Cartas comunitárias
            street: Street atual
        
        Returns:
            String descrevendo a força da mão
        """
        if not hole_cards or len(hole_cards) < 2:
            return "No Cards"
        
        # Se há cartas comunitárias suficientes, avalia mão completa com PokerKit
        if (community_cards and 
            len(community_cards) >= MIN_COMMUNITY_CARDS_FOR_POKERKIT and 
            self.hand_evaluator):
            try:
                score = self.hand_evaluator.evaluate(hole_cards, community_cards)
                # Usa função centralizada para converter score → nome da mão
                return score_to_hand_name(score)
            except Exception:
                pass
        
        # No preflop ou quando não há cartas comunitárias suficientes,
        # mostra a melhor mão possível com as hole cards
        card_ranks = [card[1] for card in hole_cards]
        card_suits = [card[0] for card in hole_cards]
        
        # Verifica se há par nas hole cards
        if card_ranks[0] == card_ranks[1]:
            return "One Pair"
        else:
            # Verifica se há cartas do mesmo naipe (flush draw potencial)
            if card_suits[0] == card_suits[1]:
                # Se há cartas comunitárias, verifica quantas do mesmo naipe
                if community_cards:
                    same_suit_community = [c for c in community_cards if c[0] == card_suits[0]]
                    if len(same_suit_community) >= 3:
                        return "Flush Draw"
                    elif len(same_suit_community) >= 1:
                        return "High Card (Flush Draw)"
                # No preflop, mesmo naipe indica potencial de flush
                return "High Card (Suited)"
            # Sem par e sem mesmo naipe, a melhor mão possível é High Card
            return "High Card"
    
    def get_hand_strength_level(self, hole_cards, community_cards):
        """Retorna nível semântico da força da mão.
        
        Args:
            hole_cards: Cartas do jogador
            community_cards: Cartas comunitárias
        
        Returns:
            String com nível (ex: "Premium", "Marginal", etc.)
        """
        if not hole_cards or len(hole_cards) < 2:
            return "N/A"
        
        # Se há cartas comunitárias suficientes, usa PokerKit para avaliação precisa
        if (community_cards and 
            len(community_cards) >= MIN_COMMUNITY_CARDS_FOR_POKERKIT and 
            self.hand_evaluator):
            try:
                score = self.hand_evaluator.evaluate(hole_cards, community_cards)
                # Usa função centralizada para converter score → nível de força
                return score_to_strength_level(score)
            except Exception:
                # Se falhar, usa avaliação básica
                pass
        
        # Avaliação básica (fallback ou quando não há cartas comunitárias suficientes)
        # No preflop, avalia apenas as hole cards
        base_strength = evaluate_hand_strength(hole_cards, community_cards)
        # Usa função centralizada para converter score heurístico → nível de força
        return score_to_strength_level_heuristic(base_strength)
    
    def format_street_pt(self, street):
        """Traduz street para português.
        
        Args:
            street: Street em inglês
        
        Returns:
            String em português
        """
        # Streets já estão em inglês, apenas capitaliza
        street_map = {
            'preflop': 'Preflop',
            'flop': 'Flop',
            'turn': 'Turn',
            'river': 'River'
        }
        return street_map.get(street, street.capitalize())
    
    def clean_player_name(self, name):
        """Remove caracteres especiais do nome do jogador.
        
        Args:
            name: Nome do jogador
        
        Returns:
            Nome limpo
        """
        if not name:
            return "Unknown"
        
        # Remove UUIDs e caracteres especiais se presentes
        # Normalmente o nome já vem limpo, mas por segurança
        return str(name).strip()

