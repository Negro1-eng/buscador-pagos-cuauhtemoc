import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# ================= CONFIGURACIÓN =================
st.set_page_config(
    page_title="Buscador de Pagos y Consumo de Contratos",
    layout="wide"
)

st.title(" Buscador de Pagos y Consumo de Contratos")

# ================= ESTADO =================
for key in ["beneficiario", "clc", "contrato", "factura"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# ================= GOOGLE SHEETS =================
ID_SHEET = "1RKjYKBPcvbxul2WgRi72DpOBwB0XZwQcFyAY9o6ldOo"

# ================= CARGA DE DATOS =================
@st.cache_data
def cargar_datos():

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    sh = client.open_by_key(ID_SHEET)

    ws_pagos = sh.worksheet("PAGOS")
    ws_comp = sh.worksheet("COMPROMISOS")

    df_pagos = pd.DataFrame(ws_pagos.get_all_records())
    df_comp = pd.DataFrame(ws_comp.get_all_records())

    df_pagos.columns = df_pagos.columns.str.strip()
    df_comp.columns = df_comp.columns.str.strip()

    return df_pagos, df_comp


df, df_comp = cargar_datos()

# ================= LISTAS =================
def col_segura(df, nombre):
    return nombre if nombre in df.columns else None

lista_beneficiarios = (
    sorted(df["BENEFICIARIO"].dropna().astype(str).unique())
    if "BENEFICIARIO" in df.columns else []
)

lista_contratos = (
    sorted(df["NUM_CONTRATO"].dropna().astype(str).unique())
    if "NUM_CONTRATO" in df.columns else []
)

# ================= FUNCIONES =================
def formato_pesos(valor):
    try:
        return f"$ {float(valor):,.2f}"
    except:
        return "$ 0.00"


def calcular_consumo(contrato):
    if not contrato:
        return 0, 0, 0

    monto_contrato = df_comp[
        df_comp["Texto cab.documento"].astype(str) == contrato
    ]["Importe total (LC)"].sum()

    monto_ejercido = (
        df[df["NUM_CONTRATO"].astype(str) == contrato]["importe"].sum()
        if "importe" in df.columns else 0
    )

    return monto_contrato, monto_ejercido, monto_contrato - monto_ejercido


def convertir_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False)
    return output.getvalue()

# ================= FILTROS =================
st.subheader("Filtros")

c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])

with c1:
    st.session_state.beneficiario = st.selectbox(
        "Beneficiario",
        [""] + lista_beneficiarios,
        index=([""] + lista_beneficiarios).index(st.session_state.beneficiario)
        if st.session_state.beneficiario in lista_beneficiarios else 0
    )

with c2:
    st.session_state.clc = st.text_input("CLC", st.session_state.clc)

with c3:
    st.session_state.contrato = st.selectbox(
        "Num. Contrato",
        [""] + lista_contratos,
        index=([""] + lista_contratos).index(st.session_state.contrato)
        if st.session_state.contrato in lista_contratos else 0
    )

with c4:
    st.session_state.factura = st.text_input("Factura", st.session_state.factura)

with c5:
    if st.button("Limpiar Busquedas"):
        for k in ["beneficiario", "clc", "contrato", "factura"]:
            st.session_state[k] = ""
        st.rerun()

# ================= FILTRADO =================
resultado = df.copy()

filtros = {
    "BENEFICIARIO": st.session_state.beneficiario,
    "CLC": st.session_state.clc,
    "NUM_CONTRATO": st.session_state.contrato,
    "FACTURA": st.session_state.factura
}

for col, val in filtros.items():
    if val and col in resultado.columns:
        resultado = resultado[
            resultado[col].astype(str).str.contains(val, case=False, na=False)
        ]

# ================= CONSUMO =================
st.subheader("Consumo del contrato")

contrato_sel = st.session_state.contrato
if not contrato_sel and "NUM_CONTRATO" in resultado.columns and len(resultado) == 1:
    contrato_sel = resultado.iloc[0]["NUM_CONTRATO"]

m1, m2, m3 = calcular_consumo(contrato_sel)

a, b, c = st.columns(3)
a.metric("Monto del contrato", formato_pesos(m1))
b.metric("Monto ejercido", formato_pesos(m2))
c.metric("Monto pendiente", formato_pesos(m3))

# ================= TABLA =================
st.subheader(" Tabla de Resultados")

columnas = [
    "BENEFICIARIO",
    "NUM_CONTRATO",
    "OFICIO_SOLICITUD",
    "CLC",
    "importe",
    "FACTURA",
    "Fecha de pago"
]

tabla = resultado[[c for c in columnas if c in resultado.columns]].copy()

if "importe" in tabla.columns:
    tabla["importe"] = tabla["importe"].apply(formato_pesos)

st.dataframe(tabla, use_container_width=True, height=420)

# ================= EXPORTAR =================
st.divider()
st.download_button(
    "Descargar resultados en Excel",
    convertir_excel(tabla),
    file_name="resultados_pagos.xlsx"
)








