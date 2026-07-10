from domain.interfaces import SetPiecesPredictor, ProbabilityCalculator
from domain.models import (
    MatchTeams, ExpectedGoals, Probabilities1X2, FairOdds, ExactScore,
    SetPiecesExpectedCounts, CountDistribution, OverUnderLine, SetPiecesPredictionResult,
)

CORNERS_OVER_UNDER_LINES = [7.5, 8.5, 9.5, 10.5, 11.5]
SHOTS_OVER_UNDER_LINES = [4.5, 5.5, 6.5, 7.5, 8.5, 9.5]


class SetPiecesUseCase:
    """Caso de uso que orquesta XGBoost + Dixon-Coles para predecir corners y tiros a puerta."""

    def __init__(
        self,
        set_pieces_predictor: SetPiecesPredictor,
        corners_calculator: ProbabilityCalculator,
        shots_calculator: ProbabilityCalculator,
        top_n: int = 5,
    ):
        self._predictor = set_pieces_predictor
        self._corners_calc = corners_calculator
        self._shots_calc = shots_calculator
        self._top_n = top_n

    def execute(self, home_team: str, away_team: str) -> SetPiecesPredictionResult:
        teams = MatchTeams(home=home_team, away=away_team)

        expected_counts = self._predictor.predict_expected_counts(home_team, away_team)

        corners_dist = self._build_distribution(
            expected_counts.corners_home,
            expected_counts.corners_away,
            home_team,
            away_team,
            self._corners_calc,
            CORNERS_OVER_UNDER_LINES,
        )

        shots_dist = self._build_distribution(
            expected_counts.shots_on_target_home,
            expected_counts.shots_on_target_away,
            home_team,
            away_team,
            self._shots_calc,
            SHOTS_OVER_UNDER_LINES,
        )

        return SetPiecesPredictionResult(
            teams=teams,
            expected_counts=expected_counts,
            corners=corners_dist,
            shots_on_target=shots_dist,
        )

    def _build_distribution(
        self,
        expected_home: float,
        expected_away: float,
        home_team: str,
        away_team: str,
        calculator: ProbabilityCalculator,
        over_under_lines: list,
    ) -> CountDistribution:
        lambdas = ExpectedGoals(home=expected_home, away=expected_away)

        outcomes, top_scores = calculator.calculate_distribution(lambdas, top_n=self._top_n)

        prob_1x2 = Probabilities1X2(
            home_win=round(outcomes["home_win"] * 100, 2),
            draw=round(outcomes["draw"] * 100, 2),
            away_win=round(outcomes["away_win"] * 100, 2),
        )

        fair_odds = FairOdds(
            home_win=round(1 / outcomes["home_win"], 2) if outcomes["home_win"] > 0 else 0.0,
            draw=round(1 / outcomes["draw"], 2) if outcomes["draw"] > 0 else 0.0,
            away_win=round(1 / outcomes["away_win"], 2) if outcomes["away_win"] > 0 else 0.0,
        )

        exact_counts = []
        for s in top_scores:
            goles_home, goles_away = s["score"].split("-")
            formatted = f"{home_team} {goles_home} - {goles_away} {away_team}"
            exact_counts.append(ExactScore(
                score=s["score"],
                formatted_score=formatted,
                probability_percent=round(s["prob"] * 100, 2),
            ))

        ou_results = calculator.calculate_over_under(lambdas, over_under_lines)
        over_under = [
            OverUnderLine(
                line=line,
                over=round(over_p * 100, 2),
                under=round(under_p * 100, 2),
            )
            for line, over_p, under_p in ou_results
        ]

        return CountDistribution(
            expected_home=round(expected_home, 4),
            expected_away=round(expected_away, 4),
            probabilities_1x2=prob_1x2,
            fair_odds=fair_odds,
            top_exact_counts=exact_counts,
            over_under=over_under,
        )
