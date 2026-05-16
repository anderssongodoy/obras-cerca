# Criterios de evaluación — hack@latam 2026 (Transparency & Corruption)

> **META PERMANENTE:** este archivo es la rúbrica oficial del jurado. Todas las decisiones de producto y técnicas se evalúan contra estos 5 criterios. Si una tarea no sube ninguno de ellos, **no la hagas hoy**.

---

## La rúbrica (suma 100%)

| # | Criterio | Peso | Pregunta del jurado |
|---|---|---:|---|
| 1 | **Impacto social** | 30% | ¿Cuánto mejora la vida de las personas? |
| 2 | **Moonshot** | 20% | El resultado se siente como 1 día de trabajo, o 1 año de progreso |
| 3 | **Complejidad técnica** | 20% | ¿Es más que solo prompting? |
| 4 | **Factor de novedad** | 15% | ¿Encontraste un nuevo enfoque para resolver el problema? |
| 5 | **Listo para usar** | 15% | ¿Lo puedo usar de inmediato? |

---

## Análisis crítico por criterio — estado actual vs techo realista

### 1. Impacto social (30%) — el más pesado

**Lo que tenemos a favor:**
- Vector real y cuantificado: **S/ 24,268 millones/año** de perjuicio por corrupción en Perú (Contraloría 2023, 12.7% del presupuesto público).
- **S/ 43,118 millones** detenidos en 2,476 obras paralizadas a dic-2024.
- Audiencia clara y enorme: ~10 millones de habitantes en Lima Metro + Callao.
- Capacidad única: "obras cerca de mí" — ningún portal estatal del Perú la ofrece.

**Para subir a 28+/30:**
- 🎯 **Caso ancla** — encontrar 1 obra `vigente + confirmada Contraloría + alto monto + zona popular` y mostrar el journey humano completo en pitch (vecino la descubre → ve al contratista → exporta evidencia).
- Estimación cuantificable para el pitch: "si 1% de los limeños lo usa, son 100,000 personas auditando obras públicas".

**Score realista hoy: 24-28 / 30**

---

### 2. Moonshot (20%)

**Lo que tenemos:**
- En <6 horas iniciales: 4 fuentes oficiales del Estado scrapeadas (Infobras, OECE OCDS, Contraloría, INEI plan), 11,183 obras en BD limpias, 275 paralizaciones clasificadas (`vigente/dudosa/zombie`), cruce con Anexo oficial de Contraloría, schema PostgreSQL completo con 11 tablas + 3 vistas.
- Cobertura: 50 distritos (43 Lima Metro + 7 Callao).

**Para subir a 17+/20:**
- Algo que el jurado **no espera ver**: mapa de calor cruzando paralizaciones × pobreza INEI, o concentración ≤8 UIT funcional con un caso real.
- Sensación visual: el deploy debe IMPRESIONAR en 30 segundos.

**Score realista hoy: 14-17 / 20**

---

### 3. Complejidad técnica (20%) — "más que solo prompting"

**Lo que tenemos:**
- ETL real (sin IA generativa en el motor) con dedup de RUC, normalización de %, cap de outliers, alias de distrito, batch processing de 11k filas.
- **Clasificación determinística** `vigente/dudosa/zombie` con regla auditable basada en cruce de fechas — el jurado verá una fórmula, no una caja negra.
- Cruce automático con Anexo oficial de Contraloría para "sello oficial".
- Schema relacional con vistas SQL y señales generadas con JSONB (evidencia auditable).
- Scrapers documentados con análisis técnico profundo (`analisis_scraping.md`) que demuestra entendimiento, no copy-paste.

**Para subir a 18+/20:**
- **Geocoding masivo** (Nominatim) → mapa funcional para 11k obras.
- **Capa LLM que SOLO redacta** explicaciones ciudadanas — IA jamás decide ni clasifica. Es exactamente lo que el criterio pide.
- **Playwright + Pentaho** para Órdenes ≤8 UIT — el scraping más complejo del proyecto, gap principal del MD §4.3.

**Score realista hoy: 16-19 / 20**

---

### 4. Factor de novedad (15%)

**Lo que tenemos:**
- "Obras cerca de mí por radio geográfico" → **no existe en ningún portal estatal del Perú**.
- Vista de contratista cruzando concentración ≤8 UIT → no se ha hecho a nivel ciudadano.
- Clasificación `vigente/dudosa/zombie` para limpiar el ruido de Infobras → **novedad técnica honesta** que el ciudadano nunca había tenido.

**Para subir a 13+/15:**
- Pitch que **venda los insights propios**: "encontramos que el 66% de las paralizaciones oficiales son zombies — Infobras tiene un problema de calidad que nadie había documentado".
- A nivel global hay proyectos similares (Brasil Serenata, México MCCI). A nivel Perú somos primeros — decirlo explícitamente.

**Score realista hoy: 11-13 / 15**

---

### 5. Listo para usar (15%) — el más vulnerable HOY

**Estado actual:**
- BD lista, scrapers funcionando, backend pendiente, frontend pendiente, deploy pendiente.

**Para subir a 13+/15:**
- 🚨 **DEPLOY antes del domingo**: Angular/Vercel + Postgres/Supabase.
- Mapa mínimo + ficha + filtro "obras cerca de mí" + botón "exportar caso CSV".
- **URL pública** que cualquier juez pueda abrir en su celular durante el pitch.

**Score realista hoy: 6-13 / 15** (rango enorme — depende 100% del deploy)

---

## Veredicto y plan de subida

| Criterio | Hoy | Techo realista | Acción |
|---|---:|---:|---|
| Impacto social | 24 | 28 | Caso ancla en pitch |
| Moonshot | 14 | 17 | Algo visual sorprendente |
| Complejidad técnica | 16 | 19 | Geocoding + Playwright Pentaho + LLM redactor |
| Factor de novedad | 11 | 13 | Pitch que venda insights propios |
| Listo para usar | 6 | 13 | **DEPLOY YA** |
| **TOTAL** | **71** | **90** | |

**100% literal: imposible.** Los jurados nunca dan 100% en los 5 criterios.
**85-90 sí es alcanzable** si:
1. Deploy antes del domingo
2. Caso ancla en el pitch
3. Playwright/Pentaho funcional para concentración ≤8 UIT
4. Geocoding de las paralizaciones para que el mapa muestre realidad

---

## Reglas operativas derivadas

Cada tarea/PR/decisión debe responder afirmativamente a al menos una de estas:

1. ¿Sube **Impacto social**? (mejora el journey ciudadano, agrega un caso, amplía la audiencia)
2. ¿Sube **Moonshot**? (algo que sorprende, ratio resultado/tiempo absurdo)
3. ¿Sube **Complejidad técnica**? (algoritmo no-trivial, integración compleja, no es solo CRUD ni prompting)
4. ¿Sube **Novedad**? (algo que ningún otro portal/proyecto del Perú hace)
5. ¿Sube **Listo para usar**? (deploy, UI, latencia, mobile, robustez)

Si una tarea no sube ninguno → **descártala**. El tiempo restante es escaso.

---

## Anti-patrones a evitar

- ❌ "Govtech genérica sin ángulo anticorrupción" → ya tenemos detección de paralización + concentración, mantenerlo visible
- ❌ "Dashboards sin verificación o valor investigativo" → cada señal con tabla de evidencia + fuente oficial + exportable (CSV)
- ❌ "Visualización bonita pero sin acción" → siempre que se muestre una señal, debe haber un botón "ver evidencia" + "fuente oficial" + "exportar"
- ❌ Sobre-ingeniería: nada de microservicios, Kafka, Elasticsearch. El motor es PostgreSQL puro y eso es deliberado y vendible ("explicable y auditable")
