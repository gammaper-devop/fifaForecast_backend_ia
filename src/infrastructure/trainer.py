import os
import sys
from pathlib import Path

# Garantizar que el intérprete de Python indexe la carpeta 'src'
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import joblib
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from infrastructure.data_processor import procesar_datos_neutrales

def entrenar_y_guardar_modelos():
    """Pipeline de reentrenamiento unificado."""
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    ruta_csv = BASE_DIR / "data" / "results.csv"
    models_dir = BASE_DIR / "models_pkl"
    
    # Obtener partidos de MongoDB para incluirlos en el entrenamiento
    from infrastructure.mongo_repository import PyMongoStatsRepository
    try:
        mongo_repo = PyMongoStatsRepository()
        # Intentamos forzar conexión rápida para verificar si Mongo está activo
        mongo_repo._client.server_info()
        mongo_matches = mongo_repo.get_all_matches()
        print(f"[INFO] Sincronizados {len(mongo_matches)} partidos desde MongoDB para el entrenamiento.")
    except Exception as e:
        print(f"[AVISO] No se pudo conectar a MongoDB ({e}). Se utilizara unicamente results.csv.")
        mongo_matches = []
        
    df_neutral, stats_neutrales, elo_actual, historial_partidos = procesar_datos_neutrales(
        str(ruta_csv), 
        mongo_matches
    )

    def definir_resultado(row):
        if row['home_score'] > row['away_score']: return 1
        elif row['home_score'] < row['away_score']: return 2
        else: return 0

    df_neutral['resultado'] = df_neutral.apply(definir_resultado, axis=1)

    # 📈 Set de variables expandido con ELO y Forma Reciente
    features = [
        'ataque_home_A', 'defensa_home_A', 'ataque_away_A', 'defensa_away_A',
        'ataque_home_B', 'defensa_home_B', 'ataque_away_B', 'defensa_away_B',
        'is_neutral_match',
        'elo_home', 'elo_away',
        'form_pts_home', 'form_pts_away',
        'form_gf_home', 'form_gf_away',
        'form_ga_home', 'form_ga_away'
    ]
    
    X = df_neutral[features]
    y_clas = df_neutral['resultado']
    y_goles_A = df_neutral['home_score']
    y_goles_B = df_neutral['away_score']

    modelo_clasificador = RandomForestClassifier(n_estimators=150, max_depth=7, random_state=42)
    modelo_clasificador.fit(X, y_clas)

    modelo_regresor_A = RandomForestRegressor(n_estimators=150, max_depth=7, random_state=42)
    modelo_regresor_A.fit(X, y_goles_A)

    modelo_regresor_B = RandomForestRegressor(n_estimators=150, max_depth=7, random_state=42)
    modelo_regresor_B.fit(X, y_goles_B)

    os.makedirs(models_dir, exist_ok=True)

    # Guardar binarios y diccionarios
    joblib.dump(modelo_clasificador, os.path.join(models_dir, 'modelo_clasificador_mundial.pkl'))
    joblib.dump(modelo_regresor_A, os.path.join(models_dir, 'modelo_regresor_A.pkl'))
    joblib.dump(modelo_regresor_B, os.path.join(models_dir, 'modelo_regresor_B.pkl'))
    joblib.dump(stats_neutrales, os.path.join(models_dir, 'stats_neutrales.pkl'))
    joblib.dump(elo_actual, os.path.join(models_dir, 'elo_actual.pkl'))
    joblib.dump(historial_partidos, os.path.join(models_dir, 'historial_partidos.pkl'))
    
    print("[OK] Modelos y estructuras de control re-entrenados y sincronizados con exito!")

def registrar_jornada_real_y_reentrenar(equipo_a, equipo_b, goles_a, goles_b):
    """Inserta el resultado del día en el set compartido y ejecuta el reentrenamiento."""
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    ruta_csv = BASE_DIR / "data" / "results.csv"
    
    nueva_jornada = {
        'date': [datetime.now().strftime('%Y-%m-%d')],
        'home_team': [equipo_a],
        'away_team': [equipo_b],
        'home_score': [goles_a],
        'away_score': [goles_b],
        'tournament': ['FIFA World Cup'],
        'city': ['Houston'],
        'country': ['United States'],
        'neutral': [True]
    }
    
    df_nuevo = pd.DataFrame(nueva_jornada)
    df_nuevo.to_csv(ruta_csv, mode='a', header=not os.path.exists(ruta_csv), index=False)
    print(f"✅ Guardado en results.csv unificado: {equipo_a} vs {equipo_b}")
    entrenar_y_guardar_modelos()

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    entrenar_y_guardar_modelos()