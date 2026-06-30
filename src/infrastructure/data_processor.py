import pandas as pd
import numpy as np

def procesar_datos_neutrales(ruta_csv: str, mongo_matches: list = None):
    """Limpia y genera estadísticas asimétricas y métricas ELO/Forma para el entrenamiento de ML."""
    df = pd.read_csv(ruta_csv)
    df['date'] = pd.to_datetime(df['date'])
    
    # 🔌 Integrar partidos desde MongoDB si están disponibles
    if mongo_matches:
        mongo_rows = []
        # Importación local para evitar dependencias circulares
        from infrastructure.team_translator import TeamTranslator
        for match in mongo_matches:
            partido = match.get("partido", {})
            local_es = partido.get("equipo_local")
            away_es = partido.get("equipo_visitante")
            
            # Traducir los nombres de las selecciones al inglés
            local_en = TeamTranslator.to_english(local_es)
            away_en = TeamTranslator.to_english(away_es)
            
            mongo_rows.append({
                "date": pd.to_datetime(partido.get("fecha")),
                "home_team": local_en,
                "away_team": away_en,
                "home_score": float(partido.get("goles_local", 0)),
                "away_score": float(partido.get("goles_visitante", 0)),
                "tournament": "FIFA World Cup",
                "city": partido.get("estadio", "Unknown"),
                "country": "United States",
                "neutral": True
            })
        if mongo_rows:
            df_mongo = pd.DataFrame(mongo_rows)
            df = pd.concat([df, df_mongo], ignore_index=True)

    # Eliminar duplicados para evitar conteos repetidos
    df = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="last")
    
    # Asegurar orden cronológico estricto para ELO y Form
    df = df.sort_values(by="date").reset_index(drop=True)
    
    # Inicializar estructuras de control por selección
    elo_actual = {}      # team_name -> elo
    historial_partidos = {} # team_name -> lista de dicts
    
    elo_home_col = []
    elo_away_col = []
    form_pts_home_col = []
    form_pts_away_col = []
    form_gf_home_col = []
    form_gf_away_col = []
    form_ga_home_col = []
    form_ga_away_col = []
    
    # Recorrido cronológico optimizado
    registros = df.to_dict('records')
    for row in registros:
        h_team = row["home_team"]
        a_team = row["away_team"]
        h_score = row["home_score"]
        a_score = row["away_score"]
        
        # 1. ELO pre-partido
        el_h = elo_actual.get(h_team, 1500.0)
        el_a = elo_actual.get(a_team, 1500.0)
        elo_home_col.append(el_h)
        elo_away_col.append(el_a)
        
        # 2. Forma pre-partido (últimos 5 encuentros)
        def get_form_metrics(team):
            hist = historial_partidos.get(team, [])
            if not hist:
                return 1.0, 1.0, 1.0
            recent = hist[-5:]
            pts = sum(x["points"] for x in recent) / len(recent)
            gf = sum(x["goals_scored"] for x in recent) / len(recent)
            ga = sum(x["goals_conceded"] for x in recent) / len(recent)
            return pts, gf, ga
            
        pts_h, gf_h, ga_h = get_form_metrics(h_team)
        pts_a, gf_a, ga_a = get_form_metrics(a_team)
        
        form_pts_home_col.append(pts_h)
        form_pts_away_col.append(pts_a)
        form_gf_home_col.append(gf_h)
        form_gf_away_col.append(gf_a)
        form_ga_home_col.append(ga_h)
        form_ga_away_col.append(ga_a)
        
        # 3. Actualizar estadísticas post-partido si el partido fue disputado
        if pd.notna(h_score) and pd.notna(a_score):
            if h_score > a_score:
                pts_h_match, pts_a_match = 3, 0
                sa_h, sa_a = 1.0, 0.0
            elif h_score < a_score:
                pts_h_match, pts_a_match = 0, 3
                sa_h, sa_a = 0.0, 1.0
            else:
                pts_h_match, pts_a_match = 1, 1
                sa_h, sa_a = 0.5, 0.5
                
            # Ecuación de ELO
            expected_h = 1.0 / (1.0 + 10.0 ** ((el_a - el_h) / 400.0))
            expected_a = 1.0 / (1.0 + 10.0 ** ((el_h - el_a) / 400.0))
            
            k = 30.0
            elo_actual[h_team] = el_h + k * (sa_h - expected_h)
            elo_actual[a_team] = el_a + k * (sa_a - expected_a)
            
            # Guardar historial
            if h_team not in historial_partidos:
                historial_partidos[h_team] = []
            if a_team not in historial_partidos:
                historial_partidos[a_team] = []
                
            historial_partidos[h_team].append({
                "goals_scored": h_score,
                "goals_conceded": a_score,
                "points": pts_h_match
            })
            historial_partidos[a_team].append({
                "goals_scored": a_score,
                "goals_conceded": h_score,
                "points": pts_a_match
            })
            
    df["elo_home"] = elo_home_col
    df["elo_away"] = elo_away_col
    df["form_pts_home"] = form_pts_home_col
    df["form_pts_away"] = form_pts_away_col
    df["form_gf_home"] = form_gf_home_col
    df["form_gf_away"] = form_gf_away_col
    df["form_ga_home"] = form_ga_home_col
    df["form_ga_away"] = form_ga_away_col
    
    # -----------------------------------------------------
    # Pipeline para subconjunto táctico >= 2018
    # -----------------------------------------------------
    df_moderno = df[df['date'].dt.year >= 2018].copy()
    df_moderno['home_team'] = df_moderno['home_team'].str.strip()
    df_moderno['away_team'] = df_moderno['away_team'].str.strip()

    # Promedios históricos de ataque/defensa por rol
    goles_como_local = df_moderno.groupby('home_team').agg(
        ataque_home=('home_score', 'mean'),
        defensa_home=('away_score', 'mean')
    ).reset_index().rename(columns={'home_team': 'equipo'})

    goles_como_visitante = df_moderno.groupby('away_team').agg(
        ataque_away=('away_score', 'mean'),
        defensa_away=('home_score', 'mean')
    ).reset_index().rename(columns={'away_team': 'equipo'})

    stats_totales = pd.merge(goles_como_local, goles_como_visitante, on='equipo', how='outer').fillna(1.0)

    # Reconstrucción del set con ataque/defensa y las variables dinámicas calculadas
    df_neutral = df_moderno.merge(stats_totales, left_on='home_team', right_on='equipo', how='left')
    df_neutral = df_neutral.rename(columns={
        'ataque_home': 'ataque_home_A', 'defensa_home': 'defensa_home_A',
        'ataque_away': 'ataque_away_A', 'defensa_away': 'defensa_away_A'
    }).drop(columns=['equipo'])

    df_neutral = df_neutral.merge(stats_totales, left_on='away_team', right_on='equipo', how='left')
    df_neutral = df_neutral.rename(columns={
        'ataque_home': 'ataque_home_B', 'defensa_home': 'defensa_home_B',
        'ataque_away': 'ataque_away_B', 'defensa_away': 'defensa_away_B'
    }).drop(columns=['equipo'])
    
    df_neutral['is_neutral_match'] = df_neutral['neutral'].astype(int)
    df_neutral = df_neutral.fillna(0)
    
    # Calcular pesos con decaimiento temporal (Half-life de 4 años = 1460 días)
    max_date = df_neutral['date'].max()
    diferencia_dias = (max_date - df_neutral['date']).dt.days
    lambda_decay = 0.000475  # ln(2) / 1460
    df_neutral['weight'] = np.exp(-lambda_decay * diferencia_dias)

    return df_neutral, stats_totales, elo_actual, historial_partidos