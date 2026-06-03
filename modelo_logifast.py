import re
from collections import defaultdict
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, value, PULP_CBC_CMD, LpStatus

# ── Parámetros operativos ────────────────────────────────────
T_UNIT   = 1    # min/unidad carga-descarga
T_TRANS  = 5    # min traslado interno por lote
T_CHANGE = 10   # min cambio entre camiones
BIG_M    = 100_000


def parse_ts(text: str) -> dict:
    """Parsea el formato TS del archivo de datos."""
    clean = re.sub(r'(\d)([rsiond])', r'\1 \2', text)
    tokens = clean.split()
    idx = 0
    I = O = N = 0
    while idx < len(tokens):
        t = tokens[idx]
        if   t == 'i': I = int(tokens[idx+1]); idx += 2
        elif t == 'o': O = int(tokens[idx+1]); idx += 2
        elif t == 'n': N = int(tokens[idx+1]); idx += 2
        else: break

    r_data = defaultdict(lambda: defaultdict(int))
    s_data = defaultdict(lambda: defaultdict(int))
    while idx + 3 < len(tokens):
        kind  = tokens[idx]
        truck = int(tokens[idx+1])
        prod  = int(tokens[idx+2])
        qty   = int(tokens[idx+3])
        if kind == 'r': r_data[truck][prod] = qty
        elif kind == 's': s_data[truck][prod] = qty
        idx += 4

    return {"I": I, "O": O, "N": N,
            "r_data": {k: dict(v) for k, v in r_data.items()},
            "s_data": {k: dict(v) for k, v in s_data.items()}}


def resolver(data: dict, time_limit: int = 120) -> dict:
    """
    Resuelve el MIP de cross-docking LogiFast.
    Retorna makespan, orden de camiones, tiempos y asignaciones.
    """
    I = data["I"]; O = data["O"]; N = data["N"]
    r_data = data["r_data"]; s_data = data["s_data"]

    inbounds  = list(range(1, I+1))
    outbounds = list(range(1, O+1))
    products  = list(range(1, N+1))

    R = {i: sum(r_data.get(i, {}).values()) for i in inbounds}
    S = {j: sum(s_data.get(j, {}).values()) for j in outbounds}

    model = LpProblem("LogiFast_CrossDocking", LpMinimize)

    # Variables
    x = {(i,j,k): LpVariable(f"x_{i}_{j}_{k}", lowBound=0)
         for i in inbounds for j in outbounds for k in products}
    v = {(i,j): LpVariable(f"v_{i}_{j}", cat='Binary')
         for i in inbounds for j in outbounds}
    sr = {(i,p): LpVariable(f"sr_{i}_{p}", cat='Binary')
          for i in inbounds for p in inbounds if i != p}
    ss = {(j,q): LpVariable(f"ss_{j}_{q}", cat='Binary')
          for j in outbounds for q in outbounds if j != q}
    ar = {i: LpVariable(f"ar_{i}", lowBound=0) for i in inbounds}
    ds = {j: LpVariable(f"ds_{j}", lowBound=0) for j in outbounds}
    C  = LpVariable("C", lowBound=0)

    model += C  # minimize makespan

    # (1) Makespan
    for j in outbounds:
        model += C >= ds[j]

    # (2) Conservación producto en inbound
    for i in inbounds:
        for k in products:
            model += lpSum(x[i,j,k] for j in outbounds) == r_data.get(i, {}).get(k, 0)

    # (3) Conservación producto en outbound
    for j in outbounds:
        for k in products:
            model += lpSum(x[i,j,k] for i in inbounds) == s_data.get(j, {}).get(k, 0)

    # (4) Relación x-v
    BX = max(max(R.values()), max(S.values())) + 1
    for i in inbounds:
        for j in outbounds:
            model += lpSum(x[i,j,k] for k in products) <= BX * v[i,j]

    # (5-7) Secuencia inbound
    for i in inbounds:
        for p in inbounds:
            if i != p:
                unload_i = T_UNIT * lpSum(x[i,j,k] for j in outbounds for k in products) + T_CHANGE
                model += ar[p] >= ar[i] + unload_i - BIG_M*(1 - sr[i,p])

    # (8) Antisimetría inbound
    for i in inbounds:
        for p in inbounds:
            if i != p:
                model += sr[i,p] + sr[p,i] == 1

    # (9-11) Secuencia outbound
    for j in outbounds:
        for q in outbounds:
            if j != q:
                load_j = T_UNIT * lpSum(x[i,j,k] for i in inbounds for k in products) + T_CHANGE
                model += ds[q] >= ds[j] + load_j - BIG_M*(1 - ss[j,q])

    # (12) Antisimetría outbound
    for j in outbounds:
        for q in outbounds:
            if j != q:
                model += ss[j,q] + ss[q,j] == 1

    # (13) Salida outbound >= llegada inbound + descarga + traslado
    for i in inbounds:
        for j in outbounds:
            model += ds[j] >= ar[i] + T_UNIT*R[i] + T_TRANS - BIG_M*(1 - v[i,j])

    model.solve(PULP_CBC_CMD(msg=0, timeLimit=time_limit))

    makespan = value(C)
    ar_vals  = {i: value(ar[i]) for i in inbounds}
    ds_vals  = {j: value(ds[j]) for j in outbounds}

    # Orden de camiones por tiempo
    inbound_order  = sorted(inbounds,  key=lambda i: ar_vals[i] or 0)
    outbound_order = sorted(outbounds, key=lambda j: ds_vals[j] or 0)

    # Asignaciones x[i,j,k] > 0
    asignaciones = []
    for i in inbounds:
        for j in outbounds:
            for k in products:
                val = value(x[i,j,k])
                if val and val > 0.01:
                    asignaciones.append({
                        "inbound": i, "outbound": j,
                        "producto": k, "unidades": round(val)
                    })

    return {
        "estado":         model.status,
        "estado_texto":   LpStatus[model.status],
        "makespan":       makespan,
        "ar":             ar_vals,
        "ds":             ds_vals,
        "inbound_order":  inbound_order,
        "outbound_order": outbound_order,
        "asignaciones":   asignaciones,
        "R": R, "S": S,
        "I": I, "O": O, "N": N,
        "r_data": r_data, "s_data": s_data,
    }


# ── Datos TS5 por defecto ────────────────────────────────────
TS5_DEFAULT = "i\t5\t\to\t3\t\tn\t8\t\tr\t1\t1\t170r\t2\t1\t6r\t2\t2\t6r\t2\t3\t19r\t2\t4\t50r\t2\t5\t38r\t2\t6\t6r\t2\t7\t19r\t2\t8\t56r\t3\t1\t49r\t3\t2\t31r\t3\t3\t60r\t3\t6\t12r\t3\t7\t37r\t3\t8\t31r\t4\t5\t143r\t4\t7\t47r\t5\t4\t58r\t5\t5\t36r\t5\t7\t72r\t5\t8\t14s\t1\t1\t75s\t1\t2\t12s\t1\t3\t59s\t1\t6\t9s\t1\t7\t98s\t1\t8\t40s\t2\t1\t150s\t2\t5\t217s\t3\t2\t25s\t3\t3\t20s\t3\t4\t108s\t3\t6\t9s\t3\t7\t77s\t3\t8\t61"
