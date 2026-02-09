import sqlite3
from utils.database import DB_PATH

def obtener_estadisticas_arbitro_equipo(arbitro, equipo, anio=None, campeonato=None):
    """Obtiene estadísticas de un árbitro vs un equipo."""
    query = """
        SELECT
            COUNT(DISTINCT p.id) AS partidos,
            SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amonestados,
            SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS expulsados
        FROM partidos p
        LEFT JOIN tarjetas t ON t.partido_id = p.id
        WHERE p.arbitro = ?
        AND (p.equipo_local = ? OR p.equipo_visitante = ?)
    """
    params = [arbitro, equipo, equipo]
    
    if anio:
        query += " AND SUBSTR(p.fecha,7,4) = ?"
        params.append(anio)
    if campeonato:
        query += " AND p.campeonato = ?"
        params.append(campeonato)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    resultado = cur.fetchone()
    conn.close()
    
    return {
        "partidos": resultado[0] or 0,
        "amonestados": resultado[1] or 0,
        "expulsados": resultado[2] or 0
    }