"""
Adaptador do ConsolePlayer para interface Web via WebSocket.
"""

import queue
import sys
import io
import re
from typing import Dict, Any, Callable, Optional, Tuple

from players.console_player import ConsolePlayer
from utils.game_history import GameHistory

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
                 on_round_complete: Optional[Callable[[Dict[str, Any]], None]] = None):
        
        # Inicializa o buffer antes de chamar super, pois super pode usar printer
        self.output_buffer = io.StringIO()
        self.on_game_update = on_game_update
        self.on_round_complete = on_round_complete
        self.input_queue = queue.Queue()
        self.game_id = None
        
        super().__init__(
            input_receiver=lambda x: "f", # Placeholder, não será usado pois sobrescrevemos __receive_action
            initial_stack=initial_stack,
            small_blind=small_blind,
            big_blind=big_blind,
            show_win_probability=show_win_probability,
            printer=self._print_to_buffer # Injeta nosso método de impressão
        )
        
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
            "round_count": round_count
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
        super().receive_game_update_message(new_action, round_state)
        # Envia atualização do jogo (pot, ações)
        sanitized_round_state = self._sanitize_round_state(round_state)
        self._send_update("game_update", {
            "action": new_action, 
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

