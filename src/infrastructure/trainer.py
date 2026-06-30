import os
import sys
from pathlib import Path

# Garantizar que el intérprete de Python indexe la carpeta 'src'
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import joblib
import pandas as pd
from datetime import datetime
from xgboost import XGBClassifier, XGBRegressor
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

    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import accuracy_score, mean_absolute_error
    import numpy as np

    print("[INFO] Realizando Validación Cruzada Temporal (TimeSeriesSplit) para los nuevos modelos XGBoost...")
    tscv = TimeSeriesSplit(n_splits=5)
    
    acc_scores = []
    mae_a_scores = []
    mae_b_scores = []
    
    for train_index, test_index in tscv.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_clas_train, y_clas_test = y_clas.iloc[train_index], y_clas.iloc[test_index]
        y_goles_a_train, y_goles_a_test = y_goles_A.iloc[train_index], y_goles_A.iloc[test_index]
        y_goles_b_train, y_goles_b_test = y_goles_B.iloc[train_index], y_goles_B.iloc[test_index]
        w_train = df_neutral['weight'].iloc[train_index]
        
        # Clasificador
        clf = XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42, eval_metric='mlogloss')
        clf.fit(X_train, y_clas_train, sample_weight=w_train)
        preds_clf = clf.predict(X_test)
        acc_scores.append(accuracy_score(y_clas_test, preds_clf))
        
        # Regresor A
        reg_a = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42)
        reg_a.fit(X_train, y_goles_a_train, sample_weight=w_train)
        preds_a = reg_a.predict(X_test)
        mae_a_scores.append(mean_absolute_error(y_goles_a_test, preds_a))
        
        # Regresor B
        reg_b = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42)
        reg_b.fit(X_train, y_goles_b_train, sample_weight=w_train)
        preds_b = reg_b.predict(X_test)
        mae_b_scores.append(mean_absolute_error(y_goles_b_test, preds_b))
        
    print(f"[REPORT-VAL] Clasificador - Accuracy Promedio CV: {np.mean(acc_scores):.4f}")
    print(f"[REPORT-VAL] Regresor A (Goles Local) - MAE Promedio CV: {np.mean(mae_a_scores):.4f}")
    print(f"[REPORT-VAL] Regresor B (Goles Visitante) - MAE Promedio CV: {np.mean(mae_b_scores):.4f}")

    # 1. --- MODELOS RANDOM FOREST (Modelo Original) ---
    print("[INFO] Entrenando modelos RandomForest...")
    rf_clf = RandomForestClassifier(n_estimators=150, max_depth=7, random_state=42)
    rf_clf.fit(X, y_clas)

    rf_reg_A = RandomForestRegressor(n_estimators=150, max_depth=7, random_state=42)
    rf_reg_A.fit(X, y_goles_A)

    rf_reg_B = RandomForestRegressor(n_estimators=150, max_depth=7, random_state=42)
    rf_reg_B.fit(X, y_goles_B)

    # 2. --- MODELOS XGBOOST (Modelo Upgraded con Decaimiento Temporal) ---
    print("[INFO] Entrenando modelos XGBoost con Time Decay...")
    xgb_clf = XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42, eval_metric='mlogloss')
    xgb_clf.fit(X, y_clas, sample_weight=df_neutral['weight'])

    xgb_reg_A = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42)
    xgb_reg_A.fit(X, y_goles_A, sample_weight=df_neutral['weight'])

    xgb_reg_B = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42)
    xgb_reg_B.fit(X, y_goles_B, sample_weight=df_neutral['weight'])

    os.makedirs(models_dir, exist_ok=True)

    # Guardar binarios de Random Forest (con sufijo y también por defecto para compatibilidad)
    joblib.dump(rf_clf, os.path.join(models_dir, 'modelo_clasificador_mundial_rf.pkl'))
    joblib.dump(rf_reg_A, os.path.join(models_dir, 'modelo_regresor_A_rf.pkl'))
    joblib.dump(rf_reg_B, os.path.join(models_dir, 'modelo_regresor_B_rf.pkl'))
    
    joblib.dump(rf_clf, os.path.join(models_dir, 'modelo_clasificador_mundial.pkl'))
    joblib.dump(rf_reg_A, os.path.join(models_dir, 'modelo_regresor_A.pkl'))
    joblib.dump(rf_reg_B, os.path.join(models_dir, 'modelo_regresor_B.pkl'))

    # Guardar binarios de XGBoost (con sufijo _xgb)
    joblib.dump(xgb_clf, os.path.join(models_dir, 'modelo_clasificador_mundial_xgb.pkl'))
    joblib.dump(xgb_reg_A, os.path.join(models_dir, 'modelo_regresor_A_xgb.pkl'))
    joblib.dump(xgb_reg_B, os.path.join(models_dir, 'modelo_regresor_B_xgb.pkl'))

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
    print(f"[OK] Guardado en results.csv unificado: {equipo_a} vs {equipo_b}")
    entrenar_y_guardar_modelos()

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    entrenar_y_guardar_modelos()