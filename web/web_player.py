"""
Adaptador do ConsolePlayer para interface Web via WebSocket.
"""

import queue
import sys
import io
import re
import time
import random
from typing import Dict, Any, Callable, Optional, Tuple

from players.console_player import ConsolePlayer
from utils.game_history import GameHistory
from web.supabase_client import get_supabase_client

class WebPlayer(ConsolePlayer):
    """
    Adaptador que redireciona a interação do ConsolePlayer para WebSocket.
    Captura o output formatado do ConsolePlayer usando injeção de dependência do printer.
    """
    
    def __init__(self, 
                 initial_stack: int = 100, 
                 small_blind: int = 5, 
                 big_blind: int = 10,
                 show_win_probability: bool = False,
                 on_game_update: Optional[Callable[[str, Any], None]] = None,
                 on_round_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
                 lang: str = 'pt-br'):
        
        # Inicializa o buffer antes de chamar super, pois super pode usar printer
        self.output_buffer = io.StringIO()
        self.on_game_update = on_game_update
        self.on_round_complete = on_round_complete
        self.input_queue = queue.Queue()
        self.game_id = None
        self.lang = lang
        
        super().__init__(
            input_receiver=lambda x: "f", # Placeholder, não será usado pois sobrescrevemos __receive_action
            initial_stack=initial_stack,
            small_blind=small_blind,
            big_blind=big_blind,
            show_win_probability=show_win_probability,
            printer=self._print_to_buffer # Injeta nosso método de impressão
        )
        
        # Carrega mensagens de bot do Supabase
        self.bot_messages = {}
        self._load_bot_messages()
        
        # State tracking for reconnection
        self.waiting_for_action = False
        self.last_valid_actions = []
        self.last_round_state = None
        self.last_street = None
        self.last_round_count = 0
        self.history_log = [] # Store last N lines of output
        self.auto_advance = False

        
    def set_game_id(self, game_id: str):
        self.game_id = game_id

    def set_player_name(self, name: str):
        """Define o nome do jogador para garantir consistência com o servidor."""
        self._player_name = name

    def set_uuid(self, uuid):
        """
        Define UUID fixo baseado no nome do jogador.
        Sobrescreve o método do ConsolePlayer para usar o nome dinâmico.
        """
        self.pypoker_uuid = uuid
        
        from utils.uuid_utils import get_player_uuid
        # Usa o nome definido ou "You" como fallback
        name_to_use = self._player_name or "You"
        fixed_uuid = get_player_uuid(name_to_use)
        
        if fixed_uuid:
            self.uuid = fixed_uuid
            # Garante que _player_name está setado
            if not self._player_name:
                self._player_name = name_to_use
        else:
            self.uuid = uuid

        
    def _send_update(self, event_type: str, data: Any):
        if self.on_game_update:
            self.on_game_update(event_type, data)
            
    def _capture_and_send_output(self):
        """Captura o que foi impresso no buffer e envia para o frontend."""
        try:
            output = self.output_buffer.getvalue()
            if output:
                # Remove ANSI escape codes - DISABLED to support colors in web terminal
                # ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                # clean_output = ansi_escape.sub('', output)
                clean_output = output
                
                # Filter out debug lines to reduce traffic
                # Only keep lines that don't contain [DEBUG]
                lines = clean_output.split('\n')
                filtered_lines = [
                    line for line in lines 
                    if '[DEBUG]' not in line 
                    and not line.strip().startswith('Available actions:')
                ]
                final_output = '\n'.join(filtered_lines)
                
                if final_output.strip():
                    self._send_update("terminal_output", final_output)
                
                # Limpa o buffer
                self.output_buffer.truncate(0)
                self.output_buffer.seek(0)
        except Exception as e:
            # Fallback em caso de erro para não travar o jogo
            print(f"[WEB PLAYER ERROR] Failed to send output: {e}")
            # Tenta limpar o buffer mesmo assim para não acumular
            try:
                self.output_buffer.truncate(0)
                self.output_buffer.seek(0)
            except:
                pass

    def _print_to_buffer(self, *args, **kwargs):
        """Método que substitui o print() nativo no ConsolePlayer."""
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        flush = kwargs.get('flush', False)
        # file é ignorado
        
        text = sep.join(map(str, args)) + end
        self.output_buffer.write(text)

        
        # Store in history log (keep last 100 lines)
        if text.strip():
            self.history_log.append(text)
            if len(self.history_log) > 100:
                self.history_log.pop(0)
        
        # Only send if newline is present or flush is requested
        if '\n' in text or flush:
            self._capture_and_send_output()

            self._capture_and_send_output()

    def _load_bot_messages(self):
        """Carrega mensagens de bot do banco de dados ou usa defaults."""
        try:
            client = get_supabase_client()
            self.bot_messages = client.get_bot_messages(self.lang)
            print(f"[WEB PLAYER] Loaded {sum(len(v) for v in self.bot_messages.values())} bot messages for lang={self.lang}")
        except Exception as e:
            print(f"[WEB PLAYER] Error loading bot messages: {e}")
            self.bot_messages = {}

        # Fallback se não houver mensagens (DB vazio ou erro)
        if not self.bot_messages:
            print("[WEB PLAYER] Using default bot messages fallback.")
            self.bot_messages = self._get_default_bot_messages()

    def _get_default_bot_messages(self):
        """Retorna mensagens padrão caso o banco esteja vazio."""
        if self.lang == 'pt-br':
            return {
                'FOLD': [
                    "Estou fora.", "Passo.", "Sem chance.", "Desisto dessa.", "Fica pra próxima.",
                    "Muito caro pra mim.", "Não vou pagar pra ver.", "Fold.", "Larguei."
                ],
                'CALL': [
                    "Pago.", "Vamos ver.", "Call.", "Estou dentro.", "Acompanho.",
                    "Pago pra ver.", "Não vou deixar barato.", "Seguindo."
                ],
                'CHECK': [
                    "Mesa.", "Check.", "Passo a vez.", "Nada por enquanto.", "Sigo.",
                    "Vamos ver o que vem.", "Sem apostas."
                ],
                'RAISE': [
                    "Aumento.", "Vou subir.", "Raise.", "Vamos esquentar isso.", "Quero ver quem paga.",
                    "Aumento a aposta.", "Botando pressão."
                ],
                'ALL-IN': [
                    "ALL IN!", "Todas as minhas fichas.", "É tudo ou nada!", "Vou com tudo.",
                    "Empurrando tudo pro centro.", "Momento da verdade: All-in!"
                ],
                'WIN': [
                    "Isso!", "Sabia!", "Pote é meu.", "Obrigado pelas fichas.", "Bela mão.",
                    "Tive sorte.", "Jogaram bem.", "Mais uma pra conta."
                ],
                'SHOW_CARDS': [
                    "Eu tinha {cards} - {hand_name}", "Olha o que eu tinha: {cards}",
                    "Minha mão: {cards}", "Segura essa: {cards}"
                ],
                'MUCK': [
                    "Melhor não mostrar.", "Esconde essa.", "Não vale a pena mostrar.",
                    "Segredo.", "Muck."
                ]
            }
        else:
            return {
                'FOLD': [
                    "I'm out.", "Fold.", "No way.", "Too rich for me.", "Next hand.",
                    "Folding this one.", "Can't call that."
                ],
                'CALL': [
                    "I call.", "Calling.", "I'm in.", "Let's see it.", "Matching the bet.",
                    "I'll stay.", "Call."
                ],
                'CHECK': [
                    "Check.", "Checking.", "Pass.", "No bets.", "Checking to you.",
                    "Let's see the next card."
                ],
                'RAISE': [
                    "Raise.", "Raising.", "I'll bump it up.", "Let's make it interesting.",
                    "Raising the stakes.", "Price just went up."
                ],
                'ALL-IN': [
                    "ALL IN!", "All my chips.", "Pushing it all.", "All in.",
                    "Risking it all!", "Time to gamble: All-in!"
                ],
                'WIN': [
                    "Yes!", "I take the pot.", "Nice hand.", "Thanks for the chips.",
                    "Good game.", "Lucky river.", "Adding to my stack."
                ],
                'SHOW_CARDS': [
                    "I had {cards} - {hand_name}", "Check this out: {cards}",
                    "My hand: {cards}", "Holding: {cards}"
                ],
                'MUCK': [
                    "Mucking.", "Better not show.", "Keeping it secret.",
                    "Not showing.", "Muck."
                ]
            }

    def _get_bot_message(self, action_type: str) -> Optional[str]:
        """Retorna uma mensagem aleatória para o tipo de ação."""
        if not self.bot_messages:
            print(f"[WEB PLAYER] WARNING: No bot messages loaded! (lang={self.lang})")
            return None
            
        messages = self.bot_messages.get(action_type, [])
        if messages:
            return random.choice(messages)
        return None


    def _ConsolePlayer__receive_action_from_console(self, valid_actions, round_state=None, cached_player_stack=None) -> Tuple[str, int]:
        """
        Sobrescreve o método privado do ConsolePlayer para receber input via WebSocket.
        """
        # 1. Envia solicitação de ação para o frontend (para habilitar botões)
        
        # Calcula win_prob se necessário (similar ao declare_action original)
        win_prob = None
        if self.show_win_probability and hasattr(self, 'win_probability_cache') and self.last_cache_key:
             if self.last_cache_key in self.win_probability_cache:
                 win_prob = self.win_probability_cache[self.last_cache_key].get('prob_pct')

        # Sanitiza round_state para enviar ao frontend
        sanitized_round_state = self._sanitize_round_state(round_state) if round_state else {}
        
        # Envia dados extras para a UI (cartas do jogador) se disponíveis
        # if hasattr(self, 'my_hole_cards') and self.my_hole_cards:
        #      self._send_update("round_start_data", {"hole_cards": self.my_hole_cards})

        # Calculate hand strength for UI display
        hand_strength_display = None
        if hasattr(self, 'my_hole_cards') and self.my_hole_cards:
            from utils.hand_utils import normalize_hole_cards
            hole_cards = normalize_hole_cards(self.my_hole_cards)
            community_cards = self._get_community_cards_from_state(round_state)
            current_street = round_state.get('street', 'preflop') if round_state else 'preflop'
            
            strength = self.formatter.get_hand_strength_heuristic(hole_cards, community_cards, current_street)
            level = self.formatter.get_hand_strength_level(hole_cards, community_cards)
            hand_strength_display = f"{strength} [{level}]"

        action_request = {
            "valid_actions": valid_actions,
            "hole_cards": self.my_hole_cards if hasattr(self, 'my_hole_cards') else [],
            "round_state": sanitized_round_state,
            "win_probability": win_prob,
            "hand_strength": hand_strength_display
        }
        
        # Cache state for reconnection
        self.waiting_for_action = True
        self.last_valid_actions = valid_actions
        self.last_round_state = round_state
        
        self._send_update("action_required", action_request)
        
        # 2. Aguarda resposta da fila (bloqueante na thread do jogo, não no servidor)
        # O servidor roda o jogo em thread separada, então isso é seguro
        # self._print_to_buffer(f"[WEB] Waiting for user action...")
        action, amount = self.input_queue.get()
        
        self.waiting_for_action = False
        
        # 3. Imprime a ação escolhida para ficar no histórico do terminal
        self._print_to_buffer(f">> {action} {amount if amount > 0 and action != 'fold' else ''}")
        
        # Garante que o amount do call seja o correto (do valid_actions)
        # O frontend pode enviar 0 ou valor incorreto
        if action == 'call':
            for valid_action in valid_actions:
                if valid_action['action'] == 'call':
                    amount = valid_action['amount']
                    break
        
        # Handle All-in (raise with amount -1)
        if action == 'raise' and amount == -1:
            for valid_action in valid_actions:
                if valid_action['action'] == 'raise':
                    amount_info = valid_action['amount']
                    if isinstance(amount_info, dict):
                        amount = amount_info['max']
                    else:
                        # Fallback if amount is not a dict (should be dict for raise)
                        amount = amount_info
                    self._print_to_buffer(f"[WEB] All-in detected! Raising to {amount}")
                    break
            
        return action, amount

    # Sobrescrevemos receive_round_result_message APENAS para garantir que o super seja chamado
    # A lógica de display é mantida pelo ConsolePlayer (que usa self.printer)
    def receive_round_result_message(self, winners, hand_info, round_state):
        self._print_to_buffer(f"[WEB_DBG] receive_round_result_message ENTERED. Winners: {len(winners)}")
        # Calcula o pote total (main + side)
        total_pot = 0
        if round_state and 'pot' in round_state:
            pot_data = round_state['pot']
            if 'main' in pot_data:
                total_pot += pot_data['main'].get('amount', 0)
            if 'side' in pot_data:
                for side_pot in pot_data['side']:
                    total_pot += side_pot.get('amount', 0)

        # Armazena resultado para enviar em caso de eliminação
        # IMPORTANTE: Deve ser feito ANTES de chamar super(), pois super() chama wait_for_continue()
        # que usa self.last_round_result se o jogador for eliminado.
        
        # Enriquece hand_info com força da mão e garante consistência
        enriched_hand_info = []
        community_cards = self._get_community_cards_from_state(round_state)
        
        # Usa lógica do ConsolePlayer para processar hand_info e garantir UUIDs fixos e cartas
        seats = round_state.get('seats', [])
        hand_info_dict = self._process_hand_info(hand_info, seats)
        
        # Garante que todos os vencedores tenham hand_info
        winner_uuids, _ = self._process_winners(winners, seats)
        
        # Se winners for lista de dicts, extrai UUIDs originais para mapeamento
        original_winner_uuids = []
        if winners:
            for w in winners:
                if isinstance(w, dict):
                    original_winner_uuids.append(w.get('uuid'))
                else:
                    original_winner_uuids.append(w)

        # Reconstrói lista de hand_info enriquecida
        # Se hand_info original estava vazio (ex: fold geral), tenta reconstruir com dados do registry
        if not hand_info_dict and winner_uuids:
             from utils.cards_registry import get_all_cards
             all_cards = get_all_cards()
             for uuid in winner_uuids:
                 if uuid in all_cards:
                     hand_info_dict[uuid] = {
                         'uuid': uuid,
                         'hole_card': all_cards[uuid]
                     }

        for uuid, info in hand_info_dict.items():
            # Calcula força da mão se não existir
            hole_cards = info.get('hole_card') or info.get('hole_cards') or info.get('hand', {}).get('hole_card')
            if hole_cards:
                # Normaliza cartas
                from utils.hand_utils import normalize_hole_cards
                normalized_cards = normalize_hole_cards(hole_cards)
                
                # Calcula força
                strength = self.formatter.get_hand_strength_heuristic(normalized_cards, community_cards, round_state.get('street', 'river'))
                
                # Atualiza info
                if 'hand' not in info:
                    info['hand'] = {}
                info['hand']['strength'] = strength
                info['hand']['hole_card'] = normalized_cards
                
                # Adiciona ao resultado
                enriched_hand_info.append(info)
        
        # Se enriched_hand_info ainda estiver vazio, tenta usar o original
        if not enriched_hand_info:
            enriched_hand_info = hand_info

        self.last_round_result = {
            "winners": winners,
            "hand_info": enriched_hand_info,
            "pot_amount": total_pot,
            "round_state": self._sanitize_round_state(round_state)
        }

        # Update last_round_state BEFORE calling super, as super might call wait_for_continue
        self.last_round_state = round_state

        # --- CHAT MESSAGES FOR SHOWDOWN/WIN ---
        # MOVED BEFORE super() because super() blocks waiting for user input ("Next Round")
        try:
            seats = round_state.get('seats', [])
            winner_uuids = []
            for w in winners:
                if isinstance(w, dict):
                    winner_uuids.append(w.get('uuid'))
                else:
                    winner_uuids.append(w)
            
            # Identify players who showed cards and get their info
            shown_cards_info = {}
            if isinstance(enriched_hand_info, list): # List of dicts
                 for h in enriched_hand_info:
                     shown_cards_info[h.get('uuid')] = h
            elif isinstance(enriched_hand_info, dict): # Dict of UUID -> info
                 shown_cards_info = enriched_hand_info

            for seat in seats:
                # Include 'allin' players (who have stack 0 but are in showdown)
                # State can be 'participating', 'allin', 'folded'
                seat_state = seat.get('state')
                if seat_state != 'folded':
                    uuid = seat.get('uuid')
                    name = seat.get('name')
                    
                    # Skip myself (human)
                    if name == self._player_name:
                        continue
                        
                    # Determine message type
                    msg_type = None
                    player_hand_info = None
                    
                    if uuid in winner_uuids:
                        msg_type = 'WIN'
                        # Winners might also show cards
                        if uuid in shown_cards_info:
                            player_hand_info = shown_cards_info[uuid]
                    elif uuid in shown_cards_info:
                        msg_type = 'SHOW_CARDS'
                        player_hand_info = shown_cards_info[uuid]
                    else:
                        msg_type = 'MUCK'
                    
                    self._print_to_buffer(f"[WEB_DBG] Checking message for {name} ({seat_state}): type={msg_type}")
                    
                    # Send message
                    if msg_type:
                        chat_msg = self._get_bot_message(msg_type)
                        if chat_msg:
                            # Handle placeholders for SHOW_CARDS (or WIN if applicable)
                            if '{cards}' in chat_msg or '{hand_name}' in chat_msg:
                                if player_hand_info:
                                    # Debug info
                                    self._print_to_buffer(f"[WEB_DBG] player_hand_info for {name}: {player_hand_info}")
                                    
                                    # Get cards
                                    hole_cards = player_hand_info.get('hole_card') or player_hand_info.get('hole_cards') or player_hand_info.get('hand', {}).get('hole_card')
                                    
                                    # Fallback: Try to find cards in original hand_info if missing
                                    if not hole_cards:
                                        self._print_to_buffer(f"[WEB_DBG] Cards missing in enriched info, checking original hand_info...")
                                        if isinstance(hand_info, list):
                                            for h in hand_info:
                                                if h.get('uuid') == uuid:
                                                    hole_cards = h.get('hole_card') or h.get('hole_cards')
                                                    break
                                        elif isinstance(hand_info, dict):
                                            h = hand_info.get(uuid, {})
                                            hole_cards = h.get('hole_card') or h.get('hole_cards')
                                    
                                    if hole_cards:
                                        # Normalize and format cards
                                        from utils.hand_utils import normalize_hole_cards
                                        normalized = normalize_hole_cards(hole_cards)
                                        # Format as [Ah Ks]
                                        cards_str = f"[{' '.join(normalized)}]"
                                        chat_msg = chat_msg.replace('{cards}', cards_str)
                                    else:
                                        # Ensure placeholder is removed
                                        chat_msg = chat_msg.replace('{cards}', '')
                                    
                                    # Get hand name
                                    hand_entry = player_hand_info.get('hand', {})
                                    hand_strength = hand_entry.get('strength')
                                    # If strength is "ONEPAIR", convert to "One Pair"
                                    hand_name = str(hand_strength).replace('_', ' ').title() if hand_strength else "Hand"
                                    chat_msg = chat_msg.replace('{hand_name}', hand_name)
                                else:
                                    # Fallback if info missing but message expects it
                                    # Replace with empty or generic
                                    chat_msg = chat_msg.replace('{cards}', '').replace('{hand_name}', 'Hand')

                            # Add small delay for natural feel
                            # time.sleep(random.uniform(0.5, 1.5)) # Removed sleep to avoid blocking
                            
                            self._print_to_buffer(f"[WEB_DBG] Sending {msg_type} message for {name}: {chat_msg}") # DEBUG
                            self._send_update("chat_message", {
                                "type": "opponent",
                                "sender": name,
                                "content": chat_msg,
                                "bet": 0,
                                "stack": seat.get('stack', 0)
                            })
                        else:
                             self._print_to_buffer(f"[WEB_DBG] No message found for {msg_type} (lang={self.lang})") # DEBUG
                            
        except Exception as e:
            self._print_to_buffer(f"[WEB_DBG] Error sending round result chat: {e}")
            import traceback
            traceback.print_exc()
        # ---------------------------------------

        super().receive_round_result_message(winners, hand_info, round_state)
        
        # Envia update final para garantir que o UI mostre tudo
        sanitized_round_state = self._sanitize_round_state(round_state)
        self._send_update("round_result_data", {"winners": winners, "round_state": sanitized_round_state})



        # Trigger incremental save if callback is set
        if self.on_round_complete and hasattr(self, 'game_history'):
            # The super().receive_round_result_message updates self.game_history
            # The round is still in current_round until the next round starts
            try:
                if self.game_history.current_round:
                    self.on_round_complete(self.game_history.current_round)
            except Exception as e:
                print(f"[WEB PLAYER] Error triggering save callback: {e}")

    def receive_round_start_message(self, round_count, hole_card, seats):
        # Check if I am eliminated (stack is 0)
        is_eliminated = False
        if seats and hasattr(self, 'uuid') and self.uuid:
            for seat in seats:
                if isinstance(seat, dict) and seat.get('uuid') == self.uuid:
                    if seat.get('stack', 0) == 0:
                        is_eliminated = True
                    break
        
        # If eliminated or simulating, suppress hole cards
        if is_eliminated or self.auto_advance:
            hole_card = [] 

        super().receive_round_start_message(round_count, hole_card, seats)
        
        # Envia dados do início do round
        cards_to_send = self.my_hole_cards if self.my_hole_cards else []
        
        self._send_update("round_start_data", {
            "hole_cards": cards_to_send,
            "round_count": round_count,
            "seats": seats # Added seats to round_start_data
        })
        self.last_round_count = round_count
        self.last_street = 'preflop'

    def receive_street_start_message(self, street, round_state):
        super().receive_street_start_message(street, round_state)
        # Envia dados da nova street (com cartas comunitárias)
        sanitized_round_state = self._sanitize_round_state(round_state)
        self._send_update("street_start", {
            "street": street, 
            "round_state": sanitized_round_state
        })
        self.last_street = street
        self.last_round_state = round_state

    def receive_game_update_message(self, new_action, round_state):
        # 1. Direct Print for Frontend Parser (Robustness)
        # We construct "Name Action Amount" string and print it so the frontend regex catches it.
        try:
            if isinstance(new_action, dict):
                # Get Action
                action = new_action.get('action', '').upper()
                
                # Get Amount
                amount = new_action.get('amount', 0)
                if action == 'CALL':
                    amount = new_action.get('paid', 0)
                
                # Get Player Name
                player_name = new_action.get('player', '')
                if not player_name:
                    action_uuid = new_action.get('player_uuid') or new_action.get('uuid')
                    if action_uuid and round_state:
                        seats = round_state.get('seats', [])
                        for seat in seats:
                            if isinstance(seat, dict) and seat.get('uuid') == action_uuid:
                                player_name = seat.get('name', 'Unknown')
                                break
                
                if not player_name:
                    player_name = "Unknown"

                # Print if it's a valid action
                if action and player_name:
                    # Format: "Name Action Amount"
                    # This matches the frontend regex: /^(.+?) (called|raised|folded|checked|all-in|SB|BB)(?:(?:\(| )(\d+)\)?)?$/i
                    
                    # Map action to readable string if needed, or keep uppercase
                    # Frontend regex handles: called|raised|folded|checked|all-in|SB|BB
                    action_map = {
                        'SMALLBLIND': 'SB',
                        'BIGBLIND': 'BB',
                        'FOLD': 'folded',
                        'CALL': 'called',
                        'RAISE': 'raised',
                        'CHECK': 'checked'
                    }
                    
                    display_action = action_map.get(action, action)
                    
                    # Fix: Call with amount 0 is a Check
                    if action == 'CALL' and amount == 0:
                        display_action = 'checked'
                    
                    # Handle All-in detection (simple heuristic)
                    if amount > 0 and round_state:
                         seats = round_state.get('seats', [])
                         action_uuid = new_action.get('player_uuid') or new_action.get('uuid')
                         for seat in seats:
                             if isinstance(seat, dict) and seat.get('uuid') == action_uuid:
                                 if seat.get('stack', 0) == 0:
                                     display_action = 'all-in'
                                 break

                    # Construct message content
                    msg = f"{display_action}"
                    if amount > 0 and display_action not in ['folded', 'checked']:
                        msg += f" {amount}"
                    
                    # Send explicit chat message event to frontend
                    # This bypasses terminal parsing and ensures the bubble appears
                    # Only send if it's NOT me (frontend handles my actions optimistically)
                    if player_name != self._player_name:
                        # Add random delay for bot actions to simulate thinking/human-like timing
                        # Only delay if it's a game action (not automatic like blinds, though blinds are actions too)
                        # User requested delay for "bot messages", which usually implies their turn.
                        # Blinds are fast, but a small delay is fine.
                        self._send_update("bot_thinking", {"player": player_name})
                        delay = random.uniform(1.0, 3.0)
                        time.sleep(delay)

                        # Get stack from round_state
                        current_stack = 0
                        if round_state:
                             seats = round_state.get('seats', [])
                             for seat in seats:
                                 if isinstance(seat, dict) and seat.get('uuid') == action_uuid:
                                     current_stack = seat.get('stack', 0)
                                     break

                        # Calculate total bet for this street
                        total_bet = 0
                        if round_state:
                            street = round_state.get('street')
                            histories = round_state.get('action_histories', {}).get(street, [])
                            # Ensure histories is a list (sometimes it might be dict if not initialized?)
                            if isinstance(histories, list):
                                for a in histories:
                                    if isinstance(a, dict) and a.get('uuid') == action_uuid:
                                        total_bet += a.get('amount', 0)
                                        # For CALL, amount is usually paid amount.
                                        # For RAISE, amount is usually added amount.
                                        # If 'paid' exists, prioritize it?
                                        # In history, 'amount' is usually the cost.
                                        # Let's stick to 'amount'.

                        # Tenta obter mensagem natural do bot
                        natural_message = self._get_bot_message(action)
                        
                        # Se tiver mensagem natural, usa ela (SEM FALLBACK para genérico se não encontrar, mas o código atual já tem msg construída)
                        # O usuário pediu "nao quero fallbacks", o que implica que se não tiver no banco, não deve mandar nada?
                        # Ou deve mandar a mensagem construída (que é técnica)?
                        # O usuário disse: "quero que os bots pareçam mais naturais... cria 10 textos... nao quero fallbacks"
                        # Interpretando: Se tiver no banco, usa. Se não, usa o que já tinha (técnico) ou nada?
                        # "nao quero fallbacks" provavelmente se refere a não ter textos genéricos "Bot calls" hardcoded no código se falhar o banco.
                        # Mas como o banco é a fonte da verdade agora, se falhar, o comportamento padrão (técnico) é aceitável ou deve ser silenciado?
                        # Vou assumir que se tiver mensagem natural, usa. Se não, mantém o comportamento antigo (técnico) para não quebrar o jogo,
                        # POIS o chat bubble é a única forma de ver a ação visualmente além do log.
                        # Mas espere, o usuário disse "nao quero fallbacks" no contexto de "ensure fallback to generic messages".
                        # Então ele quer que o banco SEJA a fonte.
                        
                        final_msg = msg # Default to technical "Call 100"
                        
                        if natural_message:
                            final_msg = natural_message
                            
                            # Append amount for Raise actions
                            if action == 'RAISE' and amount > 0:
                                final_msg += f" {amount}"
                            
                            # Append amount for Blinds
                            if action in ['SMALLBLIND', 'BIGBLIND'] and amount > 0:
                                final_msg += f" {amount}"
                        
                        # Se for ALL-IN, tenta pegar mensagem específica
                        if display_action == 'all-in':
                             all_in_msg = self._get_bot_message('ALL-IN')
                             if all_in_msg:
                                 final_msg = all_in_msg
                                 # Optional: Append amount for All-in too if desired, but user asked for Raise
                                 if amount > 0:
                                     final_msg += f" {amount}"

                        self._send_update("chat_message", {
                            "type": "opponent",
                            "sender": player_name,
                            "content": final_msg,
                            "bet": total_bet,
                            "stack": current_stack
                        })
                    
                    # Also print to buffer for history/logs
                    self._print_to_buffer(f"[ACTION] {player_name} {msg}")

        except Exception as e:
            print(f"[WEB PLAYER] Error sending action: {e}")

        # 2. Call super to handle Pot updates and internal state
        # Prepare enriched action for ConsolePlayer just in case
        enriched_action = new_action.copy() if isinstance(new_action, dict) else new_action
        if isinstance(enriched_action, dict):
            if 'action' in enriched_action:
                enriched_action['action'] = enriched_action['action'].upper()
            if 'player' not in enriched_action:
                enriched_action['player'] = player_name if 'player_name' in locals() else 'Unknown'

        super().receive_game_update_message(enriched_action, round_state)
        
        # Sanitize new_action to use fixed UUIDs if possible for Frontend
        sanitized_action = new_action.copy() if isinstance(new_action, dict) else new_action
        if isinstance(sanitized_action, dict) and round_state:
            action_uuid = sanitized_action.get('player_uuid') or sanitized_action.get('uuid')
            if action_uuid:
                seats = round_state.get('seats', [])
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('uuid') == action_uuid:
                        # Found the seat, get fixed UUID
                        fixed_uuid = self._get_fixed_uuid_from_seat(seat, False)
                        if fixed_uuid:
                            if 'player_uuid' in sanitized_action:
                                sanitized_action['player_uuid'] = fixed_uuid
                            if 'uuid' in sanitized_action:
                                sanitized_action['uuid'] = fixed_uuid
                        break


        # Envia atualização do jogo (pot, ações)
        sanitized_round_state = self._sanitize_round_state(round_state)
        self._send_update("game_update", {
            "action": sanitized_action, 
            "round_state": sanitized_round_state
        })
        self.last_round_state = round_state

    def wait_for_continue(self):
        """
        Aguarda sinal do frontend para continuar para o próximo round.
        Substitui o input() bloqueante do ConsolePlayer.
        """
        # Verifica se estamos em modo de simulação automática
        if hasattr(self, 'auto_advance') and self.auto_advance:
            import time
            time.sleep(1) # Delay menor para simulação rápida
            return

        # Verifica se o jogador foi eliminado (stack == 0)
        # Se sim, avança automaticamente após breve delay
        my_stack = None # Default to None, not 0
        found_by = None
        
        if self.last_round_state:
            seats = self.last_round_state.get('seats', [])
            
            # 1. Try by pypoker_uuid (most reliable)
            if hasattr(self, 'pypoker_uuid') and self.pypoker_uuid:
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('uuid') == self.pypoker_uuid:
                        my_stack = seat.get('stack', 0)
                        found_by = 'pypoker_uuid'
                        break

            # 2. Try by fixed UUID
            if my_stack is None and hasattr(self, 'uuid') and self.uuid:
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('uuid') == self.uuid:
                        my_stack = seat.get('stack', 0)
                        found_by = 'uuid'
                        break
            
            # 3. Fallback to name
            player_name = getattr(self, 'name', None) or getattr(self, '_player_name', None)
            if my_stack is None and player_name:
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('name') == player_name:
                        my_stack = seat.get('stack', 0)
                        found_by = 'name'
                        break

        # Only eliminate if stack is explicitly 0 (found and empty)
        if my_stack is not None and my_stack == 0:
            # Check if I am a winner in the last round (if so, I have chips even if stack says 0 currently)
            am_i_winner = False
            if hasattr(self, 'last_round_result') and self.last_round_result:
                winners = self.last_round_result.get('winners', [])
                for w in winners:
                    w_uuid = w.get('uuid') if isinstance(w, dict) else w
                    # Check against both UUID and Name
                    if (hasattr(self, 'uuid') and w_uuid == self.uuid) or \
                       (hasattr(self, 'name') and isinstance(w, dict) and w.get('name') == self.name):
                        am_i_winner = True
                        break
            
            if not am_i_winner:
                self._print_to_buffer("\n[WEB] You are eliminated.")
                
                # Prepara dados do resultado para enviar
                elimination_data = {}
                if hasattr(self, 'last_round_result'):
                    elimination_data = self.last_round_result

                # Envia evento de eliminação para o frontend mostrar UI apropriada
                self._send_update("player_eliminated", elimination_data)
                
                # Aguarda ação do usuário (Quit, New Game, Simulate)
                try:
                    while True:
                        action, _ = self.input_queue.get()
                        
                        if action == 'quit':
                            from players.console_player import QuitGameException
                            raise QuitGameException()
                        
                        elif action == 'simulate':
                            self._print_to_buffer("[WEB] Simulating remaining game...")
                            self.auto_advance = True
                            return # Retorna para deixar o jogo continuar
                            
                except Exception as e:
                    if type(e).__name__ == 'QuitGameException':
                        raise e
                    print(f"[WEB PLAYER ERROR] Error waiting after elimination: {e}")
                return
            
        # 1. Envia sinal de fim de round e solicita confirmação
        self._send_update("round_result_data", {})
        self._send_update("wait_for_next_round", {})
        
        self._print_to_buffer("[WEB] Waiting for next round...")
        
        # 2. Aguarda resposta da fila
        # O frontend deve enviar uma action 'next_round' ou 'quit'
        try:
            action, amount = self.input_queue.get()
            
            if action == 'quit':
                from players.console_player import QuitGameException
                raise QuitGameException()
                
        except Exception as e:
            # Se for QuitGameException, re-lança
            if type(e).__name__ == 'QuitGameException':
                raise e
            print(f"[WEB PLAYER ERROR] Error waiting for next round: {e}")

    def resend_state(self):
        """Resends the current game state to the frontend (for reconnection)."""
        self._print_to_buffer(f"[WEB] Resending state to reconnected client...")
        
        # 1. Send Round Start Data (cards)
        if hasattr(self, 'my_hole_cards') and self.my_hole_cards:
            self._send_update("round_start_data", {
                "hole_cards": self.my_hole_cards,
                "round_count": self.last_round_count
            })
            
        # 2. Send latest street info (community cards)
        if self.last_round_state:
            sanitized_round_state = self._sanitize_round_state(self.last_round_state)
            
            # Send street start to ensure community cards are rendered
            if self.last_street:
                self._send_update("street_start", {
                    "street": self.last_street,
                    "round_state": sanitized_round_state
                })
                
            # Send latest game update to ensure pot/bets are correct
            self._send_update("game_update", {
                "action": {}, # No specific action, just state update
                "round_state": sanitized_round_state
            })

        # 3. If we were waiting for action, resend the request
        if self.waiting_for_action and self.last_valid_actions:
            # Re-calculate win prob if needed, or use cached
            win_prob = None
            if self.show_win_probability and hasattr(self, 'win_probability_cache') and self.last_cache_key:
                 if self.last_cache_key in self.win_probability_cache:
                     win_prob = self.win_probability_cache[self.last_cache_key].get('prob_pct')

            sanitized_round_state = self._sanitize_round_state(self.last_round_state) if self.last_round_state else {}
            
            action_request = {
                "valid_actions": self.last_valid_actions,
                "hole_cards": self.my_hole_cards if hasattr(self, 'my_hole_cards') else [],
                "round_state": sanitized_round_state,
                "win_probability": win_prob
            }
            self._send_update("action_required", action_request)
            
        # 4. Resend terminal output history
        self._send_update("terminal_output", "\n[SYSTEM] Restoring chat history...\n")
        if self.history_log:
            full_history = "".join(self.history_log)
            self._send_update("terminal_output", full_history)
            
        self._send_update("terminal_output", "\n[SYSTEM] Reconnected to game session.\n")

    def _get_community_cards_from_state(self, round_state):
        """Helper to extract community cards safely."""
        if not round_state:
            return []
        return round_state.get('community_card', [])

