# Plan: Documentación del proyecto fifaForecast_backend_ia

## Contexto

Backend de IA para predecir resultados del Mundial FIFA 2026. Combina dos motores: **Random Forest** (scikit-learn, modelos `.pkl` preentrenados) y **Distribución de Poisson** con ajuste Dixon-Coles (scipy). Expone una API REST (FastAPI) con 4 endpoints bajo `/api/v1`, consulta MongoDB para estadísticas históricas y predicciones live, y sigue una **arquitectura hexagonal** (domain → application → infrastructure → entrypoints) con inyección manual de dependencias.

Stack: FastAPI 0.110, Uvicorn 0.28, Pydantic 2.6, pandas 2.2, numpy 1.26, scipy 1.12, scikit-learn 1.4, joblib, pymongo 4.6, python-dotenv. Puerto 5002.

Dataset: `data/results.csv` (~49.368 partidos internacionales desde 1872, columnas: date, home_team, away_team, home_score, away_score, tournament, city, country, neutral).

## Decisión

Crear **5 archivos Markdown** de documentación. Idioma: español (consistente con el código y los prints del proyecto). No modificar código fuente.

## Archivos a crear

### 1. `README.md` (raíz del proyecto)
Documento principal de entrada. Contenido:
- Título y descripción breve del proyecto (motor unificado RF + Poisson para Mundial 2026).
- Badge/tabla de stack tecnológico con versiones.
- Requisitos previos (Python 3.10+, MongoDB en Docker, dataset `results.csv`).
- Instalación: `pip install -r requirements.txt`, variables de entorno (`.env`): `MONGO_URI`, `MONGO_DB_NAME`, `RUTA_JSON_PARTIDOS`.
- Ejecución: `python main.py` (puerto 5002) o `uvicorn main:app --port 5002`.
- Tabla resumen de endpoints (`/api/v1/random-forest`, `/poisson`, `/match-stats`, `/predict-live`) con método, descripción y link a `docs/api-reference.md`.
- Estructura de directorios (árbol comentado).
- Link a la documentación detallada en `docs/`.
- Sección de reentrenamiento de modelos (`trainer.py`).

### 2. `docs/arquitectura.md`
Explicación de la arquitectura hexagonal / Clean Architecture:
- Diagrama de capas (domain → application → infrastructure → entrypoints) en ASCII/mermaid.
- Responsabilidad de cada capa con los archivos concretos que contiene.
- Principios SOLID aplicados: Inversión de Dependencias (interfaces ABC en `domain/interfaces.py`, inyección en `entrypoints/api.py`), Principio S (carga desacoplada), Principio O (motor estadístico intercambiable).
- Flujo de datos por endpoint (ej: `/poisson`): request → router → use case → SimuladorMundial (puente RF→Poisson) → ScipyPoissonCalculator → mapeo a modelos de dominio → response.
- El "Puente de Conexión Absoluta": cómo `PoissonUseCase` consume los lambdas proyectados del Random Forest (`predictor.py`) para alimentar el cálculo Poisson.
- Ciclo de vida: evento `startup` inicializa diccionarios Poisson.

### 3. `docs/api-reference.md`
Referencia completa de la API. Por cada endpoint:
- Método, ruta, descripción.
- Esquema de request (`MatchRequest`: home_team, away_team) con ejemplo JSON.
- Esquema de response con ejemplo JSON real (basado en los dataclasses de `domain/models.py` y los returns de los use cases).
- Códigos de error (404 equipo no registrado, 500 error interno).
Endpoints a documentar:
- `POST /api/v1/random-forest` → `RandomForestPredictionResult` (doble_oportunidad, probabilidades 1X2, mas_menos_goles, ambos_anotan, marcador_exacto).
- `POST /api/v1/poisson` → `PoissonPredictionResult` (expected_goals, probabilities_1X2, fair_odds, top_exact_scores).
- `GET /api/v1/match-stats?team=` → summary de agregación MongoDB.
- `POST /api/v1/predict-live` → predicción live in-play con métricas xG reales del torneo (metodo, probabilidades_1X2, marcadores_mas_probables, analisis_cuota).
- Endpoint raíz `GET /` (health check).
- Nota sobre `TeamTranslator` (homogeneización español→inglés entre Mongo/API y CSV).

### 4. `docs/modelos-ia.md`
Documentación del pipeline de Machine Learning:
- **Random Forest**: features usados (ataque/defensa home/away A y B, is_neutral_match), hiperparámetros (n_estimators=150, max_depth=7, random_state=42), 3 modelos (clasificador 1X2 + 2 regresores de goles A/B). Lógica de `predictor.py`: detección de anfitriones (Mexico/USA/Canada → no neutral), cálculo de doble oportunidad (umbral 72%), piso de lambdas en 0.05, desempate de marcador por diferencia de probabilidades >5%.
- **Entrenamiento** (`trainer.py`): ventana 2018+, `data_processor.py` genera stats asimétricas (ataque/defensa por rol), función `registrar_jornada_real_y_reentrenar` para reentrenamiento incremental.
- **Poisson + Dixon-Coles** (`poisson_calculator.py`): matriz 8x8, ajuste tau=0.08 en low-score (0-0, 1-0, 0-1, 1-1), normalización, cálculo 1X2 (tril/diag/triu), top_n marcadores exactos.
- **Live In-Play** (`live_poisson_use_case.py`): lambdas = ataque × defensa rival (multiplicación de intensidades), fallback 1.35/1.10 si no hay registros en Mongo, piso 0.1.
- Persistencia: `models_pkl/` (4 archivos joblib).

### 5. `docs/base-datos.md`
Documentación de MongoDB:
- Configuración: variables de entorno, URI por defecto, db `mongo-mundial`, colección `partidos_reales`.
- Script de migración `migrate_jsons_to_mongo.py`: lee JSONs de `RUTA_JSON_PARTIDOS`, índice único compuesto (fecha + equipo_local + equipo_visitante), manejo de duplicados (`DuplicateKeyError`), reporte ejecutivo.
- Estructura esperada de los documentos JSON (partido, estadisticas_generales, estadisticas_specificas) inferida de los pipelines de `mongo_repository.py`.
- Pipelines de agregación: `get_team_historical_summary` (posesión promedio) y `get_team_tournament_metrics` (xG ataque/defensa acumulado, extracción blindada por nombre de selección).
- Comando Docker sugerido para levantar MongoDB.

## Reglas de estilo
- Español, tono técnico conciso.
- Usar bloques de código con lenguaje especificado (```python, ```bash, ```json).
- Referencias a archivos con ruta relativa y número de línea cuando aplique.
- Diagramas en mermaid donde aporten claridad.
- No inventar información: todo el contenido se extrae del código real ya leído.

## Validación
- Verificar que los 5 archivos se crean en las rutas correctas.
- Confirmar que las rutas de archivo referenciadas existen en el repo.
- Comprobar que los ejemplos JSON de response coinciden con los dataclasses/returns reales del código.
