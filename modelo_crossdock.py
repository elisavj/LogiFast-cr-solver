"""
modelo_crossdock.py
MIP de Cross-Docking — LogiFast CR
Minimiza el makespan (tiempo total de operación del almacén)
"""
import re
from pulp import (LpProblem, LpMinimize, LpVariable, LpStatus,
                  lpSum, value, PULP_CBC_CMD)

# ── Parámetros operativos ────────────────────────────────────
T_UNIT   = 1    # min por unidad (carga/descarga)
T_TRANS  = 5    # min traslado interno por lote
T_CHANGE = 10   # min cambio entre camiones
BIG_M    = 99_999


def parse_ts(text: str) -> tuple[int, int, int, dict, dict]:
    """
    Parsea el formato TS del problema.
    Retorna (I, O, N, supply, demand)
      supply[i][k] = unidades del producto k en camión entrante i
      demand[j][k] = unidades del producto k requeridas por camión saliente j
    """
    # Encabezado: i O o O n O
    m_i = re.search(r'i\s+(\d+)', text)
    m_o = re.search(r'o\s+(\d+)', text)
    m_n = re.search(r'n\s+(\d+)', text)
    I = int(m_i.group(1)); O = int(m_o.group(1)); N = int(m_n.group(1))

    supply: dict[int, dict[int, int]] = {}
    demand: dict[int, dict[int, int]] = {}

    for tok in re.findall(r'[rs]\s+\d+\s+\d+\s+\d+', text):
        parts = tok.split()
        t, a, b, q = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
        if t == 'r':
            supply.setdefault(a, {})[b] = q
        else:
            demand.setdefault(a, {})[b] = q

    return I, O, N, supply, demand


def unload_time(i: int, supply: dict, K: list) -> int:
    """Tiempo de descarga del camión entrante i."""
    return sum(supply.get(i, {}).get(k, 0) for k in K) * T_UNIT + T_TRANS


def load_time(j: int, demand: dict, K: list) -> int:
    """Tiempo de carga del camión saliente j."""
    return sum(demand.get(j, {}).get(k, 0) for k in K) * T_UNIT + T_TRANS


def resolver_crossdock(text: str, time_limit: int = 120) -> dict:
    """
    Resuelve el MIP de cross-docking dado el texto TS.

    Retorna dict con:
      - status, makespan
      - inbound_schedule: {i: start_time}
      - outbound_schedule: {j: depart_time}
      - inbound_order, outbound_order (listas ordenadas)
      - flow: {(i,j): total_units}
      - supply, demand, I, O, N
    """
    I, O, N, supply, demand = parse_ts(text)
    I_set = list(range(1, I + 1))
    J_set = list(range(1, O + 1))
    K_set = list(range(1, N + 1))

    def r(i, k): return supply.get(i, {}).get(k, 0)
    def d(j, k): return demand.get(j, {}).get(k, 0)

    prob = LpProblem("CrossDocking_LogiFast", LpMinimize)

    # Variables continuas: flujo de producto k del camión i al j
    x = {(i, j, k): LpVariable(f"x_{i}_{j}_{k}", lowBound=0)
         for i in I_set for j in J_set for k in K_set}

    # Binarias: v[i][j] = 1 si fluye algo de i a j
    v = {(i, j): LpVariable(f"v_{i}_{j}", cat='Binary')
         for i in I_set for j in J_set}

    # Binarias de secuencia entrada
    alpha = {(i1, i2): LpVariable(f"a_{i1}_{i2}", cat='Binary')
             for i1 in I_set for i2 in I_set if i1 != i2}

    # Binarias de secuencia salida
    beta = {(j1, j2): LpVariable(f"b_{j1}_{j2}", cat='Binary')
            for j1 in J_set for j2 in J_set if j1 != j2}

    # Tiempos de inicio de servicio
    A = {i: LpVariable(f"A_{i}", lowBound=0) for i in I_set}
    D = {j: LpVariable(f"D_{j}", lowBound=0) for j in J_set}

    # Makespan
    Cmax = LpVariable("Cmax", lowBound=0)

    # ── Objetivo ──────────────────────────────────────────────
    prob += Cmax

    # (1) Cmax >= fin del último camión saliente
    for j in J_set:
        prob += Cmax >= D[j] + load_time(j, demand, K_set)

    # (2) Conservación oferta (inbound)
    for i in I_set:
        for k in K_set:
            prob += lpSum(x[i, j, k] for j in J_set) == r(i, k)

    # (3) Conservación demanda (outbound)
    for j in J_set:
        for k in K_set:
            prob += lpSum(x[i, j, k] for i in I_set) == d(j, k)

    # (4) Vinculación x y v
    for i in I_set:
        total_i = sum(r(i, k) for k in K_set)
        for j in J_set:
            if total_i > 0:
                prob += lpSum(x[i, j, k] for k in K_set) <= total_i * v[i, j]

    # (5)-(7) Secuencia camiones entrantes
    for i1 in I_set:
        for i2 in I_set:
            if i1 != i2:
                prob += (A[i2] >= A[i1] + unload_time(i1, supply, K_set)
                         + T_CHANGE - BIG_M * (1 - alpha[i1, i2]))

    for i1 in I_set:
        for i2 in I_set:
            if i1 < i2:
                prob += alpha[i1, i2] + alpha[i2, i1] == 1

    # (9)-(11) Secuencia camiones salientes
    for j1 in J_set:
        for j2 in J_set:
            if j1 != j2:
                prob += (D[j2] >= D[j1] + load_time(j1, demand, K_set)
                         + T_CHANGE - BIG_M * (1 - beta[j1, j2]))

    for j1 in J_set:
        for j2 in J_set:
            if j1 < j2:
                prob += beta[j1, j2] + beta[j2, j1] == 1

    # (13) Saliente j no puede partir antes de que entre i, si fluye entre ellos
    for i in I_set:
        for j in J_set:
            prob += (D[j] >= A[i] + unload_time(i, supply, K_set)
                     + T_TRANS - BIG_M * (1 - v[i, j]))

    # ── Solver ────────────────────────────────────────────────
    prob.solve(PULP_CBC_CMD(msg=0, timeLimit=time_limit))

    status   = LpStatus[prob.status]
    makespan = value(Cmax) if value(Cmax) else 0

    inbound_schedule  = {i: round(value(A[i]), 1) for i in I_set}
    outbound_schedule = {j: round(value(D[j]), 1) for j in J_set}

    inbound_order  = sorted(I_set, key=lambda i: inbound_schedule[i])
    outbound_order = sorted(J_set, key=lambda j: outbound_schedule[j])

    flow = {}
    for i in I_set:
        for j in J_set:
            total = sum(value(x[i, j, k]) or 0 for k in K_set)
            if total > 0.01:
                flow[(i, j)] = round(total)

    return {
        "status":            status,
        "makespan":          makespan,
        "inbound_schedule":  inbound_schedule,
        "outbound_schedule": outbound_schedule,
        "inbound_order":     inbound_order,
        "outbound_order":    outbound_order,
        "flow":              flow,
        "supply":            supply,
        "demand":            demand,
        "I": I, "O": O, "N": N,
        "I_set": I_set, "J_set": J_set, "K_set": K_set,
    }


if __name__ == "__main__":
    TS5 = """
    i 5 o 3 n 8
    r 1 1 170
    r 2 1 6  r 2 2 6  r 2 3 19 r 2 4 50 r 2 5 38 r 2 6 6  r 2 7 19 r 2 8 56
    r 3 1 49 r 3 2 31 r 3 3 60 r 3 6 12 r 3 7 37 r 3 8 31
    r 4 5 143 r 4 7 47
    r 5 4 58  r 5 5 36 r 5 7 72 r 5 8 14
    s 1 1 75  s 1 2 12 s 1 3 59 s 1 6 9  s 1 7 98 s 1 8 40
    s 2 1 150 s 2 5 217
    s 3 2 25  s 3 3 20 s 3 4 108 s 3 6 9 s 3 7 77 s 3 8 61
    """
    res = resolver_crossdock(TS5)
    print(f"Status  : {res['status']}")
    print(f"Makespan: {res['makespan']:.0f} min  ({res['makespan']/60:.1f} h)")
    print(f"Entrada : {'→'.join(f'I{i}' for i in res['inbound_order'])}")
    print(f"Salida  : {'→'.join(f'O{j}' for j in res['outbound_order'])}")
