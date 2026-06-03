import streamlit as st
import pandas as pd
import altair as alt
from modelo_crossdock import (resolver_crossdock, parse_ts,
                               unload_time, load_time, T_UNIT, T_TRANS, T_CHANGE)

st.set_page_config(
    page_title="Cross-Docking LogiFast CR",
    page_icon="🚚",
    layout="wide",
)

# ── Tema rosado oscuro ────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #1a0010; color: #fce4ec; }

    [data-testid="stSidebar"] { background-color: #2d0020 !important; }
    [data-testid="stSidebar"] * { color: #fce4ec !important; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #f48fb1 !important; }

    .stTabs [data-baseweb="tab-list"] {
        background-color: #2d0020; border-radius: 10px; padding: 4px; gap: 4px;
    }
    .stTabs [data-baseweb="tab"] { color: #f48fb1; font-weight: 600; border-radius: 8px; }
    .stTabs [aria-selected="true"] { background-color: #880e4f !important; color: #fff !important; }

    [data-testid="stMetricValue"]    { font-size: 1.45rem !important; color: #f48fb1 !important; }
    [data-testid="stMetricLabel"]    { color: #f8bbd0 !important; font-weight: 600; }
    [data-testid="stMetricDelta"]    { color: #f48fb1 !important; }
    [data-testid="metric-container"] {
        background-color: #2d0020; border: 1px solid #880e4f;
        border-radius: 12px; padding: 14px 18px;
    }

    h1 { color: #f48fb1 !important; }
    h2, h3 { color: #f8bbd0 !important; }
    p, li { color: #fce4ec; }
    .stCaption { color: #ad1457 !important; }

    .stButton > button {
        background-color: #880e4f; color: #fff; border: none;
        border-radius: 8px; font-weight: 700;
    }
    .stButton > button:hover { background-color: #ad1457; color: #fff; }

    [data-testid="stTextArea"] textarea {
        background-color: #2d0020 !important;
        color: #fce4ec !important;
        border-color: #880e4f !important;
        font-family: monospace;
    }
    .stDataFrame { background-color: #2d0020; }
    hr { border-color: #880e4f; opacity: 0.4; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

st.title("🚚 Optimizador Cross-Docking — LogiFast CR")
st.caption("MIP · Minimiza el tiempo total de operación del centro de distribución")

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.header("⚙️ Datos de entrada")

DEFAULT_TS = """i 5 o 3 n 8
r 1 1 170
r 2 1 6
r 2 2 6
r 2 3 19
r 2 4 50
r 2 5 38
r 2 6 6
r 2 7 19
r 2 8 56
r 3 1 49
r 3 2 31
r 3 3 60
r 3 6 12
r 3 7 37
r 3 8 31
r 4 5 143
r 4 7 47
r 5 4 58
r 5 5 36
r 5 7 72
r 5 8 14
s 1 1 75
s 1 2 12
s 1 3 59
s 1 6 9
s 1 7 98
s 1 8 40
s 2 1 150
s 2 5 217
s 3 2 25
s 3 3 20
s 3 4 108
s 3 6 9
s 3 7 77
s 3 8 61"""

ts_text = st.sidebar.text_area(
    "Archivo TS (formato texto)", value=DEFAULT_TS, height=300,
    help="Pegá aquí el contenido de cualquier archivo TS con el mismo formato"
)

st.sidebar.markdown("---")
st.sidebar.markdown("**⏱️ Parámetros operativos**")
st.sidebar.caption(f"• {T_UNIT} min/unidad (carga/descarga)")
st.sidebar.caption(f"• {T_TRANS} min traslado interno por lote")
st.sidebar.caption(f"• {T_CHANGE} min cambio entre camiones")

st.sidebar.markdown("---")
optimizar = st.sidebar.button("🚀 Optimizar", use_container_width=True)

# ── Sesión ────────────────────────────────────────────────────
if optimizar:
    with st.spinner("Resolviendo MIP… esto puede tomar unos segundos"):
        res = resolver_crossdock(ts_text)
    st.session_state["res"] = res

res = st.session_state.get("res")

# ── Pestañas ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Resultado",
    "⏱️ Programación",
    "📦 Flujo de productos",
    "📊 Datos del problema",
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — RESULTADO
# ══════════════════════════════════════════════════════════════
with tab1:
    if res is None:
        st.info("Pegá los datos en la barra lateral y presioná **Optimizar**.")
    elif res["status"] not in ("Optimal", "Not Solved") and res["makespan"] == 0:
        st.error(f"❌ Sin solución: {res['status']}")
    else:
        makespan_h = res["makespan"] / 60
        st.success(f"✅ Solución óptima encontrada — Makespan: **{res['makespan']:.0f} min  ({makespan_h:.2f} h)**")
        st.markdown("---")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("⏱️ Tiempo total (makespan)", f"{res['makespan']:.0f} min")
        c2.metric("🕐 Duración en horas",        f"{makespan_h:.2f} h")
        c3.metric("🚛 Camiones de entrada",       res["I"])
        c4.metric("📤 Camiones de salida",         res["O"])

        st.markdown("---")
        c5, c6, c7 = st.columns(3)
        c5.metric("📦 Tipos de producto",   res["N"])
        c6.metric("🔢 Total rutas de flujo", len(res["flow"]))
        c7.metric("📊 Estado del solver",    res["status"])

        st.markdown("---")
        st.subheader("🔀 Orden óptimo de atención")
        col_in, col_out = st.columns(2)
        with col_in:
            st.markdown("**Camiones de entrada (descarga)**")
            orden_in = " → ".join(f"I{i}" for i in res["inbound_order"])
            st.markdown(f"### {orden_in}")
        with col_out:
            st.markdown("**Camiones de salida (carga)**")
            orden_out = " → ".join(f"O{j}" for j in res["outbound_order"])
            st.markdown(f"### {orden_out}")

# ══════════════════════════════════════════════════════════════
# TAB 2 — PROGRAMACIÓN (GANTT)
# ══════════════════════════════════════════════════════════════
with tab2:
    if res is None:
        st.info("Optimizá primero desde la pestaña **Resultado**.")
    else:
        st.subheader("⏱️ Programación de camiones")
        st.markdown("---")

        supply = res["supply"]; demand = res["demand"]
        K_set  = res["K_set"]

        # ── Tabla entrada ──
        st.markdown("**🚛 Camiones de entrada**")
        rows_in = []
        for i in res["inbound_order"]:
            start   = res["inbound_schedule"][i]
            dur     = unload_time(i, supply, K_set)
            end     = start + dur
            units   = sum(supply.get(i, {}).get(k, 0) for k in K_set)
            prods   = ", ".join(f"P{k}({supply[i][k]})" for k in K_set if supply.get(i, {}).get(k, 0) > 0)
            rows_in.append({
                "Camión":        f"I{i}",
                "Inicio (min)":  start,
                "Fin (min)":     end,
                "Duración (min)":dur,
                "Unidades":      units,
                "Productos":     prods,
            })
        df_in = pd.DataFrame(rows_in)
        st.dataframe(df_in, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── Tabla salida ──
        st.markdown("**📤 Camiones de salida**")
        rows_out = []
        for j in res["outbound_order"]:
            start   = res["outbound_schedule"][j]
            dur     = load_time(j, demand, K_set)
            end     = start + dur
            units   = sum(demand.get(j, {}).get(k, 0) for k in K_set)
            prods   = ", ".join(f"P{k}({demand[j][k]})" for k in K_set if demand.get(j, {}).get(k, 0) > 0)
            rows_out.append({
                "Camión":        f"O{j}",
                "Inicio (min)":  start,
                "Fin (min)":     end,
                "Duración (min)":dur,
                "Unidades":      units,
                "Productos":     prods,
            })
        df_out = pd.DataFrame(rows_out)
        st.dataframe(df_out, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── Gantt ──
        st.subheader("📅 Diagrama de Gantt")
        gantt_rows = []
        for r2 in rows_in:
            gantt_rows.append({"Camión": r2["Camión"], "Tipo": "Entrada",
                                "Inicio": r2["Inicio (min)"], "Fin": r2["Fin (min)"]})
        for r2 in rows_out:
            gantt_rows.append({"Camión": r2["Camión"], "Tipo": "Salida",
                                "Inicio": r2["Inicio (min)"], "Fin": r2["Fin (min)"]})

        df_gantt = pd.DataFrame(gantt_rows)
        gantt = (
            alt.Chart(df_gantt)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height=22)
            .encode(
                x=alt.X("Inicio:Q", title="Tiempo (min)"),
                x2="Fin:Q",
                y=alt.Y("Camión:N", sort=None, title=""),
                color=alt.Color("Tipo:N", scale=alt.Scale(
                    domain=["Entrada", "Salida"],
                    range=["#e91e8c", "#f48fb1"]
                )),
                tooltip=["Camión:N", "Tipo:N", "Inicio:Q", "Fin:Q"]
            )
            .properties(height=max(200, len(gantt_rows) * 36))
        )
        st.altair_chart(gantt, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# TAB 3 — FLUJO DE PRODUCTOS
# ══════════════════════════════════════════════════════════════
with tab3:
    if res is None:
        st.info("Optimizá primero desde la pestaña **Resultado**.")
    else:
        st.subheader("📦 Flujo de unidades entre camiones")
        st.markdown("---")

        # Matriz I × J
        I_set = res["I_set"]; J_set = res["J_set"]
        matrix_data = []
        for i in I_set:
            row = {"Entrante": f"I{i}"}
            for j in J_set:
                row[f"→ O{j}"] = res["flow"].get((i, j), 0)
            row["Total salida"] = sum(res["flow"].get((i, j), 0) for j in J_set)
            matrix_data.append(row)

        # Totales por columna
        totals = {"Entrante": "Total recibido"}
        for j in J_set:
            totals[f"→ O{j}"] = sum(res["flow"].get((i, j), 0) for i in I_set)
        totals["Total salida"] = sum(res["flow"].values())
        matrix_data.append(totals)

        df_matrix = pd.DataFrame(matrix_data)
        st.dataframe(df_matrix, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📊 Unidades por ruta (I→O)")

        flow_rows = [{"Ruta": f"I{i} → O{j}", "Unidades": u}
                     for (i, j), u in sorted(res["flow"].items())]
        df_flow = pd.DataFrame(flow_rows)

        bar_flow = (
            alt.Chart(df_flow)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Ruta:N", axis=alt.Axis(labelAngle=-30)),
                y=alt.Y("Unidades:Q"),
                color=alt.value("#e91e8c"),
                tooltip=["Ruta:N", "Unidades:Q"]
            )
            .properties(height=300)
        )
        st.altair_chart(bar_flow, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# TAB 4 — DATOS DEL PROBLEMA
# ══════════════════════════════════════════════════════════════
with tab4:
    # Parsear siempre para mostrar datos aunque no se haya optimizado
    try:
        I, O, N, supply, demand = parse_ts(ts_text)
        K_set_p = list(range(1, N + 1))
        I_set_p = list(range(1, I + 1))
        J_set_p = list(range(1, O + 1))

        st.subheader("📊 Resumen del problema")
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Camiones entrantes (i)", I)
        c2.metric("Camiones salientes (o)", O)
        c3.metric("Tipos de producto (n)",  N)

        st.markdown("---")
        st.subheader("🚛 Carga por camión entrante")
        in_rows = []
        for i in I_set_p:
            row = {"Camión": f"I{i}"}
            total = 0
            for k in K_set_p:
                q = supply.get(i, {}).get(k, 0)
                row[f"P{k}"] = q if q > 0 else ""
                total += q
            row["Total"] = total
            in_rows.append(row)
        st.dataframe(pd.DataFrame(in_rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📤 Pedidos por camión saliente")
        out_rows = []
        for j in J_set_p:
            row = {"Camión": f"O{j}"}
            total = 0
            for k in K_set_p:
                q = demand.get(j, {}).get(k, 0)
                row[f"P{k}"] = q if q > 0 else ""
                total += q
            row["Total"] = total
            out_rows.append(row)
        st.dataframe(pd.DataFrame(out_rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("⚖️ Balance por producto")
        bal_rows = []
        for k in K_set_p:
            s = sum(supply.get(i, {}).get(k, 0) for i in I_set_p)
            d_tot = sum(demand.get(j, {}).get(k, 0) for j in J_set_p)
            bal_rows.append({
                "Producto":   f"P{k}",
                "Oferta":     s,
                "Demanda":    d_tot,
                "Balance":    "✅ OK" if s == d_tot else f"⚠️ Diferencia: {s-d_tot}"
            })
        st.dataframe(pd.DataFrame(bal_rows), use_container_width=True, hide_index=True)

    except Exception as e:
        st.warning(f"No se pudo parsear el archivo TS: {e}")
