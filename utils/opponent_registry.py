"""
Sistema de registro persistente de oponentes.
Melhora identificação de oponentes com mapeamento UUID persistente.
"""
import json
import os
from typing import Dict, Optional
from pathlib import Path

# Caminho para arquivo de registro de oponentes
OPPONENT_REGISTRY_FILE = Path(__file__).parent.parent / "data" / "opponent_registry.json"

class OpponentRegistry:
    """Registro persistente de oponentes com mapeamento UUID."""
    
    def __init__(self, registry_file: Optional[Path] = None):
        """
        Inicializa registro de oponentes.
        
        Args:
            registry_file: Caminho para arquivo de registro (opcional)
        """
        self.registry_file = registry_file or OPPONENT_REGISTRY_FILE
        self.registry: Dict[str, Dict] = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Dict]:
        """Carrega registro de oponentes do arquivo."""
        if not self.registry_file.exists():
            return {}
        
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save_registry(self) -> bool:
        """Salva registro de oponentes no arquivo."""
        try:
            # Garante que o diretório existe
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False
    
    def register_opponent(self, name: str, uuid: str, bot_class: Optional[str] = None) -> str:
        """
        Registra um oponente no registro persistente.
        
        Args:
            name: Nome do oponente
            uuid: UUID do oponente
            bot_class: Classe do bot (opcional, para melhor identificação)
        
        Returns:
            UUID registrado
        """
        # Cria entrada no registro
        entry = {
            'uuid': uuid,
            'name': name,
            'bot_class': bot_class
        }
        
        # Usa nome como chave (normalizado)
        key = name.strip()
        self.registry[key] = entry
        
        # Salva registro
        self._save_registry()
        
        return uuid
    
    def get_opponent_uuid(self, name: str) -> Optional[str]:
        """
        Obtém UUID de um oponente pelo nome.
        
        Args:
            name: Nome do oponente
        
        Returns:
            UUID do oponente ou None se não encontrado
        """
        key = name.strip()
        entry = self.registry.get(key)
        if entry:
            return entry.get('uuid')
        return None
    
    def get_opponent_info(self, name: str) -> Optional[Dict]:
        """
        Obtém informações completas de um oponente.
        
        Args:
            name: Nome do oponente
        
        Returns:
            Informações do oponente ou None
        """
        key = name.strip()
        return self.registry.get(key)
    
    def has_opponent(self, name: str) -> bool:
        """
        Verifica se um oponente está registrado.
        
        Args:
            name: Nome do oponente
        
        Returns:
            True se está registrado
        """
        key = name.strip()
        return key in self.registry
    
    def get_all_opponents(self) -> Dict[str, Dict]:
        """
        Retorna todos os oponentes registrados.
        
        Returns:
            Dicionário com todos os oponentes
        """
        return self.registry.copy()

# Instância global do registro
_global_registry: Optional[OpponentRegistry] = None

def get_opponent_registry() -> OpponentRegistry:
    """Retorna instância global do registro de oponentes."""
    global _global_registry
    if _global_registry is None:
        _global_registry = OpponentRegistry()
    return _global_registry

def register_opponent(name: str, uuid: str, bot_class: Optional[str] = None) -> str:
    """Registra um oponente (função de conveniência)."""
    return get_opponent_registry().register_opponent(name, uuid, bot_class)

def get_opponent_uuid_by_name(name: str) -> Optional[str]:
    """Obtém UUID de um oponente pelo nome (função de conveniência)."""
    return get_opponent_registry().get_opponent_uuid(name)




