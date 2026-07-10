# Intersección Cercha Transición × Cajón Warren — Ubicación del Montante

> **Plan mode** — análisis estructural únicamente, sin implementación de código.

**Objetivo:** Determinar la ubicación más probable del montante (vertical) en cada truss para transferir las reacciones de las cerchas de transición (ejes B y C) hacia los cajones Warren (ejes 2 y 3).

**Contexto estructural:**
- 4 cerchas: Cajón eje 2 (A→D) y eje 3 (A→D), Cercha Transición eje B (1→4) y eje C (1→4)
- Ambas tipologías: **Warren** sin montantes — solo diagonales en zigzag
- Columnas solo en el perímetro (ejes 1, 4, A y D)
- Las cerchas de transición se apoyan sobre los cajones en las intersecciones B×2, B×3, C×2, C×3

---

## 1. Supuestos de geometría de la grilla

No se especificaron dimensiones reales. Para continuar, asumimos una grilla simétrica típica de cubierta metálica:

| Dimensión | Valor supuesto | Ejes |
|-----------|:-:|------|
| L₁ (1→2) | 1.60 m | X |
| L₂ (2→3) | **3.20 m** (claro libre central) | X |
| L₃ (3→4) | 1.60 m | X |
| Total 1→4 | **6.40 m** (coincide con la cercha_transicion.std) | X |
| Hz₁ (A→B) | 1.60 m | Z |
| Hz₂ (B→C) | **3.20 m** (claro libre central) | Z |
| Hz₃ (C→D) | 1.60 m | Z |

Con esto:
- **Eje 2** está en X = 1.60 m del origen (eje 1)
- **Eje 3** está en X = 4.80 m
- **Eje B** está en Z = 1.60 m del origen (eje A)
- **Eje C** está en Z = 4.80 m

---

## 2. Cercha de Transición (eje B, 1→4)

**Geometría actual** (cercha_transicion.std):
- 9 nudos en cordón superior (1→9): x = 0, 0.8, 1.6, 2.4, 3.2, 4.0, 4.8, 5.6, 6.4
- 9 nudos en cordón inferior (10→18): mismo x
- 8 paneles @ 0.80m
- h = 1.00m

**Intersección con Cajón en eje 2** (X ≈ 1.60m):
- X=1.60m → **coincide exactamente con el nudo 3** (superior) y **nudo 12** (inferior) ✓
- No necesita montante adicional en la transición — el nudo existe

**Intersección con Cajón en eje 3** (X ≈ 4.80m):
- X=4.80m → **coincide exactamente con el nudo 7** (superior) y **nudo 16** (inferior) ✓
- No necesita montante adicional

Ambas intersecciones caen en nudos existentes de la cercha de transición. **La cercha de transición no requiere montantes nuevos.**

---

## 3. Cajón Warren (eje 2, A→D)

**Geometría actual** (cercha_warren.std):
- 20 nudos cordón superior (1→20): x desde 0 hasta 16.52 (pero en el plano, el cajón va en dirección Z)
- En el modelo STD, el cajón está en dirección X. Para el plano de cubierta, necesitamos reinterpretar:
  - X del modelo STD = coordenada Z en el plano de cubierta
  - h (vertical en modelo) = sigue siendo h estructural

**Nudos del cajón en dirección A→D (dirección Z):**
Z = 0, 0.9, 1.8, 2.7, 3.6, 4.5, 5.4, 6.3, 7.125, 8.025, 8.925, 9.825, 10.725, 11.55, 12.45, 13.35, 14.25, 15.15, 16.05, 16.52

**Intersección con Transición en eje B** (Z ≈ 1.60m):
- Panel point más cercano: Z=1.80m (nudo 3 superior, nudo 23 inferior)
- Distancia desde eje B al nudo: 1.80 - 1.60 = **0.20m** ← cae mid-panel
- **Opción A (recomendada):** Agregar montante en Z=1.60m en el cajón y mover el nudo del cordón inferior para que coincida
- **Opción B:** Reajustar la geometría del cajón para que tenga un nudo en Z=1.60m (modificar panel @ 0.80m en lugar de 0.90m)

**Intersección con Transición en eje C** (Z ≈ 4.80m):
- Panel point más cercano: Z=4.50m (nudo 6) o Z=5.40m (nudo 7)
- Distancia desde eje C: 4.80 - 4.50 = **0.30m** o 5.40 - 4.80 = 0.60m ← cae mid-panel
- **Misma solución:** agregar montante vertical en Z=4.80m

---

## 4. Ubicación recomendada de montantes

### Cercha de Transición (ejes B y C)

| Intersección | X (m) | Nudo sup. | Nudo inf. | ¿Montante necesario? |
|:---|:-:|:-:|:-:|:-:|
| B × Cajón 2 | 1.60 | 3 | 12 | **No** — ya hay nudo |
| B × Cajón 3 | 4.80 | 7 | 16 | **No** — ya hay nudo |
| C × Cajón 2 | 1.60 | 43 | 52 | **No** — ya hay nudo |
| C × Cajón 3 | 4.80 | 47 | 56 | **No** — ya hay nudo |

### Cajón Warren (ejes 2 y 3)

| Intersección | Z (m) | Nudo sup. cercano | Nudo inf. cercano | ¿Montante necesario? |
|:---|:-:|:-:|:-:|:-:|
| Eje 2 × Transición B | 1.60 | 3 (Z=1.80) | 23 (Z=1.80) | **Sí** — agregar en Z=1.60 |
| Eje 2 × Transición C | 4.80 | 6 (Z=4.50) | 26 (Z=4.50) | **Sí** — agregar en Z=4.80 |
| Eje 3 × Transición B | 1.60 | 43 (Z=1.80) | 63 (Z=1.80) | **Sí** — agregar en Z=1.60 |
| Eje 3 × Transición C | 4.80 | 46 (Z=4.50) | 66 (Z=4.50) | **Sí** — agregar en Z=4.80 |

---

## 5. Tareas de implementación

### Tarea 1: Agregar montantes al cajón Warren

Modificar `examples/cercha_warren.std`:
- Agregar 2 nuevos nudos en el cordón inferior del cajón (eje 2) en Z=1.60 y Z=4.80:
  - Nudo 81: x=1.60, y=0.0, z=0.0 (nuevo nudo inferior en B×2)
  - Nudo 82: x=4.80, y=0.0, z=0.0 (nuevo nudo inferior en C×2)
- Agregar 2 nuevos nudos en el cordón superior del cajón (eje 2) en Z=1.60 y Z=4.80:
  - Nudo 83: x=1.60, y=1.0, z=0.0 (nuevo nudo superior en B×2)
  - Nudo 84: x=4.80, y=1.0, z=0.0 (nuevo nudo superior en C×2)
- Agregar montantes (miembros verticales):
  - Miembro 195: nudo sup 3 → nudo inf 81 (ya existe el nudo sup 3 en Z=1.80, necesitamos moverlo o crear uno nuevo)

En realidad, es más limpio re-panelizar el cajón:
- Cambiar los paneles de 0.90m a 0.80m en las zonas cercanas a las intersecciones
- Esto hace que los nudos existentes coincidan con Z=1.60 y Z=4.80

### Tarea 2: Agregar soportes intermedios a la cercha de transición

Modificar `examples/cercha_transicion.std`:
- Agregar apoyos en nudos 12 (X=1.60, B×Cajón2) y 16 (X=4.80, B×Cajón3)
- Estos apoyos representan la reacción del cajón hacia la transición
- Tipo: PINNED (solo FY restringido en dirección vertical, o similar)

### Tarea 3: Verificación estructural

- Correr análisis con los montantes agregados
- Verificar que las reacciones en los nuevos apoyos coincidan con las calculadas (~52 kN cada una para combo 105)
- Verificar que la esbeltez del montante (TUBO70x4, L=1.0m) sea adecuada

---

## 6. Riesgos y preguntas abiertas

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| La grilla asumida (1.60+3.20+1.60) puede no ser la real | Todas las coordenadas cambiarían | Confirmar dimensiones reales con el usuario antes de implementar |
| Agregar montantes cambia la rigidez del cajón | Podría redistribuir fuerzas en diagonales adyacentes | Verificar fuerzas axiales en diagonales antes y después |
| Soporte intermedio en transición = apoyo simple vs empotrado | Distribución de esfuerzos distinta | Usar PINNED (solo FY) que es lo más realista |

---

**Archivo guardado:** `.hermes/plans/montante-interseccion-cerchas.md`

¿Confirmas los supuestos de grilla (L₁=1.60, L₂=3.20, L₃=1.60 / Hz₁=1.60, Hz₂=3.20, Hz₃=1.60) o tienes las dimensiones reales para ajustar el plan?
