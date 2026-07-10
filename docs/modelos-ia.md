# Modelos de Inteligencia Artificial

El ecosistema combina dos enfoques predictivos: **Random Forest** (scikit-learn) para clasificación y regresión de goles, y **Distribución de Poisson** con ajuste **Dixon-Coles** (scipy) para modelado probabilístico de marcadores.

---

## 1. Random Forest

### Modelos persistidos

| Archivo | Tipo | Objetivo |
|---------|------|---------|
| `models_pkl/modelo_clasificador_mundial.pkl` | `RandomForestClassifier` | Clasificar resultado 1X2 (0=empate, 1=local, 2=visitante) |
| `models_pkl/modelo_regresor_A.pkl` | `RandomForestRegressor` | Predecir goles del equipo local (λ₁) |
| `models_pkl/modelo_regresor_B.pkl` | `RandomForestRegressor` | Predecir goles del equipo visitante (λ₂) |
| `models_pkl/stats_neutrales.pkl` | `DataFrame` | Estadísticas de ataque/defensa por equipo y rol |

### Features (9 variables)

Los 3 modelos consumen el mismo vector de features:

| Feature | Descripción |
|---------|-------------|
| `ataque_home_A` | Ataque como local del equipo A (home) |
| `defensa_home_A` | Defensa como local del equipo A (goles concedidos) |
| `ataque_away_A` | Ataque como visitante del equipo A |
| `defensa_away_A` | Defensa como visitante del equipo A |
| `ataque_home_B` | Ataque como local del equipo B (away) |
| `defensa_home_B` | Defensa como local del equipo B |
| `ataque_away_B` | Ataque como visitante del equipo B |
| `defensa_away_B` | Defensa como visitante del equipo B |
| `is_neutral_match` | 1 si es cancha neutral, 0 si hay localía |

### Hiperparámetros

```python
RandomForestClassifier(n_estimators=150, max_depth=7, random_state=42)
RandomForestRegressor(n_estimators=150, max_depth=7, random_state=42)
```

Definidos en `src/infrastructure/trainer.py:35-42`.

### Lógica de predicción (`predictor.py`)

`SimuladorMundial.simular(equipo_1, equipo_2)`:

1. **Carga de stats:** Busca `equipo_1` y `equipo_2` en `stats_neutrales.pkl`. Si no existen, devuelve error.
2. **Detección de anfitriones:** Si alguno de los equipos es México, EE.UU. o Canadá → `is_neutral_match = 0` (tiene localía). En caso contrario → `1` (neutral).
3. **Clasificación 1X2:** `model_clas.predict_proba()` → probabilidades de empate, victoria local y victoria visitante (×100).
4. **Doble oportunidad:** Si `prob_local + prob_empate > 72%` y `prob_local > prob_visitante` → `"Gana {local} o Empate"`. Análogo para visitante. Si ninguno supera el umbral → `"Gana {local} o Gana {visitante} (Sin Empate)"`.
5. **Regresión de goles (lambdas):** `model_reg_A.predict()` → λ₁, `model_reg_B.predict()` → λ₂. Piso mínimo de **0.05** para evitar valores negativos o cero.
6. **Marcador exacto:** Redondeo de λ₁ y λ₂. Si hay empate en el redondeo y la diferencia de probabilidades 1X2 es > 5%, se ajusta el marcador a favor del más probable.
7. **Mercados derivados:**
   - Over/Under 2.5: `λ₁ + λ₂ > 2.5` → "Más de 2.5", si no "Menos de 2.5".
   - Ambos anotan: `λ₁ > 0 y λ₂ > 0` → "SÍ", si no "NO".
8. **Output:** Devuelve también `lambdas_proyectados` {home: λ₁, away: λ₂} — estos lambdas alimentan el motor Poisson (puente de conexión).

---

## 2. Pipeline de entrenamiento (`trainer.py`)

### `entrenar_y_guardar_modelos()`

1. **Carga y filtrado:** Lee `data/results.csv`, filtra partidos desde **2018** en adelante (`data_processor.py:9`).
2. **Generación de stats asimétricas:** `procesar_datos_neutrales()` calcula por equipo:
   - `ataque_home` = promedio de goles anotados como local
   - `defensa_home` = promedio de goles concedidos como local
   - `ataque_away` = promedio de goles anotados como visitante
   - `defensa_away` = promedio de goles concedidos como visitante
3. **Reconstrucción del dataset:** Merge de stats con cada partido (equipo A = local, equipo B = visitante), generando los 9 features.
4. **Entrenamiento:** Ajusta los 3 modelos (clasificador + 2 regresores) sobre el dataset reconstruido.
5. **Persistencia:** Guarda los 4 archivos `.pkl` en `models_pkl/` con `joblib.dump()`.

### `registrar_jornada_real_y_reentrenar(equipo_a, equipo_b, goles_a, goles_b)`

Reentrenamiento incremental:

1. Append del nuevo resultado al final de `data/results.csv` (torneo: "FIFA World Cup", neutral: True).
2. Ejecuta `entrenar_y_guardar_modelos()` para regenerar todos los `.pkl`.

```python
from infrastructure.trainer import registrar_jornada_real_y_reentrenar

registrar_jornada_real_y_reentrenar("Brazil", "Argentina", 2, 1)
```

---

## 3. Distribución de Poisson + Dixon-Coles

### Implementación: `poisson_calculator.py`

`ScipyPoissonCalculator.calculate_distribution(expected_goals, top_n=5)`:

1. **Matriz 8x8:** Para cada combinación de goles (i, j) donde i, j ∈ [0, 7]:

   ```
   matrix[i, j] = P(X=i) × P(Y=j) = poisson.pmf(i, μ_x) × poisson.pmf(j, μ_y)
   ```

2. **Ajuste Dixon-Coles** (corrección de dependencia en marcadores bajos):

   Con `τ = 0.08`:

   ```
   matrix[0, 0] *= (1 - μ_x × μ_y × τ)
   matrix[1, 1] *= (1 - τ)
   matrix[1, 0] *= (1 + μ_y × τ)
   matrix[0, 1] *= (1 + μ_x × τ)
   ```

   Este ajuste corrige la tendencia de Poisson a subestimar empates 0-0 y 1-1, y sobrestimar 1-0 y 0-1.

3. **Normalización:** `matrix = matrix / sum(matrix)` para que la suma total sea 1.

4. **Probabilidades 1X2:**

   ```
   home_win = sum(matriz triangular inferior estricta)  → ∑ matrix[i>j]
   draw     = sum(diagonal principal)                   → ∑ matrix[i=j]
   away_win = sum(matriz triangular superior estricta)  → ∑ matrix[i<j]
   ```

5. **Top marcadores exactos:** Ordena todas las celdas por probabilidad descendente y toma los `top_n` (default 5).

### Origen de los lambdas (μ)

| Endpoint | Origen de λ | Método |
|----------|-------------|--------|
| `POST /poisson` | Random Forest (regresores A y B) | Puente de conexión absoluta |
| `POST /predict-live` | MongoDB (xG reales del torneo) | Multiplicación de intensidades |

---

## 4. Live In-Play (`live_poisson_use_case.py`)

Predicción basada en **goles esperados (xG) reales** del torneo, almacenados en MongoDB.

### Cálculo de lambdas

```
λ_home = xg_ataque_home × xg_defensa_away
λ_away = xg_ataque_away × xg_defensa_home
```

**Multiplicación de intensidades:** Los goles proyectados son el resultado de la fuerza de ataque de un equipo multiplicada por la vulnerabilidad defensiva del rival. Esto es más realista que un promedio plano.

### Valores fallback

Si un equipo no tiene registros en MongoDB (debutante o datos no migrados):

| Parámetro | Fallback |
|-----------|----------|
| `xg_ataque` (local) | 1.35 |
| `xg_defensa` (local) | 1.10 |
| `xg_ataque` (visitante) | 1.10 |
| `xg_defensa` (visitante) | 1.35 |

Si solo uno de los dos equipos tiene registros, se usa directamente su ataque estimado como lambda (sin multiplicación).

### Piso mínimo

`λ = max(0.1, λ)` — evita que Poisson colapse con valores en 0.

---

## 5. Dataset: `data/results.csv`

Histórico de partidos internacionales (formato Kaggle):

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `date` | string (YYYY-MM-DD) | Fecha del partido |
| `home_team` | string | Equipo local (en inglés) |
| `away_team` | string | Equipo visitante (en inglés) |
| `home_score` | int | Goles del local |
| `away_score` | int | Goles del visitante |
| `tournament` | string | Torneo (Friendly, FIFA World Cup, etc.) |
| `city` | string | Ciudad |
| `country` | string | País |
| `neutral` | bool | TRUE si el partido fue en cancha neutral |

- **Total:** ~49.368 registros (desde 1872).
- **Ventana Poisson:** 2024-2026 (`data_loader.py:13`).
- **Ventana Random Forest:** 2018+ (`data_processor.py:9`).

---

## 6. XGBoost Set Pieces (Corners y Tiros a Puerta)

### Modelos persistidos

| Archivo | Tipo | Objetivo |
|---------|------|---------|
| `models_pkl/modelo_xgboost_corners_home.pkl` | `XGBRegressor` | Predecir corners del equipo local (λ) |
| `models_pkl/modelo_xgboost_corners_away.pkl` | `XGBRegressor` | Predecir corners del equipo visitante (λ) |
| `models_pkl/modelo_xgboost_shots_home.pkl` | `XGBRegressor` | Predecir tiros a puerta del equipo local (λ) |
| `models_pkl/modelo_xgboost_shots_away.pkl` | `XGBRegressor` | Predecir tiros a puerta del equipo visitante (λ) |
| `models_pkl/stats_set_pieces.pkl` | `DataFrame` | Estadísticas promedio por equipo y rol (local/visitante) |

### Features (12 variables)

Los 4 modelos comparten el mismo vector de features, extraído de estadísticas reales en MongoDB:

| Feature | Descripción |
|---------|-------------|
| `corners_scored_home_A` | Promedio de corners anotados por A como local |
| `corners_conceded_home_A` | Promedio de corners concedidos por A como local |
| `corners_scored_away_B` | Promedio de corners anotados por B como visitante |
| `corners_conceded_away_B` | Promedio de corners concedidos por B como visitante |
| `shots_scored_home_A` | Promedio de tiros a puerta de A como local |
| `shots_conceded_home_A` | Promedio de tiros a puerta concedidos por A como local |
| `shots_scored_away_B` | Promedio de tiros a puerta de B como visitante |
| `shots_conceded_away_B` | Promedio de tiros a puerta concedidos por B como visitante |
| `possession_home_A` | Posesión promedio de A como local (%) |
| `possession_away_B` | Posesión promedio de B como visitante (%) |
| `xg_home_A` | xG promedio de A como local |
| `xg_away_B` | xG promedio de B como visitante |

### Hiperparámetros

```python
XGBRegressor(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)
```

Definidos en `src/infrastructure/set_pieces_trainer.py`.

### Pipeline de entrenamiento (`set_pieces_trainer.py`)

`entrenar_y_guardar_set_pieces()`:

1. **Conexión MongoDB:** Lee `MONGO_URI` y `MONGO_DB_NAME` desde `.env`.
2. **Lectura:** Obtiene todos los documentos de `partidos_reales`.
3. **Stats por equipo:** Para cada equipo, calcula promedios desglosados por rol (local/visitante):
   - Corners anotados / concedidos
   - Tiros a puerta anotados / concedidos
   - Posesión (%)
   - xG (goles esperados)
4. **Dataset:** Construye una fila por partido con los 12 features + 4 targets.
5. **Entrenamiento:** Ajusta 4 regresores XGBoost independientes.
6. **Persistencia:** Guarda 5 archivos `.pkl` en `models_pkl/`.

```bash
python -c "import sys; sys.path.append('src'); from infrastructure.set_pieces_trainer import entrenar_y_guardar_set_pieces; entrenar_y_guardar_set_pieces()"
```

### Predicción (`set_pieces_predictor.py`)

`XGBoostSetPiecesPredictor.predict_expected_counts(home_team, away_team)`:

1. **Carga lazy:** Los modelos se cargan al primer request, no al iniciar la API.
2. **Lookup de stats:** Busca `home_team` como local y `away_team` como visitante en `stats_set_pieces.pkl`.
3. **Construcción de features:** Arma el vector de 12 features.
4. **Predicción:** 4 modelos XGBoost predicen λ para corners y tiros (home/away).
5. **Piso mínimo:** `λ = max(0.1, λ)` para evitar colapso de Poisson.
6. **Output:** `SetPiecesExpectedCounts` con los 4 lambdas.

### Dixon-Coles para Corners y Tiros a Puerta

Los lambdas predichos por XGBoost alimentan el mismo `ScipyPoissonCalculator` (con ajuste Dixon-Coles) usado para goles, pero con matrices más grandes:

| Métrica | `max_goals` | Tamaño matriz | Líneas Over/Under |
|---------|-------------|---------------|-------------------|
| Corners | 20 | 20×20 | 7.5, 8.5, 9.5, 10.5, 11.5 |
| Tiros a puerta | 15 | 15×15 | 4.5, 5.5, 6.5, 7.5, 8.5, 9.5 |

El ajuste Dixon-Coles (τ=0.08) se aplica a las celdas 0-0, 1-0, 0-1, 1-1. Para métricas con valores esperados altos (corners ~6-10), estas celdas tienen probabilidad muy baja, por lo que el ajuste tiene impacto mínimo pero se mantiene por consistencia.

### Output completo por métrica

Para cada métrica (corners y tiros a puerta), el use case devuelve:

| Campo | Descripción |
|-------|-------------|
| `expected_home` / `expected_away` | λ predichos por XGBoost |
| `probabilities_1x2` | P(home tiene más), P(empate), P(away tiene más) (%) |
| `fair_odds` | Cuotas justas = 1 / probabilidad |
| `top_exact_counts` | Top 5 conteos exactos más probables |
| `over_under` | Probabilidades Over/Under (%) para cada línea |

### Flujo XGBoost → Dixon-Coles

```
Request (home, away)
    ↓
XGBoostSetPiecesPredictor.predict_expected_counts()
    ↓  (4 modelos XGBoost)
λ_corners_home, λ_corners_away, λ_shots_home, λ_shots_away
    ↓
ScipyPoissonCalculator.calculate_distribution()  ← corners (20×20)
ScipyPoissonCalculator.calculate_over_under()    ← corners
    ↓
ScipyPoissonCalculator.calculate_distribution()  ← shots (15×15)
ScipyPoissonCalculator.calculate_over_under()    ← shots
    ↓
SetPiecesPredictionResult (domain model)
```
