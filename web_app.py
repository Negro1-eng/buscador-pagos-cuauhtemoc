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

# ================= ENCABEZADO =================
c1, c2, c3 = st.columns([1, 6, 1], vertical_alignment="center")

with c1:
    st.image("LOGO CDMX.jpg", width=110)

with c2:
    st.markdown(
        """
        <div style="text-align:center">
            <h2 style="margin-bottom:0">Alcaldía Cuauhtémoc</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

with c3:
    st.image("LOGO CUAUHTEMOC.png", width=110)

st.title("Buscador de Pagos y Consumo de Contratos")

# ================= IDS POR AÑO =================
IDS_SHEETS = {
    "2025": "14D-Q2oyPZ1u8VbDgq5QorhUKPzz9pjtZQyRxwys5nmA",
    "2026": "1Dr6IlKOECZ-rgeXQ-4hfEgFEr1lucFc-6BuljR_S9r4"
}

# ================= SELECTOR DE AÑO =================
st.subheader("Seleccionar Año")
año = st.selectbox("Año de consulta", ["2025", "2026"])

# ================= LIMPIAR FILTROS =================
if "año_anterior" not in st.session_state:
    st.session_state.año_anterior = año

if st.session_state.año_anterior != año:
    for k in ["beneficiario", "clc", "contrato", "factura"]:
        st.session_state[k] = ""
    st.session_state.año_anterior = año
    st.rerun()

# ================= ACTUALIZAR DATOS =================
col1, _ = st.columns([1, 6])

with col1:
    if st.button("Actualizar datos"):
        st.cache_data.clear()
        st.success("Datos actualizados desde Google Sheets")
        st.rerun()

# ================= ESTADO =================
for key in ["beneficiario", "clc", "contrato", "factura"]:
    st.session_state.setdefault(key, "")

# ================= GOOGLE SHEETS =================
@st.cache_data
def cargar_datos(año):

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    sheet_id = IDS_SHEETS[año]
    sh = client.open_by_key(sheet_id)

    df_pagos = pd.DataFrame(sh.worksheet("PAGOS").get_all_records())
    df_comp = pd.DataFrame(sh.worksheet("COMPROMISOS").get_all_records())

    df_pagos.columns = df_pagos.columns.str.strip().str.upper()
    df_comp.columns = df_comp.columns.str.strip().str.upper()

    return df_pagos, df_comp


df, df_comp = cargar_datos(año)

# ================= FUNCIONES =================
def formato_pesos(valor):
    try:
        return f"$ {float(valor):,.2f}"
    except:
        return "$ 0.00"


def crear_link(url, texto="Ver PDF"):
    if pd.notna(url) and str(url).startswith("http"):
        return f'<a href="{url}" target="_blank">{texto}</a>'
    return ""


def calcular_consumo(contrato):

    if not contrato:
        return 0, 0, 0

    monto_contrato = (
        df_comp[df_comp["TEXTO CAB.DOCUMENTO"].astype(str) == str(contrato)]
        ["IMPORTE TOTAL (LC)"]
        .apply(pd.to_numeric, errors="coerce")
        .sum()
    )

    monto_ejercido = (
        df[df["NUM_CONTRATO"].astype(str) == str(contrato)]
        ["IMPORTE"]
        .apply(pd.to_numeric, errors="coerce")
        .sum()
    )

    return monto_contrato, monto_ejercido, monto_contrato - monto_ejercido


def convertir_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ================= FILTROS =================
st.subheader("Filtros")

lista_beneficiarios = sorted(df["BENEFICIARIO"].dropna().astype(str).unique())

c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])

with c1:
    st.session_state.beneficiario = st.selectbox(
        "Beneficiario",
        [""] + lista_beneficiarios
    )

if st.session_state.beneficiario:
    contratos_filtrados = (
        df[df["BENEFICIARIO"] == st.session_state.beneficiario]["NUM_CONTRATO"]
        .dropna().astype(str).unique().tolist()
    )
else:
    contratos_filtrados = df["NUM_CONTRATO"].dropna().astype(str).unique().tolist()

with c2:
    st.session_state.clc = st.text_input("CLC")

with c3:
    st.session_state.contrato = st.selectbox(
        "Num. Contrato",
        [""] + sorted(contratos_filtrados)
    )

with c4:
    st.session_state.factura = st.text_input("Factura")

with c5:
    if st.button("Limpiar"):
        for k in ["beneficiario", "clc", "contrato", "factura"]:
            st.session_state[k] = ""
        st.rerun()

# ================= FILTRADO =================
resultado = df.copy()

for col, val in {
    "BENEFICIARIO": st.session_state.beneficiario,
    "CLC": st.session_state.clc,
    "NUM_CONTRATO": st.session_state.contrato,
    "FACTURA": st.session_state.factura
}.items():
    if val:
        resultado = resultado[
            resultado[col].astype(str).str.contains(val, case=False, na=False)
        ]

# ================= AGREGAR LINKS SOLO 2026 =================
if año == "2026":

    if "PDF_FACTURA" in resultado.columns:
        resultado["FACTURA_LINK"] = resultado["PDF_FACTURA"].apply(
            lambda x: crear_link(x, "Factura")
        )

    if "PDF_PAGO" in resultado.columns:
        resultado["PAGO_LINK"] = resultado["PDF_PAGO"].apply(
            lambda x: crear_link(x, "Pago")
        )

# ================= TABLA =================
st.subheader("Tabla de Resultados")

columnas = [
    "BENEFICIARIO",
    "NUM_CONTRATO",
    "CLC",
    "IMPORTE",
    "FACTURA",
    "FECHA_PAGO"
]

if año == "2026":
    columnas += ["FACTURA_LINK", "PAGO_LINK"]

tabla = resultado[[c for c in columnas if c in resultado.columns]].copy()

if "IMPORTE" in tabla.columns:
    total_importe = pd.to_numeric(tabla["IMPORTE"], errors="coerce").sum()
    tabla["IMPORTE"] = tabla["IMPORTE"].apply(formato_pesos)
else:
    total_importe = 0

# MOSTRAR HTML (para que funcionen links)
st.write(
    tabla.to_html(escape=False, index=False),
    unsafe_allow_html=True
)

# ================= TOTAL =================
st.metric("Total pagos", formato_pesos(total_importe))

# ================= EXPORTAR =================
st.download_button(
    "Descargar resultados en Excel",
    convertir_excel(tabla),
    file_name=f"resultados_pagos_{año}.xlsx"
)
























