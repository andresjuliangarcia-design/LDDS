import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

# =====================================
# CONFIGURACIÓN INICIAL
# =====================================
DB = "football_nueva.db"

st.set_page_config(
    page_title="🏆 Seguimiento Liga de Fútbol",
    page_icon="⚽",
    layout="wide"
)

# =====================================
# VERIFICAR BASE DE DATOS
# =====================================
if not os.path.exists(DB):
    st.error(f"""
    ❌ **Base de datos no encontrada**
    
    Archivo requerido: `{DB}`
    
    Archivos disponibles: {', '.join(sorted(os.listdir('.')))}
    """)
    st.stop()

# =====================================
# FUNCIONES AUXILIARES
# =====================================
def parse_fecha(fecha_str):
    """Convierte fecha de 'dd/mm/yyyy' a datetime para ordenar correctamente."""
    try:
        return pd.to_datetime(fecha_str, format='%d/%m/%Y')
    except:
        return pd.NaT
        
def formatear_goleador(nombre, goles):
    """Formatea nombre: inicial del primer nombre + apellido, con (n) si hizo más de 1 gol.
    Maneja formato: 'Apellido, Nombre' → 'C. Apellido'"""
    if not nombre or pd.isna(nombre):
        return "-"
    
    nombre = nombre.strip()
    
    # Si el nombre tiene formato "Apellido, Nombre"
    if ',' in nombre:
        partes = nombre.split(',', 1)
        apellido = partes[0].strip()
        nombre_parte = partes[1].strip()
        
        # Obtener inicial del primer nombre
        nombres = nombre_parte.split()
        if nombres:
            inicial = nombres[0][0].upper()
            resultado = f"{inicial}. {apellido}"
        else:
            resultado = apellido
    else:
        # Formato normal "Nombre Apellido"
        partes = nombre.split()
        if len(partes) >= 2:
            inicial_nombre = partes[0][0].upper()
            apellido = " ".join(partes[1:])
            resultado = f"{inicial_nombre}. {apellido}"
        else:
            resultado = nombre
    
    # Agregar cantidad de goles si es más de 1
    if goles > 1:
        resultado += f" ({goles})"
    
    return resultado

# =====================================
# FUNCIONES DE BASE DE DATOS
# =====================================
@st.cache_data(ttl=300)
def obtener_valores_unicos(columna, tabla="partidos"):
    try:
        conn = sqlite3.connect(DB)
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
    except:
        return []

@st.cache_data(ttl=300)
def obtener_equipos():
    try:
        conn = sqlite3.connect(DB)
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
        return equipos if equipos else []
    except:
        return []

@st.cache_data(ttl=300)
def obtener_jugadores():
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT jugador FROM tarjetas
            WHERE jugador IS NOT NULL AND TRIM(jugador) <> ''
            ORDER BY jugador
        """)
        jugadores = [r[0] for r in cur.fetchall()]
        conn.close()
        return jugadores if jugadores else []
    except:
        return []

def obtener_tarjetas_por_jugador(anio=None, campeonato=None, equipo=None, solo_expulsados=False):
    query = """
        SELECT
            t.jugador,
            CASE
                WHEN t.equipo = 'Local' THEN p.equipo_local
                WHEN t.equipo = 'Visitante' THEN p.equipo_visitante
            END AS equipo_jugador,
            SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amon,
            SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS exp
        FROM partidos p
        INNER JOIN tarjetas t ON t.partido_id = p.id
        WHERE p.arbitro IS NOT NULL AND p.arbitro <> ''
          AND t.jugador IS NOT NULL AND TRIM(t.jugador) <> ''
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
    if solo_expulsados:
        query += " AND t.tipo = 'Expulsado'"
    query += """
        GROUP BY t.jugador, equipo_jugador
        HAVING (amon + exp) > 0
        ORDER BY (amon + exp) DESC, t.jugador
    """
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# NUEVA FUNCIÓN: Tarjetas por equipo (no por jugador)
def obtener_tarjetas_por_equipo(anio=None, campeonato=None, equipo=None, solo_expulsados=False):
    """Obtiene tarjetas agrupadas por equipo (no por jugador)."""
    query = """
        SELECT
            CASE
                WHEN t.equipo = 'Local' THEN p.equipo_local
                WHEN t.equipo = 'Visitante' THEN p.equipo_visitante
            END AS equipo,
            SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amon,
            SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS exp
        FROM partidos p
        INNER JOIN tarjetas t ON t.partido_id = p.id
        WHERE p.arbitro IS NOT NULL AND p.arbitro <> ''
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
    if solo_expulsados:
        query += " AND t.tipo = 'Expulsado'"
    
    query += """
        GROUP BY equipo
        HAVING (amon + exp) > 0
        ORDER BY (amon + exp) DESC, equipo
    """
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_tarjetas_por_rival_equipo(equipo):
    """Obtiene tarjetas recibidas por un equipo contra cada rival."""
    query = """
        SELECT
            CASE
                WHEN (p.equipo_local = ? AND t.equipo = 'Local') THEN p.equipo_visitante
                WHEN (p.equipo_visitante = ? AND t.equipo = 'Visitante') THEN p.equipo_local
            END AS rival,
            SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amon,
            SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS exp
        FROM partidos p
        INNER JOIN tarjetas t ON t.partido_id = p.id
        WHERE p.arbitro IS NOT NULL AND p.arbitro <> ''
        AND (
            (p.equipo_local = ? AND t.equipo = 'Local')
            OR
            (p.equipo_visitante = ? AND t.equipo = 'Visitante')
        )
        GROUP BY rival
        ORDER BY (amon + exp) DESC
    """
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=(equipo, equipo, equipo, equipo))
    conn.close()
    return df

def obtener_evolucion_equipo(equipo):
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
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=(equipo, equipo))
    conn.close()
    return df

def obtener_estadisticas_arbitro_equipo(arbitro, equipo, anio=None, campeonato=None):
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
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(query, params)
    resultado = cur.fetchone()
    conn.close()
    return {
        "partidos": resultado[0] or 0,
        "amonestados": resultado[1] or 0,
        "expulsados": resultado[2] or 0
    }

def obtener_resumen_equipo(equipo):
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
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(query, (equipo, equipo))
    amon, exp = cur.fetchone()
    conn.close()
    return {
        "amonestaciones": amon or 0,
        "expulsiones": exp or 0,
        "total": (amon or 0) + (exp or 0)
    }

def obtener_goles_por_jugador(anio=None, campeonato=None, equipo=None):
    """Obtiene goles por jugador, sin importar para qué equipo jugó."""
    query = """
        SELECT
            g.jugador,
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
        GROUP BY g.jugador
        HAVING goles > 0
        ORDER BY goles DESC, g.jugador
    """
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_goleadores_por_equipo(equipo):
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
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=(equipo, equipo))
    conn.close()
    return df

def obtener_top_goleadores(limite=20):
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
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=(limite,))
    conn.close()
    return df

def obtener_rendimiento_equipo(equipo, anio=None, campeonato=None):
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
    
    # ORDEN CORREGIDO: año, mes, día
    query += " ORDER BY SUBSTR(p.fecha, 7, 4) DESC, SUBSTR(p.fecha, 4, 2) DESC, SUBSTR(p.fecha, 1, 2) DESC"
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_estadisticas_rendimiento(equipo, anio=None, campeonato=None):
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
    conn = sqlite3.connect(DB)
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

def obtener_jugadores_mas_amonestados(limite=20):
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
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=(limite,))
    conn.close()
    return df

def obtener_jugadores_mas_expulsados(limite=20):
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
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=(limite,))
    conn.close()
    return df

def calcular_puntos(goles_local, goles_visitante, equipo_local, equipo_visitante, equipo_buscar, anio):
    puntos_victoria = 3 if int(anio) >= 1995 else 2
    if goles_local > goles_visitante:
        return (puntos_victoria, 1, 0, 0) if equipo_local == equipo_buscar else (0, 0, 0, 1)
    elif goles_local < goles_visitante:
        return (puntos_victoria, 1, 0, 0) if equipo_visitante == equipo_buscar else (0, 0, 0, 1)
    else:
        return (1, 0, 1, 0)

def obtener_tabla_historica_acumulada():
    """Obtiene tabla de posiciones acumulada de TODOS los partidos históricos."""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Obtener todos los partidos con sus fechas
    cur.execute("""
        SELECT
            p.fecha,
            p.equipo_local,
            p.goles_local,
            p.equipo_visitante,
            p.goles_visitante
        FROM partidos p
        WHERE p.arbitro IS NOT NULL AND p.arbitro <> ''
        AND p.equipo_local IS NOT NULL AND p.equipo_visitante IS NOT NULL
        ORDER BY p.fecha
    """)
    
    partidos = cur.fetchall()
    conn.close()
    
    # Diccionario para acumular estadísticas por equipo
    tabla = {}
    
    for partido in partidos:
        fecha, local, gl, visitante, gv = partido
        
        # Convertir goles a enteros (manejar NULL)
        try:
            gl = int(gl) if gl is not None else 0
        except:
            gl = 0
        try:
            gv = int(gv) if gv is not None else 0
        except:
            gv = 0
        
        # Obtener año para determinar sistema de puntos
        try:
            anio = int(fecha.split('/')[2]) if fecha else 0
        except:
            anio = 0
        
        # Inicializar equipos si no existen
        if local not in tabla:
            tabla[local] = {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0, "Puntos": 0}
        if visitante not in tabla:
            tabla[visitante] = {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0, "Puntos": 0}
        
        # Acumular partidos jugados y goles
        tabla[local]["PJ"] += 1
        tabla[visitante]["PJ"] += 1
        tabla[local]["GF"] += gl
        tabla[local]["GC"] += gv
        tabla[visitante]["GF"] += gv
        tabla[visitante]["GC"] += gl
        
        # Determinar puntos según el año
        puntos_victoria = 3 if anio >= 1995 else 2
        
        # Asignar resultados y puntos
        if gl > gv:
            tabla[local]["PG"] += 1
            tabla[visitante]["PP"] += 1
            tabla[local]["Puntos"] += puntos_victoria
        elif gl < gv:
            tabla[visitante]["PG"] += 1
            tabla[local]["PP"] += 1
            tabla[visitante]["Puntos"] += puntos_victoria
        else:
            tabla[local]["PE"] += 1
            tabla[visitante]["PE"] += 1
            tabla[local]["Puntos"] += 1
            tabla[visitante]["Puntos"] += 1
    
    # Convertir a lista ordenada
    posiciones = []
    for equipo, datos in tabla.items():
        dg = datos["GF"] - datos["GC"]
        posiciones.append((
            equipo,
            datos["PJ"],
            datos["PG"],
            datos["PE"],
            datos["PP"],
            datos["GF"],
            datos["GC"],
            dg,
            datos["Puntos"]
        ))
    
    # Ordenar por: Puntos, DG, GF (descendente)
    posiciones.sort(key=lambda x: (x[8], x[7], x[5]), reverse=True)
    
    return posiciones, len(partidos)


# =====================================
# NUEVAS FUNCIONES: CAMPAÑAS Y VERSUS
# =====================================

def obtener_campania_equipo(equipo, anio=None, campeonato=None):
    """Obtiene todos los partidos de un equipo con sus goleadores."""
    query = """
        SELECT
            p.id,
            p.fecha,
            p.campeonato,
            p.equipo_local,
            p.equipo_visitante,
            p.goles_local,
            p.goles_visitante,
            CASE
                WHEN p.equipo_local = ? THEN 'Local'
                ELSE 'Visitante'
            END AS lugar,
            CASE
                WHEN p.equipo_local = ? AND p.goles_local > p.goles_visitante THEN 'Ganado'
                WHEN p.equipo_visitante = ? AND p.goles_visitante > p.goles_local THEN 'Ganado'
                WHEN p.goles_local = p.goles_visitante THEN 'Empatado'
                ELSE 'Perdido'
            END AS resultado,
            CASE
                WHEN p.equipo_local = ? THEN p.goles_local
                ELSE p.goles_visitante
            END AS goles_favor,
            CASE
                WHEN p.equipo_local = ? THEN p.goles_visitante
                ELSE p.goles_local
            END AS goles_contra
        FROM partidos p
        WHERE p.arbitro IS NOT NULL AND p.arbitro <> ''
        AND (p.equipo_local = ? OR p.equipo_visitante = ?)
    """
    params = [equipo, equipo, equipo, equipo, equipo, equipo, equipo]
    if anio:
        query += " AND SUBSTR(p.fecha, 7, 4) = ?"
        params.append(anio)
    if campeonato:
        query += " AND p.campeonato = ?"
        params.append(campeonato)
    
    # ORDEN CORREGIDO: año, mes, día
    query += " ORDER BY SUBSTR(p.fecha, 7, 4) DESC, SUBSTR(p.fecha, 4, 2) DESC, SUBSTR(p.fecha, 1, 2) DESC"
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_goleadores_partido(partido_id, equipo):
    """Obtiene los goleadores de un equipo en un partido específico."""
    query = """
        SELECT
            g.jugador,
            COUNT(*) AS goles
        FROM goles g
        JOIN partidos p ON p.id = g.partido_id
        WHERE g.partido_id = ?
        AND (
            (p.equipo_local = ? AND g.equipo = 'Local')
            OR 
            (p.equipo_visitante = ? AND g.equipo = 'Visitante')
        )
        GROUP BY g.jugador
        ORDER BY goles DESC
    """
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=(partido_id, equipo, equipo))
    conn.close()
    return df

def obtener_historial_versus(equipo1, equipo2, anio=None, campeonato=None):
    """Obtiene el historial de enfrentamientos entre dos equipos."""
    query = """
        SELECT
            p.fecha,
            p.campeonato,
            p.equipo_local,
            p.equipo_visitante,
            p.goles_local,
            p.goles_visitante,
            CASE
                WHEN p.goles_local > p.goles_visitante THEN p.equipo_local
                WHEN p.goles_visitante > p.goles_local THEN p.equipo_visitante
                ELSE 'Empate'
            END AS ganador
        FROM partidos p
        WHERE p.arbitro IS NOT NULL AND p.arbitro <> ''
        AND (
            (p.equipo_local = ? AND p.equipo_visitante = ?)
            OR
            (p.equipo_local = ? AND p.equipo_visitante = ?)
        )
    """
    params = [equipo1, equipo2, equipo2, equipo1]
    
    if anio:
        query += " AND SUBSTR(p.fecha, 7, 4) = ?"
        params.append(anio)
    if campeonato:
        query += " AND p.campeonato = ?"
        params.append(campeonato)
    
    # ORDEN CORREGIDO: año, mes, día
    query += " ORDER BY SUBSTR(p.fecha, 7, 4) DESC, SUBSTR(p.fecha, 4, 2) DESC, SUBSTR(p.fecha, 1, 2) DESC"
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_estadisticas_versus(equipo1, equipo2, anio=None, campeonato=None):
    """Obtiene estadísticas resumen del enfrentamiento entre dos equipos."""
    query = """
        SELECT
            COUNT(*) AS total_partidos,
            SUM(CASE WHEN p.equipo_local = ? AND p.goles_local > p.goles_visitante THEN 1
                     WHEN p.equipo_visitante = ? AND p.goles_visitante > p.goles_local THEN 1
                     ELSE 0 END) AS victorias_eq1,
            SUM(CASE WHEN p.equipo_local = ? AND p.goles_local > p.goles_visitante THEN 1
                     WHEN p.equipo_visitante = ? AND p.goles_visitante > p.goles_local THEN 1
                     ELSE 0 END) AS victorias_eq2,
            SUM(CASE WHEN p.goles_local = p.goles_visitante THEN 1 ELSE 0 END) AS empates,
            SUM(CASE WHEN p.equipo_local = ? THEN p.goles_local ELSE p.goles_visitante END) AS goles_eq1,
            SUM(CASE WHEN p.equipo_local = ? THEN p.goles_visitante ELSE p.goles_local END) AS goles_eq2
        FROM partidos p
        WHERE p.arbitro IS NOT NULL AND p.arbitro <> ''
        AND (
            (p.equipo_local = ? AND p.equipo_visitante = ?)
            OR
            (p.equipo_local = ? AND p.equipo_visitante = ?)
        )
    """
    params = [equipo1, equipo1, equipo2, equipo2, equipo1, equipo1, equipo1, equipo2, equipo2, equipo1]
    
    if anio:
        query += " AND SUBSTR(p.fecha, 7, 4) = ?"
        params.append(anio)
    if campeonato:
        query += " AND p.campeonato = ?"
        params.append(campeonato)
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(query, params)
    resultado = cur.fetchone()
    conn.close()
    
    if resultado:
        total, v1, v2, emp, g1, g2 = resultado
        return {
            "total_partidos": total or 0,
            "victorias_eq1": v1 or 0,
            "victorias_eq2": v2 or 0,
            "empates": emp or 0,
            "goles_eq1": g1 or 0,
            "goles_eq2": g2 or 0
        }
    return {
        "total_partidos": 0, "victorias_eq1": 0, "victorias_eq2": 0,
        "empates": 0, "goles_eq1": 0, "goles_eq2": 0
    }

# =====================================
# NUEVAS FUNCIONES: EVOLUCIÓN DE GOLES Y PUNTOS
# =====================================

def obtener_evolucion_goles_equipo(equipo):
    """Obtiene evolución anual de goles por equipo."""
    query = """
        SELECT
            SUBSTR(p.fecha, 7, 4) AS anio,
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
        GROUP BY anio
        ORDER BY anio
    """
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=(equipo, equipo, equipo, equipo, equipo, equipo))
    conn.close()
    return df

def obtener_evolucion_puntos_equipo(equipo):
    """Obtiene evolución anual de puntos por equipo (respetando regla 2/3 puntos)."""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Obtener todos los partidos del equipo con sus años
    cur.execute("""
        SELECT
            SUBSTR(p.fecha, 7, 4) AS anio,
            p.equipo_local,
            p.goles_local,
            p.equipo_visitante,
            p.goles_visitante
        FROM partidos p
        WHERE p.arbitro IS NOT NULL AND p.arbitro <> ''
        AND (p.equipo_local = ? OR p.equipo_visitante = ?)
        ORDER BY p.fecha
    """, (equipo, equipo))
    
    partidos = cur.fetchall()
    conn.close()
    
    # Acumular puntos por año
    puntos_por_anio = {}
    
    for partido in partidos:
        anio, local, gl, visitante, gv = partido
        
        # Convertir goles a enteros
        try:
            gl = int(gl) if gl is not None else 0
        except:
            gl = 0
        try:
            gv = int(gv) if gv is not None else 0
        except:
            gv = 0
        
        # Determinar puntos según el año
        puntos_victoria = 3 if int(anio) >= 1995 else 2
        
        # Calcular puntos obtenidos por el equipo
        if local == equipo:
            if gl > gv:
                puntos = puntos_victoria
            elif gl == gv:
                puntos = 1
            else:
                puntos = 0
        else:  # visitante == equipo
            if gv > gl:
                puntos = puntos_victoria
            elif gv == gl:
                puntos = 1
            else:
                puntos = 0
        
        # Acumular
        if anio not in puntos_por_anio:
            puntos_por_anio[anio] = 0
        puntos_por_anio[anio] += puntos
    
    # Convertir a DataFrame
    df = pd.DataFrame([
        {"anio": anio, "puntos": puntos}
        for anio, puntos in sorted(puntos_por_anio.items())
    ])
    
    return df

# =====================================
# SIDEBAR: FILTROS
# =====================================
st.sidebar.title("FilterWhere ⚽")
anio = st.sidebar.text_input("Año", placeholder="Ej: 2024", key="sidebar_anio")
campeonato = st.sidebar.selectbox(
    "Campeonato",
    [""] + obtener_valores_unicos("campeonato"),
    format_func=lambda x: "Todos" if x == "" else x,
    key="sidebar_campeonato"
)
equipo_filtro = st.sidebar.selectbox(
    "Equipo",
    [""] + obtener_equipos(),
    format_func=lambda x: "Todos" if x == "" else x,
    key="sidebar_equipo"
)
solo_expulsados = st.sidebar.checkbox("✅ Solo expulsados", key="sidebar_solo_expulsados")
st.sidebar.markdown("---")
st.sidebar.caption("💡 Filtros aplicados en las primeras pestañas")

# =====================================
# PESTAÑAS
# =====================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13 = st.tabs([
    "📊 Tarjetas x Jugador",
    "🆚 Tarjetas x Rival",
    "📈 Evolución Equipo",
    "⚖️ Árbitro vs Equipo",
    "⚽ Goles x Jugador",
    "🏆 Goleadores Equipo",
    "📊 Rendimiento",
    "🔝 Top Tarjetas",
    "📋 Posiciones",
    "🗓️ Campañas",
    "⚔️ Versus",
    "🥅 Evol. Goles",
    "⭐ Evol. Puntos"
])

# Tab 1: Tarjetas por Jugador
with tab1:
    st.markdown("## 📊 Tarjetas por Jugador")
    df = obtener_tarjetas_por_jugador(anio, campeonato, equipo_filtro, solo_expulsados)
    if df.empty:
        st.warning("⚠️ No se encontraron datos.")
    else:
        df["Total"] = df["amon"] + df["exp"]
        df_display = df.rename(columns={"jugador": "Jugador", "equipo_jugador": "Equipo", "amon": "Amonestaciones", "exp": "Expulsiones", "Total": "Total"})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Jugadores", len(df_display))
        with col2:
            st.metric("⚠️ Amonestados", int(df_display['Amonestaciones'].sum()))
        with col3:
            st.metric("🔴 Expulsados", int(df_display['Expulsiones'].sum()))
        with col4:
            st.metric("📊 Total", int(df_display['Total'].sum()))
        st.dataframe(df_display, use_container_width=True, height=400, hide_index=True)

# Tab 2: Tarjetas por Rival (AHORA POR EQUIPO)
with tab2:
    st.markdown("## 🆚 Tarjetas por Rival (por Equipo)")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        equipo = st.selectbox("Selecciona equipo", obtener_equipos(), key="tab2_equipo")
    
    with col2:
        if equipo:
            df_rivales = obtener_tarjetas_por_rival_equipo(equipo)
            
            if df_rivales.empty:
                st.warning("No hay datos para este equipo.")
            else:
                st.markdown(f"### 📊 Tarjetas recibidas por {equipo} contra cada rival")
                
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.metric("Rivales", len(df_rivales))
                with col_b:
                    st.metric("⚠️ Amonestaciones", int(df_rivales['amon'].sum()))
                with col_c:
                    st.metric("🔴 Expulsiones", int(df_rivales['exp'].sum()))
                with col_d:
                    st.metric("📊 Total", int((df_rivales['amon'] + df_rivales['exp']).sum()))
                
                df_display = df_rivales.rename(columns={
                    "rival": "Rival",
                    "amon": "Amonestaciones",
                    "exp": "Expulsiones"
                })
                df_display["Total"] = df_display["Amonestaciones"] + df_display["Expulsiones"]
                
                st.dataframe(
                    df_display[["Rival", "Amonestaciones", "Expulsiones", "Total"]],
                    column_config={
                        "Amonestaciones": st.column_config.NumberColumn("⚠️ Amonestaciones", format="%d"),
                        "Expulsiones": st.column_config.NumberColumn("🔴 Expulsiones", format="%d"),
                        "Total": st.column_config.NumberColumn("📊 Total", format="%d"),
                    },
                    use_container_width=True,
                    height=350,
                    hide_index=True
                )

# Tab 3: Evolución por Equipo
with tab3:
    st.markdown("## 📈 Evolución Anual de Tarjetas por Equipo")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        equipo = st.selectbox("Selecciona equipo", obtener_equipos(), key="tab3_equipo")
    
    with col2:
        if equipo:
            df = obtener_evolucion_equipo(equipo)
            
            if df.empty:
                st.info("No hay datos para este equipo.")
            else:
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Años", len(df))
                with col_b:
                    st.metric("⚠️ Amonestaciones", int(df['amon'].sum()))
                with col_c:
                    st.metric("🔴 Expulsiones", int(df['exp'].sum()))
                
                st.markdown("---")
                
                # Gráfico
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(df["anio"], df["amon"], marker="o", label="Amonestaciones", color="#FFC107")
                ax.plot(df["anio"], df["exp"], marker="s", label="Expulsiones", color="#F44336")
                ax.set_title(f"Evolución - {equipo}")
                ax.set_xlabel("Año")
                ax.set_ylabel("Cantidad")
                ax.legend()
                ax.grid(True, alpha=0.3)
                st.pyplot(fig)
                
                st.dataframe(df, use_container_width=True, hide_index=True)

# Tab 4: Árbitro vs Equipo
with tab4:
    st.markdown("## ⚖️ Árbitro vs Equipo")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        arbitro = st.selectbox("Árbitro", obtener_valores_unicos("arbitro"), key="tab4_arbitro")
        equipo = st.selectbox("Equipo", obtener_equipos(), key="tab4_equipo")
        anio_filtro = st.text_input("Año (opcional)", key="tab4_anio")
        camp_filtro = st.selectbox("Campeonato (opcional)", [""] + obtener_valores_unicos("campeonato"), key="tab4_campeonato")
    
    with col2:
        if arbitro and equipo:
            stats = obtener_estadisticas_arbitro_equipo(arbitro, equipo, anio_filtro or None, camp_filtro or None)
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("⚽ Partidos", stats["partidos"])
            with col_b:
                st.metric("⚠️ Amonestados", stats["amonestados"])
            with col_c:
                st.metric("🔴 Expulsados", stats["expulsados"])
            st.markdown(f"""
            **Resumen:**
            - El árbitro **{arbitro}** dirigió **{stats['partidos']}** partidos a **{equipo}**
            - Mostró **{stats['amonestados']}** tarjetas amarillas y **{stats['expulsados']}** rojas
            """)

# Tab 5: Goles por Jugador (CORREGIDO)
with tab5:
    st.markdown("## ⚽ Goles por Jugador")
    
    df = obtener_goles_por_jugador(anio, campeonato, equipo_filtro)
    
    if df.empty:
        st.warning("⚠️ No se encontraron datos.")
    else:
        df_display = df.rename(columns={"jugador": "Jugador", "goles": "Goles"})
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Jugadores", len(df_display))
        with col2:
            st.metric("⚽ Total Goles", int(df_display['Goles'].sum()))
        
        st.dataframe(
            df_display,
            column_config={
                "Goles": st.column_config.NumberColumn("⚽ Goles", format="%d"),
            },
            use_container_width=True,
            height=400,
            hide_index=True
        )

# Tab 6: Goleadores por Equipo
with tab6:
    st.markdown("## 🏆 Goleadores por Equipo")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        equipo = st.selectbox("Selecciona equipo", obtener_equipos(), key="tab6_equipo")
    
    with col2:
        if equipo:
            df = obtener_goleadores_por_equipo(equipo)
            
            if df.empty:
                st.info("No hay datos para este equipo.")
            else:
                st.markdown(f"### 🥅 Goleadores de {equipo}")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Jugadores", len(df))
                with col_b:
                    st.metric("⚽ Total Goles", int(df['goles'].sum()))
                
                df_display = df.rename(columns={"jugador": "Jugador", "goles": "Goles"})
                
                st.dataframe(
                    df_display,
                    column_config={
                        "Goles": st.column_config.NumberColumn("⚽ Goles", format="%d"),
                    },
                    use_container_width=True,
                    height=350,
                    hide_index=True
                )

# Tab 7: Rendimiento (CON ORDEN CORREGIDO Y SIN ID)
with tab7:
    st.markdown("## 📊 Rendimiento por Equipo")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        equipo = st.selectbox("Selecciona equipo", obtener_equipos(), key="tab7_equipo")
        anio_rend = st.text_input("Año (opcional)", key="tab7_anio")
        camp_rend = st.selectbox("Campeonato (opcional)", [""] + obtener_valores_unicos("campeonato"), key="tab7_campeonato")
    
    with col2:
        if equipo:
            stats = obtener_estadisticas_rendimiento(equipo, anio_rend or None, camp_rend or None)
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("⚽ PJ", stats["partidos_jugados"])
            with col_b:
                st.metric("✅ PG", stats["ganados"])
            with col_c:
                st.metric("🤝 PE", stats["empatados"])
            with col_d:
                st.metric("❌ PP", stats["perdidos"])
            col_e, col_f, col_g = st.columns(3)
            with col_e:
                st.metric("⚽ GF", stats["goles_favor"])
            with col_f:
                st.metric("🥅 GC", stats["goles_contra"])
            with col_g:
                st.metric("⚖️ DG", stats["diferencia"])
            
            st.markdown("---")
            st.markdown("### 📋 Partidos recientes")
            df_partidos = obtener_rendimiento_equipo(equipo, anio_rend or None, camp_rend or None)
            
            if not df_partidos.empty:
                df_display = df_partidos.rename(columns={
                    "fecha": "Fecha",
                    "campeonato": "Campeonato",
                    "equipo_local": "Local",
                    "equipo_visitante": "Visitante",
                    "goles_local": "GL",
                    "goles_visitante": "GV",
                    "resultado": "Resultado"
                })
                st.dataframe(df_display.head(20), use_container_width=True, hide_index=True)

# Tab 8: Top Tarjetas (ELIMINADO "Más Tarjetas Totales")
with tab8:
    st.markdown("## 🔝 Jugadores con más Tarjetas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⚠️ Más Amonestados")
        df_amon = obtener_jugadores_mas_amonestados(10)
        if not df_amon.empty:
            df_amon = df_amon.rename(columns={"jugador": "Jugador", "equipo": "Equipo", "amonestaciones": "Amonestaciones"})
            st.dataframe(df_amon, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("### 🔴 Más Expulsados")
        df_exp = obtener_jugadores_mas_expulsados(10)
        if not df_exp.empty:
            df_exp = df_exp.rename(columns={"jugador": "Jugador", "equipo": "Equipo", "expulsiones": "Expulsiones"})
            st.dataframe(df_exp, use_container_width=True, hide_index=True)

# Tab 9: Tabla de Posiciones (HISTORIAL COMPLETO PRIMERO)
with tab9:
    st.markdown("## 📋 Tabla Histórica - Todos los Partidos")
    
    # Obtener datos acumulados
    posiciones, total_partidos = obtener_tabla_historica_acumulada()
    
    if not posiciones:
        st.warning("⚠️ No hay datos disponibles.")
    else:
        # Mostrar métrica de partidos procesados
        st.metric(label="Partidos Procesados", value=total_partidos)
        
        st.markdown("---")
        
        # Convertir a DataFrame para mejor visualización
        df_posiciones = pd.DataFrame(posiciones, columns=[
            "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "Puntos"
        ])
        
        # Mostrar tabla completa
        st.dataframe(
            df_posiciones,
            column_config={
                "PJ": st.column_config.NumberColumn("PJ", format="%d"),
                "PG": st.column_config.NumberColumn("PG", format="%d"),
                "PE": st.column_config.NumberColumn("PE", format="%d"),
                "PP": st.column_config.NumberColumn("PP", format="%d"),
                "GF": st.column_config.NumberColumn("GF", format="%d"),
                "GC": st.column_config.NumberColumn("GC", format="%d"),
                "DG": st.column_config.NumberColumn("DG", format="%d"),
                "Puntos": st.column_config.NumberColumn("PTS", format="%d"),
            },
            use_container_width=True,
            height=600,
            hide_index=True
        )
        
        st.markdown("---")
        
        # Estadísticas adicionales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 🏆 Top 5 Equipos")
            top5 = df_posiciones.head(5)[["Equipo", "Puntos"]].reset_index(drop=True)
            top5.index = top5.index + 1
            st.dataframe(top5, use_container_width=True, hide_index=False)
        
        with col2:
            st.markdown("### ⚽ Más Goles a Favor")
            top_gf = df_posiciones.sort_values("GF", ascending=False).head(5)[["Equipo", "GF"]].reset_index(drop=True)
            top_gf.index = top_gf.index + 1
            st.dataframe(top_gf, use_container_width=True, hide_index=False)
        
        with col3:
            st.markdown("### 🥅 Mejor Diferencia de Gol")
            top_dg = df_posiciones.sort_values("DG", ascending=False).head(5)[["Equipo", "DG"]].reset_index(drop=True)
            top_dg.index = top_dg.index + 1
            st.dataframe(top_dg, use_container_width=True, hide_index=False)

# Tab 10: Campañas (CON ORDEN CORREGIDO Y SIN ID)
with tab10:
    st.markdown("## 🗓️ Campaña de un Equipo")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### 🎯 Seleccione Equipo")
        equipo_campania = st.selectbox("Equipo", obtener_equipos(), key="tab10_equipo")
        anio_campania = st.text_input("Año (opcional)", placeholder="Ej: 2024", key="tab10_anio")
        camp_campania = st.selectbox("Campeonato (opcional)", [""] + obtener_valores_unicos("campeonato"), key="tab10_campeonato")
        mostrar_goleadores = st.checkbox("⚽ Mostrar goleadores", value=True, key="tab10_goleadores")
    
    with col2:
        if equipo_campania:
            # Obtener estadísticas generales
            stats = obtener_estadisticas_rendimiento(equipo_campania, anio_campania or None, camp_campania or None)
            
            st.markdown(f"### 📊 Resumen de la Campaña: {equipo_campania}")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("⚽ Partidos", stats["partidos_jugados"])
            with col_b:
                st.metric("✅ Ganados", stats["ganados"])
            with col_c:
                st.metric("🤝 Empatados", stats["empatados"])
            with col_d:
                st.metric("❌ Perdidos", stats["perdidos"])
            
            col_e, col_f, col_g = st.columns(3)
            with col_e:
                st.metric("⚽ GF", stats["goles_favor"])
            with col_f:
                st.metric("🥅 GC", stats["goles_contra"])
            with col_g:
                st.metric("⚖️ DG", stats["diferencia"])
            
            st.markdown("---")
            
            # Obtener partidos detallados
            df_partidos = obtener_campania_equipo(equipo_campania, anio_campania or None, camp_campania or None)
            
            if df_partidos.empty:
                st.warning("⚠️ No hay partidos para mostrar con los filtros aplicados.")
            else:
                st.markdown(f"### 📋 Partidos ({len(df_partidos)} encontrados)")
                
                # Mostrar tabla de partidos
                partidos_display = []
                
                for idx, partido in df_partidos.iterrows():
                    # Determinar rival
                    rival = partido['equipo_visitante'] if partido['equipo_local'] == equipo_campania else partido['equipo_local']
                    
                    # Formatear resultado
                    if partido['equipo_local'] == equipo_campania:
                        resultado = f"{partido['goles_favor']}-{partido['goles_contra']}"
                    else:
                        resultado = f"{partido['goles_contra']}-{partido['goles_favor']}"
                    
                    # Obtener goleadores si está activado
                    goleadores_str = ""
                    if mostrar_goleadores:
                        df_goleadores = obtener_goleadores_partido(partido['id'], equipo_campania)
                        if not df_goleadores.empty:
                            goles_lista = []
                            for _, gol in df_goleadores.iterrows():
                                goles_lista.append(formatear_goleador(gol['jugador'], gol['goles']))
                            goleadores_str = ", ".join(goles_lista)
                    
                    partidos_display.append({
                        "Fecha": partido['fecha'],
                        "Lugar": partido['lugar'],
                        "Torneo": partido['campeonato'],
                        "Rival": rival,
                        "Resultado": resultado,
                        "GF": partido['goles_favor'],
                        "GC": partido['goles_contra'],
                        "⚽": partido['resultado'],
                        "Goleadores": goleadores_str if goleadores_str else "-"
                    })
                
                df_display = pd.DataFrame(partidos_display)
                
                # Reordenar columnas
                # Reordenar columnas (sin GF y GC)
                columnas_orden = ["Fecha", "Lugar", "Torneo", "Rival", "Resultado"]
                if mostrar_goleadores:
                    columnas_orden.append("Goleadores")
                
                st.dataframe(
                    df_display[columnas_orden],
                    use_container_width=True,
                    height=500,
                    hide_index=True
                )

# Tab 11: Versus (CON ORDEN CORREGIDO Y SIN ID)
with tab11:
    st.markdown("## ⚔️ Versus: Comparativa entre Equipos")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🎯 Seleccione Equipos")
        equipo1 = st.selectbox("Equipo 1", obtener_equipos(), key="tab11_equipo1")
        equipo2 = st.selectbox("Equipo 2", obtener_equipos(), key="tab11_equipo2")
        
        if equipo1 == equipo2:
            st.warning("⚠️ Selecciona dos equipos diferentes")
        
        anio_versus = st.text_input("Año (opcional)", placeholder="Ej: 2024", key="tab11_anio")
        camp_versus = st.selectbox("Campeonato (opcional)", [""] + obtener_valores_unicos("campeonato"), key="tab11_campeonato")
    
    with col2:
        if equipo1 and equipo2 and equipo1 != equipo2:
            # Obtener estadísticas resumen
            stats = obtener_estadisticas_versus(equipo1, equipo2, anio_versus or None, camp_versus or None)
            
            st.markdown(f"### 📊 Historial: {equipo1} vs {equipo2}")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("⚽ Partidos", stats["total_partidos"])
            with col_b:
                st.metric(f"✅ {equipo1}", stats["victorias_eq1"])
            with col_c:
                st.metric(f"✅ {equipo2}", stats["victorias_eq2"])
            
            col_d, col_e, col_f = st.columns(3)
            with col_d:
                st.metric("🤝 Empates", stats["empates"])
            with col_e:
                st.metric(f"⚽ GF {equipo1}", stats["goles_eq1"])
            with col_f:
                st.metric(f"⚽ GF {equipo2}", stats["goles_eq2"])
            
            # Calcular porcentajes
            if stats["total_partidos"] > 0:
                st.markdown("---")
                st.markdown("### 📈 Porcentajes")
                
                porc_eq1 = (stats["victorias_eq1"] / stats["total_partidos"]) * 100
                porc_eq2 = (stats["victorias_eq2"] / stats["total_partidos"]) * 100
                porc_emp = (stats["empates"] / stats["total_partidos"]) * 100
                
                col_x, col_y, col_z = st.columns(3)
                with col_x:
                    st.metric(f"% {equipo1}", f"{porc_eq1:.1f}%")
                with col_y:
                    st.metric(f"% {equipo2}", f"{porc_eq2:.1f}%")
                with col_z:
                    st.metric("% Empates", f"{porc_emp:.1f}%")
            
            st.markdown("---")
            
            # Obtener historial detallado
            df_historial = obtener_historial_versus(equipo1, equipo2, anio_versus or None, camp_versus or None)
            
            if df_historial.empty:
                st.warning("⚠️ No hay enfrentamientos entre estos equipos con los filtros aplicados.")
            else:
                st.markdown(f"### 📋 Historial de Enfrentamientos ({len(df_historial)} partidos)")
                
                # Formatear tabla
                historial_display = []
                
                for idx, partido in df_historial.iterrows():
                    resultado = f"{partido['goles_local']}-{partido['goles_visitante']}"
                    
                    historial_display.append({
                        "Fecha": partido['fecha'],
                        "Torneo": partido['campeonato'],
                        "Local": partido['equipo_local'],
                        "Visitante": partido['equipo_visitante'],
                        "Resultado": resultado,
                        "🏆 Ganador": partido['ganador'] if partido['ganador'] != 'Empate' else "🤝 Empate"
                    })
                
                df_display = pd.DataFrame(historial_display)
                
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    height=400,
                    hide_index=True
                )

# =====================================
# TAB 12: EVOLUCIÓN DE GOLES
# =====================================
with tab12:
    st.markdown("## 🥅 Evolución de Goles por Equipo")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### 🎯 Seleccione Equipo")
        equipo_goles = st.selectbox("Equipo", obtener_equipos(), key="tab12_equipo")
    
    with col2:
        if equipo_goles:
            df_goles = obtener_evolucion_goles_equipo(equipo_goles)
            
            if df_goles.empty:
                st.info("No hay datos para este equipo.")
            else:
                # Métricas
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Años", len(df_goles))
                with col_b:
                    st.metric("⚽ Goles a Favor", int(df_goles['goles_favor'].sum()))
                with col_c:
                    st.metric("🥅 Goles en Contra", int(df_goles['goles_contra'].sum()))
                
                st.markdown("---")
                
                # Gráfico de líneas
                fig, ax = plt.subplots(figsize=(12, 6))
                
                ax.plot(df_goles["anio"], df_goles["goles_favor"], 
                       marker="o", linewidth=3, markersize=8,
                       label="Goles a Favor", color="#4CAF50", alpha=0.9)
                ax.plot(df_goles["anio"], df_goles["goles_contra"], 
                       marker="s", linewidth=3, markersize=8,
                       label="Goles en Contra", color="#F44336", alpha=0.9)
                
                # Añadir valores en los puntos
                for i, row in df_goles.iterrows():
                    ax.annotate(f'{int(row["goles_favor"])}', 
                              (row["anio"], row["goles_favor"]),
                              textcoords="offset points", xytext=(0,10), 
                              ha='center', fontsize=9, color='#4CAF50')
                    ax.annotate(f'{int(row["goles_contra"])}', 
                              (row["anio"], row["goles_contra"]),
                              textcoords="offset points", xytext=(0,10), 
                              ha='center', fontsize=9, color='#F44336')
                
                ax.set_xlabel("Año", fontsize=12, fontweight='bold')
                ax.set_ylabel("Cantidad de Goles", fontsize=12, fontweight='bold')
                ax.set_title(f"Evolución de goles - {equipo_goles}", 
                           fontsize=14, fontweight='bold', pad=20)
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.legend(fontsize=11, loc='upper left')
                ax.set_xticks(df_goles["anio"])
                
                plt.tight_layout()
                st.pyplot(fig)
                
                # Tabla de datos
                st.markdown("### 📋 Datos Detallados")
                df_display = df_goles.rename(columns={
                    "anio": "Año",
                    "goles_favor": "⚽ Goles a Favor",
                    "goles_contra": "🥅 Goles en Contra"
                })
                df_display["⚖️ Diferencia"] = df_display["⚽ Goles a Favor"] - df_display["🥅 Goles en Contra"]
                
                st.dataframe(
                    df_display,
                    column_config={
                        "⚽ Goles a Favor": st.column_config.NumberColumn("⚽ GF", format="%d"),
                        "🥅 Goles en Contra": st.column_config.NumberColumn("🥅 GC", format="%d"),
                        "⚖️ Diferencia": st.column_config.NumberColumn("⚖️ DG", format="%d"),
                    },
                    use_container_width=True,
                    hide_index=True
                )

# =====================================
# TAB 13: EVOLUCIÓN DE PUNTOS
# =====================================
with tab13:
    st.markdown("## ⭐ Evolución de Puntos por Equipo")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### 🎯 Seleccione Equipo")
        equipo_puntos = st.selectbox("Equipo", obtener_equipos(), key="tab13_equipo")
    
    with col2:
        if equipo_puntos:
            df_puntos = obtener_evolucion_puntos_equipo(equipo_puntos)
            
            if df_puntos.empty:
                st.info("No hay datos para este equipo.")
            else:
                # Métricas
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Años", len(df_puntos))
                with col_b:
                    st.metric("⭐ Puntos Totales", int(df_puntos['puntos'].sum()))
                
                st.markdown("---")
                
                # Gráfico de líneas
                fig, ax = plt.subplots(figsize=(12, 6))
                
                ax.plot(df_puntos["anio"], df_puntos["puntos"], 
                       marker="D", linewidth=3, markersize=8,
                       label="Puntos", color="#FF9800", alpha=0.9)
                
                # Añadir valores en los puntos
                for i, row in df_puntos.iterrows():
                    ax.annotate(f'{int(row["puntos"])}', 
                              (row["anio"], row["puntos"]),
                              textcoords="offset points", xytext=(0,10), 
                              ha='center', fontsize=9, color='#FF9800')
                
                ax.set_xlabel("Año", fontsize=12, fontweight='bold')
                ax.set_ylabel("Puntos", fontsize=12, fontweight='bold')
                ax.set_title(f"Evolución de puntos - {equipo_puntos}", 
                           fontsize=14, fontweight='bold', pad=20)
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.legend(fontsize=11, loc='upper left')
                ax.set_xticks(df_puntos["anio"])
                
                plt.tight_layout()
                st.pyplot(fig)
                
                # Tabla de datos
                st.markdown("### 📋 Datos Detallados")
                df_display = df_puntos.rename(columns={
                    "anio": "Año",
                    "puntos": "⭐ Puntos"
                })
                
                st.dataframe(
                    df_display,
                    column_config={
                        "⭐ Puntos": st.column_config.NumberColumn("⭐ Puntos", format="%d"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Nota sobre sistema de puntos
                st.markdown("---")
                primer_anio = int(df_puntos["anio"].min())
                ultimo_anio = int(df_puntos["anio"].max())
                
                if primer_anio < 1995 and ultimo_anio >= 1995:
                    st.info(f"""
                    📝 **Sistema de puntos aplicado:**
                    - **{primer_anio} - 1994**: 2 puntos por victoria
                    - **1995 - {ultimo_anio}**: 3 puntos por victoria
                    """)
                elif primer_anio < 1995:
                    st.info(f"📝 **Sistema de puntos**: 2 puntos por victoria ({primer_anio} - {ultimo_anio})")
                else:
                    st.info(f"📝 **Sistema de puntos**: 3 puntos por victoria ({primer_anio} - {ultimo_anio})")

# =====================================
# FOOTER
# =====================================
st.markdown("---")

st.caption("🏆 Sistema de Estadísticas ⚽ | Liga Deportiva del Sur")

