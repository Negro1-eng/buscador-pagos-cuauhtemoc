import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from io import BytesIO
import os
import re

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

# ================= IDS DE CARPETAS DRIVE POR AÑO =================
IDS_DRIVE = {
    "2025": {
        "comprobacion_pago": "PEGA_AQUI_ID_CARPETA_COMPROBACION_2025",
        "factura": "PEGA_AQUI_ID_CARPETA_FACTURA_2025",
        "contrato": "PEGA_AQUI_ID_CARPETA_PRINCIPAL_CONTRATOS_2025"
    },
    "2026": {
        "comprobacion_pago": "1E-MRmWlPBHzDRTHq89XgKFpHp_kRHcMI",
        "factura": "1VNOrMmdZWalCykgRZSgsHNYlDFU6w6sP",
        "contrato": "1-0UgXXPq6YzkrRiBxKPOESdhKtT5Eqd3"
    }
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

# ================= FUNCIONES AUXILIARES DRIVE =================
def normalizar_nombre(valor):
    if pd.isna(valor):
        return ""
    valor = str(valor).strip().lower()
    valor = os.path.splitext(valor)[0]
    valor = re.sub(r"[-_/\\.,]+", " ", valor)
    valor = re.sub(r"\s+", " ", valor)
    return valor

def obtener_links_drive_pdfs(service, folder_id):
    links = {}
    page_token = None

    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false",
            fields="nextPageToken, files(id, name)",
            pageSize=1000,
            pageToken=page_token,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()

        files = response.get("files", [])

        for file in files:
            nombre = file["name"]
            file_id = file["id"]
            clave = normalizar_nombre(nombre)
            links[clave] = f"https://drive.google.com/file/d/{file_id}/view"

        page_token = response.get("nextPageToken", None)
        if page_token is None:
            break

    return links

def obtener_links_carpetas_drive(service, folder_id):
    links = {}
    page_token = None

    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="nextPageToken, files(id, name)",
            pageSize=1000,
            pageToken=page_token,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()

        files = response.get("files", [])

        for file in files:
            nombre = file["name"]
            file_id = file["id"]
            clave = normalizar_nombre(nombre)
            links[clave] = f"https://drive.google.com/drive/folders/{file_id}"

        page_token = response.get("nextPageToken", None)
        if page_token is None:
            break

    return links

# ================= GOOGLE SHEETS =================
@st.cache_data
def cargar_datos(año):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    service = build("drive", "v3", credentials=creds)
    sheet_id = IDS_SHEETS[año]
    sh = client.open_by_key(sheet_id)

    df_pagos = pd.DataFrame(sh.worksheet("PAGOS").get_all_records())
    df_comp = pd.DataFrame(sh.worksheet("COMPROMISOS").get_all_records())

    df_pagos.columns = df_pagos.columns.str.strip().str.upper()
    df_comp.columns = df_comp.columns.str.strip().str.upper()

    carpeta_comprobacion = IDS_DRIVE[año]["comprobacion_pago"]
    carpeta_factura = IDS_DRIVE[año]["factura"]
    carpeta_contrato = IDS_DRIVE[año]["contrato"]

    links_comprobacion = {}
    links_factura = {}
    links_contrato = {}

    if carpeta_comprobacion and "PEGA_AQUI" not in carpeta_comprobacion:
        links_comprobacion = obtener_links_drive_pdfs(service, carpeta_comprobacion)

    if carpeta_factura and "PEGA_AQUI" not in carpeta_factura:
        links_factura = obtener_links_drive_pdfs(service, carpeta_factura)

    if carpeta_contrato and "PEGA_AQUI" not in carpeta_contrato:
        links_contrato = obtener_links_carpetas_drive(service, carpeta_contrato)

    if "COMPROBACION DE PAGO" in df_pagos.columns:
        df_pagos["PDF COMPROBACION"] = (
            df_pagos["COMPROBACION DE PAGO"]
            .apply(normalizar_nombre)
            .map(links_comprobacion)
        )
    else:
        df_pagos["PDF COMPROBACION"] = None

    if "FACTURA" in df_pagos.columns:
        df_pagos["PDF FACTURA"] = (
            df_pagos["FACTURA"]
            .apply(normalizar_nombre)
            .map(links_factura)
        )
    else:
        df_pagos["PDF FACTURA"] = None

    if "NUM_CONTRATO" in df_pagos.columns:
        df_pagos["PDF CONTRATO"] = (
            df_pagos["NUM_CONTRATO"]
            .apply(normalizar_nombre)
            .map(links_contrato)
        )
    else:
        df_pagos["PDF CONTRATO"] = None

    return df_pagos, df_comp

df, df_comp = cargar_datos(año)

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

def obtener_link_contrato(contrato):
    if not contrato or "PDF CONTRATO" not in df.columns:
        return None

    contrato_normalizado = normalizar_nombre(contrato)

    coincidencias = df.loc[
        df["NUM_CONTRATO"].apply(normalizar_nombre) == contrato_normalizado,
        "PDF CONTRATO"
    ].dropna()

    if coincidencias.empty:
        return None

    return coincidencias.iloc[0]

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
        for k in ["beneficiario", "clc", "contrato", "factura"]:
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

# ================= BOTÓN PARA VER CONTRATO =================
contrato_para_link = st.session_state.contrato

if not contrato_para_link and not resultado.empty and "NUM_CONTRATO" in resultado.columns:
    contratos_unicos = resultado["NUM_CONTRATO"].dropna().astype(str).unique().tolist()
    if len(contratos_unicos) == 1:
        contrato_para_link = contratos_unicos[0]

link_contrato = obtener_link_contrato(contrato_para_link)

if contrato_para_link:
    st.subheader("Carpeta del contrato")

    if link_contrato:
        st.link_button("Visualizar carpeta del contrato", link_contrato)
    else:
        st.warning(
            "No se encontró la carpeta del contrato en Drive. "
            "Verifica que la subcarpeta tenga el mismo nombre que el NUM_CONTRATO."
        )

# ================= CONSUMO =================
st.subheader("Consumo del contrato")

m1, m2, m3 = calcular_consumo(st.session_state.contrato)

a, b, c = st.columns(3)

a.metric("Monto del contrato", formato_pesos(m1))
b.metric("Monto ejercido", formato_pesos(m2))
c.metric("Monto pendiente", formato_pesos(m3))

# ================= TABLA =================
st.subheader("Tabla de Resultados")

columnas = [
    "BENEFICIARIO",
    "NUM_CONTRATO",
    "PDF CONTRATO",
    "OFICIO_SOLICITUD",
    "CLC",
    "COMPROBACION DE PAGO",
    "PDF COMPROBACION",
    "IMPORTE",
    "FACTURA",
    "PDF FACTURA",
    "FECHA_PAGO",
]

tabla = resultado[[c for c in columnas if c in resultado.columns]].copy()

if "FECHA_PAGO" in tabla.columns:
    tabla["FECHA_PAGO"] = pd.to_datetime(
        tabla["FECHA_PAGO"],
        errors="coerce"
    ).dt.strftime("%d/%m/%Y")

if "IMPORTE" in tabla.columns:
    total_importe = pd.to_numeric(tabla["IMPORTE"], errors="coerce").sum()
    tabla["IMPORTE"] = tabla["IMPORTE"].apply(formato_pesos)
else:
    total_importe = 0
    st.warning("No se encontró la columna IMPORTE")

st.markdown("---")

col_t1, col_t2 = st.columns([4, 1])

with col_t1:
    st.markdown("### MONTO TOTAL DE PAGOS ENCONTRADOS")

with col_t2:
    st.metric("", formato_pesos(total_importe))

alto_tabla = min(420, (len(tabla) + 1) * 35)

st.dataframe(
    tabla,
    use_container_width=True,
    height=alto_tabla,
    column_config={
        "PDF CONTRATO": st.column_config.LinkColumn(
            "CARPETA CONTRATO",
            display_text="Ver carpeta"
        ),
        "PDF COMPROBACION": st.column_config.LinkColumn(
            "PDF COMPROBACION",
            display_text="Ver PDF"
        ),
        "PDF FACTURA": st.column_config.LinkColumn(
            "PDF FACTURA",
            display_text="Ver PDF"
        )
    }
)

# ================= EXPORTAR =================
st.divider()

st.download_button(
    "Descargar resultados en Excel",
    convertir_excel(tabla),
    file_name=f"resultados_pagos_{año}.xlsx"
)
