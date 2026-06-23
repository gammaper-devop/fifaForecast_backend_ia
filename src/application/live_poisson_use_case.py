from domain.interfaces import ProbabilityCalculator
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

        # 2. Asignar lambdas base de seguridad (Fallback) si no hay registros en Mongo
        # Valores base calculados a partir de la media de goles esperados del torneo
        att_home = metrics_home["xg_ataque"] if metrics_home else 1.35
        def_home = metrics_home["xg_defensa"] if metrics_home else 1.10
        
        att_away = metrics_away["xg_ataque"] if metrics_away else 1.10
        def_away = metrics_away["xg_defensa"] if metrics_away else 1.35

        # 🚀 CORRECCIÓN MATEMÁTICA: Multiplicación de intensidades en lugar de promedios planos
        # Los goles proyectados son el resultado de la fuerza de ataque multiplicada por la vulnerabilidad defensiva del rival.
        if metrics_home and metrics_away:
            lambda_home = att_home * def_away
            lambda_away = att_away * def_home
        else:
            # Si uno es debutante, usamos su ataque estimado o el fallback directo
            lambda_home = att_home
            lambda_away = att_away

        # Asegurar un piso mínimo de 0.1 para evitar que Poisson colapse con valores en 0
        expected = ExpectedGoals(home=max(0.1, lambda_home), away=max(0.1, lambda_away))
        
        # 3. Calcular la distribución Dixon-Coles probabilística con el TOP 5 solicitado 🚀
        outcomes, top_scores = self._prob_calculator.calculate_distribution(expected, top_n=5)

        # 4. Retornar un formato estandarizado y limpio para el bot de WhatsApp
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