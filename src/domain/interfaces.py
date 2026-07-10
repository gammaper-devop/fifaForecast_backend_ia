from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Optional, Any
import pandas as pd
from domain.models import ExpectedGoals, SetPiecesExpectedCounts

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

    @abstractmethod
    def calculate_over_under(self, expected_goals: ExpectedGoals, lines: List[float]) -> List[Tuple[float, float, float]]:
        """Calcula probabilidades Over/Under para un conjunto de líneas. Devuelve (line, over, under)."""
        pass

class MatchStatsRepository(ABC):
    """Interfaz abstracta para la persistencia de estadísticas de partidos (Principio de Inversión de Dependencias)."""
    @abstractmethod
    def get_team_historical_summary(self, team_name: str) -> Optional[Dict[str, Any]]:
        pass

class SetPiecesPredictor(ABC):
    """Interfaz para el motor predictivo de corners y tiros a puerta basado en XGBoost (Principio de Inversión de Dependencias)."""
    @abstractmethod
    def predict_expected_counts(self, home_team: str, away_team: str) -> SetPiecesExpectedCounts:
        pass