# Base de Datos — MongoDB

MongoDB almacena los **partidos reales del torneo** con sus estadísticas avanzadas (xG, posesión, etc.). Se usa para dos funcionalidades: estadísticas históricas de selecciones (`GET /match-stats`) y predicciones live in-play basadas en xG reales (`POST /predict-live`).

---

## Configuración

### Variables de entorno (`.env`)

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MONGO_URI` | URI de conexión a MongoDB | `mongodb://localhost:27017/` |
| `MONGO_DB_NAME` | Nombre de la base de datos | `mongo-mundial` |
| `RUTA_JSON_PARTIDOS` | Directorio con JSONs de partidos a migrar | Raíz del proyecto |

### Conexión

La clase `PyMongoStatsRepository` (`src/infrastructure/mongo_repository.py`) establece la conexión:

```python
client = MongoClient(uri)
db = client["mongo-mundial"]
collection = db["partidos_reales"]
```

### Levantar MongoDB con Docker

```bash
docker run -d \
  --name mongo-mundial \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=<password> \
  mongo:latest
```

---

## Colección: `partidos_reales`

### Esquema del documento

Inferido de los pipelines de agregación en `mongo_repository.py`:

```json
{
  "partido": {
    "fecha": "2026-06-13",
    "equipo_local": "Mexico",
    "equipo_visitante": "Canada"
  },
  "estadisticas_generales": {
    "posesion_porcentaje": {
      "Mexico": 62.3,
      "Canada": 37.7
    },
    "goles_esperados_xG": {
      "Mexico": 1.85,
      "Canada": 0.72
    }
  },
  "estadisticas_specificas": {
    "tiros_puerta": 7,
    "corners": 9,
    "faltas": 12
  }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `partido.fecha` | string | Fecha del partido (usado en índice único) |
| `partido.equipo_local` | string | Nombre de la selección local |
| `partido.equipo_visitante` | string | Nombre de la selección visitante |
| `estadisticas_generales.posesion_porcentaje` | object | Posesión por equipo (clave = nombre, valor = %) |
| `estadisticas_generales.goles_esperados_xG` | object | xG por equipo (clave = nombre, valor = goles esperados) |
| `estadisticas_specificas` | object | Métricas adicionales del partido |

### Índice único compuesto

```javascript
db.partidos_reales.createIndex(
  { "partido.fecha": 1, "partido.equipo_local": 1, "partido.equipo_visitante": 1 },
  { unique: true }
)
```

Evita duplicados: un mismo partido (fecha + local + visitante) no puede insertarse dos veces.

---

## Script de migración: `migrate_jsons_to_mongo.py`

ETL que carga archivos JSON de partidos reales en MongoDB.

### Uso

```bash
python migrate_jsons_to_mongo.py
```

### Flujo

1. **Conexión:** Lee `MONGO_URI` y `MONGO_DB_NAME` desde `.env` (con fallbacks). Valida conexión con `serverSelectionTimeoutMS=2000`.
2. **Índice:** Crea el índice único compuesto anti-duplicados.
3. **Escaneo:** Lee todos los archivos `.json` del directorio `RUTA_JSON_PARTIDOS` (excluye `empty_template.json`).
4. **Inserción:** Inserta cada JSON en `partidos_reales`.
5. **Manejo de duplicados:** `DuplicateKeyError` → omite sin fallar.
6. **Reporte:** Imprime resumen: partidos nuevos, duplicados omitidos, archivos con error.

### Salida esperada

```
=== INICIANDO SINCRONIZACIÓN CON MONGO-MUNDIAL ===
Buscando archivos JSON en: /ruta/jsons
✅ [NUEVO] Guardado con éxito: partido_001.json
⏭️  [OMITIDO] Ya existía en la base de datos: partido_002.json

==================================================
PROCESO DE SINCRONIZACIÓN DIARIA TERMINADO
Partidos nuevos indexados hoy: 1
Historial preservado (duplicados omitidos): 1
==================================================
```

---

## Pipelines de agregación

### `get_team_historical_summary(team_name)`

Ubicado en `mongo_repository.py:16`. Calcula estadísticas agregadas de un equipo en el torneo.

```javascript
[
  { "$match": {
      "$or": [
        { "partido.equipo_local": team_name },
        { "partido.equipo_visitante": team_name }
      ]
  }},
  { "$project": {
      "is_local": { "$eq": ["$partido.equipo_local", team_name] },
      "stats_gen": "$estadisticas_generales",
      "stats_esp": "$estadisticas_specificas"
  }},
  { "$group": {
      "_id": null,
      "partidos_jugados": { "$sum": 1 },
      "avg_pos": { "$avg": { "$cond": ["$is_local",
        "$stats_gen.posesion_porcentaje.<team>",
        "$stats_gen.posesion_porcentaje.<team>"] }}
  }}
]
```

**Resultado:**

```json
{
  "_id": null,
  "partidos_jugados": 5,
  "avg_pos": 58.4
}
```

### `get_team_tournament_metrics(team_name)`

Ubicado en `mongo_repository.py:46`. Calcula el **xG real acumulado** (ataque y defensa) del equipo.

```javascript
[
  { "$match": {
      "$or": [
        { "partido.equipo_local": team_name },
        { "partido.equipo_visitante": team_name }
      ]
  }},
  { "$project": {
      "is_local": { "$eq": ["$partido.equipo_local", team_name] },
      "local_name": "$partido.equipo_local",
      "away_name": "$partido.equipo_visitante",
      "goles_esperados": "$estadisticas_generales.goles_esperados_xG"
  }}
]
```

El cálculo final se realiza en Python (no en el pipeline):

- **Extracción blindada:** Busca el xG por el **nombre exacto de la selección** en el diccionario `goles_esperados`, nunca por posición. Fallback de 1.35 (local) / 1.10 (visitante) si el nombre no existe.
- **Acumulación:** Suma el xG anotado y concedido en cada partido, distinguiendo si el equipo fue local o visitante.
- **Promedio:** Divide por el número de partidos.

**Resultado:**

```json
{
  "xg_ataque": 1.72,
  "xg_defensa": 0.89
}
```

Estos valores alimentan el cálculo de lambdas en `LivePoissonUseCase`:

```
λ_home = xg_ataque_home × xg_defensa_away
λ_away = xg_ataque_away × xg_defensa_home
```

---

## Integración con el sistema

| Endpoint | Método de Mongo | Uso |
|----------|----------------|-----|
| `GET /api/v1/match-stats` | `get_team_historical_summary()` | Estadísticas históricas (posesión, partidos jugados) |
| `POST /api/v1/predict-live` | `get_team_tournament_metrics()` | xG reales para calcular lambdas de Poisson live |
| `POST /api/v1/set-pieces` | — (offline, vía entrenamiento) | Modelos XGBoost entrenados desde `partidos_reales` |

Los endpoints `POST /random-forest` y `POST /poisson` **no consultan MongoDB**: usan exclusivamente el dataset CSV y los modelos `.pkl`.

El endpoint `POST /set-pieces` **no consulta MongoDB en runtime**: los modelos XGBoost se entrenan offline desde `partidos_reales` y se persisten como `.pkl`. La API solo carga los `.pkl` (lazy) al recibir el primer request.

---

## Entrenamiento XGBoost desde MongoDB

El script `src/infrastructure/set_pieces_trainer.py` lee todos los documentos de `partidos_reales` y entrena 4 modelos XGBoost:

```bash
python -c "import sys; sys.path.append('src'); from infrastructure.set_pieces_trainer import entrenar_y_guardar_set_pieces; entrenar_y_guardar_set_pieces()"
```

### Campos de MongoDB usados para features

| Campo MongoDB | Feature derivado |
|---------------|-----------------|
| `estadisticas_especificas.corners[equipo]` | `corners_scored` (anotados) / `corners_conceded` (del rival) |
| `estadisticas_generales.tiros_a_puerta[equipo]` | `shots_scored` / `shots_conceded` |
| `estadisticas_generales.posesion_porcentaje[equipo]` | `possession` |
| `estadisticas_generales.goles_esperados_xG[equipo]` | `xg` |

Por cada equipo se calculan promedios desglosados por rol (`home` = local, `away` = visitante), generando 12 features por partido. Ver [`docs/modelos-ia.md`](modelos-ia.md) sección 6 para detalles completos.
