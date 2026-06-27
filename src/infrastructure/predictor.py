import os
import joblib
import pandas as pd
from pathlib import Path
from domain.interfaces import PredictorModel

class SimuladorMundial(PredictorModel):
    """Clase encargada de interactuar con los binarios persistidos de Random Forest."""
    def __init__(self):
        # Localización de ruta absoluta dinámica sin importar la terminal de ejecución
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        MODELS_DIR = BASE_DIR / "models_pkl"

        self.model_clas = joblib.load(os.path.join(MODELS_DIR, 'modelo_clasificador_mundial.pkl'))
        self.model_reg_A = joblib.load(os.path.join(MODELS_DIR, 'modelo_regresor_A.pkl'))
        self.model_reg_B = joblib.load(os.path.join(MODELS_DIR, 'modelo_regresor_B.pkl'))
        self.stats_data = joblib.load(os.path.join(MODELS_DIR, 'stats_neutrales.pkl'))
        
        # Cargar diccionarios de ELO y Forma Reciente
        try:
            self.elo_actual = joblib.load(os.path.join(MODELS_DIR, 'elo_actual.pkl'))
            self.historial_partidos = joblib.load(os.path.join(MODELS_DIR, 'historial_partidos.pkl'))
        except Exception:
            # Fallback en caso de que aún no existan
            self.elo_actual = {}
            self.historial_partidos = {}
            
        self.anfitriones = ["Mexico", "United States", "Canada", "México", "EE.UU", "Canadá"]

    def simular(self, equipo_1: str, equipo_2: str) -> dict:
        # Traducir los nombres de las selecciones de Español a Inglés para buscar en los datasets históricos
        from infrastructure.team_translator import TeamTranslator
        eq1_en = TeamTranslator.to_english(equipo_1)
        eq2_en = TeamTranslator.to_english(equipo_2)

        stats_1 = self.stats_data[self.stats_data['equipo'] == eq1_en]
        stats_2 = self.stats_data[self.stats_data['equipo'] == eq2_en]
        
        if stats_1.empty or stats_2.empty:
            return {"error": f"Uno de los equipos ({equipo_1} o {equipo_2}) no está registrado."}

        es_neutral = 1
        # Comprobar si alguno es anfitrión
        if eq1_en in self.anfitriones or eq2_en in self.anfitriones or equipo_1 in self.anfitriones or equipo_2 in self.anfitriones:
            es_neutral = 0

        # ELO pre-partido
        el_1 = self.elo_actual.get(eq1_en, 1500.0)
        el_2 = self.elo_actual.get(eq2_en, 1500.0)
        
        # Forma Reciente (últimos 5 partidos)
        def get_current_form(team_en):
            hist = self.historial_partidos.get(team_en, [])
            if not hist:
                return 1.0, 1.0, 1.0
            recent = hist[-5:]
            pts = sum(x["points"] for x in recent) / len(recent)
            gf = sum(x["goals_scored"] for x in recent) / len(recent)
            ga = sum(x["goals_conceded"] for x in recent) / len(recent)
            return pts, gf, ga
            
        pts_1, gf_1, ga_1 = get_current_form(eq1_en)
        pts_2, gf_2, ga_2 = get_current_form(eq2_en)

        # Construir el vector de variables de entrada coincidiendo exactamente con el entrenamiento (17 variables)
        cara_1 = pd.DataFrame([{
            'ataque_home_A': stats_1['ataque_home'].values[0], 'defensa_home_A': stats_1['defensa_home'].values[0],
            'ataque_away_A': stats_1['ataque_away'].values[0], 'defensa_away_A': stats_1['defensa_away'].values[0],
            'ataque_home_B': stats_2['ataque_home'].values[0], 'defensa_home_B': stats_2['defensa_home'].values[0],
            'ataque_away_B': stats_2['ataque_away'].values[0], 'defensa_away_B': stats_2['defensa_away'].values[0],
            'is_neutral_match': es_neutral,
            'elo_home': el_1, 'elo_away': el_2,
            'form_pts_home': pts_1, 'form_pts_away': pts_2,
            'form_gf_home': gf_1, 'form_gf_away': gf_2,
            'form_ga_home': ga_1, 'form_ga_away': ga_2
        }])

        p1 = self.model_clas.predict_proba(cara_1)[0]
        prob_empate = float(p1[0] * 100)
        prob_eq1 = float(p1[1] * 100)
        prob_eq2 = float(p1[2] * 100)

        if prob_eq1 + prob_empate > 72 and prob_eq1 > prob_eq2:
            doble_oportunidad = f"Gana {equipo_1} o Empate"
        elif prob_eq2 + prob_empate > 72 and prob_eq2 > prob_eq1:
            doble_oportunidad = f"Empate o Gana {equipo_2}"
        else:
            doble_oportunidad = f"Gana {equipo_1} o Gana {equipo_2} (Sin Empate)"

        lambda_1 = max(0.05, float(self.model_reg_A.predict(cara_1)[0]))
        lambda_2 = max(0.05, float(self.model_reg_B.predict(cara_1)[0]))
        
        goles_1_round = int(round(lambda_1))
        goles_2_round = int(round(lambda_2))

        if goles_1_round == goles_2_round:
            if prob_eq1 - prob_eq2 > 5: goles_1_round += 1
            elif prob_eq2 - prob_eq1 > 5: goles_2_round += 1

        # Retornar estructura idéntica para consumo del frontend
        return {
            "equipo_1": equipo_1,
            "equipo_2": equipo_2,
            "doble_oportunidad": doble_oportunidad,
            "probabilidad_1": round(prob_eq1, 1),
            "probabilidad_empate": round(prob_empate, 1),
            "probabilidad_2": round(prob_eq2, 1),
            "mas_menos_goles": "Más de 2.5" if (goles_1_round + goles_2_round) > 2.5 else "Menos de 2.5",
            "ambos_anotan": "SÍ" if goles_1_round > 0 and goles_2_round > 0 else "NO",
            "marcador_exacto": f"{goles_1_round} - {goles_2_round}",
            "lambdas_proyectados": {"home": lambda_1, "away": lambda_2}
        }