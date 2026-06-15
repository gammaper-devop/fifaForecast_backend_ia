from domain.models import RandomForestPredictionResult

class RandomForestUseCase:
    """Caso de uso aislado para explotar las predicciones directas de ML."""
    def __init__(self, simulador_forest):
        # Inyección por constructor (Principio de Inversión de Dependencias)
        self._simulador = simulador_forest

    def execute(self, home_team: str, away_team: str) -> RandomForestPredictionResult:
        rf_output = self._simulador.simular(home_team, away_team)
        
        if "error" in rf_output:
            raise ValueError(rf_output["error"])
            
        return RandomForestPredictionResult(
            equipo_1=rf_output["equipo_1"],
            equipo_2=rf_output["equipo_2"],
            doble_oportunidad=rf_output["doble_oportunidad"],
            probabilidad_1=rf_output["probabilidad_1"],
            probabilidad_empate=rf_output["probabilidad_empate"],
            probabilidad_2=rf_output["probabilidad_2"],
            mas_menos_goles=rf_output["mas_menos_goles"],
            ambos_anotan=rf_output["ambos_anotan"],
            marcador_exacto=rf_output["marcador_exacto"]
        )