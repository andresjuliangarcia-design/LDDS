import sqlite3
import pandas as pd
from utils.database import DB_PATH

def obtener_rendimiento_equipo(equipo, anio=None, campeonato=None):
    """Obtiene rendimiento de un equipo (partidos jugados, ganados, perdidos, empatados)."""
    query = """
        SELECT
            p.fecha,
            p.campeonato,
            p.equipo_local,
            p.equipo_visitante,
            p.goles_local,
            p.goles_visitante,
            CASE
                WHEN p.equipo_local = ? AND p.goles_local > p.goles_visitante THEN 'Ganado'
                WHEN p.equipo_visitante = ? AND p.goles_visitante > p.goles_local THEN 'Ganado'
                WHEN p.goles_local = p.goles_visitante THEN 'Empatado'
                ELSE 'Perdido'
            END AS resultado
        FROM partidos p
        WHERE p.arbitro IS NOT NULL AND p.arbitro <> ''
        AND (p.equipo_local = ? OR p.equipo_visitante = ?)
    """
    
    params = [equipo, equipo, equipo, equipo]
    if anio:
        query += " AND SUBSTR(p.fecha, 7, 4) = ?"
        params.append(anio)
    if campeonato:
        query += " AND p.campeonato = ?"
        params.append(campeonato)
    
    query += " ORDER BY p.fecha DESC"
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_estadisticas_rendimiento(equipo, anio=None, campeonato=None):
    """Obtiene estadísticas resumen de rendimiento."""
    query = """
        SELECT
            COUNT(*) AS partidos_jugados,
            SUM(CASE
                WHEN (p.equipo_local = ? AND p.goles_local > p.goles_visitante) OR
                     (p.equipo_visitante = ? AND p.goles_visitante > p.goles_local)
                THEN 1 ELSE 0 END) AS ganados,
            SUM(CASE WHEN p.goles_local = p.goles_visitante THEN 1 ELSE 0 END) AS empatados,
            SUM(CASE
                WHEN (p.equipo_local = ? AND p.goles_local < p.goles_visitante) OR
                     (p.equipo_visitante = ? AND p.goles_visitante < p.goles_local)
                THEN 1 ELSE 0 END) AS perdidos,
            SUM(CASE
                WHEN p.equipo_local = ? THEN p.goles_local
                WHEN p.equipo_visitante = ? THEN p.goles_visitante
                ELSE 0 END) AS goles_favor,
            SUM(CASE
                WHEN p.equipo_local = ? THEN p.goles_visitante
                WHEN p.equipo_visitante = ? THEN p.goles_local
                ELSE 0 END) AS goles_contra
        FROM partidos p
        WHERE p.arbitro IS NOT NULL AND p.arbitro <> ''
        AND (p.equipo_local = ? OR p.equipo_visitante = ?)
    """
    
    params = [equipo, equipo, equipo, equipo, equipo, equipo, equipo, equipo, equipo, equipo]
    if anio:
        query += " AND SUBSTR(p.fecha, 7, 4) = ?"
        params.append(anio)
    if campeonato:
        query += " AND p.campeonato = ?"
        params.append(campeonato)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    resultado = cur.fetchone()
    conn.close()
    
    if resultado:
        pj, g, e, p, gf, gc = resultado
        return {
            "partidos_jugados": pj or 0,
            "ganados": g or 0,
            "empatados": e or 0,
            "perdidos": p or 0,
            "goles_favor": gf or 0,
            "goles_contra": gc or 0,
            "diferencia": (gf or 0) - (gc or 0)
        }
    return {
        "partidos_jugados": 0, "ganados": 0, "empatados": 0, "perdidos": 0,
        "goles_favor": 0, "goles_contra": 0, "diferencia": 0
    }