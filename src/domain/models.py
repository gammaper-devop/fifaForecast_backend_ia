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

@dataclass
class SetPiecesExpectedCounts:
    corners_home: float
    corners_away: float
    shots_on_target_home: float
    shots_on_target_away: float

@dataclass
class OverUnderLine:
    line: float
    over: float
    under: float

@dataclass
class CountDistribution:
    expected_home: float
    expected_away: float
    probabilities_1x2: Probabilities1X2
    fair_odds: FairOdds
    top_exact_counts: List[ExactScore]
    over_under: List[OverUnderLine]

@dataclass
class SetPiecesPredictionResult:
    teams: MatchTeams
    expected_counts: SetPiecesExpectedCounts
    corners: CountDistribution
    shots_on_target: CountDistribution