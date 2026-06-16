from typing import Optional, Dict, Any
from pymongo import MongoClient
from domain.interfaces import MatchStatsRepository

class PyMongoStatsRepository(MatchStatsRepository):
    """Implementación real del contrato utilizando el contenedor de MongoDB."""
    def __init__(self, uri: str = "mongodb://localhost:27017/", db_name: str = "mongo-mundial"):
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
                    "stats_esp": "$estadisticas_especificas"
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
        """Calcula el xG real acumulado (Ataque y Defensa) del equipo en lo que va del torneo."""
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
            # Extraer las llaves para saber quién es quién
            keys = list(xg_dict.keys())
            if len(keys) < 2:
                continue
                
            local_team, away_team = keys[0], keys[1]
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