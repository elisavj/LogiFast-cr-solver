# 🚚 Cross-Docking LogiFast CR — Optimización MIP

> Proyecto del curso **Modelos de Optimización Industrial I**  
> Universidad de Costa Rica · I Semestre 2026  
> **Estudiantes:** Elisa Velázquez Jiménez (C4K907) · Liz Calvo Cordero (C4D553)  
> **Profesor:** David Benavides

---

## 📁 Estructura del repositorio

```
.
├── modelo_crossdock.py        # Modelo MIP (PuLP) — lógica de optimización
├── app_crossdock.py           # Interfaz web interactiva (Streamlit)
├── requirements_crossdock.txt # Dependencias
└── README.md
```

---

## 📌 Descripción del problema

**LogiFast CR** opera un centro de distribución tipo *cross-docking* en el Valle Central de Costa Rica. Los productos de camiones proveedores deben transferirse a camiones de clientes en el menor tiempo posible, usando almacenamiento temporal cuando sea necesario.

El centro cuenta con:
- 1 muelle de recepción (entrada)
- 1 muelle de despacho (salida)
- Área de almacenamiento temporal (ilimitada, pero costosa en tiempo)

**Pregunta clave:** ¿En qué orden deben atenderse los camiones de entrada y salida para completar todas las operaciones en el menor tiempo posible?

### Parámetros operativos

| Parámetro | Valor |
|-----------|-------|
| Carga/descarga por unidad de producto | 1 min |
| Traslado interno por lote | 5 min |
| Cambio entre camiones | 10 min |
| Almacenamiento temporal | ilimitado |

---

## ⚙️ Modelo matemático

### Variables de decisión

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `x[i][j][k]` | Continua ≥ 0 | Unidades del producto `k` transferidas del camión entrante `i` al saliente `j` |
| `v[i][j]` | Binaria | 1 si fluye algún producto del camión `i` al camión `j` |
| `α[i1][i2]` | Binaria | 1 si el camión entrante `i1` se atiende antes que `i2` |
| `β[j1][j2]` | Binaria | 1 si el camión saliente `j1` parte antes que `j2` |
| `A[i]` | Continua ≥ 0 | Tiempo de inicio de descarga del camión entrante `i` |
| `D[j]` | Continua ≥ 0 | Tiempo de inicio de carga del camión saliente `j` |
| `Cmax` | Continua ≥ 0 | Makespan — tiempo total de operación (objetivo) |

### Función objetivo

```
Min Cmax
```

### Restricciones

```
(1)  Cmax ≥ D[j] + tiempo_carga[j]                              ∀j
     — el makespan es mayor o igual al fin del último camión saliente

(2)  Σⱼ x[i][j][k] = supply[i][k]                              ∀i, k
     — toda la carga del camión entrante i debe ser distribuida

(3)  Σᵢ x[i][j][k] = demand[j][k]                              ∀j, k
     — el camión saliente j debe recibir exactamente lo que necesita

(4)  Σₖ x[i][j][k] ≤ supply_total[i] · v[i][j]                ∀i, j
     — vincula las variables de flujo x con las binarias v

(5)  A[i2] ≥ A[i1] + unload[i1] + t_cambio − M(1−α[i1,i2])    ∀i1≠i2
     — secuencia válida de camiones entrantes

(6)  α[i1,i2] + α[i2,i1] = 1                                   ∀i1 < i2
     — entre cada par de entrantes, uno va antes que el otro

(7)  α[i,i] no definida — ningún camión se precede a sí mismo

(9)  D[j2] ≥ D[j1] + load[j1] + t_cambio − M(1−β[j1,j2])      ∀j1≠j2
     — secuencia válida de camiones salientes

(10) β[j1,j2] + β[j2,j1] = 1                                   ∀j1 < j2
     — entre cada par de salientes, uno va antes que el otro

(11) β[j,j] no definida — ningún camión se precede a sí mismo

(13) D[j] ≥ A[i] + unload[i] + t_trans − M(1−v[i][j])         ∀i, j
     — el camión saliente j no puede partir antes de que el entrante i
       haya terminado su descarga, si transfieren productos entre ellos
```

---

## 📂 Formato del archivo TS

```
i <num_entrantes>  o <num_salientes>  n <num_productos>
r <camión> <producto> <cantidad>   # camión que llega (r = recibe)
s <camión> <producto> <cantidad>   # camión que sale  (s = sale)
```

Ejemplo:
```
r 2 1 6    → Camión entrante 2, producto 1, 6 unidades
s 1 2 12   → Camión saliente 1, producto 2, 12 unidades
```

---

## 📊 Resultado para TS5

| | |
|-|-|
| Camiones de entrada | 5 |
| Camiones de salida | 3 |
| Tipos de producto | 8 |
| **Makespan óptimo** | **1710 min (28.5 h)** |
| Orden de entrada | I5 → I2 → I3 → I4 → I1 |
| Orden de salida | O3 → O2 → O1 |

---

## 🚀 Instalación y uso

### Requisitos

- Python 3.10+
- pip

### Instalación

```bash
git clone https://github.com/tu-usuario/crossdocking-logifastcr.git
cd crossdocking-logifastcr
pip install -r requirements_crossdock.txt
```

### Ejecutar el modelo por consola

```bash
python modelo_crossdock.py
```

### Ejecutar la app web

```bash
streamlit run app_crossdock.py
```

Abre http://localhost:8501. Desde la barra lateral podés pegar cualquier archivo TS con el mismo formato, independientemente del número de camiones o productos.

La app tiene 4 pestañas:
- **📋 Resultado** — makespan óptimo y orden de camiones
- **⏱️ Programación** — tabla de horarios y diagrama de Gantt
- **📦 Flujo de productos** — matriz de transferencias entre camiones
- **📊 Datos del problema** — tablas de oferta, demanda y balance por producto

---

## 📚 Referencias

- Boysen, N., Fliedner, M., & Scholl, A. (2010). Scheduling inbound and outbound trucks at cross docking terminals. *OR Spectrum*, 32(1), 135–161.
- Wolsey, L. A. (1998). *Integer Programming*. Wiley.
