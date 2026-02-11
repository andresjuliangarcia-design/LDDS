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
    
    Archivos en el servidor: {', '.join(sorted(os.listdir('.')))}
    """)
    st.stop()

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
solo_expulsados = st.sidebar.checkbox("✅ Solo jugadores expulsados", value=False, key="sidebar_solo_expulsados")

st.sidebar.markdown("---")
st.sidebar.caption("💡 Filtros aplicados en 'Tarjetas por Jugador'")

# =====================================
# PESTAÑAS
# =====================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Tarjetas por Jugador",
    "📈 Evolución por Equipo",
    "🆚 Resumen por Rival",
    "📋 Consulta por Equipo",
    "⚖️ Árbitro vs Equipo"
])

# =====================================
# TAB 1: TARJETAS POR JUGADOR
# =====================================
with tab1:
    st.markdown("## 📊 Tarjetas por Jugador")
    
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
    if equipo_filtro:
        query += " AND (p.equipo_local = ? OR p.equipo_visitante = ?)"
        params.extend([equipo_filtro, equipo_filtro])
    if solo_expulsados:
        query += " AND t.tipo = 'Expulsado'"
    
    query += """
        GROUP BY t.jugador, equipo_jugador
        HAVING (amon + exp) > 0
        ORDER BY (amon + exp) DESC, t.jugador
    """
    
    try:
        conn = sqlite3.connect(DB)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty:
            st.warning("⚠️ No se encontraron datos con los filtros aplicados.")
        else:
            df["Total"] = df["amon"] + df["exp"]
            df_display = df.rename(columns={
                "jugador": "Jugador",
                "equipo_jugador": "Equipo",
                "amon": "Amonestaciones",
                "exp": "Expulsiones"
            })
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Jugadores", len(df_display))
            with col2:
                st.metric("⚠️ Amonestados", int(df_display['Amonestaciones'].sum()))
            with col3:
                st.metric("🔴 Expulsados", int(df_display['Expulsiones'].sum()))
            with col4:
                st.metric("📊 Total", int(df_display['Total'].sum()))
            
            st.dataframe(
                df_display[["Jugador", "Equipo", "Amonestaciones", "Expulsiones", "Total"]],
                column_config={
                    "Amonestaciones": st.column_config.NumberColumn("⚠️ Amonestaciones", format="%d"),
                    "Expulsiones": st.column_config.NumberColumn("🔴 Expulsiones", format="%d"),
                    "Total": st.column_config.NumberColumn("📊 Total", format="%d"),
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )
    except Exception as e:
        st.error(f"Error: {e}")

# =====================================
# TAB 2: EVOLUCIÓN POR EQUIPO
# =====================================
with tab2:
    st.markdown("## 📈 Evolución Anual por Equipo")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        equipo = st.selectbox("Selecciona equipo", obtener_equipos(), key="tab2_equipo")
    
    with col2:
        if equipo:
            try:
                conn = sqlite3.connect(DB)
                cur = conn.cursor()
                cur.execute("""
                    SELECT SUBSTR(p.fecha, 7, 4) AS anio,
                           SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amon,
                           SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS exp
                    FROM partidos p
                    JOIN tarjetas t ON t.partido_id = p.id
                    WHERE (p.equipo_local = ? OR p.equipo_visitante = ?)
                    GROUP BY anio ORDER BY anio
                """, (equipo, equipo))
                
                filas = cur.fetchall()
                conn.close()
                
                if filas:
                    df = pd.DataFrame(filas, columns=["Año", "Amonestaciones", "Expulsiones"])
                    
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.plot(df["Año"], df["Amonestaciones"], marker="o", label="Amonestaciones", color="#FFC107")
                    ax.plot(df["Año"], df["Expulsiones"], marker="s", label="Expulsiones", color="#F44336")
                    ax.set_title(f"Evolución - {equipo}")
                    ax.set_xlabel("Año")
                    ax.set_ylabel("Cantidad")
                    ax.legend()
                    ax.grid(True, alpha=0.3)
                    st.pyplot(fig)
                    
                    st.dataframe(df, hide_index=True, use_container_width=True)
                else:
                    st.info("No hay datos para este equipo.")
            except Exception as e:
                st.error(f"Error: {e}")

# =====================================
# TAB 3: RESUMEN POR RIVAL
# =====================================
with tab3:
    st.markdown("## 🆚 Resumen por Rival")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        jugador = st.selectbox("Selecciona jugador", obtener_jugadores(), key="tab3_jugador")
    
    with col2:
        if jugador:
            try:
                conn = sqlite3.connect(DB)
                
                # Obtener equipo del jugador
                cur = conn.cursor()
                cur.execute("""
                    SELECT DISTINCT
                        CASE WHEN t.equipo = 'Local' THEN p.equipo_local
                             WHEN t.equipo = 'Visitante' THEN p.equipo_visitante END
                    FROM partidos p JOIN tarjetas t ON t.partido_id = p.id
                    WHERE t.jugador = ? LIMIT 1
                """, (jugador,))
                equipo_jug = cur.fetchone()
                equipo_jug = equipo_jug[0] if equipo_jug else "Desconocido"
                
                # Resumen por rival
                df_rivales = pd.read_sql_query("""
                    SELECT
                        CASE WHEN t.equipo = 'Local' THEN p.equipo_visitante
                             WHEN t.equipo = 'Visitante' THEN p.equipo_local END AS rival,
                        COUNT(*) AS total,
                        SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amon,
                        SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS exp
                    FROM partidos p JOIN tarjetas t ON t.partido_id = p.id
                    WHERE t.jugador = ?
                    GROUP BY rival ORDER BY total DESC
                """, conn, params=(jugador,))
                conn.close()
                
                if not df_rivales.empty:
                    st.markdown(f"**Jugador:** {jugador} | **Equipo:** {equipo_jug}")
                    
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("Rivales", len(df_rivales))
                    with col_b:
                        st.metric("⚠️ Amonestaciones", int(df_rivales['amon'].sum()))
                    with col_c:
                        st.metric("🔴 Expulsiones", int(df_rivales['exp'].sum()))
                    with col_d:
                        st.metric("📊 Total", int(df_rivales['total'].sum()))
                    
                    df_rivales = df_rivales.rename(columns={"rival": "Rival", "amon": "Amonestaciones", "exp": "Expulsiones", "total": "Total"})
                    st.dataframe(
                        df_rivales[["Rival", "Amonestaciones", "Expulsiones", "Total"]],
                        column_config={
                            "Amonestaciones": st.column_config.NumberColumn("⚠️ Amonestaciones", format="%d"),
                            "Expulsiones": st.column_config.NumberColumn("🔴 Expulsiones", format="%d"),
                            "Total": st.column_config.NumberColumn("📊 Total", format="%d"),
                        },
                        hide_index=True,
                        use_container_width=True,
                        height=350
                    )
                else:
                    st.warning("No hay datos para este jugador.")
            except Exception as e:
                st.error(f"Error: {e}")

# =====================================
# TAB 4: CONSULTA POR EQUIPO
# =====================================
with tab4:
    st.markdown("## 📋 Consulta Histórica por Equipo")
    
    equipo = st.selectbox("Selecciona equipo", obtener_equipos(), key="tab4_equipo")
    
    if equipo:
        try:
            conn = sqlite3.connect(DB)
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END)
                FROM partidos p JOIN tarjetas t ON t.partido_id = p.id
                WHERE p.equipo_local = ? OR p.equipo_visitante = ?
            """, (equipo, equipo))
            amon, exp = cur.fetchone()
            conn.close()
            
            amon = amon or 0
            exp = exp or 0
            total = amon + exp
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("⚠️ Amonestaciones", amon)
            with col2:
                st.metric("🔴 Expulsiones", exp)
            with col3:
                st.metric("📊 Total", total)
            
            if total > 0:
                fig, ax = plt.subplots(figsize=(6, 6))
                ax.pie([amon, exp], labels=["Amonestaciones", "Expulsiones"], 
                       colors=["#FFC107", "#F44336"], autopct='%1.1f%%', startangle=90)
                ax.set_title(f"Distribución - {equipo}")
                st.pyplot(fig)
        except Exception as e:
            st.error(f"Error: {e}")

# =====================================
# TAB 5: ÁRBITRO VS EQUIPO
# =====================================
with tab5:
    st.markdown("## ⚖️ Árbitro vs Equipo")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        arbitro = st.selectbox("Árbitro", obtener_valores_unicos("arbitro"), key="tab5_arbitro")
        equipo = st.selectbox("Equipo", obtener_equipos(), key="tab5_equipo")
        anio_filtro = st.text_input("Año (opcional)", key="tab5_anio")
        camp_filtro = st.selectbox("Campeonato (opcional)", [""] + obtener_valores_unicos("campeonato"), key="tab5_campeonato")
    
    with col2:
        if arbitro and equipo:
            try:
                query = """
                    SELECT COUNT(DISTINCT p.id),
                           SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END),
                           SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END)
                    FROM partidos p LEFT JOIN tarjetas t ON t.partido_id = p.id
                    WHERE p.arbitro = ? AND (p.equipo_local = ? OR p.equipo_visitante = ?)
                """
                params = [arbitro, equipo, equipo]
                if anio_filtro:
                    query += " AND SUBSTR(p.fecha,7,4) = ?"
                    params.append(anio_filtro)
                if camp_filtro:
                    query += " AND p.campeonato = ?"
                    params.append(camp_filtro)
                
                conn = sqlite3.connect(DB)
                cur = conn.cursor()
                cur.execute(query, params)
                partidos, amon, exp = cur.fetchone()
                conn.close()
                
                partidos = partidos or 0
                amon = amon or 0
                exp = exp or 0
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("⚽ Partidos", partidos)
                with col_b:
                    st.metric("⚠️ Amonestados", amon)
                with col_c:
                    st.metric("🔴 Expulsados", exp)
                
                st.markdown(f"""
                **Resumen:**
                - El árbitro **{arbitro}** dirigió **{partidos}** partidos a **{equipo}**
                - Mostró **{amon}** tarjetas amarillas y **{exp}** rojas
                - Total: **{amon + exp}** tarjetas
                """)
            except Exception as e:
                st.error(f"Error: {e}")

# =====================================
# FOOTER
# =====================================
st.markdown("---")
st.caption("🏆 Sistema de Seguimiento de Liga de Fútbol | football_nueva.db")