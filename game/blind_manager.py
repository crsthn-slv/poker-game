"""
Gerenciador automático de blinds para poker.

Calcula Small Blind (SB) e Big Blind (BB) automaticamente baseado nas stacks
dos jogadores, garantindo valores proporcionais e estáveis.
"""

# Valores válidos para arredondamento de blinds
VALID_DENOMINATIONS = [1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000]


def round_to_valid_denomination(value):
    """
    Arredonda um valor para o valor válido mais próximo da lista de denominações.
    
    Args:
        value: Valor a ser arredondado
        
    Returns:
        int: Valor arredondado para a denominação válida mais próxima
    """
    if value <= 0:
        return 1
    
    # Encontra a denominação válida mais próxima
    for i, denom in enumerate(VALID_DENOMINATIONS):
        # Se o valor está entre duas denominações, escolhe a mais próxima
        if i == len(VALID_DENOMINATIONS) - 1:
            # Último valor: retorna ele se estiver acima
            return denom if value >= denom else VALID_DENOMINATIONS[i - 1] if i > 0 else 1
        
        if value <= denom:
            # Está entre denom anterior e atual
            if i == 0:
                return denom
            
            # Calcula qual está mais próximo
            prev_denom = VALID_DENOMINATIONS[i - 1]
            diff_to_prev = abs(value - prev_denom)
            diff_to_current = abs(value - denom)
            
            return prev_denom if diff_to_prev < diff_to_current else denom
    
    # Valor maior que todas as denominações: retorna a última
    return VALID_DENOMINATIONS[-1]


def get_denomination_index(value):
    """
    Retorna o índice da denominação na lista VALID_DENOMINATIONS.
    
    Args:
        value: Valor da denominação
        
    Returns:
        int: Índice na lista, ou -1 se não encontrado
    """
    try:
        return VALID_DENOMINATIONS.index(value)
    except ValueError:
        return -1


def calculate_blinds_from_reference_stack(reference_stack):
    """
    Calcula SB e BB baseado na stack de referência (5% para BB).
    
    Args:
        reference_stack: Stack de referência (maior stack na mesa)
        
    Returns:
        tuple: (small_blind, big_blind)
    """
    # BB é 5% da stack de referência
    bb_raw = reference_stack * 0.05
    
    # Arredonda BB para valor válido
    big_blind = round_to_valid_denomination(bb_raw)
    
    # Garante que BB >= 1
    if big_blind < 1:
        big_blind = 1
    
    # SB é metade do BB
    sb_raw = big_blind / 2.0
    
    # Tenta arredondar para valor válido da lista
    small_blind = round_to_valid_denomination(sb_raw)
    
    # Se o SB arredondado está muito longe do valor desejado (BB/2),
    # considera usar um valor intermediário que não esteja na lista mas faça sentido
    # Exemplo: BB=25, sb_raw=12.5, arredonda para 10 ou 20, mas 12 seria mais preciso
    if abs(small_blind - sb_raw) > abs(int(sb_raw) - sb_raw) and int(sb_raw) not in VALID_DENOMINATIONS:
        # Verifica se um valor intermediário seria melhor
        # Permite valores como 12 quando BB=25 se estiverem próximos de BB/2
        candidate_sb = int(sb_raw)
        if candidate_sb < big_blind and candidate_sb >= 1:
            # Usa o valor intermediário se for razoável (é um inteiro)
            small_blind = candidate_sb
    
    # Garante que SB >= 1
    if small_blind < 1:
        small_blind = 1
    
    # Se SB for maior ou igual a BB após arredondamento, ajusta
    if small_blind >= big_blind:
        # Se BB for 1, ambos devem ser 1 (caso especial)
        if big_blind == 1:
            small_blind = 1
        else:
            # Encontra o SB válido que seja metade ou próximo da metade do BB
            # Procurar na lista de denominações um valor <= BB/2
            target_sb = big_blind / 2.0
            small_blind = round_to_valid_denomination(target_sb)
            if small_blind >= big_blind:
                # Se ainda for maior, usa a denominação anterior a BB
                bb_index = get_denomination_index(big_blind)
                if bb_index > 0:
                    small_blind = VALID_DENOMINATIONS[bb_index - 1]
                else:
                    small_blind = 1
    
    return small_blind, big_blind


def calculate_blinds_from_stacks(stacks):
    """
    Calcula SB e BB baseado nas stacks dos jogadores.
    Usa a maior stack como stack de referência.
    
    Args:
        stacks: Lista de stacks dos jogadores (inteiros)
        
    Returns:
        tuple: (small_blind, big_blind)
    """
    if not stacks or len(stacks) == 0:
        # Valores padrão se não houver stacks
        return 1, 2
    
    # Encontra a maior stack (stack de referência)
    reference_stack = max(stacks)
    
    return calculate_blinds_from_reference_stack(reference_stack)


def should_update_blinds(current_sb, current_bb, new_reference_stack, previous_reference_stack=None):
    """
    Determina se os blinds devem ser atualizados.
    
    Atualiza quando:
    - O BB calculado muda pelo menos 1 nível na lista de denominações, OU
    - A stack de referência varia mais de 10%
    
    Args:
        current_sb: Small blind atual
        current_bb: Big blind atual
        new_reference_stack: Nova stack de referência
        previous_reference_stack: Stack de referência anterior (opcional)
        
    Returns:
        bool: True se deve atualizar, False caso contrário
    """
    # Calcula os novos blinds
    new_sb, new_bb = calculate_blinds_from_reference_stack(new_reference_stack)
    
    # Verifica se o BB mudou pelo menos 1 nível
    current_bb_index = get_denomination_index(current_bb)
    new_bb_index = get_denomination_index(new_bb)
    
    if current_bb_index == -1 or new_bb_index == -1:
        # Se não encontrou índice, atualiza por segurança
        return True
    
    # Mudou pelo menos 1 nível
    if abs(new_bb_index - current_bb_index) >= 1:
        return True
    
    # Verifica variação de 10% na stack de referência
    if previous_reference_stack is not None and previous_reference_stack > 0:
        variation = abs(new_reference_stack - previous_reference_stack) / previous_reference_stack
        if variation >= 0.10:  # 10% de variação
            return True
    
    return False


class BlindManager:
    """
    Gerenciador de blinds com estado para rastrear mudanças e evitar
    atualizações desnecessárias.
    """
    
    def __init__(self, initial_reference_stack=None):
        """
        Inicializa o gerenciador de blinds.
        
        Args:
            initial_reference_stack: Stack de referência inicial (opcional)
        """
        self.current_sb = None
        self.current_bb = None
        self.previous_reference_stack = initial_reference_stack
        self.reference_stack = initial_reference_stack
        
        # Calcula blinds iniciais se fornecido stack
        if initial_reference_stack is not None:
            self.current_sb, self.current_bb = calculate_blinds_from_reference_stack(
                initial_reference_stack
            )
    
    def update_from_stacks(self, stacks):
        """
        Atualiza os blinds baseado nas stacks dos jogadores.
        Só atualiza se houver mudança significativa.
        
        Args:
            stacks: Lista de stacks dos jogadores
            
        Returns:
            tuple: (small_blind, big_blind, was_updated)
        """
        if not stacks or len(stacks) == 0:
            # Mantém valores atuais se não houver stacks
            return self.current_sb, self.current_bb, False
        
        # Encontra maior stack
        new_reference_stack = max(stacks)
        self.reference_stack = new_reference_stack
        
        # Se ainda não tem blinds definidos, define agora
        if self.current_sb is None or self.current_bb is None:
            self.current_sb, self.current_bb = calculate_blinds_from_reference_stack(
                new_reference_stack
            )
            self.previous_reference_stack = new_reference_stack
            return self.current_sb, self.current_bb, True
        
        # Verifica se deve atualizar
        if should_update_blinds(
            self.current_sb,
            self.current_bb,
            new_reference_stack,
            self.previous_reference_stack
        ):
            self.current_sb, self.current_bb = calculate_blinds_from_reference_stack(
                new_reference_stack
            )
            self.previous_reference_stack = new_reference_stack
            return self.current_sb, self.current_bb, True
        
        return self.current_sb, self.current_bb, False
    
    def get_blinds(self):
        """
        Retorna os blinds atuais.
        
        Returns:
            tuple: (small_blind, big_blind) ou (None, None) se não definidos
        """
        return self.current_sb, self.current_bb
    
    def reset(self, new_reference_stack=None):
        """
        Reseta o gerenciador com nova stack de referência.
        
        Args:
            new_reference_stack: Nova stack de referência (opcional)
        """
        self.previous_reference_stack = new_reference_stack
        self.reference_stack = new_reference_stack
        
        if new_reference_stack is not None:
            self.current_sb, self.current_bb = calculate_blinds_from_reference_stack(
                new_reference_stack
            )
        else:
            self.current_sb = None
            self.current_bb = None

