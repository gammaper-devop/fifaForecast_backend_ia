from abc import ABC, abstractmethod
from typing import Dict, Tuple, List
import pandas as pd
from domain.models import ExpectedGoals

class MatchDataLoader(ABC):
    """Interfaz para la carga desacoplada de registros desde el CSV (Principio S)."""
    @abstractmethod
    def load_recent_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]]]:
        pass

class ProbabilityCalculator(ABC):
    """Interfaz para el motor estadístico de distribución y cálculo matricial (Principio O)."""
    @abstractmethod
    def calculate_distribution(self, expected_goals: ExpectedGoals, top_n: int = 5) -> Tuple[Dict[str, float], List[Dict[str, float]]]:
        pass