"""
Utilitários para gerenciamento centralizado de memória dos bots.
"""
import os

def get_memory_path(filename):
    """
    Retorna o caminho completo para o arquivo de memória.
    Centraliza todas as memórias em data/memory/
    
    Args:
        filename: Nome do arquivo de memória (ex: 'tight_player_memory.json')
    
    Returns:
        Caminho completo para o arquivo de memória
    """
    # Obtém o diretório raiz do projeto (poker_test/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Cria diretório de memória se não existir
    memory_dir = os.path.join(project_root, 'data', 'memory')
    os.makedirs(memory_dir, exist_ok=True)
    
    # Retorna caminho completo
    return os.path.join(memory_dir, filename)

