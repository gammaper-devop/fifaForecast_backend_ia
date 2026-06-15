from domain.interfaces import MatchDataLoader, ProbabilityCalculator
from domain.models import MatchTeams, ExpectedGoals, Probabilities1X2, FairOdds, ExactScore, PoissonPredictionResult

class PoissonUseCase:
    """Caso de uso unificado que consume el Puente de Conexión Absoluta del Random Forest."""
    def __init__(
        self, 
        data_loader: MatchDataLoader, 
        prob_calculator: ProbabilityCalculator,
        simulador_forest,
        data_path: str,
        top_n: int = 5
    ):
        self._data_loader = data_loader
        self._prob_calculator = prob_calculator
        self._simulador_forest = simulador_forest
        self._data_path = data_path
        self.top_n = top_n
        self._team_stats = {}
        
    def initialize(self):
        """Pre-carga los diccionarios de control de equipos al inicializar la API."""
        _, self._team_stats = self._data_loader.load_recent_data(self._data_path)
        
    def execute(self, home_team: str, away_team: str) -> PoissonPredictionResult:
        teams = MatchTeams(home=home_team, away=away_team)
        
        # Validación de integridad de los datos de entrada
        if home_team not in self._team_stats or away_team not in self._team_stats:
            raise ValueError("Uno o ambos equipos no existen en los registros recientes.")
            
        # 🌁 EL PUENTE DE CONEXIÓN ABSOLUTA:
        # Extraemos el cálculo predictivo del RandomForest para alimentar el motor Poisson
        rf_output = self._simulador_forest.simular(home_team, away_team)
        
        if "error" in rf_output:
            raise ValueError(rf_output["error"])
            
        lambdas = ExpectedGoals(
            home=rf_output["lambdas_proyectados"]["home"], 
            away=rf_output["lambdas_proyectados"]["away"]
        )
        
        # 2. Distribución estadística matricial con ajuste Dixon-Coles
        outcomes, top_scores = self._prob_calculator.calculate_distribution(lambdas, top_n=self.top_n)
        
        # 3. Mapeo final al Modelo de Dominio
        prob_1x2 = Probabilities1X2(
            home_win=round(outcomes["home_win"] * 100, 2),
            draw=round(outcomes["draw"] * 100, 2),
            away_win=round(outcomes["away_win"] * 100, 2)
        )
        
        fair_odds = FairOdds(
            home_win=round(1 / outcomes["home_win"], 2) if outcomes["home_win"] > 0 else 0.0,
            draw=round(1 / outcomes["draw"], 2) if outcomes["draw"] > 0 else 0.0,
            away_win=round(1 / outcomes["away_win"], 2) if outcomes["away_win"] > 0 else 0.0
        )
        
        exact_scores_models = []
        for s in top_scores:
            goles_home, goles_away = s["score"].split("-")
            formatted = f"{home_team} {goles_home} - {goles_away} {away_team}"
            
            exact_scores_models.append(
                ExactScore(
                    score=s["score"],
                    formatted_score=formatted,
                    probability_percent=round(s["prob"] * 100, 2)
                )
            )
        
        return PoissonPredictionResult(
            teams=teams,
            expected_goals=ExpectedGoals(home=round(lambdas.home, 4), away=round(lambdas.away, 4)),
            probabilities_1X2=prob_1x2,
            fair_odds=fair_odds,
            top_exact_scores=exact_scores_models
        )