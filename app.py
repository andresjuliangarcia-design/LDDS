import streamlit as st
import os

st.title("✅ Prueba de conexión")

# Verificar archivos en el directorio
archivos = os.listdir('.')
st.write("Archivos en el servidor:")
for archivo in archivos:
    st.write(f"📄 {archivo}")

# Verificar si existe la DB
if os.path.exists("football_nueva.db"):
    st.success("✅ ¡Base de datos encontrada!")
    st.write(f"Tamaño: {os.path.getsize('football_nueva.db')} bytes")
else:
    st.error("❌ ¡Base de datos NO encontrada!")
    st.info("Sube el archivo football_nueva.db a la raíz del repositorio")