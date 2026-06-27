from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Optional, Any
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

class MatchStatsRepository(ABC):
    """Interfaz abstracta para la persistencia de estadísticas de partidos (Principio de Inversión de Dependencias)."""
    @abstractmethod
    def get_team_historical_summary(self, team_name: str) -> Optional[Dict[str, Any]]:
        pass

class FeatureExtractor(ABC):
    """Interfaz abstracta para la extracción de características (Features) de los equipos."""
    @abstractmethod
    def extract_features(self, home_team: str, away_team: str, is_neutral: int = 1) -> pd.DataFrame:
        pass

class PredictorModel(ABC):
    """Interfaz abstracta para el motor predictivo de machine learning."""
    @abstractmethod
    def simular(self, equipo_1: str, equipo_2: str) -> dict:
        pass