from pypokerengine.players import BasePokerPlayer
import random
import json
import os
from .memory_utils import get_memory_path

class RandomPlayer(BasePokerPlayer):
    """Jogador que faz decisões aleatórias. Blefa 25% das vezes. Aprendizado estocástico básico com memória persistente."""
    
    def __init__(self, memory_file="random_player_memory.json"):
        self.memory_file = get_memory_path(memory_file)
        self.bluff_probability = 0.25  # 25% de chance de blefar
        self.bluff_call_ratio = 0.50  # 50% CALL / 50% RAISE quando blefar
        
        # Sistema de aprendizado estocástico (básico)
        self.action_probabilities = {
            'fold': 0.33,
            'call': 0.33,
            'raise': 0.34
        }
        self.action_results = {
            'fold': {'wins': 0, 'total': 0},
            'call': {'wins': 0, 'total': 0},
            'raise': {'wins': 0, 'total': 0}
        }
        self.last_action = None
        self.total_rounds = 0
        self.wins = 0
        
        # Carrega memória anterior se existir
        self.load_memory()
    
    def declare_action(self, valid_actions, hole_card, round_state):
        hand_strength = self._evaluate_hand_strength(hole_card)
        should_bluff = self._should_bluff()
        
        if should_bluff:
            return self._bluff_action(valid_actions, round_state)
        else:
            return self._normal_action(valid_actions, hand_strength, round_state)
    
    def _should_bluff(self):
        """Decide se deve blefar baseado na probabilidade configurada."""
        return random.random() < self.bluff_probability
    
    def _bluff_action(self, valid_actions, round_state):
        """Executa blefe: escolhe aleatoriamente entre CALL ou RAISE."""
        # 50% CALL / 50% RAISE (totalmente aleatório)
        bluff_choice = random.random() < 0.50
        
        if bluff_choice and valid_actions[2]['amount']['min'] != -1:
            # Faz RAISE aleatório
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, max_amount)
            return raise_action['action'], amount
        else:
            # Faz CALL
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _analyze_table_context(self, round_state):
        """Analisa o contexto da mesa (não usado, mas mantido para consistência)."""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([s for s in round_state['seats'] if s['state'] == 'participating'])
        street = round_state['street']
        
        return {
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street
        }
    
    def _evaluate_hand_strength(self, hole_card):
        """Avalia a força das cartas (não usado muito, pois é aleatório)."""
        if not hole_card or len(hole_card) < 2:
            return 0
        
        card_ranks = [card[1] for card in hole_card]
        
        # Par
        if card_ranks[0] == card_ranks[1]:
            return 30
        
        # Cartas altas
        high_cards = ['A', 'K', 'Q']
        if any(rank in high_cards for rank in card_ranks):
            return 20
        
        return 10
    
    def _normal_action(self, valid_actions, hand_strength, round_state):
        """Ação normal: aleatória baseada em probabilidades aprendidas."""
        # Escolhe ação baseado em probabilidades aprendidas
        rand = random.random()
        if rand < self.action_probabilities['fold']:
            action_choice = 'fold'
        elif rand < self.action_probabilities['fold'] + self.action_probabilities['call']:
            action_choice = 'call'
        else:
            action_choice = 'raise'
        
        # Armazena última ação para aprendizado
        self.last_action = action_choice
        
        if action_choice == 'fold':
            fold_action = valid_actions[0]
            return fold_action['action'], fold_action['amount']
        elif action_choice == 'call':
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
        else:  # raise
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, max_amount)
                return raise_action['action'], amount
            else:
                # Se não pode fazer raise, faz call
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
    
    def receive_game_start_message(self, game_info):
        pass
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        """Salva memória periodicamente."""
        if round_count % 5 == 0:
            self.save_memory()
    
    def receive_street_start_message(self, street, round_state):
        pass
    
    def receive_game_update_message(self, action, round_state):
        pass
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado estocástico: ajusta probabilidades baseado em resultados."""
        self.total_rounds += 1
        
        # Verifica se ganhou
        won = any(w['uuid'] == self.uuid for w in winners)
        if won:
            self.wins += 1
        
        # Atualiza estatísticas da última ação
        if self.last_action:
            self.action_results[self.last_action]['total'] += 1
            if won:
                self.action_results[self.last_action]['wins'] += 1
        
        # Aprendizado estocástico: ajusta probabilidades lentamente
        if self.total_rounds >= 10:
            # Calcula win rate por ação
            for action in ['fold', 'call', 'raise']:
                stats = self.action_results[action]
                if stats['total'] > 0:
                    win_rate = stats['wins'] / stats['total']
                    
                    # Ajusta probabilidade baseado em win rate (aprendizado lento)
                    if win_rate > 0.5:
                        # Ação está funcionando: aumenta probabilidade
                        self.action_probabilities[action] = min(0.5, 
                            self.action_probabilities[action] + 0.02)
                    elif win_rate < 0.3:
                        # Ação não está funcionando: reduz probabilidade
                        self.action_probabilities[action] = max(0.1, 
                            self.action_probabilities[action] - 0.02)
            
            # Normaliza probabilidades
            total = sum(self.action_probabilities.values())
            for action in self.action_probabilities:
                self.action_probabilities[action] /= total
        
        # Salva memória após ajustes
        self.save_memory()
    
    def save_memory(self):
        """Salva memória aprendida em arquivo."""
        memory = {
            'bluff_probability': self.bluff_probability,
            'action_probabilities': self.action_probabilities,
            'action_results': self.action_results,
            'total_rounds': self.total_rounds,
            'wins': self.wins
        }
        
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            pass  # Silencioso
    
    def load_memory(self):
        """Carrega memória aprendida de arquivo."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    memory = json.load(f)
                
                self.bluff_probability = memory.get('bluff_probability', 0.25)
                self.action_probabilities = memory.get('action_probabilities', {
                    'fold': 0.33, 'call': 0.33, 'raise': 0.34
                })
                self.action_results = memory.get('action_results', {
                    'fold': {'wins': 0, 'total': 0},
                    'call': {'wins': 0, 'total': 0},
                    'raise': {'wins': 0, 'total': 0}
                })
                self.total_rounds = memory.get('total_rounds', 0)
                self.wins = memory.get('wins', 0)
            except Exception as e:
                pass  # Silencioso

