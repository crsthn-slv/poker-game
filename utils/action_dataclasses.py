"""
Dataclasses para estruturar dados de ações e análises de blefe.
Garante consistência e elimina erros de dicionário.
"""
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class CurrentActions:
    """Estrutura de dados para ações do round atual."""
    has_raises: bool = False
    raise_count: int = 0
    call_count: int = 0
    last_action: Optional[str] = None  # 'raise', 'call', 'fold' ou None
    total_aggression: float = 0.0  # 0.0 a 1.0
    is_passive: bool = False
    passive_opportunity_score: float = 0.0  # 0.0 a 1.0
    
    def to_dict(self) -> Dict:
        """Converte para dicionário (compatibilidade com código existente)."""
        return {
            'has_raises': self.has_raises,
            'raise_count': self.raise_count,
            'call_count': self.call_count,
            'last_action': self.last_action,
            'total_aggression': self.total_aggression,
            'is_passive': self.is_passive,
            'passive_opportunity_score': self.passive_opportunity_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CurrentActions':
        """Cria instância a partir de dicionário."""
        return cls(
            has_raises=data.get('has_raises', False),
            raise_count=data.get('raise_count', 0),
            call_count=data.get('call_count', 0),
            last_action=data.get('last_action'),
            total_aggression=data.get('total_aggression', 0.0),
            is_passive=data.get('is_passive', False),
            passive_opportunity_score=data.get('passive_opportunity_score', 0.0)
        )


@dataclass
class BluffAnalysis:
    """Estrutura de dados para análise de blefe dos oponentes."""
    possible_bluff_probability: float = 0.0  # 0.0 a 1.0
    should_call_bluff: bool = False
    bluff_confidence: float = 0.0  # 0.0 a 1.0
    analysis_factors: Optional[Dict] = None
    
    def __post_init__(self):
        """Garante que analysis_factors seja um dicionário."""
        if self.analysis_factors is None:
            self.analysis_factors = {
                'multiple_raises': False,
                'high_aggression': False,
                'early_street': False,
                'small_pot': False,
                'opponent_bluff_history': False
            }
    
    def to_dict(self) -> Dict:
        """Converte para dicionário (compatibilidade com código existente)."""
        return {
            'possible_bluff_probability': self.possible_bluff_probability,
            'should_call_bluff': self.should_call_bluff,
            'bluff_confidence': self.bluff_confidence,
            'analysis_factors': self.analysis_factors
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BluffAnalysis':
        """Cria instância a partir de dicionário."""
        return cls(
            possible_bluff_probability=data.get('possible_bluff_probability', 0.0),
            should_call_bluff=data.get('should_call_bluff', False),
            bluff_confidence=data.get('bluff_confidence', 0.0),
            analysis_factors=data.get('analysis_factors')
        )




