import sys
import os
from fastapi import FastAPI

# Garantizar que el intérprete de Python indexe la carpeta 'src' de manera nativa sin importar variables de entorno externas
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from entrypoints.api import router, poisson_use_case

app = FastAPI(
    title="Fifa World Cup 2026 Unified Forecasting Engine",
    description="Ecosistema unificado de Inteligencia Artificial (Random Forest + Distribución de Poisson)."
)

# Acoplamos el Router Único con sus dos endpoints
app.include_router(router)

@app.on_event("startup")
def startup_event():
    """Ciclo de vida Starlette: Inicializa los diccionarios de Poisson al encender la API."""
    print("🧠 Inicializando el motor analítico unificado...")
    poisson_use_case.initialize()
    print("🚀 ¡Ecosistema predictivo operando exitosamente!")

@app.get("/")
def root():
    return {"status": "online", "project": "fifaForecast_backend", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    # Exponer de manera estricta el puerto 5001 solicitado
    uvicorn.run("main:app", host="127.0.0.1", port=5001, reload=True)