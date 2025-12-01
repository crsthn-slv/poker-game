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
                 on_game_update: Optional[Callable[[str, Any], None]] = None):
        
        # Inicializa o buffer antes de chamar super, pois super pode usar printer
        self.output_buffer = io.StringIO()
        self.on_game_update = on_game_update
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
                filtered_lines = [line for line in lines if '[DEBUG]' not in line]
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

        action_request = {
            "valid_actions": valid_actions,
            "hole_cards": self.my_hole_cards if hasattr(self, 'my_hole_cards') else [],
            "round_state": sanitized_round_state,
            "win_probability": win_prob
        }
        
        # Cache state for reconnection
        self.waiting_for_action = True
        self.last_valid_actions = valid_actions
        self.last_round_state = round_state
        
        self._send_update("action_required", action_request)
        
        # 2. Aguarda resposta da fila (bloqueante na thread do jogo, não no servidor)
        # O servidor roda o jogo em thread separada, então isso é seguro
        self._print_to_buffer(f"[WEB] Waiting for user action...")
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
        super().receive_round_result_message(winners, hand_info, round_state)
        # Envia update final para garantir que o UI mostre tudo
        sanitized_round_state = self._sanitize_round_state(round_state)
        self._send_update("round_result_data", {"winners": winners, "round_state": sanitized_round_state})

    def receive_round_start_message(self, round_count, hole_card, seats):
        super().receive_round_start_message(round_count, hole_card, seats)
        # Envia dados do início do round
        self._send_update("round_start_data", {
            "hole_cards": self.my_hole_cards,
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
        # Verifica se o jogador foi eliminado (stack == 0)
        # Se sim, avança automaticamente após breve delay
        my_stack = 0
        if self.last_round_state and hasattr(self, 'uuid') and self.uuid:
            seats = self.last_round_state.get('seats', [])
            for seat in seats:
                if isinstance(seat, dict) and seat.get('uuid') == self.uuid:
                    my_stack = seat.get('stack', 0)
                    break
        
        if my_stack == 0:
            self._print_to_buffer("\n[WEB] You are eliminated. Auto-advancing to next round...")
            import time
            time.sleep(2) # Pequeno delay para ver o resultado
            return # Retorna sem esperar input
            
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

