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

# ================= IDS =================
IDS_SHEETS = {
    "2025": "14D-Q2oyPZ1u8VbDgq5QorhUKPzz9pjtZQyRxwys5nmA",
    "2026": "1Dr6IlKOECZ-rgeXQ-4hfEgFEr1lucFc-6BuljR_S9r4"
}

# ================= SELECTOR =================
año = st.selectbox("Año de consulta", ["2025", "2026"])

# ================= CACHE =================
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

    # 🔥 NORMALIZACIÓN PRO
    def limpiar_columnas(df):
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )
        return df

    df_pagos = limpiar_columnas(df_pagos)
    df_comp = limpiar_columnas(df_comp)

    return df_pagos, df_comp


df, df_comp = cargar_datos(año)

# ================= FUNCIONES =================
def formato_pesos(valor):
    try:
        return f"$ {float(valor):,.2f}"
    except:
        return "$ 0.00"


def obtener_columna(df, nombre):
    """Busca columnas aunque cambien ligeramente"""
    for col in df.columns:
        if nombre in col:
            return col
    return None


def calcular_consumo(contrato):

    if not contrato:
        return 0, 0, 0

    col_contrato_comp = obtener_columna(df_comp, "texto")
    col_importe_comp = obtener_columna(df_comp, "importe")

    col_contrato = obtener_columna(df, "num_contrato")
    col_importe = obtener_columna(df, "importe")

    monto_contrato = 0
    monto_ejercido = 0

    if col_contrato_comp and col_importe_comp:
        monto_contrato = pd.to_numeric(
            df_comp[df_comp[col_contrato_comp].astype(str) == str(contrato)][col_importe_comp],
            errors="coerce"
        ).sum()

    if col_contrato and col_importe:
        monto_ejercido = pd.to_numeric(
            df[df[col_contrato].astype(str) == str(contrato)][col_importe],
            errors="coerce"
        ).sum()

    return monto_contrato, monto_ejercido, monto_contrato - monto_ejercido


def convertir_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ================= FILTROS =================
st.subheader("Filtros")

col_benef = obtener_columna(df, "beneficiario")
col_contrato = obtener_columna(df, "contrato")
col_clc = obtener_columna(df, "clc")
col_factura = obtener_columna(df, "factura")

lista_beneficiarios = sorted(df[col_benef].dropna().astype(str).unique()) if col_benef else []

c1, c2, c3, c4 = st.columns(4)

with c1:
    beneficiario = st.selectbox("Beneficiario", [""] + lista_beneficiarios)

with c2:
    contrato = st.text_input("Contrato")

with c3:
    clc = st.text_input("CLC")

with c4:
    factura = st.text_input("Factura")

# ================= FILTRADO =================
resultado = df.copy()

filtros = [
    (col_benef, beneficiario),
    (col_contrato, contrato),
    (col_clc, clc),
    (col_factura, factura),
]

for col, val in filtros:
    if col and val:
        resultado = resultado[
            resultado[col].astype(str).str.contains(val, case=False, na=False)
        ]

# ================= CONSUMO =================
st.subheader("Consumo del contrato")

m1, m2, m3 = calcular_consumo(contrato)

a, b, c = st.columns(3)
a.metric("Monto del contrato", formato_pesos(m1))
b.metric("Monto ejercido", formato_pesos(m2))
c.metric("Monto pendiente", formato_pesos(m3))

# ================= TABLA =================
st.subheader("Resultados")

col_importe = obtener_columna(resultado, "importe")
col_fecha = obtener_columna(resultado, "fecha")

tabla = resultado.copy()

if col_fecha:
    tabla[col_fecha] = pd.to_datetime(tabla[col_fecha], errors="coerce").dt.strftime("%d/%m/%Y")

if col_importe:
    total_importe = pd.to_numeric(tabla[col_importe], errors="coerce").sum()
    tabla[col_importe] = tabla[col_importe].apply(formato_pesos)
else:
    total_importe = 0
    st.warning("No se encontró columna de importe")

st.metric("TOTAL PAGOS", formato_pesos(total_importe))

st.dataframe(tabla, use_container_width=True)

# ================= EXPORTAR =================
st.download_button(
    "Descargar Excel",
    convertir_excel(tabla),
    file_name=f"pagos_{año}.xlsx"
)


























