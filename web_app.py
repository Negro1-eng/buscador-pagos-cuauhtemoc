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

st.title("🔎 Buscador de Pagos y Consumo de Contratos")

# ================= GOOGLE SHEETS =================
ID_SHEET_PAGOS = "1RKjYKBPcvbxul2WgRi72DpOBwB0XZwQcFyAY9o6ldOo"
ID_SHEET_COMP = "1RKjYKBPcvbxul2WgRi72DpOBwB0XZwQcFyAY9o6ldOo"

# ================= CARGA DE DATOS =================
@st.cache_data
def cargar_datos():

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)

    ws_pagos = client.open_by_key(ID_SHEET_PAGOS).sheet1
    ws_comp = client.open_by_key(ID_SHEET_COMP).sheet1

    df_pagos = pd.DataFrame(ws_pagos.get_all_records())
    df_comp = pd.DataFrame(ws_comp.get_all_records())

    df_pagos.columns = df_pagos.columns.str.strip()
    df_comp.columns = df_comp.columns.str.strip()

    for col in ["NUM_CONTRATO", "OFICIO_SOLICITUD", "FACTURA"]:
        if col not in df_pagos.columns:
            df_pagos[col] = ""

    return df_pagos, df_comp


df, df_comp = cargar_datos()

st.write("Columnas detectadas:")
st.write(list(df.columns))

# ================= LISTAS =================
lista_contratos = sorted(df["NUM_CONTRATO"].dropna().astype(str).unique().tolist())
lista_beneficiarios = sorted(df["BENEFICIARIO"].dropna().astype(str).unique().tolist())

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

    monto_ejercido = df[
        df["NUM_CONTRATO"].astype(str) == contrato
    ]["importe"].sum()

    return monto_contrato, monto_ejercido, monto_contrato - monto_ejercido

def convertir_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False)
    return output.getvalue()

# ================= FILTROS =================
st.subheader("🎯 Filtros de búsqueda")

c1, c2, c3, c4 = st.columns(4)

with c1:
    beneficiario = st.selectbox("Beneficiario", [""] + lista_beneficiarios)

with c2:
    clc = st.text_input("CLC")

with c3:
    contrato = st.selectbox("Num. Contrato", [""] + lista_contratos)

with c4:
    factura = st.text_input("Factura")

resultado = df.copy()

filtros = {
    "BENEFICIARIO": beneficiario,
    "CLC": clc,
    "NUM_CONTRATO": contrato,
    "FACTURA": factura
}

for col, val in filtros.items():
    if val:
        resultado = resultado[
            resultado[col].astype(str).str.contains(val, case=False, na=False)
        ]

# ================= CONSUMO AUTOMÁTICO =================
st.subheader("💰 Consumo del contrato")

contrato_seleccionado = contrato

if not contrato_seleccionado and len(resultado) == 1:
    contrato_seleccionado = resultado.iloc[0]["NUM_CONTRATO"]

m1, m2, m3 = calcular_consumo(contrato_seleccionado)

a, b, c = st.columns(3)
a.metric("Monto del contrato", formato_pesos(m1))
b.metric("Monto ejercido", formato_pesos(m2))
c.metric("Monto pendiente", formato_pesos(m3))

# ================= TABLA =================
st.subheader("📋 Resultados")

tabla = resultado[[
    "BENEFICIARIO",
    "NUM_CONTRATO",
    "OFICIO_SOLICITUD",
    "CLC",
    "importe",
    "FACTURA",
    "Fecha de pago"
]].copy()

tabla["importe"] = tabla["importe"].apply(formato_pesos)

st.dataframe(tabla, use_container_width=True, height=420)

# ================= EXPORTAR =================
st.divider()
st.download_button(
    "📥 Descargar resultados en Excel",
    convertir_excel(tabla),
    file_name="resultados_pagos.xlsx"
)




