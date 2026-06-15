import pandas as pd

def procesar_datos_neutrales(ruta_csv: str):
    """Limpia y genera estadísticas asimétricas para el entrenamiento de Random Forest."""
    df = pd.read_csv(ruta_csv)
    df['date'] = pd.to_datetime(df['date'])

    # Ventana táctica óptima para el Random Forest (desde 2018)
    df_moderno = df[df['date'].dt.year >= 2018].copy()
    df_moderno['home_team'] = df_moderno['home_team'].str.strip()
    df_moderno['away_team'] = df_moderno['away_team'].str.strip()

    # Agregaciones de goles por rol
    goles_como_local = df_moderno.groupby('home_team').agg(
        ataque_home=('home_score', 'mean'),
        defensa_home=('away_score', 'mean')
    ).reset_index().rename(columns={'home_team': 'equipo'})

    goles_como_visitante = df_moderno.groupby('away_team').agg(
        ataque_away=('away_score', 'mean'),
        defensa_away=('home_score', 'mean')
    ).reset_index().rename(columns={'away_team': 'equipo'})

    stats_totales = pd.merge(goles_como_local, goles_como_visitante, on='equipo', how='outer').fillna(1.0)

    # Reconstrucción asimétrica del set
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

    return df_neutral, stats_totales