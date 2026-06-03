# ☀️🚚 Optimización Industrial — UCR

> Proyecto del curso **Modelos de Optimización Industrial I**  
> Universidad de Costa Rica · I Semestre 2026  
> **Estudiantes:** Elisa Velázquez Jiménez (C4K907) · Liz Calvo Cordero (C4D553)  
> **Profesor:** David Benavides

---

## 📁 Estructura del repositorio

```
.
├── modelo_paneles.py         # Modelo PLE — paneles solares
├── app_paneles.py            # App Streamlit — paneles solares
├── requirements.txt          # Dependencias paneles
│
├── modelo_crossdock.py       # Modelo MIP — cross-docking LogiFast CR
├── app_crossdock.py          # App Streamlit — cross-docking
├── requirements_crossdock.txt
│
└── README.md
```

---

## Parte A — Optimizador de Paneles Solares

Modelo de **Programación Lineal Entera (PLE)** que minimiza la inversión en paneles solares fotovoltaicos para hogares costarricenses, garantizando que la energía generada cubra el consumo mensual y no se exceda el área de techo disponible.

### Paneles disponibles

| Panel | Potencia | Área   | Costo  | Energía mensual* |
|-------|----------|--------|--------|------------------|
| A     | 400 W    | 1.9 m² | $190   | 43.2 kWh/mes     |
| B     | 450 W    | 2.1 m² | $205   | 48.6 kWh/mes     |
| C     | 550 W    | 2.5 m² | $255   | 59.4 kWh/mes     |

> *`E = Pdc × HSP × PR` con HSP = 4.5 h/día y PR = 0.80*

### Modelo matemático

**Variables:** `CA`, `CB`, `CC` — cantidad de cada panel (enteros ≥ 0)

```
Min W = 190·CA + 205·CB + 255·CC

R1: CA + CB + CC ≥ 1
R2: 1.9·CA + 2.1·CB + 2.5·CC ≤ área_techo
R3: E_A·CA + E_B·CB + E_C·CC ≥ demanda_mensual / días
    CA, CB, CC ∈ ℤ⁺
```

### Ejecutar

```bash
pip install -r requirements.txt
streamlit run app_paneles.py
```

La app tiene 4 pestañas: **Optimizador · Análisis Financiero · Análisis Energético · Referencia de Paneles**

---

## Parte B — Cross-Docking LogiFast CR

Modelo de **Programación Entera Mixta (MIP)** que minimiza el tiempo total de operación (makespan) de un centro de distribución *cross-docking*, determinando el orden óptimo de atención de camiones entrantes y salientes.

### Descripción del problema

LogiFast CR opera un centro con 1 muelle de recepción y 1 de despacho. Los productos de los camiones proveedores deben transferirse a los camiones de clientes en el menor tiempo posible, usando almacenamiento temporal cuando sea necesario.

### Parámetros operativos

| Parámetro | Valor |
|-----------|-------|
| Carga/descarga por unidad | 1 min |
| Traslado interno por lote | 5 min |
| Cambio entre camiones | 10 min |
| Almacenamiento temporal | ilimitado |

### Modelo matemático

**Variables de decisión:**

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `x[i][j][k]` | Continua ≥ 0 | Unidades del producto k del camión i al camión j |
| `v[i][j]` | Binaria | 1 si fluye algún producto de i a j |
| `α[i1][i2]` | Binaria | 1 si el camión entrante i1 se atiende antes que i2 |
| `β[j1][j2]` | Binaria | 1 si el camión saliente j1 sale antes que j2 |
| `A[i]` | Continua ≥ 0 | Tiempo de inicio de atención del camión entrante i |
| `D[j]` | Continua ≥ 0 | Tiempo de partida del camión saliente j |
| `Cmax` | Continua ≥ 0 | Makespan (objetivo) |

**Función objetivo:**
```
Min Cmax
```

**Restricciones (13 en total):**
```
(1)  Cmax ≥ D[j] + tiempo_carga[j]                        ∀j
(2)  Σⱼ x[i][j][k] = supply[i][k]                         ∀i,k
(3)  Σᵢ x[i][j][k] = demand[j][k]                         ∀j,k
(4)  Σₖ x[i][j][k] ≤ supply_total[i] · v[i][j]           ∀i,j
(5)  A[i2] ≥ A[i1] + unload[i1] + t_change - M(1-α[i1,i2]) ∀i1≠i2
(6)  α[i1,i2] + α[i2,i1] = 1                              ∀i1<i2
(7)  α[i,i] no definida (no se precede a sí mismo)
(9)  D[j2] ≥ D[j1] + load[j1] + t_change - M(1-β[j1,j2])  ∀j1≠j2
(10) β[j1,j2] + β[j2,j1] = 1                              ∀j1<j2
(13) D[j] ≥ A[i] + unload[i] + t_trans - M(1-v[i][j])    ∀i,j
```

### Resultado para TS5

| | Valor |
|-|-------|
| Camiones entrada | 5 |
| Camiones salida | 3 |
| Tipos de producto | 8 |
| **Makespan óptimo** | **1710 min (28.5 h)** |
| Orden entrada | I5 → I2 → I3 → I4 → I1 |
| Orden salida | O3 → O2 → O1 |

### Ejecutar

```bash
pip install -r requirements_crossdock.txt
streamlit run app_crossdock.py
```

La app acepta cualquier archivo TS con el mismo formato (cualquier número de camiones y productos) y tiene 4 pestañas: **Resultado · Programación (Gantt) · Flujo de productos · Datos del problema**

---

## 📚 Referencias

- Messenger, R. A., & Abtahi, A. (2017). *Photovoltaic Systems Engineering* (4ta ed.). CRC Press.
- Autoridad Reguladora de los Servicios Públicos. *Tarifas electricidad*. https://aresep.go.cr
- Boysen, N., Fliedner, M., & Scholl, A. (2010). Scheduling inbound and outbound trucks at cross docking terminals. *OR Spectrum*, 32(1), 135–161.
