import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from io import BytesIO

# ================= CONFIG =================
st.set_page_config(
    page_title="Buscador de Pagos y Consumo de Contratos",
    layout="wide"
)

# ================= IDS =================
IDS_SHEETS = {
    "2025": "14D-Q2oyPZ1u8VbDgq5QorhUKPzz9pjtZQyRxwys5nmA",
    "2026": "1Dr6IlKOECZ-rgeXQ-4hfEgFEr1lucFc-6BuljR_S9r4"
}

# 🔥 CARPETAS DRIVE
FOLDER_FACTURAS = "1VNOrMmdZWalCykgRZSgsHNYlDFU6w6sP"
FOLDER_PAGOS = "1E-MRmWlPBHzDRTHq89XgKFpHp_kRHcMI"

# ================= HEADER =================
st.title("Buscador de Pagos y Consumo de Contratos")

# ================= SELECTOR =================
año = st.selectbox("Año", ["2025", "2026"])

# ================= GOOGLE SHEETS =================
@st.cache_data
def cargar_datos(año):

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    sh = client.open_by_key(IDS_SHEETS[año])

    df_pagos = pd.DataFrame(sh.worksheet("PAGOS").get_all_records())
    df_comp = pd.DataFrame(sh.worksheet("COMPROMISOS").get_all_records())

    df_pagos.columns = df_pagos.columns.str.strip().str.upper()
    df_comp.columns = df_comp.columns.str.strip().str.upper()

    return df_pagos, df_comp

df, df_comp = cargar_datos(año)

# ================= DRIVE =================
@st.cache_data
def obtener_pdfs_drive():

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    service = build("drive", "v3", credentials=creds)

    def listar(folder_id):
        resultados = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/pdf'",
            fields="files(id, name)"
        ).execute()
        return resultados.get("files", [])

    return listar(FOLDER_FACTURAS), listar(FOLDER_PAGOS)

# 🔥 SOLO CARGA DRIVE SI ES 2026
if año == "2026":
    facturas_drive, pagos_drive = obtener_pdfs_drive()

# ================= FUNCIONES =================
def formato_pesos(x):
    try:
        return f"$ {float(x):,.2f}"
    except:
        return "$ 0.00"

def generar_link(valor, archivos):
    if pd.isna(valor):
        return ""
    valor = str(valor)

    for archivo in archivos:
        if valor in archivo["name"]:
            return f"https://drive.google.com/file/d/{archivo['id']}/view"
    return ""

def crear_link_html(url, texto):
    if url:
        return f'<a href="{url}" target="_blank">{texto}</a>'
    return ""

def convertir_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ================= FILTROS =================
st.subheader("Filtros")

beneficiario = st.selectbox(
    "Beneficiario",
    [""] + sorted(df["BENEFICIARIO"].dropna().astype(str).unique())
)

clc = st.text_input("CLC")
contrato = st.text_input("Contrato")
factura = st.text_input("Factura")

# ================= FILTRADO =================
resultado = df.copy()

for col, val in {
    "BENEFICIARIO": beneficiario,
    "CLC": clc,
    "NUM_CONTRATO": contrato,
    "FACTURA": factura
}.items():
    if val:
        resultado = resultado[
            resultado[col].astype(str).str.contains(val, case=False, na=False)
        ]

# ================= LINKS DRIVE =================
if año == "2026":

    resultado["LINK_FACTURA"] = resultado["FACTURA"].apply(
        lambda x: generar_link(x, facturas_drive)
    )

    resultado["LINK_PAGO"] = resultado["CLC"].apply(
        lambda x: generar_link(x, pagos_drive)
    )

# ================= TABLA =================
st.subheader("Resultados")

columnas = [
    "BENEFICIARIO",
    "NUM_CONTRATO",
    "CLC",
    "IMPORTE",
    "FACTURA",
    "FECHA_PAGO"
]

tabla = resultado[[c for c in columnas if c in resultado.columns]].copy()

# FORMATO FECHA
if "FECHA_PAGO" in tabla.columns:
    tabla["FECHA_PAGO"] = pd.to_datetime(
        tabla["FECHA_PAGO"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")

# TOTAL
total = pd.to_numeric(tabla["IMPORTE"], errors="coerce").sum()

tabla["IMPORTE"] = tabla["IMPORTE"].apply(formato_pesos)

# 🔥 AGREGAR LINKS VISUALES
if año == "2026":

    tabla["📄 FACTURA"] = resultado["LINK_FACTURA"].apply(
        lambda x: crear_link_html(x, "Ver PDF")
    )

    tabla["💰 PAGO"] = resultado["LINK_PAGO"].apply(
        lambda x: crear_link_html(x, "Ver PDF")
    )

# ================= MOSTRAR =================
st.metric("Total", formato_pesos(total))

st.write(
    tabla.to_html(escape=False, index=False),
    unsafe_allow_html=True
)

# ================= DESCARGA =================
st.download_button(
    "Descargar Excel",
    convertir_excel(tabla),
    file_name=f"pagos_{año}.xlsx"
)








