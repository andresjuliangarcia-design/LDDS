import sqlite3
import pandas as pd
from utils.database import DB_PATH

def obtener_equipo_jugador(jugador):
    """Obtiene el equipo de un jugador."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT
            CASE
                WHEN t.equipo = 'Local' THEN p.equipo_local
                WHEN t.equipo = 'Visitante' THEN p.equipo_visitante
            END AS equipo_jugador
        FROM partidos p
        JOIN tarjetas t ON t.partido_id = p.id
        WHERE t.jugador = ?
        LIMIT 1
    """, (jugador,))
    resultado = cur.fetchone()
    conn.close()
    return resultado[0] if resultado else "Desconocido"

def obtener_tarjetas_por_rival(jugador):
    """Obtiene resumen de tarjetas por rival para un jugador."""
    query = """
        SELECT
            CASE
                WHEN t.equipo = 'Local' THEN p.equipo_visitante
                WHEN t.equipo = 'Visitante' THEN p.equipo_local
            END AS rival,
            COUNT(*) AS total_tarjetas,
            SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amon,
            SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS exp
        FROM partidos p
        JOIN tarjetas t ON t.partido_id = p.id
        WHERE t.jugador = ?
        GROUP BY rival
        ORDER BY total_tarjetas DESC
    """
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=(jugador,))
    conn.close()
    return df