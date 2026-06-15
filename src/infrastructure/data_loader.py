import pandas as pd
from typing import Dict, Tuple
from domain.interfaces import MatchDataLoader

class PandasMatchDataLoader(MatchDataLoader):
    """Cargador de datos históricos que segmenta la ventana de tiempo del Mundial."""
    def load_recent_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]]]:
        df = pd.read_csv(file_path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.dropna(subset=["home_score", "away_score"])
        
        # Filtro temporal estricto (2024-2026) para las estadísticas de Poisson
        df_recent = df[(df["date"] >= "2024-01-01") & (df["date"] <= "2026-12-31")].copy()
        
        home_avg = df_recent["home_score"].mean()
        away_avg = df_recent["away_score"].mean()
        
        team_stats = {}
        teams = set(df_recent["home_team"]).union(set(df_recent["away_team"]))
        
        for team in teams:
            h_m = df_recent[df_recent["home_team"] == team]
            a_m = df_recent[df_recent["away_team"] == team]
            
            team_stats[team] = {
                "att_home": (h_m["home_score"].mean() / home_avg) if len(h_m) > 0 else 1.0,
                "def_home": (h_m["away_score"].mean() / away_avg) if len(h_m) > 0 else 1.0,
                "att_away": (a_m["away_score"].mean() / away_avg) if len(a_m) > 0 else 1.0,
                "def_away": (a_m["home_score"].mean() / home_avg) if len(a_m) > 0 else 1.0,
            }
            
        return df_recent, team_stats