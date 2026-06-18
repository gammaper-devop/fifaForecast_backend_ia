from domain.interfaces import MatchStatsRepository

class GetStatsUseCase:
    """Caso de uso encargado de orquestar la obtención de analítica deportiva avanzada."""
    def __init__(self, repository: MatchStatsRepository):
        self._repository = repository

    def execute(self, team_name: str):
        summary = self._repository.get_team_historical_summary(team_name)
        if not summary:
            raise ValueError(f"No se encontraron registros en el torneo para la selección: '{team_name}'")
        return summary