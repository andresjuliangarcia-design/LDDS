import sqlite3
import pandas as pd
from utils.database import DB_PATH

def obtener_goles_por_jugador(anio=None, campeonato=None, equipo=None):
    """Obtiene goles por jugador con filtros."""
    query = """
        SELECT
            g.jugador,
            CASE
                WHEN g.equipo = 'Local' THEN p.equipo_local
                WHEN g.equipo = 'Visitante' THEN p.equipo_visitante
            END AS equipo_jugador,
            COUNT(*) AS goles
        FROM partidos p
        INNER JOIN goles g ON g.partido_id = p.id
        WHERE g.jugador IS NOT NULL AND TRIM(g.jugador) <> ''
    """
    
    params = []
    if anio:
        query += " AND SUBSTR(p.fecha, 7, 4) = ?"
        params.append(anio)
    if campeonato:
        query += " AND p.campeonato = ?"
        params.append(campeonato)
    if equipo:
        query += " AND (p.equipo_local = ? OR p.equipo_visitante = ?)"
        params.extend([equipo, equipo])
    
    query += """
        GROUP BY g.jugador, equipo_jugador
        HAVING goles > 0
        ORDER BY goles DESC, g.jugador
    """
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_goleadores_por_equipo(equipo):
    """Obtiene los goleadores de un equipo específico."""
    query = """
        SELECT
            g.jugador,
            COUNT(*) AS goles
        FROM partidos p
        INNER JOIN goles g ON g.partido_id = p.id
        WHERE g.jugador IS NOT NULL AND TRIM(g.jugador) <> ''
        AND (
            (p.equipo_local = ? AND g.equipo = 'Local')
            OR 
            (p.equipo_visitante = ? AND g.equipo = 'Visitante')
        )
        GROUP BY g.jugador
        ORDER BY goles DESC
    """
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=(equipo, equipo))
    conn.close()
    return df

def obtener_top_goleadores(limite=20):
    """Obtiene el top de goleadores históricos."""
    query = """
        SELECT
            g.jugador,
            CASE
                WHEN g.equipo = 'Local' THEN p.equipo_local
                WHEN g.equipo = 'Visitante' THEN p.equipo_visitante
            END AS equipo,
            COUNT(*) AS goles
        FROM partidos p
        INNER JOIN goles g ON g.partido_id = p.id
        WHERE g.jugador IS NOT NULL AND TRIM(g.jugador) <> ''
        GROUP BY g.jugador, equipo
        ORDER BY goles DESC
        LIMIT ?
    """
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=(limite,))
    conn.close()
    return df