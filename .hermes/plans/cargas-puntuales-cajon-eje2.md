# Cargas puntuales sobre Cajón Eje 2 — provenientes de cerchas de transición

**Objetivo:** Determinar qué cargas puntuales (D, Lr, W, G) deben agregarse al cajón del eje 2 en las intersecciones con las cerchas de transición de los ejes B y C.

---

## 1. Geometría de las intersecciones

El cajón eje 2 (box: planos en z=0 y z=0.28) recibe las reacciones de 2 cerchas de transición:

| Intersección | Coordenada Z en cajón | Nudo plano frontal (z=0) | Nudo plano posterior (z=0.28) |
|:---|---:|:---:|:---:|
| **B × Cajón 2** | **5.40 m** (nudo 7) | nudo 7 (sup) / nudo 27 (inf) | nudo 47 (sup) / nudo 67 (inf) |
| **C × Cajón 2** | **10.725 m** (nudo 13) | nudo 13 (sup) / nudo 33 (inf) | nudo 53 (sup) / nudo 73 (inf) |

Ambas caen **exactamente en nudos existentes** del cajón Warren — no se requieren montantes adicionales.

---

## 2. Reacciones de la cercha de transición (por módulo de 6.40m)

Del análisis de `cercha_transicion.std` (módulo simple, 2 apoyos):

| Carga | Apoyo izquierdo (N10) | Apoyo derecho (N18) |
|:---|:---:|:---:|
| **D** (muerta) | 15.17 kN (FY) / 13.38 kN (FX) | 15.06 kN (FY) / -12.65 kN (FX) |
| **Lr** (cubierta) | 9.80 kN (FY) / 8.78 kN (FX) | 9.68 kN (FY) / -8.05 kN (FX) |
| **W** (viento) | 8.01 kN (FY) / 7.25 kN (FX) | 7.89 kN (FY) / -6.51 kN (FX) |
| **G** (granizo) | 18.76 kN (FY) / 16.45 kN (FX) | 18.64 kN (FY) / -15.72 kN (FX) |

FY positivo = hacia arriba (compresión en el apoyo).

---

## 3. Reacción total en el apoyo intermedio (eje 2)

En el eje 2 convergen **2 módulos consecutivos** de la cercha de transición:
- Módulo 1→2: apoyo derecho → N18
- Módulo 2→3: apoyo izquierdo → N10

| Carga | N18 (mód. 1→2) | N10 (mód. 2→3) | **Total FY** | Total FX (aprox.) |
|:---|:---:|:---:|:---:|:---:|
| **D** | 15.06 | 15.17 | **30.23 kN** | 0.73 kN (se cancela casi) |
| **Lr** | 9.68 | 9.80 | **19.48 kN** | 0.73 kN |
| **W** | 7.89 | 8.01 | **15.90 kN** | 0.74 kN |
| **G** | 18.64 | 18.76 | **37.40 kN** | 0.73 kN |

La componente FX prácticamente se cancela entre módulos adyacentes (±13 kN → ~0.7 kN neto). Se puede despreciar para el diseño del cajón — solo FY significativa.

---

## 4. Distribución en las dos caras del cajón (z=0 y z=0.28)

El cajón es un box con 2 planos verticales paralelos (separación 0.28m). La cercha de transición es un plano único vertical centrado entre ambos planos del cajón (o apoyada sobre los rieles transversales).

**Hipótesis razonable:** la reacción se reparte por igual entre las 2 caras del cajón a través de los rieles transversales.

### Cargas puntuales a adicionar en el Cajón Eje 2

**Intersección B × Cajón 2** (z=5.40m):

| Carga | Plano frontal (z=0) — nudo 7 sup / 27 inf | Plano posterior (z=0.28) — nudo 47 sup / 67 inf |
|:---|---:|---:|
| D | 30.23/2 = **15.12 kN** ↓ | **15.12 kN** ↓ |
| Lr | 19.48/2 = **9.74 kN** ↓ | **9.74 kN** ↓ |
| W | 15.90/2 = **7.95 kN** ↓ | **7.95 kN** ↓ |
| G | 37.40/2 = **18.70 kN** ↓ | **18.70 kN** ↓ |

**Intersección C × Cajón 2** (z=10.725m):

| Carga | Plano frontal (z=0) — nudo 13 sup / 33 inf | Plano posterior (z=0.28) — nudo 53 sup / 73 inf |
|:---|---:|---:|
| D | **15.12 kN** ↓ | **15.12 kN** ↓ |
| Lr | **9.74 kN** ↓ | **9.74 kN** ↓ |
| W | **7.95 kN** ↓ | **7.95 kN** ↓ |
| G | **18.70 kN** ↓ | **18.70 kN** ↓ |

> Nota: estas cargas son adicionales a las cargas de cubierta (D, Lr, W, G) que ya tiene el cajón. Deben aplicarse como **JOINT LOAD FY** en los nudos superiores del cajón en cada plano.

---

## 5. Preguntas abiertas

- Las cargas se aplican en el **cordón superior** (nudos 7, 47, 13, 53). ¿Correcto, o deben ir en el cordón inferior?
- La cercha de transición, ¿está alineada con un plano específico del cajón o centrada entre ambos? La distribución 50/50 cambia si la transición está alineada solo con el plano frontal (z=0).

Confirma y pasamos a modificar el .std del cajón.
