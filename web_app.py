import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
# ================= ENCABEZADO =================
c1, c2, c3 = st.columns(
    [1, 6, 1],
    vertical_alignment="center"
)

with c1:
    st.image(
        "LOGO CDMX.jpg",
        width=110
    )

with c2:
    st.markdown(
        """
        <div style="text-align:center">
            <h2 style="margin-bottom:0">Alcaldía Cuauhtémoc</h2>
            <span style="font-size:10px;color:#555">
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

with c3:
    st.image(
        "LOGO CUAUHTEMOC.png",
        width=110
    )

# ================= CONFIGURACIÓN =================
st.set_page_config(
    page_title="Buscador de Pagos y Consumo de Contratos",
    layout="wide"
)

st.title(" Buscador de Pagos y Consumo de Contratos")

# ================= ACTUALIZAR DATOS =================
col1, col2 = st.columns([1, 6])

with col1:
    if st.button("Actualizar datos"):
        st.cache_data.clear()
        st.success("Datos actualizados desde Google Sheets")
        st.rerun()

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

# ================= LISTAS BASE =================
lista_beneficiarios = (
    sorted(df["BENEFICIARIO"].dropna().astype(str).unique())
    if "BENEFICIARIO" in df.columns else []
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

    monto_contrato = (
        df_comp[df_comp["Texto cab.documento"].astype(str) == str(contrato)]
        ["Importe total (LC)"]
        .apply(pd.to_numeric, errors="coerce")
        .sum()
        if "Texto cab.documento" in df_comp.columns
        and "Importe total (LC)" in df_comp.columns
        else 0
    )

    monto_ejercido = (
        df[df["NUM_CONTRATO"].astype(str) == str(contrato)]
        ["importe"]
        .apply(pd.to_numeric, errors="coerce")
        .sum()
        if "NUM_CONTRATO" in df.columns and "importe" in df.columns
        else 0
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

# ---- BENEFICIARIO ----
with c1:
    st.session_state.beneficiario = st.selectbox(
        "Beneficiario",
        [""] + lista_beneficiarios,
        index=([""] + lista_beneficiarios).index(st.session_state.beneficiario)
        if st.session_state.beneficiario in lista_beneficiarios else 0
    )

# ---- CONTRATOS DEPENDIENTES DEL BENEFICIARIO ----
if st.session_state.beneficiario:
    contratos_filtrados = (
        df[df["BENEFICIARIO"] == st.session_state.beneficiario]["NUM_CONTRATO"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
else:
    contratos_filtrados = (
        df["NUM_CONTRATO"].dropna().astype(str).unique().tolist()
        if "NUM_CONTRATO" in df.columns else []
    )

contratos_filtrados = sorted(contratos_filtrados)

# ---- CLC ----
with c2:
    st.session_state.clc = st.text_input("CLC", st.session_state.clc)

# ---- SELECT CONTRATO ----
with c3:
    st.session_state.contrato = st.selectbox(
        "Num. Contrato",
        [""] + contratos_filtrados,
        index=([""] + contratos_filtrados).index(st.session_state.contrato)
        if st.session_state.contrato in contratos_filtrados else 0
    )

# ---- FACTURA ----
with c4:
    st.session_state.factura = st.text_input("Factura", st.session_state.factura)

# ---- LIMPIAR ----
with c5:
    if st.button("Limpiar Busquedas"):
        for k in ["beneficiario", "clc", "contrato", "factura"]:
            st.session_state[k] = ""
        st.rerun()

# ================= FILTRADO =================
resultado = df.copy()

# ⚠️ Regla: si beneficiario tiene MÁS DE UN contrato y NO se elige contrato → no mostrar resultados
if st.session_state.beneficiario and len(contratos_filtrados) > 1 and not st.session_state.contrato:
    resultado = resultado.iloc[0:0]
else:
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

m1, m2, m3 = calcular_consumo(st.session_state.contrato)

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
    "FECHA_PAGO"
]

tabla = resultado[[c for c in columnas if c in resultado.columns]].copy()

if "FECHA_PAGO" in tabla.columns:
    tabla["FECHA_PAGO"] = pd.to_datetime(
        tabla["FECHA_PAGO"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")

if "importe" in tabla.columns:
    tabla["importe"] = tabla["importe"].apply(formato_pesos)

# ================= TOTAL DE IMPORTE =================
if "importe" in resultado.columns:
    total_importe = (
        resultado["importe"]
        .apply(lambda x: str(x).replace("$", "").replace(",", ""))
        .apply(pd.to_numeric, errors="coerce")
        .sum()
    )

    fila_total = {col: "" for col in tabla.columns}
    fila_total["BENEFICIARIO"] = "TOTAL"
    fila_total["importe"] = formato_pesos(total_importe)

    tabla = pd.concat(
        [tabla, pd.DataFrame([fila_total])],
        ignore_index=True
    )
st.dataframe(tabla, use_container_width=True, height=420)

# ================= EXPORTAR =================
st.divider()
st.download_button(
    "Descargar resultados en Excel",
    convertir_excel(tabla),
    file_name="resultados_pagos.xlsx"
)


















