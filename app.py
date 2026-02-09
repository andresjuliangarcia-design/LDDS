import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd

# Importar módulos
from utils.database import verificar_db, obtener_equipos, obtener_jugadores, obtener_valores_unicos
from consultas.tarjetas import obtener_tarjetas_por_jugador
from consultas.rivales import obtener_equipo_jugador, obtener_tarjetas_por_rival
from consultas.evolucion import obtener_evolucion_equipo
from consultas.arbitros import obtener_estadisticas_arbitro_equipo
from consultas.estadisticas import obtener_resumen_equipo
from consultas.goles import obtener_goles_por_jugador, obtener_goleadores_por_equipo, obtener_top_goleadores
from consultas.rendimiento import obtener_rendimiento_equipo, obtener_estadisticas_rendimiento
from consultas.top_jugadores import (
    obtener_jugadores_mas_amonestados,
    obtener_jugadores_mas_expulsados,
    obtener_jugadores_mas_tarjetas
)
from consultas.posiciones import obtener_tabla_posiciones

# =====================================
# CONFIGURACIÓN INICIAL
# =====================================
try:
    verificar_db()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

st.set_page_config(
    page_title="🏆 Seguimiento Liga de Fútbol",
    page_icon="⚽",
    layout="wide"
)

# =====================================
# SIDEBAR: FILTROS GLOBALES
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
# PESTAÑAS PRINCIPALES
# =====================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📊 Tarjetas x Jugador",
    "🆚 Tarjetas x Rival",
    "📈 Evolución Equipo",
    "⚖️ Árbitro vs Equipo",
    "⚽ Goles x Jugador",
    "🏆 Goleadores Equipo",
    "📊 Rendimiento",
    "🔝 Top Tarjetas",
    "📋 Posiciones",
    "ℹ️ Info"
])

# =====================================
# TAB 1: TARJETAS POR JUGADOR
# =====================================
with tab1:
    st.markdown("## 📊 Tarjetas por Jugador")
    
    df = obtener_tarjetas_por_jugador(anio, campeonato, equipo_filtro, solo_expulsados)
    
    if df.empty:
        st.warning("⚠️ No se encontraron datos.")
    else:
        df["Total"] = df["amon"] + df["exp"]
        df_display = df.rename(columns={
            "jugador": "Jugador",
            "equipo_jugador": "Equipo",
            "amon": "Amonestaciones",
            "exp": "Expulsiones",
            "Total": "Total"
        })
        
        # Métricas
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
            df_display,
            column_config={
                "Amonestaciones": st.column_config.NumberColumn("⚠️ Amonestaciones", format="%d"),
                "Expulsiones": st.column_config.NumberColumn("🔴 Expulsiones", format="%d"),
                "Total": st.column_config.NumberColumn("📊 Total", format="%d"),
            },
            use_container_width=True,
            height=400
        )

# =====================================
# TAB 2: RESUMEN POR RIVAL
# =====================================
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
                
                df_display = df_rivales.rename(columns={
                    "rival": "Rival",
                    "amon": "Amonestaciones",
                    "exp": "Expulsiones",
                    "total_tarjetas": "Total"
                })
                
                st.dataframe(
                    df_display,
                    column_config={
                        "Amonestaciones": st.column_config.NumberColumn("⚠️ Amonestaciones", format="%d"),
                        "Expulsiones": st.column_config.NumberColumn("🔴 Expulsiones", format="%d"),
                        "Total": st.column_config.NumberColumn("📊 Total", format="%d"),
                    },
                    use_container_width=True,
                    height=350
                )

# =====================================
# TAB 3: EVOLUCIÓN POR EQUIPO
# =====================================
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
                
                st.dataframe(df, use_container_width=True)

# =====================================
# TAB 4: ÁRBITRO VS EQUIPO
# =====================================
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
            - Total: **{stats['amonestados'] + stats['expulsados']}** tarjetas
            """)

# =====================================
# TAB 5: GOLES POR JUGADOR
# =====================================
with tab5:
    st.markdown("## ⚽ Goles por Jugador")
    
    df = obtener_goles_por_jugador(anio, campeonato, equipo_filtro)
    
    if df.empty:
        st.warning("⚠️ No se encontraron datos.")
    else:
        df_display = df.rename(columns={
            "jugador": "Jugador",
            "equipo_jugador": "Equipo",
            "goles": "Goles"
        })
        
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
            height=400
        )

# =====================================
# TAB 6: GOLEADORES POR EQUIPO
# =====================================
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
                    height=350
                )

# =====================================
# TAB 7: RENDIMIENTO
# =====================================
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
            
            # Detalle de partidos
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
                st.dataframe(df_display.head(20), use_container_width=True)

# =====================================
# TAB 8: TOP JUGADORES (TARJETAS)
# =====================================
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
            df_total = df_total.rename(columns={
                "jugador": "Jugador",
                "equipo": "Equipo",
                "amonestaciones": "Amonestaciones",
                "expulsiones": "Expulsiones",
                "total_tarjetas": "Total"
            })
            st.dataframe(df_total, use_container_width=True, hide_index=True)

# =====================================
# TAB 9: TABLA DE POSICIONES
# =====================================
with tab9:
    st.markdown("## 📋 Tabla de Posiciones")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        anio_pos = st.text_input("Año", value="2024", key="tab9_anio")
        camp_pos = st.selectbox("Campeonato (opcional)", [""] + obtener_valores_unicos("campeonato"), key="tab9_campeonato")
        
        if st.button("📊 Generar Tabla", type="primary", key="tab9_btn"):
            pass
    
    with col2:
        if anio_pos:
            try:
                df_pos = obtener_tabla_posiciones(anio_pos, camp_pos or None)
                
                if df_pos.empty:
                    st.warning("No hay datos para este año/campeonato.")
                else:
                    # Mostrar info sobre sistema de puntos
                    sistema = "3 puntos por victoria" if int(anio_pos) >= 1995 else "2 puntos por victoria"
                    st.info(f"📅 Año: {anio_pos} | Sistema de puntos: {sistema}")
                    
                    # Mostrar tabla
                    st.dataframe(
                        df_pos,
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
                        height=500
                    )
            except ValueError:
                st.error("Por favor ingresa un año válido (ej: 2024)")

# =====================================
# TAB 10: INFO
# =====================================
with tab10:
    st.markdown("## ℹ️ Información de la Aplicación")
    
    st.markdown("""
    ### 🏆 Sistema de Seguimiento de Liga de Fútbol
    
    **Funcionalidades disponibles:**
    
    - 📊 **Tarjetas por Jugador**: Filtra y visualiza tarjetas amarillas y rojas
    - 🆚 **Resumen por Rival**: Ve contra qué equipos recibió tarjetas cada jugador
    - 📈 **Evolución por Equipo**: Gráfico anual de tarjetas por equipo
    - ⚖️ **Árbitro vs Equipo**: Estadísticas de enfrentamientos específicos
    - ⚽ **Goles por Jugador**: Ranking de goleadores con filtros
    - 🏆 **Goleadores por Equipo**: Top goleadores de cada equipo
    - 📊 **Rendimiento**: Estadísticas de partidos (ganados, perdidos, empatados)
    - 🔝 **Top Tarjetas**: Ranking de jugadores más amonestados/expulsados
    - 📋 **Tabla de Posiciones**: Posiciones con sistema de puntos histórico (2 o 3 puntos)
    
    ---
    
    **Base de datos:** `football_nueva.db`
    
    **Desarrollado con:** Streamlit, Python, SQLite, Pandas, Matplotlib
    """)

# =====================================
# FOOTER
# =====================================
st.markdown("---")
st.caption("🏆 Sistema de Seguimiento de Liga de Fútbol ⚽ | football_nueva.db")