# FIFA World Cup 2026 — Unified Forecasting Engine

Backend de Inteligencia Artificial para predecir resultados del **Mundial FIFA 2026**. Combina dos motores predictivos en un solo ecosistema:

1. **Random Forest** (scikit-learn) — clasifica resultados (1X2, doble oportunidad, over/under 2.5 goles, ambos anotan, marcador exacto) usando modelos `.pkl` preentrenados.
2. **Distribución de Poisson** con ajuste **Dixon-Coles** (scipy) — calcula goles esperados, probabilidades 1X2, cuotas justas y top marcadores exactos a partir del histórico de partidos internacionales.
3. **XGBoost + Dixon-Coles** — predice corners y tiros a puerta con distribución probabilística completa (1X2, Over/Under, conteos exactos) entrenado desde estadísticas reales en MongoDB.

Además consulta **MongoDB** para estadísticas históricas de selecciones y predicciones *live in-play* basadas en xG reales del torneo.

---

## Stack tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Framework web | FastAPI | 0.110.0 |
| Servidor ASGI | Uvicorn | 0.28.0 |
| Validación | Pydantic | 2.6.4 |
| Procesamiento de datos | pandas | 2.2.1 |
| Cálculo numérico | numpy | 1.26.4 |
| Estadística | scipy | 1.12.0 |
| Machine Learning | scikit-learn | 1.4.1.post1 |
| Machine Learning (set pieces) | XGBoost | 2.0.3 |
| Persistencia de modelos | joblib | 1.3.2 |
| Base de datos | MongoDB (pymongo) | 4.6.2 |
| Variables de entorno | python-dotenv | 1.0.1 |

---

## Requisitos previos

- **Python 3.10+**
- **MongoDB** ejecutándose (contenedor Docker recomendado)
- Dataset `data/results.csv` (~49.368 partidos internacionales desde 1872)

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd fifaForecast_backend_ia

# 2. Instalar dependencias
pip install -r requirements.txt
```

### Variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
MONGO_URI=mongodb://usuario:password@localhost:27017/?authSource=admin
MONGO_DB_NAME=mongo-mundial
RUTA_JSON_PARTIDOS=/ruta/absoluta/a/jsons_de_partidos
```

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MONGO_URI` | URI de conexión a MongoDB | `mongodb://localhost:27017/` |
| `MONGO_DB_NAME` | Nombre de la base de datos | `mongo-mundial` |
| `RUTA_JSON_PARTIDOS` | Directorio con JSONs de partidos reales | Raíz del proyecto |

---

## Ejecución

```bash
# Opción 1: directa
python main.py

# Opción 2: con uvicorn y recarga
uvicorn main:app --host 127.0.0.1 --port 5002 --reload
```

La API queda disponible en `http://127.0.0.1:5002`.

- Documentación interactiva (Swagger UI): `http://127.0.0.1:5002/docs`
- ReDoc: `http://127.0.0.1:5002/redoc`

Al iniciar, el evento `startup` pre-carga los diccionarios de estadísticas de Poisson en memoria.

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/api/v1/random-forest` | Predicción con Random Forest |
| `POST` | `/api/v1/poisson` | Predicción con distribución de Poisson |
| `GET` | `/api/v1/match-stats?team=` | Estadísticas históricas desde MongoDB |
| `POST` | `/api/v1/predict-live` | Simulación live in-play (Poisson + xG de MongoDB) |
| `POST` | `/api/v1/set-pieces` | Predicción de corners y tiros a puerta (XGBoost + Dixon-Coles) |

> Referencia completa con ejemplos request/response en [`docs/api-reference.md`](docs/api-reference.md).

---

## Estructura de directorios

```
fifaForecast_backend_ia/
├── main.py                          # Punto de entrada FastAPI + evento startup
├── migrate_jsons_to_mongo.py        # Script ETL: JSON → MongoDB
├── requirements.txt
├── .env                             # Variables de entorno (no versionado)
├── data/
│   └── results.csv                  # Histórico de partidos (dataset Poisson + RF)
├── models_pkl/                      # Modelos serializados (joblib)
│   ├── modelo_clasificador_mundial.pkl
│   ├── modelo_regresor_A.pkl
│   ├── modelo_regresor_B.pkl
│   ├── stats_neutrales.pkl
│   ├── modelo_xgboost_corners_home.pkl
│   ├── modelo_xgboost_corners_away.pkl
│   ├── modelo_xgboost_shots_home.pkl
│   ├── modelo_xgboost_shots_away.pkl
│   └── stats_set_pieces.pkl
└── src/
    ├── domain/                      # Núcleo: entidades + interfaces (ABC)
    │   ├── models.py
    │   └── interfaces.py
    ├── application/                 # Casos de uso (orquestación)
    │   ├── random_forest_use_case.py
    │   ├── poisson_use_case.py
    │   ├── get_stats_use_case.py
    │   ├── live_poisson_use_case.py
    │   └── set_pieces_use_case.py
    ├── infrastructure/              # Adaptadores/implementaciones concretas
    │   ├── data_loader.py
    │   ├── data_processor.py
    │   ├── poisson_calculator.py
    │   ├── predictor.py
    │   ├── trainer.py
    │   ├── set_pieces_trainer.py
    │   ├── set_pieces_predictor.py
    │   ├── team_translator.py
    │   └── mongo_repository.py
    └── entrypoints/
        └── api.py                   # Router /api/v1 + inyección de dependencias
```

---

## Reentrenamiento de modelos

El pipeline de reentrenamiento vive en `src/infrastructure/trainer.py`:

```python
from infrastructure.trainer import entrenar_y_guardar_modelos, registrar_jornada_real_y_reentrenar

# Reentrenar con el dataset actual
entrenar_y_guardar_modelos()

# Registrar un resultado real y reentrenar automáticamente
registrar_jornada_real_y_reentrenar("Brazil", "Argentina", 2, 1)
```

Esto regenera los 4 archivos `.pkl` en `models_pkl/`. Ver [`docs/modelos-ia.md`](docs/modelos-ia.md) para detalles del pipeline.

### Set Pieces (XGBoost)

El pipeline de entrenamiento para corners y tiros a puerta vive en `src/infrastructure/set_pieces_trainer.py` y lee los datos desde MongoDB:

```bash
python -c "import sys; sys.path.append('src'); from infrastructure.set_pieces_trainer import entrenar_y_guardar_set_pieces; entrenar_y_guardar_set_pieces()"
```

Esto genera 5 archivos `.pkl` (4 modelos XGBoost + 1 DataFrame de stats). La API carga los modelos de forma **lazy** al primer request a `/api/v1/set-pieces`.

---

## Migración de datos a MongoDB

```bash
python migrate_jsons_to_mongo.py
```

Carga los JSONs de partidos reales en MongoDB con índice único anti-duplicados. Ver [`docs/base-datos.md`](docs/base-datos.md).

---

## Documentación adicional

| Documento | Contenido |
|-----------|-----------|
| [`docs/arquitectura.md`](docs/arquitectura.md) | Arquitectura hexagonal, capas, SOLID, flujos de datos |
| [`docs/api-reference.md`](docs/api-reference.md) | Referencia completa de la API REST |
| [`docs/modelos-ia.md`](docs/modelos-ia.md) | Pipeline de Machine Learning (RF + Poisson + Dixon-Coles) |
| [`docs/base-datos.md`](docs/base-datos.md) | MongoDB: configuración, migración, esquema, agregaciones |
