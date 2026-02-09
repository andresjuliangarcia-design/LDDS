import sqlite3
import pandas as pd
from utils.database import DB_PATH

def obtener_jugadores_mas_amonestados(limite=20):
    """Obtiene los jugadores con más tarjetas amarillas."""
    query = """
        SELECT
            t.jugador,
            CASE
                WHEN t.equipo = 'Local' THEN p.equipo_local
                WHEN t.equipo = 'Visitante' THEN p.equipo_visitante
            END AS equipo,
            COUNT(*) AS amonestaciones
        FROM partidos p
        INNER JOIN tarjetas t ON t.partido_id = p.id
        WHERE t.tipo = 'Amonestado'
        AND t.jugador IS NOT NULL AND TRIM(t.jugador) <> ''
        GROUP BY t.jugador, equipo
        ORDER BY amonestaciones DESC
        LIMIT ?
    """
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=(limite,))
    conn.close()
    return df

def obtener_jugadores_mas_expulsados(limite=20):
    """Obtiene los jugadores con más tarjetas rojas."""
    query = """
        SELECT
            t.jugador,
            CASE
                WHEN t.equipo = 'Local' THEN p.equipo_local
                WHEN t.equipo = 'Visitante' THEN p.equipo_visitante
            END AS equipo,
            COUNT(*) AS expulsiones
        FROM partidos p
        INNER JOIN tarjetas t ON t.partido_id = p.id
        WHERE t.tipo = 'Expulsado'
        AND t.jugador IS NOT NULL AND TRIM(t.jugador) <> ''
        GROUP BY t.jugador, equipo
        ORDER BY expulsiones DESC
        LIMIT ?
    """
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=(limite,))
    conn.close()
    return df

def obtener_jugadores_mas_tarjetas(limite=20):
    """Obtiene los jugadores con más tarjetas totales (amarillas + rojas)."""
    query = """
        SELECT
            t.jugador,
            CASE
                WHEN t.equipo = 'Local' THEN p.equipo_local
                WHEN t.equipo = 'Visitante' THEN p.equipo_visitante
            END AS equipo,
            SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amonestaciones,
            SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS expulsiones,
            COUNT(*) AS total_tarjetas
        FROM partidos p
        INNER JOIN tarjetas t ON t.partido_id = p.id
        WHERE t.jugador IS NOT NULL AND TRIM(t.jugador) <> ''
        GROUP BY t.jugador, equipo
        ORDER BY total_tarjetas DESC
        LIMIT ?
    """
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=(limite,))
    conn.close()
    return df