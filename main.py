import streamlit as st
import pandas as pd
import plotly.express as px
import difflib

st.set_page_config(layout="wide")
st.title("Revisión Programación SED")

# ========== FUNCIONES UTILITARIAS ==========

@st.cache_data(show_spinner=False)
def cargar_hoja(archivo, hoja, columnas):
    df = pd.read_excel(archivo, sheet_name=hoja, header=7)
    return df[df.columns.intersection(columnas)]

@st.cache_data(show_spinner=False)
def cargar_cronograma(archivo):
    columnas = [
        "Clave Q", "Dep Siglas", "ID Meta", "Clave de Meta", "Clave de Actividad /Hito", "Tipo",
        "Fase Actividad / Hito", "Descripción", "Fecha de Inicio", "Fecha de Termino",
        "Monto Actividad / Hito"
    ]
    df = pd.read_excel(archivo, sheet_name="Sección de Metas-Cronograma", header=7)
    df = df[df.columns.intersection(columnas)]
    df["Fecha de Inicio"] = pd.to_datetime(df["Fecha de Inicio"], dayfirst=True, errors='coerce')
    df["Fecha de Termino"] = pd.to_datetime(df["Fecha de Termino"], dayfirst=True, errors='coerce')
    return df

@st.cache_data(show_spinner=False)
def agregar_totales(df):
    df = df.copy()
    df["Cantidad Total"] = df.filter(like="Cantidad").sum(axis=1, skipna=True)
    df["Monto Total"] = df.filter(like="Monto").sum(axis=1, skipna=True)
    return df


# ========== INTERFAZ LATERAL ==========

with st.sidebar:
    st.header("Carga de archivos")
    archivo_antes = st.file_uploader("Archivo - Corte Antes", type=["xlsx"], key="archivo_antes")
    archivo_ahora = st.file_uploader("Archivo - Corte Ahora", type=["xlsx"], key="archivo_ahora")

# ========== CARGA Y FILTRO INICIAL ==========

if archivo_antes and archivo_ahora:
    with st.spinner("Cargando y procesando archivos..."):

        # --- Cargar hoja 'Datos Generales' para extraer Claves Q disponibles ---
        columnas_datos = [
            "Fecha", "Clave Q", "Nombre del Proyecto (Ejercicio Actual)", "Eje", "Dep Siglas",
            "Diagnóstico", "Objetivo General", "Descripción del Proyecto",
            "Descripción del Avance Actual", "Alcance Anual"
        ]
        datos_ahora = cargar_hoja(archivo_ahora, "Datos Generales", columnas_datos)
        datos_antes = cargar_hoja(archivo_antes, "Datos Generales", columnas_datos)

        # --- Filtro por Eje (primer nivel) ---
        ejes_disponibles = datos_ahora["Eje"].dropna().unique().tolist()
        eje_sel = st.sidebar.selectbox("Filtrar por Eje", [""] + sorted(ejes_disponibles))

        # --- Filtro por Dependencia (segundo nivel) ---
        if eje_sel:
            deps_filtradas = datos_ahora[datos_ahora["Eje"] == eje_sel]["Dep Siglas"].dropna().unique().tolist()
            dep_sel = st.sidebar.selectbox("Filtrar por Dependencia", [""] + sorted(deps_filtradas))
        else:
            dep_sel = None

        # --- Filtro por Clave Q (tercer nivel) ---
        if eje_sel and dep_sel:
            claves_filtradas = datos_ahora[
                (datos_ahora["Eje"] == eje_sel) &
                (datos_ahora["Dep Siglas"] == dep_sel)
            ]["Clave Q"].dropna().unique().tolist()
            clave_q = st.sidebar.selectbox("Selecciona una Clave Q", [""] + sorted(claves_filtradas))
        else:
            clave_q = None

        # --- Control de flujo: si no hay Clave Q seleccionada, detener ejecución ---
        if not clave_q:
            st.warning("Selecciona una Clave Q específica en el panel lateral para ver los datos comparativos.")
            st.stop()

        # ========== FILTRAR TODOS LOS DATAFRAMES POR CLAVE Q ANTES DE USARLOS ==========

        datos_ahora = datos_ahora[datos_ahora["Clave Q"] == clave_q]
        datos_antes = datos_antes[datos_antes["Clave Q"] == clave_q]

        # Cargar y filtrar metas
        columnas_metas = [
            "Clave Q", "ID Meta", "Clave de Meta", "Descripción de la Meta", "Unidad de Medida",
            "ID Mpio", "Municipio", "Registro Presupuestal", "Cantidad Estatal", "Monto Estatal",
            "Cantidad Federal", "Monto Federal", "Cantidad Municipal", "Monto Municipal",
            "Cantidad Ingresos Propios", "Monto Ingresos Propios", "Cantidad Otros", "Monto Otros"
        ]
        metas_ahora = cargar_hoja(archivo_ahora, "Sección de Metas", columnas_metas)
        metas_antes = cargar_hoja(archivo_antes, "Sección de Metas", columnas_metas)
        metas_ahora = agregar_totales(metas_ahora)
        metas_antes = agregar_totales(metas_antes)

        metas_ahora = metas_ahora[metas_ahora["Clave Q"] == clave_q]
        metas_antes = metas_antes[metas_antes["Clave Q"] == clave_q]

        # Cronograma
        metas_crono_ahora = cargar_cronograma(archivo_ahora)
        metas_crono_antes = cargar_cronograma(archivo_antes)

        metas_crono_ahora = metas_crono_ahora[metas_crono_ahora["Clave Q"] == clave_q]
        metas_crono_antes = metas_crono_antes[metas_crono_antes["Clave Q"] == clave_q]

        # Partidas
        columnas_partidas = [
            "Clave Q", "ID Meta", "Clave de Meta", "Partida", "Monto Anual",
            "Monto Enero", "Monto Febrero", "Monto Marzo", "Monto Abril", "Monto Mayo",
            "Monto Junio", "Monto Julio", "Monto Agosto", "Monto Septiembre",
            "Monto Octubre", "Monto Noviembre", "Monto Diciembre"
        ]
        metas_partidas_ahora = cargar_hoja(archivo_ahora, "Sección de Metas-Partidas", columnas_partidas)
        metas_partidas_antes = cargar_hoja(archivo_antes, "Sección de Metas-Partidas", columnas_partidas)

        metas_partidas_ahora = metas_partidas_ahora[metas_partidas_ahora["Clave Q"] == clave_q]
        metas_partidas_antes = metas_partidas_antes[metas_partidas_antes["Clave Q"] == clave_q]

        # Cumplimiento (filtrado por Clave de Meta más adelante)
        columnas_cumplimiento = ["Clave de Meta", "Cantidad"] + [f"Cumplimiento {mes}" for mes in [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]]
        cumplimiento_ahora = cargar_hoja(archivo_ahora, "Sección de Metas-Cumplimiento", columnas_cumplimiento)
        cumplimiento_antes = cargar_hoja(archivo_antes, "Sección de Metas-Cumplimiento", columnas_cumplimiento)

        cumplimiento_ahora = cumplimiento_ahora.dropna(subset=["Clave de Meta"])
        cumplimiento_antes = cumplimiento_antes.dropna(subset=["Clave de Meta"])


    ################################################ DATOS GENERALES #########################################
    with st.expander("Datos Generales", expanded=False):    
            st.subheader("Comparativo de Datos Generales")

            campos_texto = [
                "Diagnóstico", "Objetivo General", "Descripción del Proyecto",
                "Descripción del Avance Actual", "Alcance Anual"
            ]

            def resaltar_diferencias(texto_antes, texto_ahora):
                matcher = difflib.SequenceMatcher(None, texto_antes, texto_ahora)
                res_antes = ""
                res_ahora = ""
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag == "equal":
                        res_antes += texto_antes[i1:i2]
                        res_ahora += texto_ahora[j1:j2]
                    elif tag == "replace":
                        res_antes += f"<del style='color:red'>{texto_antes[i1:i2]}</del>"
                        res_ahora += f"<span style='background-color:lightgreen'>{texto_ahora[j1:j2]}</span>"
                    elif tag == "delete":
                        res_antes += f"<del style='color:red'>{texto_antes[i1:i2]}</del>"
                    elif tag == "insert":
                        res_ahora += f"<span style='background-color:lightgreen'>{texto_ahora[j1:j2]}</span>"
                return res_antes, res_ahora

            if clave_q == "Todos":
                st.info("Selecciona una Clave Q específica en el panel lateral para ver los datos comparativos.")
            else:
                st.markdown(f"### Clave Q: {clave_q}")

                fila_antes = datos_antes
                fila_ahora = datos_ahora

                if fila_antes.empty or fila_ahora.empty:
                    st.warning("No se encontró información para esta Clave Q.")
                else:
                    for campo in campos_texto:
                        valor_antes = str(fila_antes[campo].values[0])
                        valor_ahora = str(fila_ahora[campo].values[0])

                        st.markdown(f"**{campo}**")
                        col1, col2 = st.columns(2)

                        if valor_antes != valor_ahora:
                            st.info("🔄 Modificado")
                            antes_html, ahora_html = resaltar_diferencias(valor_antes, valor_ahora)
                            with col1:
                                st.markdown("Antes:")
                                st.markdown(f"<div style='border:1px solid #ccc;padding:8px'>{antes_html}</div>", unsafe_allow_html=True)
                            with col2:
                                st.markdown("Ahora:")
                                st.markdown(f"<div style='border:1px solid #ccc;padding:8px'>{ahora_html}</div>", unsafe_allow_html=True)
                        else:
                            st.success("✔ Sin cambios")
                            with col1:
                                st.markdown("Antes:")
                                st.markdown(valor_antes)
                            with col2:
                                st.markdown("Ahora:")
                                st.markdown(valor_ahora)




    # --------- Filtro de Clave de Meta (solo si hay datos y clave_q) ---------
            if not metas_ahora.empty and clave_q is not None:
                st.markdown("### Seleccionar Meta")

                metas_disponibles = (
                    metas_ahora[metas_ahora["Clave Q"] == clave_q][["Clave de Meta", "Descripción de la Meta"]]
                    .dropna(subset=["Clave de Meta"])
                    .drop_duplicates()
                    .sort_values("Clave de Meta")
                )

                metas_disponibles["Etiqueta"] = metas_disponibles["Clave de Meta"] + " - " + metas_disponibles["Descripción de la Meta"]

                clave_meta_filtro = st.selectbox(
                    "Selecciona una Clave de Meta",
                    [""] + metas_disponibles["Etiqueta"].tolist(),
                    key="filtro_meta"
                )

                clave_meta_filtro_valor = clave_meta_filtro.split(" - ")[0] if clave_meta_filtro else None

            else:
                clave_meta_filtro_valor = None


    ############################## SECCIÓN DE METAS ############################################################
    def resaltar_diferencias(texto_antes, texto_ahora):
        matcher = difflib.SequenceMatcher(None, texto_antes, texto_ahora)
        res_antes = ""
        res_ahora = ""
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                res_antes += texto_antes[i1:i2]
                res_ahora += texto_ahora[j1:j2]
            elif tag == "replace":
                res_antes += f"<del style='color:red'>{texto_antes[i1:i2]}</del>"
                res_ahora += f"<span style='background-color:lightgreen'>{texto_ahora[j1:j2]}</span>"
            elif tag == "delete":
                res_antes += f"<del style='color:red'>{texto_antes[i1:i2]}</del>"
            elif tag == "insert":
                res_ahora += f"<span style='background-color:lightgreen'>{texto_ahora[j1:j2]}</span>"
        return res_antes, res_ahora


    with st.expander("Sección de Metas", expanded=True):
        if metas_ahora.empty:
            st.info("No hay datos disponibles para esta Clave Q.")
        else:
            campos_metas_texto = ["Descripción de la Meta", "Unidad de Medida"]

            claves_meta_unicas = metas_ahora["Clave de Meta"].dropna().unique()

            for clave_meta in claves_meta_unicas:
        

                if clave_meta_filtro_valor and clave_meta != clave_meta_filtro_valor:
                    continue  # 👉 Omitir si no coincide con filtro

                st.markdown(f"#### Meta: {clave_meta}")

                df_ahora_meta = metas_ahora[metas_ahora["Clave de Meta"] == clave_meta]
                df_antes_meta = metas_antes[metas_antes["Clave de Meta"] == clave_meta]

                fila_ahora = df_ahora_meta.head(1)
                fila_antes = df_antes_meta.head(1)

                col1, col2 = st.columns(2)

                # Comparativos cualitativos
                for campo in campos_metas_texto:
                    valor_ahora = str(fila_ahora[campo].values[0]) if not fila_ahora.empty else ""
                    valor_antes = str(fila_antes[campo].values[0]) if not fila_antes.empty else ""

                    if campo == "Descripción de la Meta":
                        antes_html, ahora_html = resaltar_diferencias(valor_antes, valor_ahora)

                        col1.markdown(f"**{campo} (Antes)**")
                        col1.markdown(f"<div style='border:1px solid #ccc;padding:8px'>{antes_html}</div>", unsafe_allow_html=True)

                        col2.markdown(f"**{campo} (Ahora)**")
                        col2.markdown(f"<div style='border:1px solid #ccc;padding:8px'>{ahora_html}</div>", unsafe_allow_html=True)
                    else:
                        col1.markdown(f"**{campo} (Antes)**")
                        col1.markdown(valor_antes)
                        col2.markdown(f"**{campo} (Ahora)**")
                        col2.markdown(valor_ahora)

                # ---------- Métricas generales ----------
                total_antes_cantidad = df_antes_meta["Cantidad Total"].sum()
                total_ahora_cantidad = df_ahora_meta["Cantidad Total"].sum()
                total_antes_monto = df_antes_meta["Monto Total"].sum()
                total_ahora_monto = df_ahora_meta["Monto Total"].sum()

                diferencia_cantidad = total_ahora_cantidad - total_antes_cantidad
                diferencia_monto = total_ahora_monto - total_antes_monto

                color_cantidad = "green" if diferencia_cantidad > 0 else "red" if diferencia_cantidad < 0 else "black"
                color_monto = "green" if diferencia_monto > 0 else "red" if diferencia_monto < 0 else "black"

                col_total1, col_total2 = st.columns(2)
                col_total1.metric("Cantidad Total (Ahora)", f"{total_ahora_cantidad:,.2f}")
                col_total1.markdown(f"<span style='color:{color_cantidad}'>Diferencia: {diferencia_cantidad:,.2f}</span>", unsafe_allow_html=True)

                col_total2.metric("Monto Total (Ahora)", f"${total_ahora_monto:,.2f}")
                col_total2.markdown(f"<span style='color:{color_monto}'>Diferencia: ${diferencia_monto:,.2f}</span>", unsafe_allow_html=True)

                # ---------- Comparativo por Municipio ----------
                st.markdown("##### Comparativo por Municipio")

                resumen_antes = df_antes_meta.groupby("Municipio")[["Cantidad Total", "Monto Total"]].sum().reset_index()
                resumen_ahora = df_ahora_meta.groupby("Municipio")[["Cantidad Total", "Monto Total"]].sum().reset_index()

                resumen_antes = resumen_antes.rename(columns={
                    "Cantidad Total": "Cantidad Total (Antes)",
                    "Monto Total": "Monto Total (Antes)"
                })
                resumen_ahora = resumen_ahora.rename(columns={
                    "Cantidad Total": "Cantidad Total (Ahora)",
                    "Monto Total": "Monto Total (Ahora)"
                })

                resumen_comparativo = pd.merge(resumen_antes, resumen_ahora, on="Municipio", how="outer").fillna(0)
                resumen_comparativo = resumen_comparativo[[
                    "Municipio",
                    "Cantidad Total (Antes)", "Cantidad Total (Ahora)",
                    "Monto Total (Antes)", "Monto Total (Ahora)"
                ]]

                for col in ["Monto Total (Antes)", "Monto Total (Ahora)"]:
                    resumen_comparativo[col] = resumen_comparativo[col].apply(lambda x: f"${x:,.2f}")

                st.dataframe(resumen_comparativo, use_container_width=True)


############################## SECCIÓN DE CRONOGRAMA ############################################################
        if clave_meta_filtro_valor:
            with st.expander("Sección de Cronograma"):
                st.subheader("Cronograma")

                clave_meta_seleccionada = clave_meta_filtro_valor

                df_crono_ahora_qm = metas_crono_ahora[metas_crono_ahora["Clave de Meta"] == clave_meta_seleccionada]
                df_crono_antes_qm = metas_crono_antes[metas_crono_antes["Clave de Meta"] == clave_meta_seleccionada]

                if df_crono_ahora_qm.empty and df_crono_antes_qm.empty:
                    st.info("No se encontraron actividades o hitos para esta meta en ninguna de las versiones.")
                else:
                    # Marcar versión
                    df_crono_ahora_qm = df_crono_ahora_qm.copy()
                    df_crono_ahora_qm["Versión"] = "Ahora"

                    df_crono_antes_qm = df_crono_antes_qm.copy()
                    df_crono_antes_qm["Versión"] = "Antes"

                    df_crono_comparado = pd.concat([df_crono_antes_qm, df_crono_ahora_qm], ignore_index=True)

                    # Convertir clave numérica
                    df_crono_comparado["Clave Num"] = pd.to_numeric(
                        df_crono_comparado["Clave de Actividad /Hito"], errors="coerce"
                    )

                    df_crono_comparado["Actividad"] = (
                        df_crono_comparado["Clave de Actividad /Hito"].astype(str) +
                        " - " + df_crono_comparado["Descripción"].astype(str) +
                        " (" + df_crono_comparado["Versión"] + ")"
                    )

                    orden_y = df_crono_comparado.sort_values("Clave Num")["Actividad"].tolist()

                    # Ajustar fechas iguales (inicio = término)
                    mismo_dia = (
                        df_crono_comparado["Fecha de Inicio"] == df_crono_comparado["Fecha de Termino"]
                    )
                    df_crono_comparado.loc[mismo_dia, "Fecha de Termino"] += pd.Timedelta(days=1)

                    # Gantt
                    fig = px.timeline(
                        df_crono_comparado,
                        x_start="Fecha de Inicio",
                        x_end="Fecha de Termino",
                        y="Actividad",
                        color="Versión",
                        color_discrete_map={"Antes": "steelblue", "Ahora": "seagreen"},
                        title=f"Cronograma de Actividades / Hitos - Meta {clave_meta_seleccionada}"
                    )

                    fig.update_yaxes(categoryorder="array", categoryarray=orden_y)
                    fig.update_yaxes(autorange="reversed")
                    fig.update_layout(height=600)

                    st.plotly_chart(fig, use_container_width=True)

                    # Tabla de detalle (solo versión actual)
                    st.markdown("##### Detalle de Actividades / Hitos (Versión Actual)")

                    columnas_tabla = [
                        "Clave de Actividad /Hito", "Fase Actividad / Hito", "Descripción",
                        "Fecha de Inicio", "Fecha de Termino", "Monto Actividad / Hito"
                    ]

                    tabla_actual = df_crono_ahora_qm[columnas_tabla].sort_values("Clave de Actividad /Hito").copy()

                    tabla_actual["Monto Actividad / Hito"] = tabla_actual["Monto Actividad / Hito"].apply(
                        lambda x: f"${x:,.2f}" if pd.notna(x) else ""
                    )
                    tabla_actual["Fecha de Inicio"] = tabla_actual["Fecha de Inicio"].dt.strftime("%d/%m/%Y")
                    tabla_actual["Fecha de Termino"] = tabla_actual["Fecha de Termino"].dt.strftime("%d/%m/%Y")

                    st.dataframe(tabla_actual, use_container_width=True)


        ############################## SECCIÓN DE METAS-PARTIDAS ############################################################
        if clave_meta_filtro_valor:
            with st.expander("Sección de Metas-Partidas"):
                st.subheader("Partidas por Meta")

                clave_meta = clave_meta_filtro_valor

                df_partidas_ahora_qm = metas_partidas_ahora[metas_partidas_ahora["Clave de Meta"] == clave_meta]
                df_partidas_antes_qm = metas_partidas_antes[metas_partidas_antes["Clave de Meta"] == clave_meta]

                # --- Comparativo de montos anuales por partida ---
                resumen_ahora = (
                    df_partidas_ahora_qm.groupby("Partida")["Monto Anual"].sum().reset_index()
                    .rename(columns={"Monto Anual": "Monto Anual (Ahora)"})
                )
                resumen_antes = (
                    df_partidas_antes_qm.groupby("Partida")["Monto Anual"].sum().reset_index()
                    .rename(columns={"Monto Anual": "Monto Anual (Antes)"})
                )

                df_comparativo = pd.merge(resumen_antes, resumen_ahora, on="Partida", how="outer").fillna(0)
                df_comparativo["Diferencia"] = (
                    df_comparativo["Monto Anual (Ahora)"] - df_comparativo["Monto Anual (Antes)"]
                )

                # Formato de moneda
                for col in ["Monto Anual (Antes)", "Monto Anual (Ahora)", "Diferencia"]:
                    df_comparativo[col] = df_comparativo[col].apply(lambda x: f"${x:,.2f}")

                st.markdown("##### Comparativo de Montos por Partida")
                st.dataframe(df_comparativo, use_container_width=True)

                # --- Distribución mensual por meta ---
                meses = [
                    "Monto Enero", "Monto Febrero", "Monto Marzo", "Monto Abril", "Monto Mayo",
                    "Monto Junio", "Monto Julio", "Monto Agosto", "Monto Septiembre",
                    "Monto Octubre", "Monto Noviembre", "Monto Diciembre"
                ]

                # Sumar por mes
                sum_mensual_ahora = df_partidas_ahora_qm[meses].sum()
                sum_mensual_antes = df_partidas_antes_qm[meses].sum()

                df_mensual = pd.DataFrame({
                    "Mes": [mes.replace("Monto ", "") for mes in meses],
                    "Antes": sum_mensual_antes.values,
                    "Ahora": sum_mensual_ahora.values
                })

                fig = px.bar(
                    df_mensual,
                    x="Mes",
                    y=["Antes", "Ahora"],
                    barmode="group",
                    title=f"Distribución Mensual de Montos - Meta {clave_meta}",
                    labels={"value": "Monto", "variable": "Versión"},
                    color_discrete_map={"Antes": "steelblue", "Ahora": "seagreen"}
                )

                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)


 ############################## SECCIÓN DE METAS - CUMPLIMIENTO ############################################################
    with st.expander("Sección de Cumplimiento por Meta", expanded=False):
        st.subheader("Cumplimiento Programado (Mensual)")

        clave_meta = clave_meta_filtro_valor

        df_cump_ahora = cumplimiento_ahora[ cumplimiento_ahora["Clave de Meta"] == clave_meta ]
        df_cump_antes = cumplimiento_antes[ cumplimiento_antes["Clave de Meta"] == clave_meta ]

        # Obtener cantidad programada
        cantidad_ahora = df_cump_ahora["Cantidad"].values[0] if not df_cump_ahora.empty else None
        cantidad_antes = df_cump_antes["Cantidad"].values[0] if not df_cump_antes.empty else None

        # Mostrar métricas
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Cantidad Programada (Ahora)", f"{cantidad_ahora:.2f}" if cantidad_ahora is not None else "—")
        with col2:
            st.metric("Cantidad Programada (Antes)", f"{cantidad_antes:.2f}" if cantidad_antes is not None else "—")

        # Gráfico de cumplimiento mensual
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        columnas_mensuales = [f"Cumplimiento {mes}" for mes in meses]

        valores_ahora = (
            df_cump_ahora.iloc[0][columnas_mensuales].fillna(0).values if not df_cump_ahora.empty else [0] * 12
        )
        valores_antes = (
            df_cump_antes.iloc[0][columnas_mensuales].fillna(0).values if not df_cump_antes.empty else [0] * 12
        )

        df_cumplimiento = pd.DataFrame({
            "Mes": meses * 2,
            "Valor": list(valores_antes) + list(valores_ahora),
            "Versión": ["Antes"] * 12 + ["Ahora"] * 12
        })

        fig_cump = px.bar(
            df_cumplimiento,
            x="Mes",
            y="Valor",
            color="Versión",
            barmode="group",
            color_discrete_map={"Antes": "steelblue", "Ahora": "seagreen"},
            title=f"Cumplimiento Programado por Mes - Meta {clave_meta}"
        )
        fig_cump.update_layout(xaxis_tickangle=-45, height=400)

        st.plotly_chart(fig_cump, use_container_width=True)



else:
    st.info("Bienvenido, para comenzar, carga los archivos de corte (Detalle de Q's) 'Antes' y 'Ahora' en el panel lateral. Una vez cargados, selecciona el Eje y la Dependencia o Entidad. Por último, seleccióna la Clave Q y podrás explorar los datos y compararlos entre las dos fechas de corte.")


