from domain.interfaces import ProbabilityCalculator, MatchDataLoader
from domain.models import ExpectedGoals
from infrastructure.mongo_repository import PyMongoStatsRepository

class LivePoissonUseCase:
    """Caso de uso de predicción táctica basado en el rendimiento xG real del torneo."""
    def __init__(self, mongo_repo: PyMongoStatsRepository, prob_calculator: ProbabilityCalculator):
        self._mongo_repo = mongo_repo
        self._prob_calculator = prob_calculator

    def execute(self, home_team: str, away_team: str):
        # 1. Intentar buscar métricas reales de este torneo en MongoDB
        metrics_home = self._mongo_repo.get_team_tournament_metrics(home_team)
        metrics_away = self._mongo_repo.get_team_tournament_metrics(away_team)

        # 2. Si no hay partidos jugados en el torneo, asignar lambdas base de seguridad
        lambda_home = metrics_home["xg_ataque"] if metrics_home else 1.35
        lambda_away = metrics_away["xg_ataque"] if metrics_away else 1.10

        # Si ya se cruzaron datos, refinamos los lambdas cruzando ataque vs defensa
        if metrics_home and metrics_away:
            lambda_home = (metrics_home["xg_ataque"] + metrics_away["xg_defensa"]) / 2
            lambda_away = (metrics_away["xg_ataque"] + metrics_home["xg_defensa"]) / 2

        expected = ExpectedGoals(home=max(0.1, lambda_home), away=max(0.1, lambda_away))
        
        # 3. Calcular la matriz Dixon-Coles probabilística con el TOP 5 solicitado 🚀
        outcomes, top_scores = self._prob_calculator.calculate_distribution(expected, top_n=5)

        # 4. Retornar un formato ultra valioso para el apostador
        return {
            "metodo": "Métricas xG Reales del Torneo (Live In-Play)",
            "encuentro": f"{home_team} vs {away_team}",
            "probabilidades_1X2": {
                "gana_local": round(outcomes["home_win"] * 100, 1),
                "empate": round(outcomes["draw"] * 100, 1),
                "gana_visitante": round(outcomes["away_win"] * 100, 1)
            },
            "marcadores_mas_probables": top_scores,
            "analisis_cuota": "Recomendado Local o Empate" if outcomes["home_win"] > outcomes["away_win"] else "Recomendado Visitante o Empate"
        }