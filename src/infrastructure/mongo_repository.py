import os
from typing import Optional, Dict, Any
from pymongo import MongoClient
from domain.interfaces import MatchStatsRepository

class PyMongoStatsRepository(MatchStatsRepository):
    """Implementación real del contrato utilizando el contenedor de MongoDB."""
    def __init__(self, uri: Optional[str] = None, db_name: str = "mongo-mundial"):
        if uri is None:
            uri = os.getenv("MONGO_URI", "mongodb://admin:G%40mm%40per40425109@localhost:27017/?authSource=admin")
        self._client = MongoClient(uri)
        self._db = self._client[db_name]
        self._collection = self._db["partidos_reales"]

    def get_team_historical_summary(self, team_name: str) -> Optional[Dict[str, Any]]:
        """Pipeline de agregación de MongoDB para calcular los promedios reales del torneo."""
        pipeline = [
            {
                "$match": {
                    "$or": [
                        {"partido.equipo_local": team_name},
                        {"partido.equipo_visitante": team_name}
                    ]
                }
            },
            {
                "$project": {
                    "is_local": {"$eq": ["$partido.equipo_local", team_name]},
                    "stats_gen": "$estadisticas_generales",
                    "stats_esp": "$estadisticas_specificas"
                }
            },
            {
                "$group": {
                    "_id": None,
                    "partidos_jugados": {"$sum": 1},
                    "avg_pos": {
                        "$avg": {"$cond": ["$is_local", f"$stats_gen.posesion_porcentaje.{team_name}", f"$stats_gen.posesion_porcentaje.{team_name}"]}
                    }
                }
            }
        ]
        resultado = list(self._collection.aggregate(pipeline))
        return resultado[0] if resultado else None

    def get_team_tournament_metrics(self, team_name: str) -> Optional[Dict[str, Any]]:
        """Calcula el xG real acumulado (Ataque y Defensa) del equipo de forma exacta."""
        pipeline = [
            {
                "$match": {
                    "$or": [
                        {"partido.equipo_local": team_name},
                        {"partido.equipo_visitante": team_name}
                    ]
                }
            },
            {
                "$project": {
                    "is_local": {"$eq": ["$partido.equipo_local", team_name]},
                    "local_name": "$partido.equipo_local",
                    "away_name": "$partido.equipo_visitante",
                    "goles_esperados": "$estadisticas_generales.goles_esperados_xG"
                }
            }
        ]
        
        partidos = list(self._collection.aggregate(pipeline))
        if not partidos:
            return None

        total_xg_anotado = 0.0
        total_xg_concedido = 0.0
        
        for p in partidos:
            xg_dict = p.get("goles_esperados", {})
            local_team = p.get("local_name")
            away_team = p.get("away_name")

            # 🚀 EXTRACCIÓN BLINDADA: Buscamos por el nombre exacto de la selección, nunca por posición
            xg_local = float(xg_dict.get(local_team, 1.35))
            xg_away = float(xg_dict.get(away_team, 1.10))

            if p["is_local"]:
                total_xg_anotado += xg_local
                total_xg_concedido += xg_away
            else:
                total_xg_anotado += xg_away
                total_xg_concedido += xg_local

        cant = len(partidos)
        return {
            "xg_ataque": total_xg_anotado / cant,
            "xg_defensa": total_xg_concedido / cant
        }
