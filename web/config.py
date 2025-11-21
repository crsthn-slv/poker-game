"""
Configurações centralizadas para o servidor Flask.
Todas as configurações podem ser sobrescritas por variáveis de ambiente.
"""
import os

# Configurações do Servidor
SERVER_PORT = int(os.environ.get('PORT', 5002))
SERVER_HOST = os.environ.get('HOST', '0.0.0.0')
DEBUG_MODE = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

# Configurações de CORS
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')

# Configurações de Jogo
DEFAULT_MAX_ROUNDS = int(os.environ.get('MAX_ROUNDS', 10))
DEFAULT_INITIAL_STACK = int(os.environ.get('INITIAL_STACK', 100))
DEFAULT_SMALL_BLIND = int(os.environ.get('SMALL_BLIND', 5))

# Configurações de Logging
POKER_DEBUG = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'

