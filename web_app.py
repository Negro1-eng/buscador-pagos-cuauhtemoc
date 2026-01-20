import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ===============================
# CONFIGURACIÓN STREAMLIT
# ===============================
st.set_page_config(
    page_title="Buscador de Pagos Cuauhtémoc",
    layout="wide"
)

st.title("🔎 Buscador de Pagos y Compromisos")

# ===============================
# CONEXIÓN A GOOGLE SHEETS
# ===============================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

gc = gspread.authorize(credentials)

# ID del archivo
SPREADSHEET_ID = st.secrets["spreadsheet_id"]

sh = gc.open_by_key(SPREADSHEET_ID)

ws_pagos = sh.worksheet("PAGOS")
ws_compromisos = sh.worksheet("COMPROMISOS")

# ===============================
# CARGA DE DATOS
# ===============================
df_pagos = pd.DataFrame(ws_pagos.get_all_records())
df_compromisos = pd.DataFrame(ws_compromisos.get_all_records())

# Normalizar nombres
df_pagos.columns = df_pagos.columns.str.strip().str.upper()
df_compromisos.columns = df_compromisos.columns.str.strip().str.upper()

# ===============================
# FILTROS (SESSION STATE)
# ===============================
if "filtro_beneficiario" not in st.session_state:
    st.session_state.filtro_beneficiario = ""

if "filtro_clc" not in st.session_state:
    st.session_state.filtro_clc = ""

if "filtro_ejercicio" not in st.session_state:
    st.session_state.filtro_ejercicio = "TODOS"

# ===============================
# BARRA DE BÚSQUEDA
# ===============================
col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

with col1:
    beneficiario = st.text_input(
        "Beneficiario",
        key="filtro_beneficiario"
    )

with col2:
    clc = st.text_input(
        "CLC",
        key="filtro_clc"
    )

with col3:
    ejercicios = ["TODOS"] + sorted(
        df_compromisos["EJERCICIO"].astype(str).unique().tolist()
    )
    ejercicio = st.selectbox(
        "Ejercicio",
        ejercicios,
        key="filtro_ejercicio"
    )

with col4:
    st.write("")
    st.write("")
    if st.button("🧹 Limpiar"):
        st.session_state.filtro_beneficiario = ""
        st.session_state.filtro_clc = ""
        st.session_state.filtro_ejercicio = "TODOS"
        st.rerun()

# ===============================
# CRUCE DE INFORMACIÓN
# ===============================
resultado = df_compromisos.merge(
    df_pagos,
    how="left",
    on="CLC"
)

# ===============================
# APLICAR FILTROS
# ===============================
if beneficiario:
    resultado = resultado[
        resultado["BENEFICIARIO"].str.contains(
            beneficiario, case=False, na=False
        )
    ]

if clc:
    resultado = resultado[
        resultado["CLC"].astype(str).str.contains(clc, na=False)
    ]

if ejercicio != "TODOS":
    resultado = resultado[
        resultado["EJERCICIO"].astype(str) == ejercicio
    ]

# ===============================
# COLUMNAS A MOSTRAR
# (COMPROMISOS + 3 DE PAGOS)
# ===============================
columnas_finales = [
    "BENEFICIARIO",
    "CLC",
    "EJERCICIO",
    "MONTO",
    "FECHA DE PAGO",
    "ORDEN DE PAGO",
    "COMPROBACIÓN DE PAGO"
]

# Ajustar nombres por si vienen distinto
resultado.columns = resultado.columns.str.replace("_", " ")

tabla = resultado[[c for c in columnas_finales if c in resultado.columns]].copy()

# ===============================
# RESULTADO
# ===============================
st.markdown("### 📄 Resultados")

st.dataframe(
    tabla,
    use_container_width=True,
    hide_index=True
)

st.caption(f"Registros encontrados: {len(tabla)}")











