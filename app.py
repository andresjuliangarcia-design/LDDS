import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os

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
# FUNCIONES DE BASE DE DATOS (todo en un solo archivo)
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

def obtener_equipo_jugador(jugador):
    conn = sqlite3.connect(DB)
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
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(query, conn, params=(jugador,))
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
    query += " ORDER BY p.fecha DESC"
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

def obtener_jugadores_mas_tarjetas(limite=20):
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

def obtener_tabla_posiciones(anio, campeonato=None):
    conn = sqlite3.connect(DB)
    query_equipos = """
        SELECT DISTINCT equipo FROM (
            SELECT equipo_local AS equipo FROM partidos
            UNION
            SELECT equipo_visitante FROM partidos
        ) WHERE equipo IS NOT NULL AND equipo <> ''
    """
    equipos = pd.read_sql_query(query_equipos, conn)
    equipos_list = equipos['equipo'].tolist()
    
    query_partidos = """
        SELECT
            p.equipo_local,
            p.equipo_visitante,
            p.goles_local,
            p.goles_visitante,
            SUBSTR(p.fecha, 7, 4) AS anio
        FROM partidos p
        WHERE SUBSTR(p.fecha, 7, 4) = ?
    """
    params = [anio]
    if campeonato:
        query_partidos += " AND p.campeonato = ?"
        params.append(campeonato)
    partidos = pd.read_sql_query(query_partidos, conn, params=params)
    conn.close()
    
    estadisticas = []
    for equipo in equipos_list:
        pj = pg = pe = pp = gf = gc = puntos = 0
        for _, partido in partidos.iterrows():
            if partido['equipo_local'] == equipo or partido['equipo_visitante'] == equipo:
                pj += 1
                pts, ganado, empate, perdido = calcular_puntos(
                    partido['goles_local'],
                    partido['goles_visitante'],
                    partido['equipo_local'],
                    partido['equipo_visitante'],
                    equipo,
                    anio
                )
                puntos += pts
                pg += ganado
                pe += empate
                pp += perdido
                if partido['equipo_local'] == equipo:
                    gf += partido['goles_local'] or 0
                    gc += partido['goles_visitante'] or 0
                else:
                    gf += partido['goles_visitante'] or 0
                    gc += partido['goles_local'] or 0
        if pj > 0:
            estadisticas.append({
                'Equipo': equipo,
                'PJ': pj,
                'PG': pg,
                'PE': pe,
                'PP': pp,
                'GF': gf,
                'GC': gc,
                'DG': gf - gc,
                'Puntos': puntos
            })
    
    df = pd.DataFrame(estadisticas)
    if not df.empty:
        df = df.sort_values(['Puntos', 'DG', 'GF'], ascending=[False, False, False])
        df = df.reset_index(drop=True)
        df.index = df.index + 1
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📊 Tarjetas x Jugador",
    "🆚 Tarjetas x Rival",
    "📈 Evolución Equipo",
    "⚖️ Árbitro vs Equipo",
    "⚽ Goles x Jugador",
    "🏆 Goleadores Equipo",
    "📊 Rendimiento",
    "🔝 Top Tarjetas",
    "📋 Posiciones"
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
        st.dataframe(df_display, use_container_width=True, height=400)

# Tab 2: Resumen por Rival
with tab2:
    st.markdown("## 🆚 Resumen de Tarjetas por Rival")
    col1, col2 = st.columns([1, 3])
    with col1:
        jugador = st.selectbox("Selecciona jugador", obtener_jugadores(), key="tab2_jugador")
    with col2:
        if jugador:
            equipo_jug = obtener_equipo_jugador(jugador)
            df_rivales = obtener_tarjetas_por_rival(jugador)
            if df_rivales.empty:
                st.warning("No hay datos para este jugador.")
            else:
                st.markdown(f"**Jugador:** {jugador} | **Equipo:** {equipo_jug}")
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.metric("Rivales", len(df_rivales))
                with col_b:
                    st.metric("⚠️ Amonestaciones", int(df_rivales['amon'].sum()))
                with col_c:
                    st.metric("🔴 Expulsiones", int(df_rivales['exp'].sum()))
                with col_d:
                    st.metric("📊 Total", int(df_rivales['total_tarjetas'].sum()))
                df_display = df_rivales.rename(columns={"rival": "Rival", "amon": "Amonestaciones", "exp": "Expulsiones", "total_tarjetas": "Total"})
                st.dataframe(df_display, use_container_width=True, height=350)

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
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(df["anio"], df["amon"], marker="o", label="Amonestaciones", color="#FFC107")
                ax.plot(df["anio"], df["exp"], marker="s", label="Expulsiones", color="#F44336")
                ax.set_title(f"Evolución - {equipo}")
                ax.set_xlabel("Año")
                ax.set_ylabel("Cantidad")
                ax.legend()
                ax.grid(True, alpha=0.3)
                st.pyplot(fig)
                st.dataframe(df, use_container_width=True)

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

# Tab 5: Goles por Jugador
with tab5:
    st.markdown("## ⚽ Goles por Jugador")
    df = obtener_goles_por_jugador(anio, campeonato, equipo_filtro)
    if df.empty:
        st.warning("⚠️ No se encontraron datos.")
    else:
        df_display = df.rename(columns={"jugador": "Jugador", "equipo_jugador": "Equipo", "goles": "Goles"})
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Jugadores", len(df_display))
        with col2:
            st.metric("⚽ Total Goles", int(df_display['Goles'].sum()))
        st.dataframe(df_display, use_container_width=True, height=400)

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
                st.dataframe(df_display, use_container_width=True, height=350)

# Tab 7: Rendimiento
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
                df_display = df_partidos.rename(columns={"fecha": "Fecha", "campeonato": "Campeonato", "equipo_local": "Local", "equipo_visitante": "Visitante", "goles_local": "GL", "goles_visitante": "GV", "resultado": "Resultado"})
                st.dataframe(df_display.head(20), use_container_width=True)

# Tab 8: Top Tarjetas
with tab8:
    st.markdown("## 🔝 Jugadores con más Tarjetas")
    col1, col2, col3 = st.columns(3)
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
    with col3:
        st.markdown("### 📊 Más Tarjetas Totales")
        df_total = obtener_jugadores_mas_tarjetas(10)
        if not df_total.empty:
            df_total = df_total.rename(columns={"jugador": "Jugador", "equipo": "Equipo", "amonestaciones": "Amonestaciones", "expulsiones": "Expulsiones", "total_tarjetas": "Total"})
            st.dataframe(df_total, use_container_width=True, hide_index=True)

# Tab 9: Tabla de Posiciones
with tab9:
    st.markdown("## 📋 Tabla de Posiciones")
    col1, col2 = st.columns([1, 3])
    with col1:
        anio_pos = st.text_input("Año", value="2024", key="tab9_anio")
        camp_pos = st.selectbox("Campeonato (opcional)", [""] + obtener_valores_unicos("campeonato"), key="tab9_campeonato")
    with col2:
        if anio_pos:
            try:
                df_pos = obtener_tabla_posiciones(anio_pos, camp_pos or None)
                if df_pos.empty:
                    st.warning("No hay datos para este año/campeonato.")
                else:
                    sistema = "3 puntos por victoria" if int(anio_pos) >= 1995 else "2 puntos por victoria"
                    st.info(f"📅 Año: {anio_pos} | Sistema de puntos: {sistema}")
                    st.dataframe(df_pos, use_container_width=True, height=500)
            except ValueError:
                st.error("Por favor ingresa un año válido (ej: 2024)")

# Footer
st.markdown("---")
st.caption("🏆 Sistema de Seguimiento de Liga de Fútbol ⚽ | football_nueva.db")