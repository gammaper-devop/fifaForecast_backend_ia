from dataclasses import dataclass
from typing import List, Dict

@dataclass
class MatchTeams:
    home: str
    away: str

@dataclass
class ExpectedGoals:
    home: float
    away: float

@dataclass
class Probabilities1X2:
    home_win: float
    draw: float
    away_win: float

@dataclass
class FairOdds:
    home_win: float
    draw: float
    away_win: float

@dataclass
class ExactScore:
    score: str
    formatted_score: str
    probability_percent: float

@dataclass
class PoissonPredictionResult:
    teams: MatchTeams
    expected_goals: ExpectedGoals
    probabilities_1X2: Probabilities1X2
    fair_odds: FairOdds
    top_exact_scores: List[ExactScore]

@dataclass
class RandomForestPredictionResult:
    equipo_1: str
    equipo_2: str
    doble_oportunidad: str
    probabilidad_1: float
    probabilidad_empate: float
    probabilidad_2: float
    mas_menos_goles: str
    ambos_anotan: str
    marcador_exacto: str