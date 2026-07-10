import os
import joblib
import pandas as pd
from pathlib import Path
from domain.interfaces import SetPiecesPredictor
from domain.models import SetPiecesExpectedCounts
from infrastructure.set_pieces_trainer import FEATURES


class XGBoostSetPiecesPredictor(SetPiecesPredictor):
    """Adaptador concreto que carga los binarios XGBoost persistidos y predice corners y tiros a puerta."""

    def __init__(self):
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        self._models_dir = BASE_DIR / "models_pkl"
        self._loaded = False

    def _ensure_models_loaded(self):
        if self._loaded:
            return

        required = [
            'modelo_xgboost_corners_home.pkl',
            'modelo_xgboost_corners_away.pkl',
            'modelo_xgboost_shots_home.pkl',
            'modelo_xgboost_shots_away.pkl',
            'stats_set_pieces.pkl',
        ]
        missing = [f for f in required if not os.path.exists(os.path.join(self._models_dir, f))]
        if missing:
            raise ValueError(
                f"Modelos XGBoost de set pieces no encontrados: {missing}. "
                f"Ejecuta el entrenamiento primero: "
                f"python -c \"import sys; sys.path.append('src'); "
                f"from infrastructure.set_pieces_trainer import entrenar_y_guardar_set_pieces; "
                f"entrenar_y_guardar_set_pieces()\""
            )

        self._modelo_corners_home = joblib.load(os.path.join(self._models_dir, 'modelo_xgboost_corners_home.pkl'))
        self._modelo_corners_away = joblib.load(os.path.join(self._models_dir, 'modelo_xgboost_corners_away.pkl'))
        self._modelo_shots_home = joblib.load(os.path.join(self._models_dir, 'modelo_xgboost_shots_home.pkl'))
        self._modelo_shots_away = joblib.load(os.path.join(self._models_dir, 'modelo_xgboost_shots_away.pkl'))
        self._stats = joblib.load(os.path.join(self._models_dir, 'stats_set_pieces.pkl'))
        self._loaded = True

    def _obtener_stats(self, equipo: str, rol: str):
        fila = self._stats[(self._stats['equipo'] == equipo) & (self._stats['rol'] == rol)]
        if fila.empty:
            return None
        return fila.iloc[0]

    def _construir_features(self, home_team: str, away_team: str) -> pd.DataFrame:
        s_home = self._obtener_stats(home_team, 'home')
        s_away = self._obtener_stats(away_team, 'away')

        if s_home is None:
            raise ValueError(f"El equipo '{home_team}' no tiene estadisticas como local en los registros de set pieces.")
        if s_away is None:
            raise ValueError(f"El equipo '{away_team}' no tiene estadisticas como visitante en los registros de set pieces.")

        return pd.DataFrame([{
            'corners_scored_home_A': s_home['corners_scored'],
            'corners_conceded_home_A': s_home['corners_conceded'],
            'corners_scored_away_B': s_away['corners_scored'],
            'corners_conceded_away_B': s_away['corners_conceded'],
            'shots_scored_home_A': s_home['shots_scored'],
            'shots_conceded_home_A': s_home['shots_conceded'],
            'shots_scored_away_B': s_away['shots_scored'],
            'shots_conceded_away_B': s_away['shots_conceded'],
            'possession_home_A': s_home['possession'],
            'possession_away_B': s_away['possession'],
            'xg_home_A': s_home['xg'],
            'xg_away_B': s_away['xg'],
        }])

    def predict_expected_counts(self, home_team: str, away_team: str) -> SetPiecesExpectedCounts:
        self._ensure_models_loaded()
        features = self._construir_features(home_team, away_team)

        corners_home = max(0.1, float(self._modelo_corners_home.predict(features)[0]))
        corners_away = max(0.1, float(self._modelo_corners_away.predict(features)[0]))
        shots_home = max(0.1, float(self._modelo_shots_home.predict(features)[0]))
        shots_away = max(0.1, float(self._modelo_shots_away.predict(features)[0]))

        return SetPiecesExpectedCounts(
            corners_home=round(corners_home, 4),
            corners_away=round(corners_away, 4),
            shots_on_target_home=round(shots_home, 4),
            shots_on_target_away=round(shots_away, 4),
        )
