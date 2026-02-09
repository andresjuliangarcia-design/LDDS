import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

# =====================================
# CONFIGURACIÓN INICIAL
# =====================================
DB = "football_nueva.db"

st.set_page_config(
    page_title="🏆 Seguimiento Liga de Fútbol",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# =====================================
# FUNCIONES DE BASE DE DATOS
# =====================================
@st.cache_data(ttl=300)
def obtener_valores_unicos(columna, tabla="partidos"):
    """Obtiene valores únicos de una columna."""
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
    except Exception as e:
        st.error(f"Error al obtener valores: {e}")
        return []

@st.cache_data(ttl=300)
def obtener_equipos():
    """Obtiene lista de equipos (locales y visitantes)."""
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
        return equipos
    except Exception as e:
        st.error(f"Error al obtener equipos: {e}")
        return []

@st.cache_data(ttl=300)
def obtener_jugadores():
    """Obtiene lista de jugadores con tarjetas."""
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
        return jugadores
    except Exception as e:
        st.error(f"Error al obtener jugadores: {e}")
        return []

# =====================================
# SIDEBAR: FILTROS PRINCIPALES
# =====================================
st.sidebar.title("FilterWhere ⚽")

# Filtros globales
st.sidebar.markdown("### 🔍 Filtros Generales")
anio = st.sidebar.text_input("Año", placeholder="Ej: 2024", help="Filtrar por año del partido")
campeonato = st.sidebar.selectbox(
    "Campeonato",
    [""] + obtener_valores_unicos("campeonato"),
    format_func=lambda x: "Todos" if x == "" else x
)
equipo_filtro = st.sidebar.selectbox(
    "Equipo",
    [""] + obtener_equipos(),
    format_func=lambda x: "Todos" if x == "" else x
)
solo_expulsados = st.sidebar.checkbox("✅ Solo jugadores expulsados", value=False)

st.sidebar.markdown("---")
st.sidebar.info("💡 Los filtros se aplican en la pestaña 'Tarjetas por Jugador'")

# =====================================
# PESTAÑAS PRINCIPALES
# =====================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Tarjetas por Jugador",
    "📈 Evolución por Equipo",
    "🆚 Resumen por Rival",
    "📋 Consulta por Equipo",
    "⚖️ Árbitro vs Equipo"
])

# =====================================
# PESTAÑA 1: TARJETAS POR JUGADOR
# =====================================
with tab1:
    st.markdown('<div class="main-header">Tarjetas por Jugador</div>', unsafe_allow_html=True)
    
    # Consulta principal
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
        df_jugadores = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df_jugadores.empty:
            st.warning("⚠️ No se encontraron datos con los filtros aplicados.")
        else:
            # Métricas resumen
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Jugadores", len(df_jugadores))
            with col2:
                st.metric("⚠️ Amonestados", int(df_jugadores['amon'].sum()))
            with col3:
                st.metric("🔴 Expulsados", int(df_jugadores['exp'].sum()))
            with col4:
                st.metric("📊 Total Tarjetas", int((df_jugadores['amon'] + df_jugadores['exp']).sum()))
            
            st.markdown("---")
            
            # Formatear y mostrar tabla
            df_jugadores["Total"] = df_jugadores["amon"] + df_jugadores["exp"]
            df_display = df_jugadores.rename(columns={
                "jugador": "Jugador",
                "equipo_jugador": "Equipo",
                "amon": "Amonestaciones",
                "exp": "Expulsiones"
            })
            
            st.dataframe(
                df_display[["Jugador", "Equipo", "Amonestaciones", "Expulsiones", "Total"]],
                column_config={
                    "Amonestaciones": st.column_config.NumberColumn("⚠️ Amonestaciones", width="small", format="%d"),
                    "Expulsiones": st.column_config.NumberColumn("🔴 Expulsiones", width="small", format="%d"),
                    "Total": st.column_config.NumberColumn("📊 Total", width="small", format="%d"),
                },
                hide_index=True,
                use_container_width=True,
                height=450
            )
            
            # Gráfico de barras - Top 10
            st.markdown("### 📊 Top 10 Jugadores con más tarjetas")
            
            top10 = df_display.head(10)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            x = range(len(top10))
            width = 0.35
            
            bars1 = ax.bar([i - width/2 for i in x], top10["Amonestaciones"], 
                          width, label="Amonestaciones", color="#FFC107", alpha=0.8)
            bars2 = ax.bar([i + width/2 for i in x], top10["Expulsiones"], 
                          width, label="Expulsiones", color="#F44336", alpha=0.8)
            
            # Añadir valores en las barras
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{int(height)}',
                               ha='center', va='bottom', fontsize=9)
            
            ax.set_xlabel("Jugador", fontsize=11, fontweight='bold')
            ax.set_ylabel("Cantidad", fontsize=11, fontweight='bold')
            ax.set_title("Top 10 - Distribución de Tarjetas", fontsize=13, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(top10["Jugador"], rotation=45, ha='right', fontsize=10)
            ax.legend(fontsize=10)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)
            
            plt.tight_layout()
            st.pyplot(fig)
            
    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {e}")

# =====================================
# PESTAÑA 2: EVOLUCIÓN POR EQUIPO
# =====================================
with tab2:
    st.markdown('<div class="main-header">Evolución Anual de Tarjetas por Equipo</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### 🎯 Seleccione Equipo")
        equipo_grafico = st.selectbox(
            "Equipo",
            obtener_equipos(),
            key="equipo_grafico"
        )
        
        if st.button("📊 Generar Gráfico", type="primary", use_container_width=True):
            pass
    
    with col2:
        if equipo_grafico:
            try:
                conn = sqlite3.connect(DB)
                cur = conn.cursor()
                cur.execute("""
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
                """, (equipo_grafico, equipo_grafico))
                
                filas = cur.fetchall()
                conn.close()
                
                if filas:
                    df = pd.DataFrame(filas, columns=["Año", "Amonestaciones", "Expulsiones"])
                    
                    # Métricas
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Años Registrados", len(df))
                    with col_b:
                        st.metric("⚠️ Total Amonestaciones", int(df["Amonestaciones"].sum()))
                    with col_c:
                        st.metric("🔴 Total Expulsiones", int(df["Expulsiones"].sum()))
                    
                    st.markdown("---")
                    
                    # Gráfico de líneas
                    fig, ax = plt.subplots(figsize=(12, 6))
                    
                    ax.plot(df["Año"], df["Amonestaciones"], 
                           marker="o", linewidth=3, markersize=8,
                           label="Amonestaciones", color="#FFC107", alpha=0.9)
                    ax.plot(df["Año"], df["Expulsiones"], 
                           marker="s", linewidth=3, markersize=8,
                           label="Expulsiones", color="#F44336", alpha=0.9)
                    
                    # Añadir valores en los puntos
                    for i, row in df.iterrows():
                        ax.annotate(f'{int(row["Amonestaciones"])}', 
                                  (row["Año"], row["Amonestaciones"]),
                                  textcoords="offset points", xytext=(0,10), 
                                  ha='center', fontsize=9, color='#FFC107')
                        ax.annotate(f'{int(row["Expulsiones"])}', 
                                  (row["Año"], row["Expulsiones"]),
                                  textcoords="offset points", xytext=(0,10), 
                                  ha='center', fontsize=9, color='#F44336')
                    
                    ax.set_xlabel("Año", fontsize=12, fontweight='bold')
                    ax.set_ylabel("Cantidad", fontsize=12, fontweight='bold')
                    ax.set_title(f"Evolución de tarjetas - {equipo_grafico}", 
                               fontsize=14, fontweight='bold', pad=20)
                    ax.grid(True, alpha=0.3, linestyle='--')
                    ax.legend(fontsize=11, loc='upper left')
                    ax.set_xticks(df["Año"])
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Tabla de datos
                    st.markdown("### 📋 Datos Detallados")
                    st.dataframe(
                        df.style.highlight_max(axis=0, props='font-weight: bold; color: #1E88E5;'),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("ℹ️ No hay datos disponibles para este equipo.")
                    
            except Exception as e:
                st.error(f"❌ Error al generar gráfico: {e}")

# =====================================
# PESTAÑA 3: RESUMEN POR RIVAL
# =====================================
with tab3:
    st.markdown('<div class="main-header">Resumen de Tarjetas por Rival</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### 🎯 Seleccione Jugador")
        jugador = st.selectbox(
            "Jugador",
            obtener_jugadores(),
            key="jugador_rival"
        )
        
        if st.button("🔍 Consultar", type="primary", use_container_width=True):
            pass
    
    with col2:
        if jugador:
            try:
                conn = sqlite3.connect(DB)
                
                # Obtener equipo del jugador
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
                equipo_jugador = resultado[0] if resultado else "Desconocido"
                
                # Obtener resumen por rival
                query_rival = """
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
                
                df_rivales = pd.read_sql_query(query_rival, conn, params=(jugador,))
                conn.close()
                
                if df_rivales.empty:
                    st.warning(f"⚠️ No se encontraron tarjetas para {jugador}")
                else:
                    st.markdown(f"### 👤 {jugador}")
                    st.markdown(f"**Equipo:** {equipo_jugador}")
                    
                    st.markdown("---")
                    
                    # Métricas
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("Rivales", len(df_rivales))
                    with col_b:
                        st.metric("⚠️ Amonestaciones", int(df_rivales['amon'].sum()))
                    with col_c:
                        st.metric("🔴 Expulsiones", int(df_rivales['exp'].sum()))
                    with col_d:
                        st.metric("📊 Total", int(df_rivales['total_tarjetas'].sum()))
                    
                    st.markdown("---")
                    
                    # Tabla
                    df_rivales = df_rivales.rename(columns={
                        "rival": "Rival",
                        "amon": "Amonestaciones",
                        "exp": "Expulsiones",
                        "total_tarjetas": "Total"
                    })
                    
                    st.dataframe(
                        df_rivales[["Rival", "Amonestaciones", "Expulsiones", "Total"]],
                        column_config={
                            "Amonestaciones": st.column_config.NumberColumn("⚠️ Amonestaciones", width="small", format="%d"),
                            "Expulsiones": st.column_config.NumberColumn("🔴 Expulsiones", width="small", format="%d"),
                            "Total": st.column_config.NumberColumn("📊 Total", width="small", format="%d"),
                        },
                        hide_index=True,
                        use_container_width=True,
                        height=400
                    )
                    
                    # Gráfico de barras
                    if len(df_rivales) > 0:
                        st.markdown("### 📊 Distribución por Rival")
                        
                        fig, ax = plt.subplots(figsize=(12, 6))
                        
                        x = range(len(df_rivales))
                        width = 0.35
                        
                        ax.bar([i - width/2 for i in x], df_rivales["Amonestaciones"], 
                              width, label="Amonestaciones", color="#FFC107", alpha=0.8)
                        ax.bar([i + width/2 for i in x], df_rivales["Expulsiones"], 
                              width, label="Expulsiones", color="#F44336", alpha=0.8)
                        
                        ax.set_xlabel("Rival", fontsize=11, fontweight='bold')
                        ax.set_ylabel("Cantidad", fontsize=11, fontweight='bold')
                        ax.set_title(f"Tarjetas de {jugador} por Rival", fontsize=13, fontweight='bold')
                        ax.set_xticks(x)
                        ax.set_xticklabels(df_rivales["Rival"], rotation=45, ha='right', fontsize=10)
                        ax.legend(fontsize=10)
                        ax.grid(axis='y', alpha=0.3, linestyle='--')
                        ax.set_axisbelow(True)
                        
                        plt.tight_layout()
                        st.pyplot(fig)
                        
            except Exception as e:
                st.error(f"❌ Error en consulta: {e}")

# =====================================
# PESTAÑA 4: CONSULTA POR EQUIPO
# =====================================
with tab4:
    st.markdown('<div class="main-header">Consulta Histórica de Tarjetas por Equipo</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🎯 Seleccione Equipo")
        equipo_consulta = st.selectbox(
            "Equipo",
            obtener_equipos(),
            key="equipo_consulta"
        )
        
        if st.button("🔍 Consultar", type="primary", use_container_width=True):
            pass
    
    with col2:
        if equipo_consulta:
            try:
                conn = sqlite3.connect(DB)
                cur = conn.cursor()
                cur.execute("""
                    SELECT
                        SUM(CASE WHEN t.tipo = 'Amonestado' THEN 1 ELSE 0 END) AS amon,
                        SUM(CASE WHEN t.tipo = 'Expulsado' THEN 1 ELSE 0 END) AS exp
                    FROM partidos p
                    JOIN tarjetas t ON t.partido_id = p.id
                    WHERE p.arbitro IS NOT NULL
                      AND p.arbitro <> ''
                      AND (p.equipo_local = ? OR p.equipo_visitante = ?)
                """, (equipo_consulta, equipo_consulta))
                
                amon, exp = cur.fetchone()
                conn.close()
                
                amon = amon or 0
                exp = exp or 0
                total = amon + exp
                
                # Tarjetas métricas grandes
                st.markdown(f"### 📊 Resumen para {equipo_consulta}")
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric(label="⚽ Partidos con Árbitro", value="N/A")
                with col_b:
                    st.metric(label="⚠️ Amonestaciones", value=amon)
                with col_c:
                    st.metric(label="🔴 Expulsiones", value=exp)
                
                st.metric(label="📊 Total Tarjetas", value=total)
                
                st.markdown("---")
                
                # Gráfico circular
                if total > 0:
                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
                    
                    # Gráfico circular
                    labels = ['Amonestaciones', 'Expulsiones']
                    sizes = [amon, exp]
                    colors = ['#FFC107', '#F44336']
                    explode = (0.05, 0)
                    
                    ax1.pie(sizes, explode=explode, labels=labels, colors=colors,
                           autopct='%1.1f%%', startangle=90, shadow=True,
                           textprops={'fontsize': 11, 'fontweight': 'bold'})
                    ax1.set_title(f"Distribución de Tarjetas", fontsize=13, fontweight='bold')
                    
                    # Gráfico de barras simple
                    bars = ax2.bar(labels, sizes, color=colors, alpha=0.8)
                    ax2.set_ylabel("Cantidad", fontsize=11, fontweight='bold')
                    ax2.set_title(f"Cantidad por Tipo", fontsize=13, fontweight='bold')
                    ax2.grid(axis='y', alpha=0.3, linestyle='--')
                    ax2.set_axisbelow(True)
                    
                    # Añadir valores en las barras
                    for bar in bars:
                        height = bar.get_height()
                        ax2.text(bar.get_x() + bar.get_width()/2., height,
                                f'{int(height)}',
                                ha='center', va='bottom', fontsize=11, fontweight='bold')
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Texto explicativo
                    st.markdown(f"""
                    **Resumen:**
                    - El equipo **{equipo_consulta}** ha recibido un total de **{total}** tarjetas
                    - **{amon}** tarjetas amarillas (amonestaciones)
                    - **{exp}** tarjetas rojas (expulsiones)
                    """)
                else:
                    st.info(f"ℹ️ El equipo {equipo_consulta} no tiene tarjetas registradas.")
                    
            except Exception as e:
                st.error(f"❌ Error en consulta: {e}")

# =====================================
# PESTAÑA 5: ÁRBITRO VS EQUIPO
# =====================================
with tab5:
    st.markdown('<div class="main-header">Árbitro vs Equipo</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🔍 Parámetros de Consulta")
        
        arbitro = st.selectbox(
            "Árbitro",
            obtener_valores_unicos("arbitro"),
            key="arbitro_select"
        )
        
        equipo_arb = st.selectbox(
            "Equipo",
            obtener_equipos(),
            key="equipo_arb"
        )
        
        anio_arb = st.text_input("Año (opcional)", placeholder="Ej: 2024", key="anio_arb")
        campeonato_arb = st.selectbox(
            "Campeonato (opcional)",
            [""] + obtener_valores_unicos("campeonato"),
            format_func=lambda x: "Todos" if x == "" else x,
            key="campeonato_arb"
        )
        
        if st.button("🔍 Consultar", type="primary", use_container_width=True):
            pass
    
    with col2:
        if arbitro and equipo_arb:
            try:
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
                params = [arbitro, equipo_arb, equipo_arb]
                
                if anio_arb:
                    query += " AND SUBSTR(p.fecha,7,4) = ?"
                    params.append(anio_arb)
                if campeonato_arb:
                    query += " AND p.campeonato = ?"
                    params.append(campeonato_arb)
                
                conn = sqlite3.connect(DB)
                cur = conn.cursor()
                cur.execute(query, params)
                partidos, amon, exp = cur.fetchone()
                conn.close()
                
                partidos = partidos or 0
                amon = amon or 0
                exp = exp or 0
                
                st.markdown(f"### 📊 Resultados: {arbitro} vs {equipo_arb}")
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric(label="⚽ Partidos", value=partidos)
                with col_b:
                    st.metric(label="⚠️ Amonestados", value=amon)
                with col_c:
                    st.metric(label="🔴 Expulsados", value=exp)
                
                # Gráfico de barras
                if partidos > 0:
                    st.markdown("---")
                    
                    fig, ax = plt.subplots(figsize=(8, 5))
                    
                    categorias = ['Amonestados', 'Expulsados']
                    valores = [amon, exp]
                    colores = ['#FFC107', '#F44336']
                    
                    bars = ax.bar(categorias, valores, color=colores, alpha=0.8)
                    ax.set_ylabel("Cantidad", fontsize=11, fontweight='bold')
                    ax.set_title(f"Tarjetas mostradas por {arbitro} a {equipo_arb}", 
                               fontsize=12, fontweight='bold')
                    ax.grid(axis='y', alpha=0.3, linestyle='--')
                    ax.set_axisbelow(True)
                    
                    # Añadir valores
                    for bar in bars:
                        height = bar.get_height()
                        if height > 0:
                            ax.text(bar.get_x() + bar.get_width()/2., height,
                                   f'{int(height)}',
                                   ha='center', va='bottom', fontsize=11, fontweight='bold')
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                
                # Texto detallado
                st.markdown("---")
                st.markdown(f"""
                **Resumen detallado:**
                - El árbitro **{arbitro}** ha dirigido **{partidos}** partidos a **{equipo_arb}**
                - Ha mostrado **{amon}** tarjetas amarillas (amonestaciones)
                - Ha mostrado **{exp}** tarjetas rojas (expulsiones)
                - **Total de tarjetas:** {amon + exp}
                - **Promedio por partido:** {((amon + exp) / partidos):.2f} tarjetas
                """ if partidos > 0 else f"""
                **Resumen:**
                - El árbitro **{arbitro}** no ha dirigido partidos a **{equipo_arb}** con los filtros aplicados.
                """)
                
            except Exception as e:
                st.error(f"❌ Error en consulta: {e}")

# =====================================
# FOOTER
# =====================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    🏆 Sistema de Seguimiento de Liga de Fútbol | Base de datos: football_nueva.db
</div>
""", unsafe_allow_html=True)