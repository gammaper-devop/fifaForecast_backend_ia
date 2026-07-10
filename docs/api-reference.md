# Referencia de la API REST

Base URL: `http://127.0.0.1:5002`

Todos los endpoints de predicción están bajo el prefijo `/api/v1`.

---

## Health Check

### `GET /`

Verifica que la API está operativa.

**Response `200 OK`:**

```json
{
  "status": "online",
  "project": "fifaForecast_backend",
  "version": "1.0.0"
}
```

---

## Modelo de request compartido

Los endpoints `POST` usan el mismo esquema `MatchRequest`:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `home_team` | `string` | Nombre de la selección local (en inglés, formato CSV) |
| `away_team` | `string` | Nombre de la selección visitante (en inglés, formato CSV) |

> **Nota sobre nombres de equipos:** Los nombres deben coincidir con el formato del CSV `data/results.csv` (ej: `Brazil`, `Argentina`, `Germany`). La clase `TeamTranslator` (`src/infrastructure/team_translator.py`) permite homogeneizar nombres en español (ej: `brasil` → `Brazil`) para integración con MongoDB/API externas.

---

## `POST /api/v1/random-forest`

Predicción con el motor Random Forest. Usa 3 modelos preentrenados (clasificador 1X2 + 2 regresores de goles).

**Request:**

```json
{
  "home_team": "Brazil",
  "away_team": "Argentina"
}
```

**Response `200 OK`:**

```json
{
  "equipo_1": "Brazil",
  "equipo_2": "Argentina",
  "doble_oportunidad": "Gana Brazil o Empate",
  "probabilidad_1": 58.3,
  "probabilidad_empate": 24.1,
  "probabilidad_2": 17.6,
  "mas_menos_goles": "Más de 2.5",
  "ambos_anotan": "SÍ",
  "marcador_exacto": "2 - 1"
}
```

| Campo | Descripción |
|-------|-------------|
| `doble_oportunidad` | Recomendación de doble oportunidad (umbral 72%) |
| `probabilidad_1` | Probabilidad de victoria local (%) |
| `probabilidad_empate` | Probabilidad de empate (%) |
| `probabilidad_2` | Probabilidad de victoria visitante (%) |
| `mas_menos_goles` | `"Más de 2.5"` o `"Menos de 2.5"` |
| `ambos_anotan` | `"SÍ"` o `"NO"` |
| `marcador_exacto` | Marcador proyectado (ej: `"2 - 1"`) |

**Errores:**

| Código | Causa |
|--------|-------|
| `404` | Uno o ambos equipos no están registrados en `stats_neutrales.pkl` |
| `500` | Error interno del motor |

---

## `POST /api/v1/poisson`

Predicción con distribución de Poisson ajustada por Dixon-Coles. Los goles esperados (lambdas) provienen del Random Forest (puente de conexión).

**Request:**

```json
{
  "home_team": "Brazil",
  "away_team": "Argentina"
}
```

**Response `200 OK`:**

```json
{
  "teams": {
    "home": "Brazil",
    "away": "Argentina"
  },
  "expected_goals": {
    "home": 1.8234,
    "away": 1.0567
  },
  "probabilities_1X2": {
    "home_win": 52.45,
    "draw": 24.18,
    "away_win": 23.37
  },
  "fair_odds": {
    "home_win": 1.91,
    "draw": 4.14,
    "away_win": 4.28
  },
  "top_exact_scores": [
    {
      "score": "1-1",
      "formatted_score": "Brazil 1 - 1 Argentina",
      "probability_percent": 14.82
    },
    {
      "score": "2-1",
      "formatted_score": "Brazil 2 - 1 Argentina",
      "probability_percent": 12.35
    },
    {
      "score": "1-0",
      "formatted_score": "Brazil 1 - 0 Argentina",
      "probability_percent": 10.71
    },
    {
      "score": "0-1",
      "formatted_score": "Brazil 0 - 1 Argentina",
      "probability_percent": 8.43
    },
    {
      "score": "2-0",
      "formatted_score": "Brazil 2 - 0 Argentina",
      "probability_percent": 7.92
    }
  ]
}
```

| Campo | Descripción |
|-------|-------------|
| `expected_goals` | Goles esperados (λ) proyectados por el Random Forest |
| `probabilities_1X2` | Probabilidades 1X2 (%) tras ajuste Dixon-Coles |
| `fair_odds` | Cuotas justas = 1 / probabilidad |
| `top_exact_scores` | Top 5 marcadores más probables con probabilidad (%) |

**Errores:**

| Código | Causa |
|--------|-------|
| `404` | Uno o ambos equipos no existen en los registros recientes (ventana 2024-2026) |
| `500` | Error interno del motor |

---

## `GET /api/v1/match-stats`

Estadísticas históricas de una selección desde MongoDB (pipeline de agregación).

**Query parameter:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `team` | `string` | Nombre de la selección (en español) |

**Ejemplo:**

```
GET /api/v1/match-stats?team=Brasil
```

**Response `200 OK`:**

```json
{
  "_id": null,
  "partidos_jugados": 5,
  "avg_pos": 58.4
}
```

| Campo | Descripción |
|-------|-------------|
| `partidos_jugados` | Total de partidos del equipo en la colección `partidos_reales` |
| `avg_pos` | Posesión promedio (%) |

**Errores:**

| Código | Causa |
|--------|-------|
| `404` | No se encontraron registros en el torneo para la selección |
| `500` | Error al consultar MongoDB |

---

## `POST /api/v1/predict-live`

Simulación *live in-play* basada en métricas xG reales del torneo almacenadas en MongoDB. No usa el Random Forest; los lambdas se calculan multiplicando ataque del equipo por defensa del rival.

**Request:**

```json
{
  "home_team": "Brasil",
  "away_team": "Argentina"
}
```

**Response `200 OK`:**

```json
{
  "metodo": "Métricas xG Reales del Torneo (Live In-Play)",
  "encuentro": "Brasil vs Argentina",
  "probabilidades_1X2": {
    "gana_local": 49.8,
    "empate": 26.3,
    "gana_visitante": 23.9
  },
  "marcadores_mas_probables": [
    {
      "score": "1-1",
      "prob": 0.1482
    },
    {
      "score": "1-0",
      "prob": 0.1071
    },
    {
      "score": "2-1",
      "prob": 0.0935
    },
    {
      "score": "0-1",
      "prob": 0.0843
    },
    {
      "score": "2-0",
      "prob": 0.0712
    }
  ],
  "analisis_cuota": "Recomendado Local o Empate"
}
```

| Campo | Descripción |
|-------|-------------|
| `metodo` | Identificador del método de cálculo |
| `encuentro` | Formato legible del partido |
| `probabilidades_1X2` | Probabilidades 1X2 (%) |
| `marcadores_mas_probables` | Top 5 marcadores con probabilidad (fracción 0-1) |
| `analisis_cuota` | Recomendación táctica basada en comparación de probabilidades |

**Cálculo de lambdas:**

```
λ_home = xg_ataque_home × xg_defensa_away
λ_away = xg_ataque_away × xg_defensa_home
```

Si un equipo no tiene registros en MongoDB, se usan valores **fallback**: ataque 1.35, defensa 1.10. Piso mínimo de 0.1 para evitar colapso de Poisson.

**Errores:**

| Código | Causa |
|--------|-------|
| `404` | Equipo no encontrado (manejado por fallback interno) |
| `500` | Error en la simulación live in-play |

---

## `POST /api/v1/set-pieces`

Predicción de **corners** y **tiros a puerta** usando XGBoost + Dixon-Coles. Los goles esperados (λ) provienen de 4 modelos XGBoost preentrenados desde MongoDB. Luego se aplica Dixon-Coles para obtener distribuciones probabilísticas completas.

**Request:**

```json
{
  "home_team": "España",
  "away_team": "Belgica"
}
```

> Los nombres de equipos deben coincidir con los usados en MongoDB (`partidos_reales`), en español.

**Response `200 OK`:**

```json
{
  "teams": {
    "home": "España",
    "away": "Belgica"
  },
  "expected_counts": {
    "corners_home": 6.7963,
    "corners_away": 5.2084,
    "shots_on_target_home": 7.5213,
    "shots_on_target_away": 4.6998
  },
  "corners": {
    "expected_home": 6.7963,
    "expected_away": 5.2084,
    "probabilities_1x2": {
      "home_win": 62.26,
      "draw": 10.52,
      "away_win": 27.22
    },
    "fair_odds": {
      "home_win": 1.61,
      "draw": 9.51,
      "away_win": 3.67
    },
    "top_exact_counts": [
      {
        "score": "6-5",
        "formatted_score": "España 6 - 5 Belgica",
        "probability_percent": 2.67
      },
      {
        "score": "7-5",
        "formatted_score": "España 7 - 5 Belgica",
        "probability_percent": 2.6
      },
      {
        "score": "6-4",
        "formatted_score": "España 6 - 4 Belgica",
        "probability_percent": 2.57
      },
      {
        "score": "7-4",
        "formatted_score": "España 7 - 4 Belgica",
        "probability_percent": 2.49
      },
      {
        "score": "5-5",
        "formatted_score": "España 5 - 5 Belgica",
        "probability_percent": 2.36
      }
    ],
    "over_under": [
      { "line": 7.5, "over": 91.07, "under": 8.93 },
      { "line": 8.5, "over": 84.53, "under": 15.47 },
      { "line": 9.5, "over": 75.8, "under": 24.2 },
      { "line": 10.5, "over": 65.33, "under": 34.67 },
      { "line": 11.5, "over": 53.89, "under": 46.11 }
    ]
  },
  "shots_on_target": {
    "expected_home": 7.5213,
    "expected_away": 4.6998,
    "probabilities_1x2": {
      "home_win": 74.47,
      "draw": 8.5,
      "away_win": 17.04
    },
    "fair_odds": {
      "home_win": 1.34,
      "draw": 11.77,
      "away_win": 5.87
    },
    "top_exact_counts": [
      {
        "score": "7-4",
        "formatted_score": "España 7 - 4 Belgica",
        "probability_percent": 2.73
      },
      {
        "score": "8-4",
        "formatted_score": "España 8 - 4 Belgica",
        "probability_percent": 2.57
      },
      {
        "score": "7-5",
        "formatted_score": "España 7 - 5 Belgica",
        "probability_percent": 2.57
      },
      {
        "score": "6-4",
        "formatted_score": "España 6 - 4 Belgica",
        "probability_percent": 2.54
      },
      {
        "score": "8-5",
        "formatted_score": "España 8 - 5 Belgica",
        "probability_percent": 2.42
      }
    ],
    "over_under": [
      { "line": 4.5, "over": 99.34, "under": 0.66 },
      { "line": 5.5, "over": 98.21, "under": 1.79 },
      { "line": 6.5, "over": 95.91, "under": 4.09 },
      { "line": 7.5, "over": 91.89, "under": 8.11 },
      { "line": 8.5, "over": 85.74, "under": 14.26 },
      { "line": 9.5, "over": 77.4, "under": 22.6 }
    ]
  }
}
```

### Campos de la respuesta

| Campo | Descripción |
|-------|-------------|
| `expected_counts` | λ predichos por XGBoost para corners y tiros a puerta (home/away) |
| `corners` / `shots_on_target` | Distribución Dixon-Coles completa por métrica |
| `expected_home` / `expected_away` | Goles esperados (λ) por equipo |
| `probabilities_1x2` | Probabilidad de que home tenga más, empate, o away tenga más (%) |
| `fair_odds` | Cuotas justas = 1 / probabilidad |
| `top_exact_counts` | Top 5 conteos exactos más probables (formato `"home-away"`) |
| `over_under` | Líneas Over/Under con probabilidades (%) |

### Líneas Over/Under

| Métrica | Líneas | Matriz Dixon-Coles |
|---------|--------|---------------------|
| Corners | 7.5, 8.5, 9.5, 10.5, 11.5 | 20×20 |
| Tiros a puerta | 4.5, 5.5, 6.5, 7.5, 8.5, 9.5 | 15×15 |

**Errores:**

| Código | Causa |
|--------|-------|
| `404` | Equipo no encontrado en `stats_set_pieces.pkl`, o modelos XGBoost no entrenados |
| `500` | Error en el motor XGBoost + Dixon-Coles |

> **Modelos lazy:** La API arranca sin requerir los modelos XGBoost. Se cargan al primer request a este endpoint. Si no existen, devuelve 404 con instrucciones de entrenamiento.

---

## Traducción de nombres de equipos

La clase `TeamTranslator` (`src/infrastructure/team_translator.py`) homogeneiza nombres entre español (MongoDB/API externa) e inglés (CSV):

| Español (input) | Inglés (output CSV) |
|-----------------|---------------------|
| `brasil` | `Brazil` |
| `alemania` | `Germany` |
| `paises bajos` | `Netherlands` |
| `estados unidos` / `eeuu` | `United States` |
| `corea del sur` / `corea` | `South Korea` |
| `costa de marfil` | `Ivory Coast` |
| `rd congo` | `Democratic Republic of the Congo` |

Si un nombre no está en el diccionario, se aplica `.title()` como fallback.
