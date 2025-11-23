"""
Utilitários para tratamento de erros e logging nos players.
"""
import os
import logging
from functools import wraps

# Configuração de logging
LOG_LEVEL = os.environ.get('POKER_PLAYER_LOG_LEVEL', 'WARNING').upper()
logger = logging.getLogger('poker_players')
logger.setLevel(getattr(logging, LOG_LEVEL, logging.WARNING))

# Handler apenas se não existir
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def safe_file_operation(operation_name='file operation'):
    """Decorator para operações de arquivo seguras.
    
    Captura exceções de I/O e loga em modo debug, mas não quebra o jogo.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError:
                logger.debug(f"{operation_name}: Arquivo não encontrado (normal na primeira execução)")
                return None
            except PermissionError:
                logger.warning(f"{operation_name}: Sem permissão para acessar arquivo")
                return None
            except (IOError, OSError) as e:
                logger.warning(f"{operation_name}: Erro de I/O: {e}")
                return None
            except Exception as e:
                logger.error(f"{operation_name}: Erro inesperado: {e}", exc_info=True)
                return None
        return wrapper
    return decorator


def safe_memory_save(memory_file, memory_data):
    """Salva memória de forma segura com tratamento de erros.
    
    Args:
        memory_file: Caminho do arquivo de memória
        memory_data: Dados a serem salvos (dict)
    
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    import time
    from datetime import datetime
    
    start_time = time.time()
    bot_name = memory_file.split('/')[-1].replace('_memory.json', '') if memory_file else 'unknown'
    
    @safe_file_operation('save_memory')
    def _save():
        import json
        import os
        
        # Cria diretório se não existir
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        
        with open(memory_file, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        return True
    
    result = _save() is not None
    elapsed_time = time.time() - start_time
    
    # Log apenas se demorar mais de 0.1s ou se houver erro
    if elapsed_time > 0.1 or not result:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        status = "✅" if result else "❌"
        print(f"💾 [MEMORY] [{timestamp}] {status} Bot {bot_name} - save_memory: {elapsed_time:.3f}s")
    
    return result


def safe_memory_load(memory_file, default_data=None):
    """Carrega memória de forma segura com tratamento de erros.
    
    Args:
        memory_file: Caminho do arquivo de memória
        default_data: Dados padrão se arquivo não existir
    
    Returns:
        Dados carregados ou default_data
    """
    @safe_file_operation('load_memory')
    def _load():
        import json
        
        if not os.path.exists(memory_file):
            return default_data
        
        with open(memory_file, 'r') as f:
            return json.load(f)
    
    result = _load()
    return result if result is not None else (default_data or {})

