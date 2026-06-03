import streamlit as st
import pandas as pd
import altair as alt
from modelo_logifast import parse_ts, resolver, TS5_DEFAULT

st.set_page_config(page_title="LogiFast CR — Cross Docking", page_icon="🚚", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@400;600;700&display=swap');
*, body, .stApp { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'DM Serif Display', serif !important; }
.stApp { background: #1a000d; }
[data-testid="stSidebar"] { background: #2a0016; }
[data-testid="stSidebar"] * { color: #f8bbd0 !important; }
.stTabs [data-baseweb="tab-list"] { background:#2a0016; border-radius:12px; padding:4px; gap:4px; }
.stTabs [data-baseweb="tab"] { color:#f48fb1; font-weight:600; border-radius:8px; }
.stTabs [aria-selected="true"] { background:#880e4f !important; color:#fff !important; }
.stApp,.stApp p,.stApp label,.stApp span,.stApp div { color:#f8bbd0; }
h1,h2,h3 { color:#f48fb1 !important; }
[data-testid="stMetricValue"] { font-size:1.5rem !important; color:#f48fb1; font-weight:700; }
[data-testid="stMetricLabel"] { color:#f8bbd0; font-weight:600; }
[data-testid="metric-container"] { background:linear-gradient(135deg,#3d0022,#2a0016); border:1px solid #880e4f; border-radius:14px; padding:14px 18px; }
.stButton>button { background:linear-gradient(135deg,#880e4f,#c2185b); color:#fff; border:none; border-radius:10px; font-weight:700; padding:.5rem 1.4rem; }
.stButton>button:hover { background:linear-gradient(135deg,#ad1457,#e91e8c); }
hr { border-color:#880e4f; opacity:.4; }
.stSuccess { background:#3d0022 !important; border-left:4px solid #f48fb1 !important; }
.stInfo    { background:#2a0016 !important; border-left:4px solid #880e4f !important; }
.stError   { background:#3d0022 !important; border-left:4px solid #c2185b !important; }
[data-testid="stDataFrame"] { background:#2a0016; border-radius:10px; }
[data-testid="stDataFrame"] * { color:#f8bbd0 !important; }
.stTextArea textarea { background:#2a0016 !important; color:#f8bbd0 !important; border:1px solid #880e4f !important; }
.block-container { padding-top:1.6rem; max-width:1200px; }
</style>
""", unsafe_allow_html=True)

st.title("🚚 LogiFast CR — Optimización Cross Docking")
st.caption("Programación Entera Mixta · Minimiza makespan · PuLP + CBC")

# ── Sidebar ──────────────────────────────────────────────────
st.sidebar.header("⚙️ Parámetros")
t_unit   = st.sidebar.number_input("Tiempo carga/descarga (min/unidad)", 1, 10, 1)
t_trans  = st.sidebar.number_input("Tiempo traslado interno (min/lote)", 1, 30, 5)
t_change = st.sidebar.number_input("Tiempo cambio camión (min)", 1, 30, 10)
time_lim = st.sidebar.slider("Límite tiempo solver (seg)", 30, 300, 120)
st.sidebar.markdown("---")
st.sidebar.subheader("📂 Datos (formato TS)")
ts_input = st.sidebar.text_area("Pegá tu archivo TS aquí", value=TS5_DEFAULT, height=160)
resolver_btn = st.sidebar.button("🚀 Resolver", use_container_width=True)

# ── Resolver ─────────────────────────────────────────────────
if "resultado" not in st.session_state:
    data = parse_ts(TS5_DEFAULT)
    st.session_state["resultado"] = resolver(data)
    st.session_state["data"] = data

if resolver_btn:
    with st.spinner("Resolviendo MIP…"):
        import modelo_logifast as _m
        _m.T_UNIT = t_unit; _m.T_TRANS = t_trans; _m.T_CHANGE = t_change
        data = parse_ts(ts_input)
        st.session_state["resultado"] = resolver(data, time_limit=time_lim)
        st.session_state["data"] = data

res  = st.session_state["resultado"]
data = st.session_state["data"]
ok   = res["estado"] == 1

# ── Tabs ─────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Resultado", "📦 Datos del problema", "📐 Modelo matemático", "🔄 Diagrama de flujo"
])

# ════════════════════════════════════════════════════════════
# TAB 1 — RESULTADO
# ════════════════════════════════════════════════════════════
with tab1:
    if not ok:
        st.error(f"❌ Estado del solver: {res['estado_texto']}")
    else:
        makespan = int(res["makespan"])
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("⏱️ Makespan", f"{makespan} min", f"{makespan/60:.1f} h")
        c2.metric("🚛 Camiones entrada", res["I"])
        c3.metric("🚚 Camiones salida",  res["O"])
        c4.metric("📦 Productos",        res["N"])

        st.markdown("---")
        col_in, col_out = st.columns(2)

        with col_in:
            st.subheader("🚛 Orden de entrada (inbound)")
            rows = []
            t_acum = 0.0
            for i in res["inbound_order"]:
                at = res["ar"][i] or 0
                rows.append({
                    "Orden": res["inbound_order"].index(i)+1,
                    "Camión": f"Inbound {i}",
                    "Llegada (min)": int(at),
                    "Unidades": res["R"][i],
                    "Descarga (min)": res["R"][i] * t_unit,
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        with col_out:
            st.subheader("🚚 Orden de salida (outbound)")
            rows2 = []
            for j in res["outbound_order"]:
                dt = res["ds"][j] or 0
                rows2.append({
                    "Orden": res["outbound_order"].index(j)+1,
                    "Camión": f"Outbound {j}",
                    "Salida (min)": int(dt),
                    "Unidades": res["S"][j],
                    "Carga (min)": res["S"][j] * t_unit,
                })
            st.dataframe(pd.DataFrame(rows2), use_container_width=True, hide_index=True)

        # Gantt
        st.markdown("---")
        st.subheader("📅 Diagrama de Gantt")

        gantt_rows = []
        for i in res["inbound_order"]:
            at = res["ar"][i] or 0
            dur = res["R"][i] * t_unit
            gantt_rows.append({"Camión": f"IN-{i}", "Inicio": at, "Fin": at+dur, "Tipo": "Entrada"})
        for j in res["outbound_order"]:
            dt = res["ds"][j] or 0
            # estimate start = departure - load time
            load = res["S"][j] * t_unit
            gantt_rows.append({"Camión": f"OUT-{j}", "Inicio": max(0, dt-load), "Fin": dt, "Tipo": "Salida"})

        df_gantt = pd.DataFrame(gantt_rows)
        gantt = (
            alt.Chart(df_gantt)
            .mark_bar(height=28, cornerRadius=4)
            .encode(
                x=alt.X("Inicio:Q", title="Tiempo (min)"),
                x2="Fin:Q",
                y=alt.Y("Camión:N", sort=None, title=None),
                color=alt.Color("Tipo:N", scale=alt.Scale(
                    domain=["Entrada","Salida"], range=["#f48fb1","#e91e8c"]
                )),
                tooltip=["Camión:N","Inicio:Q","Fin:Q","Tipo:N"]
            )
            .properties(height=260)
        )
        rule = alt.Chart(pd.DataFrame({"x":[makespan]})).mark_rule(
            color="#fff", strokeDash=[4,4], strokeWidth=2
        ).encode(x="x:Q")
        st.altair_chart(gantt + rule, use_container_width=True)
        st.caption(f"Línea blanca = makespan ({makespan} min)")

        # Asignaciones
        st.markdown("---")
        st.subheader("🔀 Asignaciones producto (inbound → outbound)")
        if res["asignaciones"]:
            df_asig = pd.DataFrame(res["asignaciones"])
            df_asig.columns = ["Inbound","Outbound","Producto","Unidades"]
            st.dataframe(df_asig, use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron asignaciones detalladas.")

# ════════════════════════════════════════════════════════════
# TAB 2 — DATOS
# ════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📦 Datos del problema")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Camiones de entrada (inbound)**")
        r_rows = []
        for i in range(1, data["I"]+1):
            for k, q in sorted(data["r_data"].get(i,{}).items()):
                r_rows.append({"Camión": f"Inbound {i}", "Producto": k, "Unidades": q})
        st.dataframe(pd.DataFrame(r_rows), use_container_width=True, hide_index=True)

    with c2:
        st.markdown("**Camiones de salida (outbound)**")
        s_rows = []
        for j in range(1, data["O"]+1):
            for k, q in sorted(data["s_data"].get(j,{}).items()):
                s_rows.append({"Camión": f"Outbound {j}", "Producto": k, "Unidades": q})
        st.dataframe(pd.DataFrame(s_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📊 Unidades totales por camión")
    if ok:
        df_vol = pd.DataFrame(
            [{"Camión": f"IN-{i}", "Unidades": res["R"][i], "Tipo":"Entrada"} for i in range(1,data["I"]+1)] +
            [{"Camión": f"OUT-{j}", "Unidades": res["S"][j], "Tipo":"Salida"} for j in range(1,data["O"]+1)]
        )
        bar = (
            alt.Chart(df_vol).mark_bar(cornerRadiusTopLeft=5,cornerRadiusTopRight=5)
            .encode(
                x=alt.X("Camión:N", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Unidades:Q"),
                color=alt.Color("Tipo:N", scale=alt.Scale(
                    domain=["Entrada","Salida"], range=["#f48fb1","#e91e8c"])),
                tooltip=["Camión:N","Unidades:Q","Tipo:N"]
            ).properties(height=250)
        )
        st.altair_chart(bar, use_container_width=True)

    st.markdown("---")
    st.subheader("🗺️ Matriz producto × camión (inbound)")
    prods = list(range(1, data["N"]+1))
    mat = {f"IN-{i}": {f"P{k}": data["r_data"].get(i,{}).get(k,0) for k in prods}
           for i in range(1,data["I"]+1)}
    st.dataframe(pd.DataFrame(mat).T, use_container_width=True)

# ════════════════════════════════════════════════════════════
# TAB 3 — MODELO MATEMÁTICO
# ════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📐 Formulación MIP — Cross Docking LogiFast")
    st.markdown("---")

    c1, c2 = st.columns([1,1], gap="large")
    with c1:
        st.markdown("### Conjuntos")
        st.markdown("""
- $I$ = camiones de entrada (inbound)  
- $J$ = camiones de salida (outbound)  
- $K$ = tipos de producto
""")
        st.markdown("### Variables de decisión")
        st.markdown("""
| Variable | Tipo | Descripción |
|----------|------|-------------|
| $x_{ijk}$ | Continua ≥ 0 | Unidades de prod. $k$ del inbound $i$ al outbound $j$ |
| $v_{ij}$ | Binaria | 1 si inbound $i$ transfiere algo a outbound $j$ |
| $\\sigma^r_{ip}$ | Binaria | 1 si inbound $i$ va antes que $p$ |
| $\\sigma^s_{jq}$ | Binaria | 1 si outbound $j$ sale antes que $q$ |
| $a_i^r$ | Continua ≥ 0 | Tiempo de llegada al muelle del inbound $i$ |
| $d_j^s$ | Continua ≥ 0 | Tiempo de salida del muelle del outbound $j$ |
| $C$ | Continua ≥ 0 | Makespan (tiempo total de operación) |
""")

        st.markdown("### Función objetivo")
        st.latex(r"\min \; C")

        st.markdown("### Restricciones clave")
        st.latex(r"(1)\quad C \geq d_j^s \quad \forall j \in J")
        st.latex(r"(2)\quad \sum_j x_{ijk} = r_{ik} \quad \forall i,k")
        st.latex(r"(3)\quad \sum_i x_{ijk} = s_{jk} \quad \forall j,k")
        st.latex(r"(4)\quad \sum_k x_{ijk} \leq M \cdot v_{ij} \quad \forall i,j")
        st.latex(r"(5\text{-}7)\quad a_p^r \geq a_i^r + t^{desc}_i + t_{cambio} - M(1-\sigma^r_{ip})")
        st.latex(r"(8)\quad \sigma^r_{ip} + \sigma^r_{pi} = 1 \quad \forall i \neq p")
        st.latex(r"(9\text{-}12)\quad \text{Análogos para outbound}")
        st.latex(r"(13)\quad d_j^s \geq a_i^r + t^{desc}_i + t_{traslado} - M(1-v_{ij})")

    with c2:
        st.markdown("### Parámetros operativos")
        st.markdown(f"""
| Parámetro | Valor |
|-----------|-------|
| $t_{{unit}}$ — min/unidad | {t_unit} min |
| $t_{{traslado}}$ — min/lote | {t_trans} min |
| $t_{{cambio}}$ — entre camiones | {t_change} min |
| Almacenamiento temporal | Ilimitado |
""")
        if ok:
            st.markdown("---")
            st.markdown("### ✅ Solución actual")
            st.latex(rf"C^* = {int(res['makespan'])}\text{{ min}} = {res['makespan']/60:.1f}\text{{ h}}")
            st.markdown("**Secuencia inbound:**  " +
                " → ".join(f"IN-{i}" for i in res["inbound_order"]))
            st.markdown("**Secuencia outbound:**  " +
                " → ".join(f"OUT-{j}" for j in res["outbound_order"]))

            st.markdown("**Tamaño del modelo:**")
            I,O,N = data["I"],data["O"],data["N"]
            st.markdown(f"""
- Variables continuas $x$: {I}×{O}×{N} = **{I*O*N}**  
- Variables binarias $v$: {I}×{O} = **{I*O}**  
- Variables binarias $\\sigma^r$: {I}×({I}-1) = **{I*(I-1)}**  
- Variables binarias $\\sigma^s$: {O}×({O}-1) = **{O*(O-1)}**  
- **Total variables: {I*O*N + I*O + I*(I-1) + O*(O-1)}**
""")

# ════════════════════════════════════════════════════════════
# TAB 4 — DIAGRAMA DE FLUJO
# ════════════════════════════════════════════════════════════
with tab4:
    st.subheader("🔄 Flujo de productos — Inbound → Outbound")
    if not ok:
        st.info("Resolvé primero para ver el diagrama.")
    else:
        # Sankey-style usando Altair como heatmap de flujo
        st.markdown("**Matriz de transferencia (unidades de producto entre camiones)**")
        I, O, N = data["I"], data["O"], data["N"]
        matrix = []
        for i in range(1, I+1):
            for j in range(1, O+1):
                total = sum(
                    round(a["unidades"])
                    for a in res["asignaciones"]
                    if a["inbound"] == i and a["outbound"] == j
                )
                matrix.append({"Inbound": f"IN-{i}", "Outbound": f"OUT-{j}", "Unidades": total})

        df_mat = pd.DataFrame(matrix)
        heat = (
            alt.Chart(df_mat)
            .mark_rect(cornerRadius=4)
            .encode(
                x=alt.X("Outbound:N", title="Camión de salida"),
                y=alt.Y("Inbound:N",  title="Camión de entrada"),
                color=alt.Color("Unidades:Q", scale=alt.Scale(
                    scheme="pinkwhitegreen" , reverse=True
                ), title="Unidades"),
                tooltip=["Inbound:N","Outbound:N","Unidades:Q"]
            )
            .properties(height=300, title="Calor = más unidades transferidas")
        )
        text_overlay = (
            alt.Chart(df_mat)
            .mark_text(fontSize=14, fontWeight="bold", color="#f8bbd0")
            .encode(
                x="Outbound:N", y="Inbound:N",
                text=alt.Text("Unidades:Q", format=".0f")
            )
        )
        st.altair_chart(heat + text_overlay, use_container_width=True)

        st.markdown("---")
        st.markdown("**Detalle por producto**")
        if res["asignaciones"]:
            df_det = pd.DataFrame(res["asignaciones"])
            df_det.columns = ["Inbound","Outbound","Producto","Unidades"]
            df_det["Inbound"]  = df_det["Inbound"].apply(lambda x: f"IN-{x}")
            df_det["Outbound"] = df_det["Outbound"].apply(lambda x: f"OUT-{x}")
            df_det["Producto"] = df_det["Producto"].apply(lambda x: f"P{x}")
            st.dataframe(df_det.sort_values(["Inbound","Outbound","Producto"]),
                        use_container_width=True, hide_index=True)
