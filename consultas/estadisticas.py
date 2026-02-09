import sqlite3
from utils.database import DB_PATH

def obtener_resumen_equipo(equipo):
    """Obtiene resumen histórico de tarjetas por equipo."""
    query = """
        SELECT
            SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amon,
            SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS exp
        FROM partidos p
        JOIN tarjetas t ON t.partido_id = p.id
        WHERE p.arbitro IS NOT NULL
          AND p.arbitro <> ''
          AND (p.equipo_local = ? OR p.equipo_visitante = ?)
    """
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, (equipo, equipo))
    amon, exp = cur.fetchone()
    conn.close()
    
    return {
        "amonestaciones": amon or 0,
        "expulsiones": exp or 0,
        "total": (amon or 0) + (exp or 0)
    }