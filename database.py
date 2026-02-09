import sqlite3
import os

DB_PATH = "football_nueva.db"

def verificar_db():
    """Verifica que la base de datos exista."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Base de datos no encontrada: {DB_PATH}")
    return DB_PATH

def obtener_valores_unicos(columna, tabla="partidos"):
    """Obtiene valores únicos de una columna."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"""
        SELECT DISTINCT {columna}
        FROM {tabla}
        WHERE {columna} IS NOT NULL AND TRIM({columna}) <> ''
        ORDER BY {columna}
    """)
    valores = [r[0] for r in cur.fetchall()]
    conn.close()
    return valores

def obtener_equipos():
    """Obtiene lista de equipos."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT equipo FROM (
            SELECT equipo_local AS equipo FROM partidos
            UNION
            SELECT equipo_visitante FROM partidos
        ) WHERE equipo IS NOT NULL AND equipo <> ''
        ORDER BY equipo
    """)
    equipos = [r[0] for r in cur.fetchall()]
    conn.close()
    return equipos

def obtener_jugadores():
    """Obtiene lista de jugadores con tarjetas."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT jugador FROM tarjetas
        WHERE jugador IS NOT NULL AND TRIM(jugador) <> ''
        ORDER BY jugador
    """)
    jugadores = [r[0] for r in cur.fetchall()]
    conn.close()
    return jugadores