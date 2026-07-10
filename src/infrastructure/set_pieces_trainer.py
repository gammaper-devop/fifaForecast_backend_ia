import os
import joblib
import pandas as pd
from pathlib import Path
from xgboost import XGBRegressor
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

FEATURES = [
    'corners_scored_home_A', 'corners_conceded_home_A',
    'corners_scored_away_B', 'corners_conceded_away_B',
    'shots_scored_home_A', 'shots_conceded_home_A',
    'shots_scored_away_B', 'shots_conceded_away_B',
    'possession_home_A', 'possession_away_B',
    'xg_home_A', 'xg_away_B',
]


def _extraer_corners(doc, equipo):
    esp = doc.get('estadisticas_especificas', {})
    corners = esp.get('corners', {})
    return float(corners.get(equipo, 0))


def _extraer_shots(doc, equipo):
    gen = doc.get('estadisticas_generales', {})
    tiros = gen.get('tiros_a_puerta', {})
    return float(tiros.get(equipo, 0))


def _extraer_posesion(doc, equipo):
    gen = doc.get('estadisticas_generales', {})
    pos = gen.get('posesion_porcentaje', {})
    return float(pos.get(equipo, 50))


def _extraer_xg(doc, equipo):
    gen = doc.get('estadisticas_generales', {})
    xg = gen.get('goles_esperados_xG', {})
    return float(xg.get(equipo, 1.0))


def _construir_stats_por_equipo(partidos):
    """Calcula estadísticas promedio por equipo desglosadas por rol (local/visitante)."""
    registros = []

    for doc in partidos:
        p = doc.get('partido', {})
        local = p.get('equipo_local')
        visitante = p.get('equipo_visitante')
        if not local or not visitante:
            continue

        registros.append({
            'equipo': local, 'rol': 'home',
            'corners_scored': _extraer_corners(doc, local),
            'corners_conceded': _extraer_corners(doc, visitante),
            'shots_scored': _extraer_shots(doc, local),
            'shots_conceded': _extraer_shots(doc, visitante),
            'possession': _extraer_posesion(doc, local),
            'xg': _extraer_xg(doc, local),
        })
        registros.append({
            'equipo': visitante, 'rol': 'away',
            'corners_scored': _extraer_corners(doc, visitante),
            'corners_conceded': _extraer_corners(doc, local),
            'shots_scored': _extraer_shots(doc, visitante),
            'shots_conceded': _extraer_shots(doc, local),
            'possession': _extraer_posesion(doc, visitante),
            'xg': _extraer_xg(doc, visitante),
        })

    df = pd.DataFrame(registros)
    if df.empty:
        return pd.DataFrame()

    stats = df.groupby(['equipo', 'rol']).mean().reset_index()
    return stats


def _obtener_stats_equipo(stats_df, equipo, rol):
    """Filtra las estadísticas de un equipo bajo un rol específico."""
    fila = stats_df[(stats_df['equipo'] == equipo) & (stats_df['rol'] == rol)]
    if fila.empty:
        return None
    return fila.iloc[0]


def _construir_dataset(partidos, stats_df):
    """Construye la matriz de features y los targets para entrenamiento."""
    filas = []
    for doc in partidos:
        p = doc.get('partido', {})
        local = p.get('equipo_local')
        visitante = p.get('equipo_visitante')
        if not local or not visitante:
            continue

        s_home = _obtener_stats_equipo(stats_df, local, 'home')
        s_away = _obtener_stats_equipo(stats_df, visitante, 'away')
        if s_home is None or s_away is None:
            continue

        filas.append({
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
            'target_corners_home': _extraer_corners(doc, local),
            'target_corners_away': _extraer_corners(doc, visitante),
            'target_shots_home': _extraer_shots(doc, local),
            'target_shots_away': _extraer_shots(doc, visitante),
        })

    return pd.DataFrame(filas)


def entrenar_y_guardar_set_pieces():
    """Pipeline de entrenamiento XGBoost para corners y tiros a puerta desde MongoDB."""
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME = os.getenv("MONGO_DB_NAME", "mongo-mundial")

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    models_dir = BASE_DIR / "models_pkl"

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client[DB_NAME]
    coleccion = db["partidos_reales"]

    partidos = list(coleccion.find({}))
    if not partidos:
        print("No se encontraron documentos en partidos_reales. Abortando entrenamiento.")
        return

    print(f"Documentos leidos desde MongoDB: {len(partidos)}")

    stats_df = _construir_stats_por_equipo(partidos)
    if stats_df.empty:
        print("No se pudieron calcular estadisticas por equipo. Abortando.")
        return

    dataset = _construir_dataset(partidos, stats_df)
    if dataset.empty:
        print("Dataset vacio. Abortando entrenamiento.")
        return

    print(f"Dataset de entrenamiento: {len(dataset)} muestras, {len(FEATURES)} features")

    X = dataset[FEATURES]
    y_corners_home = dataset['target_corners_home']
    y_corners_away = dataset['target_corners_away']
    y_shots_home = dataset['target_shots_home']
    y_shots_away = dataset['target_shots_away']

    params = dict(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)

    modelo_corners_home = XGBRegressor(**params)
    modelo_corners_home.fit(X, y_corners_home)

    modelo_corners_away = XGBRegressor(**params)
    modelo_corners_away.fit(X, y_corners_away)

    modelo_shots_home = XGBRegressor(**params)
    modelo_shots_home.fit(X, y_shots_home)

    modelo_shots_away = XGBRegressor(**params)
    modelo_shots_away.fit(X, y_shots_away)

    os.makedirs(models_dir, exist_ok=True)

    joblib.dump(modelo_corners_home, os.path.join(models_dir, 'modelo_xgboost_corners_home.pkl'))
    joblib.dump(modelo_corners_away, os.path.join(models_dir, 'modelo_xgboost_corners_away.pkl'))
    joblib.dump(modelo_shots_home, os.path.join(models_dir, 'modelo_xgboost_shots_home.pkl'))
    joblib.dump(modelo_shots_away, os.path.join(models_dir, 'modelo_xgboost_shots_away.pkl'))
    joblib.dump(stats_df, os.path.join(models_dir, 'stats_set_pieces.pkl'))

    print("Modelos XGBoost de set pieces entrenados y guardados con exito.")


if __name__ == "__main__":
    entrenar_y_guardar_set_pieces()
