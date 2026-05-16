# Verificación manual — Obras paralizadas 2026

Guía para validar humanamente cada obra contra **4 fuentes paralelas**:
1. **Infobras live** (ficha pública oficial)
2. **Portal institucional** de la entidad ejecutora
3. **PTE Estándar** (Portal de Transparencia Estándar — sección "Proyectos de inversión e Infobras")
4. **MEF Consulta Amigable** (ejecución presupuestal real)

Lo que mi BD tiene vs lo que reportan estas 4 fuentes te dice qué tan confiable es el dato.

---

## ⚠️ Cómo leer "EN EJECUCIÓN" en Infobras live

**Importante**: el campo "ESTADO DE OBRA" en la ficha pública de Infobras **NO se actualiza automáticamente al paralizar**. La entidad puede tener internamente `Existe Paralización = SI` pero el estado público sigue mostrando "EN EJECUCIÓN". Solo cuando la entidad hace un cambio explícito, aparece "PARALIZADA".

Por eso al verificar, **fíjate en**:
- ⚠️ **"FECHA DEL ÚLTIMO AVANCE"** — si dice "ENE 2026" o anterior y hoy es mayo, la obra no se ha movido (eso es la paralización real)
- ⚠️ **"PORCENTAJE DE AVANCE FÍSICO"** — comparar con BD (debería coincidir o ser mayor en live)
- ⚠️ **"FECHA DE FIN" vencida** sin "FECHA DE FIN REAL" — obra que debió terminar y no lo hizo

---

## 🎯 Las 8 obras paralizadas en 2026 (mi BD)

### 1. INFOBRAS 536317 — **SJL Pasos a desnivel** ⚠️ DUDOSA

**Mi BD dice:** S/ 489 M · 11.31% · paralizada feb 2026 · Conflictos sociales
**Pero verifiqué live y dice:** S/ 96.5 M · 18.93% · último avance ABR 2026 (¡activa!)

| Fuente | Link | Qué buscar |
|---|---|---|
| Infobras live | [Ver ficha](https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=536317) | "FECHA DEL ÚLTIMO AVANCE" — si dice ABR 2026 está activa |
| Invermet web | [invermet.gob.pe](https://www.invermet.gob.pe/) | Sección "Obras" o "Proyectos en ejecución" — buscar Av Próceres / Wiesse |
| PTE Invermet | [gob.pe/invermet](https://www.gob.pe/institucion/invermet/transparencia) | Proyectos de inversión |
| Muni SJL | [munisjl.gob.pe](https://munisjl.gob.pe/) | El distrito donde está físicamente; aunque no la ejecutan, puede listarla |

---

### 2. INFOBRAS 42593 — **JNJ San Isidro** ✅ ANCLA SÓLIDA

**Mi BD dice:** S/ 32 M · 99.86% · paralizada enero 2026 · Resolución de contrato
**Live confirmó:** ESTADO = "PARALIZADA" explícito ✅

| Fuente | Link | Qué buscar |
|---|---|---|
| Infobras live | [Ver ficha](https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=42593) | Estado "PARALIZADA" ya confirmado |
| JNJ web | [jnj.gob.pe](https://www.jnj.gob.pe/) | Buscar "Sede Paseo de la República 3285" o "Resolución de contrato" |
| PTE JNJ | [gob.pe/jnj](https://www.gob.pe/institucion/jnj/transparencia) | Proyectos de inversión |
| Muni San Isidro | [munisanisidro.gob.pe](https://www.munisanisidro.gob.pe/) | La sede física está en SI; podría tener nota |

---

### 3. INFOBRAS 169395 — **UNMSM Letras** 🟡 INTERMEDIA

**Mi BD dice:** S/ 18.79 M · 93.67% · paralizada feb 2026 · Otras causales
**Live confirmó:** avance 93.67%, último avance MAR 2026, estado "EN EJECUCIÓN" (no dice paralizada)

| Fuente | Link | Qué buscar |
|---|---|---|
| Infobras live | [Ver ficha](https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=169395) | Último avance — ¿se mueve o no? |
| UNMSM | [unmsm.edu.pe](https://www.unmsm.edu.pe/) | Buscar "Facultad de Letras" + obras |
| PTE UNMSM | [gob.pe/unmsm](https://www.gob.pe/institucion/unmsm/transparencia) | Proyectos de inversión |
| Muni Lima | [munlima.gob.pe](https://www.munlima.gob.pe/) | Para cruzar con Cercado de Lima |

---

### 4. INFOBRAS 101998 — **SEDAPAL Colector Chorrillos** ⚠️ AVANCE 0%

**Mi BD dice:** S/ 10.15 M · **0% avance** · paralizada enero 2026 · Otras causales
Una obra de S/10M sin haberse iniciado en 4 meses post-firma.

| Fuente | Link | Qué buscar |
|---|---|---|
| Infobras live | [Ver ficha](https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=101998) | Si dice 0% es real, hay que ver qué pasó con el expediente |
| SEDAPAL | [sedapal.com.pe](https://www.sedapal.com.pe/) | Sección Obras / Licitaciones; buscar "Circunvalación Chorrillos" |
| PTE SEDAPAL | [gob.pe/sedapal](https://www.gob.pe/institucion/sedapal/transparencia) | Proyectos de inversión |
| Muni Chorrillos | [munichorrillos.gob.pe](https://www.munichorrillos.gob.pe/) | Comunicados de obras de saneamiento |

---

### 5. INFOBRAS 540978 — **Piscina semiolímpica Los Olivos**

**Mi BD dice:** S/ 3.58 M · 73.82% · paralizada feb 2026 · Otras causales

| Fuente | Link | Qué buscar |
|---|---|---|
| Infobras live | [Ver ficha](https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=540978) | Estado actual + último avance |
| Muni Los Olivos | [munilosolivos.gob.pe](https://www.munilosolivos.gob.pe/) | Sección Obras → buscar piscina o Urb Pro |
| PTE Los Olivos | [gob.pe/munilosolivos](https://www.gob.pe/institucion/munilosolivos/transparencia) | Proyectos de inversión |

---

### 6. INFOBRAS 540067 — **Veredas Villa Alejandro / Lurín** ⚠️ NOMBRE INCONSISTENTE

**Ojo:** mi BD la pone en **VMT** pero el nombre dice "Villa Alejandro, distrito de Lurín". Eso significa que la entidad ejecutora (Muni Lurín) registró la obra a nombre de un distrito que NO le pertenece, o el campo distrito está mal. Vale la pena que tú verifiques.

**Mi BD dice:** S/ 3.26 M · 54.9% · paralizada enero 2026 · Otras causales

| Fuente | Link | Qué buscar |
|---|---|---|
| Infobras live | [Ver ficha](https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=540067) | El "DISTRITO" en la ficha vs lo que dice mi BD |
| Muni Lurín | [munilurin.gob.pe](https://www.munilurin.gob.pe/) | Buscar PJ Villa Alejandro |
| PTE Muni Lurín | [gob.pe/munilurin](https://www.gob.pe/institucion/munilurin/transparencia) | Proyectos de inversión |

---

### 7. INFOBRAS 504340 — **Chorrillos Av Santa Rosa** ✅ ANCLA CON SELLO CONTRALORÍA

**Mi BD dice:** S/ 3.17 M · 79.43% · paralizada feb 2026 · **Confirmada por Contraloría dic-2025** ✅
**Live confirmó:** avance 79.43%, último avance MAR 2026, S/ 3.52 M

| Fuente | Link | Qué buscar |
|---|---|---|
| Infobras live | [Ver ficha](https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=504340) | Verificar monto y avance — coinciden con BD |
| Muni Chorrillos | [munichorrillos.gob.pe](https://www.munichorrillos.gob.pe/) | "Av Santa Rosa" / "AA.HH. San Genaro II" |
| PTE Chorrillos | [gob.pe/munichorrillos](https://www.gob.pe/institucion/munichorrillos/transparencia) | Proyectos de inversión |

---

### 8. INFOBRAS 538068 — **Alumbrado Cruz del Portillo / Lurín**

**Mi BD dice:** S/ 0.97 M · 91.67% · paralizada enero 2026 · Otras causales

| Fuente | Link | Qué buscar |
|---|---|---|
| Infobras live | [Ver ficha](https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=538068) | Estado actual |
| Muni Lurín | [munilurin.gob.pe](https://www.munilurin.gob.pe/) | Comunicados zonales |

---

## 📋 Checklist de verificación (lo que vas marcando)

Por cada obra que verifiques, anota:

| Pregunta | Si la respuesta es... |
|---|---|
| ¿La obra existe en Infobras live? | **Sí** → BD bien · **No** → obra borrada, alertar |
| ¿"FECHA DEL ÚLTIMO AVANCE" es > 2 meses atrás? | **Sí** → realmente paralizada · **No** → obra activa, BD errada |
| ¿El monto en live difiere >20% de mi BD? | **Sí** → revisar mi ingestor · **No** → ok |
| ¿La encuentras en la web institucional/PTE? | **Sí** → coherente · **No** → la entidad no la publicita pero existe (señal) |
| ¿La encuentras en la web de la muni del distrito? | **Sí** → bonus · **No** → normal, no toda muni lista obras de terceros |

---

## 🛠 Patrones de URL útiles para cualquier obra

Si quieres verificar otra obra que no esté en esta lista:

```
Infobras live:    https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId={CODIGO_INFOBRAS}
PTE de entidad:   https://www.gob.pe/institucion/{slug-entidad}/transparencia
Web institucional: https://www.gob.pe/institucion/{slug-entidad}
MEF Consulta Amigable: https://apps5.mineco.gob.pe/transparencia/Navegador/default.aspx
   (Interactivo: navegar por Departamento > Provincia > Distrito > Proyecto)
```

**Slugs gob.pe conocidos para nuestros casos:**
- `jnj` — Junta Nacional de Justicia
- `munichorrillos` — Muni Chorrillos
- `munisanisidro` — Muni San Isidro
- `munilima` — Muni Metropolitana de Lima
- `munisjl` — Muni SJL
- `munilosolivos` — Muni Los Olivos
- `munilurin` — Muni Lurín
- `unmsm` — UNMSM
- `invermet` — Fondo Metropolitano de Inversiones
- `sedapal` — SEDAPAL

---

## 🎯 Si encuentras una inconsistencia importante, dime:

1. **Código INFOBRAS** + URL donde la viste
2. **Qué diferencia hay** (mi BD vs lo que viste)
3. **En qué fuente confías más** (Infobras live > PTE > muni web > BD bulk)

Con eso actualizo la BD y la señal correspondiente. Toma ~30 min verificar las 8 con calma.
