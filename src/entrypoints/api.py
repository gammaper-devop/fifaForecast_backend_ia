from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path

# 🚀 AGREGAMOS EL PREFIJO 'src.' PARA QUE PYLANCE LO RESUELVA DE INMEDIATO:
from infrastructure.data_loader import PandasMatchDataLoader
from infrastructure.poisson_calculator import ScipyPoissonCalculator
from infrastructure.predictor import SimuladorMundial
from application.random_forest_use_case import RandomForestUseCase
from application.poisson_use_case import PoissonUseCase

router = APIRouter(prefix="/api/v1")

# Construcción de rutas absolutas para el entorno de producción
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / "data" / "results.csv"

# Inyección e Instanciación unificada de dependencias (Composición)
data_loader = PandasMatchDataLoader()
poisson_calculator = ScipyPoissonCalculator()
simulador_forest = SimuladorMundial()

rf_use_case = RandomForestUseCase(simulador_forest=simulador_forest)
poisson_use_case = PoissonUseCase(
    data_loader=data_loader,
    prob_calculator=poisson_calculator,
    simulador_forest=simulador_forest,
    data_path=str(DATA_PATH),
    top_n=5
)

class MatchRequest(BaseModel):
    home_team: str
    away_team: str

@router.post("/randomForest")
def predict_random_forest(request: MatchRequest):
    try:
        return rf_use_case.execute(request.home_team, request.away_team)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno en el módulo Random Forest.")

@router.post("/poisson")
def predict_poisson(request: MatchRequest):
    try:
        return poisson_use_case.execute(request.home_team, request.away_team)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno en el módulo de distribución Poisson.")