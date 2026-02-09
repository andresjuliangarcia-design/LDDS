import sqlite3
import pandas as pd
from utils.database import DB_PATH

def obtener_evolucion_equipo(equipo):
    """Obtiene evolución anual de tarjetas por equipo."""
    query = """
        SELECT
            SUBSTR(p.fecha, 7, 4) AS anio,
            SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amon,
            SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS exp
        FROM partidos p
        JOIN tarjetas t ON t.partido_id = p.id
        WHERE p.arbitro IS NOT NULL
          AND p.arbitro <> ''
          AND (
              (p.equipo_local = ? AND t.equipo = 'Local')
              OR 
              (p.equipo_visitante = ? AND t.equipo = 'Visitante')
          )
        GROUP BY anio
        ORDER BY anio
    """
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=(equipo, equipo))
    conn.close()
    return df