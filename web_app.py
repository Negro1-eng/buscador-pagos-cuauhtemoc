import streamlit as st
import pandas as pd
from io import BytesIO

# ================= CONFIGURACIÓN =================
st.set_page_config(
    page_title="Buscador de Pagos y Consumo de Contratos",
    layout="wide"
)

st.title("🔎 Buscador de Pagos y Consumo de Contratos")

# ================= CARGAR ARCHIVOS =================
archivo_pagos = r"C:\Users\ASUS\Desktop\programas y pruebas\proyecto 1\PAGOS.xlsx"
archivo_compromisos = r"C:\Users\ASUS\Desktop\programas y pruebas\proyecto 1\compromisos cuauhtemoc 2025.XLSX"

@st.cache_data
def cargar_datos():
    df_pagos = pd.read_excel(archivo_pagos)
    df_comp = pd.read_excel(archivo_compromisos)

    df_pagos.columns = df_pagos.columns.str.strip()
    df_comp.columns = df_comp.columns.str.strip()

    for col in ["NUM_CONTRATO", "OFICIO_SOLICITUD", "FACTURA"]:
        if col not in df_pagos.columns:
            df_pagos[col] = ""

    return df_pagos, df_comp

df, df_comp = cargar_datos()

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
        dataframe.to_excel(writer, index=False, sheet_name="Resultados")
    return output.getvalue()

# ================= FILTROS =================
st.subheader("🎯 Filtros de búsqueda")

col1, col2, col3, col4 = st.columns(4)

with col1:
    beneficiario = st.selectbox("Beneficiario", [""] + lista_beneficiarios)
    fecha_pago = st.text_input("Fecha de pago")

with col2:
    clc = st.text_input("CLC")
    importe = st.text_input("Importe")

with col3:
    contrato_filtro = st.selectbox("Num. Contrato", [""] + lista_contratos)
    oficio = st.text_input("Oficio solicitud")

with col4:
    factura = st.text_input("Factura")

# ================= FILTRADO =================
resultado = df.copy()

filtros = {
    "BENEFICIARIO": beneficiario,
    "CLC": clc,
    "Fecha de pago": fecha_pago,
    "importe": importe,
    "NUM_CONTRATO": contrato_filtro,
    "OFICIO_SOLICITUD": oficio,
    "FACTURA": factura
}

for columna, valor in filtros.items():
    if valor:
        resultado = resultado[
            resultado[columna].astype(str).str.contains(valor, case=False, na=False)
        ]

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

# 👉 SELECCIÓN DE FILA (ESTO ES LA CLAVE)
seleccion = st.dataframe(
    tabla,
    use_container_width=True,
    height=420,
    selection_mode="single-row",
    on_select="rerun"
)

# ================= DETERMINAR CONTRATO ACTIVO =================
contrato_seleccionado = contrato_filtro

if seleccion and seleccion["selection"]["rows"]:
    fila = seleccion["selection"]["rows"][0]
    contrato_seleccionado = str(tabla.iloc[fila]["NUM_CONTRATO"])

# ================= PANEL CONSUMO =================
st.subheader("💰 Consumo del contrato")

monto_contrato, monto_ejercido, monto_pendiente = calcular_consumo(contrato_seleccionado)

c1, c2, c3 = st.columns(3)

c1.metric("Monto del contrato", formato_pesos(monto_contrato))
c2.metric("Monto ejercido", formato_pesos(monto_ejercido))
c3.metric("Monto pendiente", formato_pesos(monto_pendiente))

# ================= DESCARGA EXCEL =================
st.divider()
st.subheader("⬇️ Exportar resultados")

excel = convertir_excel(tabla)

st.download_button(
    label="📥 Descargar resultados en Excel",
    data=excel,
    file_name="resultados_pagos_filtrados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


