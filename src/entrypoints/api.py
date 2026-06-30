from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path

from infrastructure.data_loader import PandasMatchDataLoader
from infrastructure.poisson_calculator import ScipyPoissonCalculator
from infrastructure.predictor import SimuladorMundial
from infrastructure.mongo_repository import PyMongoStatsRepository

from application.random_forest_use_case import RandomForestUseCase
from application.poisson_use_case import PoissonUseCase
from application.get_stats_use_case import GetStatsUseCase
from application.live_poisson_use_case import LivePoissonUseCase
from infrastructure.team_translator import TeamTranslator

router = APIRouter(prefix="/api/v1")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / "data" / "results.csv"

# Instanciación e Inyección de Dependencias
data_loader = PandasMatchDataLoader()
poisson_calculator = ScipyPoissonCalculator()
simulador_forest = SimuladorMundial(model_prefix="rf")
simulador_xgb = SimuladorMundial(model_prefix="xgb")
mongo_repo = PyMongoStatsRepository()

rf_use_case = RandomForestUseCase(simulador_forest=simulador_forest)
xgb_use_case = RandomForestUseCase(simulador_forest=simulador_xgb)
poisson_use_case = PoissonUseCase(
    data_loader=data_loader,
    prob_calculator=poisson_calculator,
    simulador_forest=simulador_xgb,
    data_path=str(DATA_PATH),
    top_n=5
)
stats_use_case = GetStatsUseCase(repository=mongo_repo)
live_poisson_use_case = LivePoissonUseCase(mongo_repo=mongo_repo, prob_calculator=poisson_calculator)

class MatchRequest(BaseModel):
    home_team: str
    away_team: str

@router.post("/random-forest")
def predict_random_forest(request: MatchRequest):
    """Endpoint clásico que utiliza el modelo RandomForest original."""
    try:  
        return rf_use_case.execute(request.home_team, request.away_team)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en Random Forest: {str(e)}")

@router.post("/predict-ml")
def predict_ml(request: MatchRequest):
    """Endpoint moderno que utiliza el modelo XGBoost con decaimiento temporal y ELO."""
    try:
        return xgb_use_case.execute(request.home_team, request.away_team)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en XGBoost Engine: {str(e)}")

@router.post("/poisson")
def predict_poisson(request: MatchRequest):
    try:
        return poisson_use_case.execute(request.home_team, request.away_team)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en Poisson: {str(e)}")
    
@router.get("/match-stats")
def get_team_stats(team: str = Query(..., description="Nombre de la selección en español")):
    try:
        return stats_use_case.execute(team.strip())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Error al consultar MongoDB.")

@router.post("/predict-live")
def predict_live_match(request: MatchRequest):
    try:
        return live_poisson_use_case.execute(request.home_team.strip(), request.away_team.strip())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la simulación Live In-Play: {str(e)}")