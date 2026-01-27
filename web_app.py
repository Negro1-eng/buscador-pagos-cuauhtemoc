import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

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

# ================= CONFIGURACIÓN =================
st.set_page_config(
    page_title="Buscador de Pagos y Consumo de Contratos",
    layout="wide"
)

st.title("Buscador de Pagos y Consumo de Contratos")

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
ID_SHEET = "1RKjYKBPcvbxul2WgRi72DpOBwB0XZwQcFyAY9o6ldOo"

@st.cache_data
def cargar_datos():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key(ID_SHEET)

    df_pagos = pd.DataFrame(sh.worksheet("PAGOS").get_all_records())
    df_comp = pd.DataFrame(sh.worksheet("COMPROMISOS").get_all_records())

    df_pagos.columns = df_pagos.columns.str.strip()
    df_comp.columns = df_comp.columns.str.strip()

    return df_pagos, df_comp


df, df_comp = cargar_datos()

# ================= LISTAS =================
lista_beneficiarios = sorted(df["BENEFICIARIO"].dropna().astype(str).unique())

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
    )

    monto_ejercido = (
        df[df["NUM_CONTRATO"].astype(str) == str(contrato)]
        ["importe"]
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
        for k in st.session_state:
            st.session_state[k] = ""
        st.rerun()

# ================= FILTRADO =================
resultado = df.copy()

if st.session_state.beneficiario and len(contratos_filtrados) > 1 and not st.session_state.contrato:
    resultado = resultado.iloc[0:0]
else:
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

# ================= CONSUMO =================
st.subheader("Consumo del contrato")

m1, m2, m3 = calcular_consumo(st.session_state.contrato)
a, b, c = st.columns(3)
a.metric("Monto del contrato", formato_pesos(m1))
b.metric("Monto ejercido", formato_pesos(m2))
c.metric("Monto pendiente", formato_pesos(m3))

# ================= TABLA =================
st.subheader("Tabla de Resultados")

columnas = ["BENEFICIARIO", "NUM_CONTRATO", "OFICIO_SOLICITUD", "CLC", "importe", "FACTURA", "FECHA_PAGO"]
tabla = resultado[[c for c in columnas if c in resultado.columns]].copy()

if "FECHA_PAGO" in tabla:
    tabla["FECHA_PAGO"] = pd.to_datetime(tabla["FECHA_PAGO"], errors="coerce").dt.strftime("%d/%m/%Y")

total_importe = tabla["importe"].apply(pd.to_numeric, errors="coerce").sum()
tabla["importe"] = tabla["importe"].apply(formato_pesos)

st.markdown("---")

col_t1, col_t2 = st.columns([4, 1])

with col_t1:
    st.markdown("###  MONTO TOTAL DE PAGOS ENCONTRADOS")

with col_t2:
    st.metric(
        label="",
        value=formato_pesos(total_importe)
    )


#fila_total = {c: "" for c in tabla.columns}
#fila_total["BENEFICIARIO"] = "TOTAL"
#fila_total["importe"] = f"**{formato_pesos(total_importe)}**"

#tabla = pd.concat([tabla, pd.DataFrame([fila_total])], ignore_index=True)

alto_tabla = min(420, (len(tabla) + 1) * 35)

st.dataframe(tabla, use_container_width=True, height=alto_tabla)

# ================= EXPORTAR =================
st.divider()
st.download_button(
    "Descargar resultados en Excel",
    convertir_excel(tabla),
    file_name="resultados_pagos.xlsx"
)





















