import os
import joblib
import pandas as pd
from datetime import datetime
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from infrastructure.data_processor import procesar_datos_neutrales

def entrenar_y_guardar_modelos():
    """Pipeline de reentrenamiento unificado."""
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    ruta_csv = BASE_DIR / "data" / "results.csv"
    models_dir = BASE_DIR / "models_pkl"
    
    df_neutral, stats_neutrales = procesar_datos_neutrales(str(ruta_csv))

    def definir_resultado(row):
        if row['home_score'] > row['away_score']: return 1
        elif row['home_score'] < row['away_score']: return 2
        else: return 0

    df_neutral['resultado'] = df_neutral.apply(definir_resultado, axis=1)

    features = [
        'ataque_home_A', 'defensa_home_A', 'ataque_away_A', 'defensa_away_A',
        'ataque_home_B', 'defensa_home_B', 'ataque_away_B', 'defensa_away_B',
        'is_neutral_match'
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

    joblib.dump(modelo_clasificador, os.path.join(models_dir, 'modelo_clasificador_mundial.pkl'))
    joblib.dump(modelo_regresor_A, os.path.join(models_dir, 'modelo_regresor_A.pkl'))
    joblib.dump(modelo_regresor_B, os.path.join(models_dir, 'modelo_regresor_B.pkl'))
    joblib.dump(stats_neutrales, os.path.join(models_dir, 'stats_neutrales.pkl'))
    
    print("🎯 ¡Modelos re-entrenados y sincronizados con éxito!")

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