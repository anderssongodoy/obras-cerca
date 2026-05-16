# Obras Cerca — Documento maestro del proyecto

**Hackathon:** hack@latam 2026 (15-17 mayo 2026)
**Track:** Transparency & Corruption
**Equipo:** 4 personas (entrada por sobrecupo, sin perks de patrocinadores)
**Estado de redacción:** v2 pre-evento

---

## 1. Identidad del proyecto

**Nombre:** Obras Cerca

**Tagline:** *No hacemos otro dashboard. Convertimos información dispersa del Estado peruano sobre obras públicas en expedientes priorizados, auditables y comprensibles para cualquier ciudadano.*

**Una línea para pitch:** Plataforma ciudadana que muestra qué obras públicas hay cerca de ti en el Perú, en qué estado están, quién las ejecuta y qué señales objetivas merecen revisión, todo enlazado a fuentes oficiales.

---

## 2. Objetivo

### Objetivo general

Construir una herramienta web que permita a cualquier persona en el Perú visualizar las obras públicas cercanas a su ubicación, entender su estado y detectar señales objetivas de revisión sobre contratistas y obras detenidas, basándose exclusivamente en datos oficiales del Estado peruano.

### Objetivos específicos

1. Integrar en una sola interfaz fuentes públicas dispersas del Estado peruano (OECE, Infobras, Contraloría, INEI) sobre obras públicas y contratistas.
2. Permitir al ciudadano buscar y geolocalizar obras por radio desde su ubicación actual, una capacidad que ningún portal estatal ofrece hoy.
3. Identificar y destacar obras públicas detenidas en la zona piloto, usando la definición oficial de Contraloría (≥6 meses sin avance).
4. Detectar patrones de concentración de contratistas en compras menores ≤8 UIT por entidad, mostrando la evidencia auditable de cada señal.
5. Traducir el lenguaje técnico de auditoría a lenguaje ciudadano accesible para vecinos, periodistas y juntas vecinales.
6. Garantizar que toda señal mostrada sea trazable a su fuente oficial mediante enlaces verificables.

---

## 3. Problema que resuelve

Hoy un ciudadano peruano que quiere saber qué obras hay cerca de su casa, quién las ejecuta o por qué llevan años paradas, tiene que navegar al menos 4 portales estatales distintos (Infobras, SEACE, MEF Consulta Amigable, Portal de Transparencia Estándar), cada uno con su propia lógica y sin búsqueda diseñada para el vecino.

Las cifras del problema:

- **S/ 24,268 millones** de perjuicio estimado por corrupción e inconducta funcional en 2023, según la Contraloría — equivalente al 12.7% del presupuesto público ejecutado.
- **2,476 obras públicas paralizadas** a diciembre 2024 según Infobras, sumando **S/ 43,118 millones** en inversión detenida. El dato a diciembre 2025 ya está publicado.
- **S/ 19,536 millones** en contrataciones ≤8 UIT en 2024 (24.2% del total nacional), el segmento más opaco y atomizado de la compra pública.
- **Transportes y Comunicaciones** concentra el 28.9% de las obras paralizadas, seguido por Vivienda y Saneamiento (20.9%).

El problema no es la falta de datos. Es que están dispersos, en lenguaje técnico de auditor, sin búsqueda geográfica ciudadana y sin cruce automático entre fuentes. **La oportunidad es integración + diseño centrado en el vecino + explicabilidad.**

---

## 4. Propuesta de valor

Obras Cerca tiene tres funcionalidades principales, diseñadas como partes de un solo producto coherente.

### 4.1 Exploración geográfica ciudadana

Mapa interactivo con obras públicas representadas como puntos (locales), líneas (obras viales) o polígonos (parques, colegios). El usuario puede usar su ubicación actual y filtrar por radio (500m, 1km, 3km, 5km, 10km), o buscar manualmente por distrito, contratista, entidad o nombre de obra. Cada obra abre una ficha completa con datos, fechas, montos, contratista y enlace directo a la fuente oficial.

### 4.2 Monitoreo de obras detenidas

Las obras con paralización detectada (sin avance ≥6 meses según la definición oficial de Contraloría) se destacan en rojo intenso en el mapa y tienen una ficha extendida que muestra meses sin actualización, monto comprometido vs ejecutado, sector afectado y, cuando aplica, contexto poblacional del distrito desde el Mapa de Pobreza del INEI. Cada ficha se acompaña de una explicación en lenguaje ciudadano generada automáticamente.

### 4.3 Análisis de contratistas

Cuando el ciudadano hace clic en el contratista de una obra, se abre una vista que reúne en un solo lugar las obras que ese RUC ha ganado, los procedimientos en los que participó y las órdenes de compra y servicios ≤8 UIT que recibe por entidad. Cuando un contratista concentra una proporción anormal de las compras menores de una misma entidad en los últimos 12 meses (por ejemplo, >30%), se muestra una señal de revisión con la fórmula visible y la tabla de evidencia debajo. Esta vista no existe hoy en ningún portal estatal.

### 4.4 Diferencial real frente a Infobras

Infobras es la principal referencia hoy y es importante reconocer qué hace bien antes de explicar qué no hace. Infobras ofrece mapa nacional con conteo de obras por departamento, ficha detallada por obra (código Infobras, código único de inversión, % avance físico, entidad responsable, fechas de inicio/fin/último avance, modalidad, contratista, expediente técnico, ubicación), gráfico de distribución de estados, costo de obra y secciones de control social, comentarios y denuncias.

Lo que Obras Cerca hace diferente:

| Capacidad | Infobras | Obras Cerca |
|---|---|---|
| Mapa nacional de obras | ✅ Con conteo por departamento | ✅ Con conteo y filtros adicionales |
| Búsqueda por departamento o nombre | ✅ | ✅ |
| Ficha técnica de cada obra | ✅ Muy completa | ✅ + explicación en lenguaje ciudadano |
| Geolocalización del usuario + filtro por radio | ❌ | ✅ "Obras cerca de mí a 500m, 1km, 3km" |
| Búsqueda por dirección o desde GPS del navegador | ❌ | ✅ |
| Ficha de contratista con sus obras | ❌ Aparece como dato dentro de obra, no como vista propia | ✅ Vista dedicada que reúne todas sus obras |
| Cruce con compras menores ≤8 UIT del mismo contratista | ❌ | ✅ Detecta concentración por entidad |
| Detección automática de paralización con explicación | ⚠️ Solo etiqueta "paralizada", sin contexto | ✅ Meses detenida, monto detenido, sector, impacto poblacional |
| Lenguaje accesible al vecino | ❌ Lenguaje técnico de auditor | ✅ Lenguaje ciudadano generado automáticamente |
| Exportar evidencia de un caso (CSV) | ❌ | ✅ Para periodismo de datos |
| Cruce con sanciones e impedimentos OECE | ❌ | ✅ |
| Diseño optimizado para móvil | ⚠️ Funcional pero pesado | ✅ Pensado para vecino con celular |

**El diferencial concreto:** Infobras es la ficha técnica de la obra para el auditor. Obras Cerca es la herramienta del vecino, periodista y junta vecinal. No competimos con Infobras, lo complementamos y lo hacemos legible.

---

## 5. Alcance del MVP

### Alcance geográfico

**[POR DECIDIR EN EQUIPO]** — recomendación: Lima Metropolitana + Provincia Constitucional del Callao.

Razones de la recomendación:
- ~10 millones de habitantes → mayor relevancia para jurado y demo.
- 43 distritos + Callao → variedad de gobiernos locales y perfiles socioeconómicos.
- Mayor volumen de obras y contratistas → más probabilidad de encontrar 5-10 casos jugosos para el pitch.
- Datos disponibles homogéneos.

Demo profunda en 3-5 distritos donde se identifiquen los mejores casos.

### Alcance temporal de los datos

- Obras paralizadas: corte a diciembre 2025 (último informe oficial Contraloría).
- Procedimientos OECE: 2023, 2024 y lo disponible de 2025-2026.
- Órdenes ≤8 UIT: 2024-2025 (lo que esté en CONOSCE).
- Maestro de municipalidades: INEI RNM 2025.

### Alcance funcional (MVP estricto)

Sí entra al MVP:
- Mapa con obras y filtros básicos.
- Geolocalización del usuario con filtro por radio.
- Ficha de obra con datos y enlace a fuente oficial.
- Detección visual de obras detenidas con ficha enriquecida.
- Vista de contratista con cálculo de concentración en compras menores.
- Búsqueda por distrito, contratista, entidad.
- Explicaciones generadas en lenguaje ciudadano.
- Exportar caso (CSV con filas de evidencia) — para periodistas.

No entra al MVP:
- Detección de fraccionamiento por agregación de órdenes.
- Bunching de órdenes justo bajo el umbral 8 UIT.
- Análisis de desalineación con el PAC.
- Scraping en vivo de SEACE o Infobras.
- OCR de documentos PDF de expedientes.
- Cruce con beneficiarios finales / sociedades.
- Grafos de proveedores relacionados.
- Comparación entre distritos.
- Reporte PDF descargable.
- App móvil nativa.

---

## 6. Funcionalidades detalladas

### 6.1 Pantalla principal — mapa

- Centrado por defecto en Lima Metropolitana.
- Capas conmutables: en ejecución, terminadas, detenidas, futuras (PAC).
- Colores por estado (rojo para detenidas, naranja en ejecución, verde terminadas, azul en licitación).
- Botón "usar mi ubicación" con permiso explícito del navegador.
- Filtro de radio: 500m / 1km / 3km / 5km / 10km.
- Filtros por: tipo de obra, entidad, año, estado, sector.
- Buscador superior con autocompletado.

### 6.2 Ficha de obra

- Nombre, descripción y ubicación (distrito, provincia).
- Entidad responsable y nivel de gobierno.
- Contratista (RUC + razón social, link a su vista de contratista).
- Monto referencial, monto adjudicado, diferencia.
- Fechas: convocatoria, buena pro, contrato, inicio, fin estimado, última actualización.
- Estado actual.
- Avance físico y avance financiero.
- Número de postores y nivel de competencia (bajo/limitado/mayor).
- Señales de revisión activas (si aplican).
- Enlaces a fuente oficial (Infobras, SEACE, MEF).
- Explicación generada en lenguaje ciudadano.
- Disclaimer de no acusación.

### 6.3 Ficha de obra detenida (extensión cuando aplica)

Además de los datos anteriores:
- Meses desde la última actualización en Infobras.
- Monto comprometido vs ejecutado en porcentaje y valor absoluto.
- Sector al que pertenece la obra detenida.
- Cuando hay match con Mapa de Pobreza INEI: *"esta obra atiende a un distrito con X% de pobreza monetaria"*.
- Explicación generada en lenguaje ciudadano sobre el impacto de la paralización.

### 6.4 Vista de contratista

- RUC, razón social, estado del RUC.
- Obras adjudicadas (lista con link a cada ficha).
- Procedimientos ganados (últimos 12-24 meses).
- **Análisis de compras menores**: órdenes ≤8 UIT recibidas de cada entidad en los últimos 12 meses, con suma agregada y porcentaje sobre el total de compras menores de esa entidad. Cuando supera el umbral, se marca con señal de revisión.
- Tabla de evidencia: cada orden listada con fecha, monto, descripción, link al documento.
- Sanciones o impedimentos (si existen en lista pública OECE).

### 6.5 Capa de explicación ciudadana (con IA)

Genera texto en lenguaje accesible para fichas, basándose en los datos calculados. No toma decisiones, solo redacta. Si la API se cae, la ficha sigue funcionando con datos crudos.

Ejemplos de output esperado:
- *"Esta obra de saneamiento lleva 14 meses sin avance. Se gastó S/2.3M de los S/4.1M presupuestados. Última actualización en Infobras: marzo 2025."*
- *"Este contratista recibió 47 órdenes de servicio ≤8 UIT de esta entidad en el último año, por un total de S/1.8M. Eso representa el 52% de las compras menores de la entidad en ese periodo."*

### 6.6 Exportar caso

Cualquier alerta tiene un botón "Descargar evidencia" que genera un CSV con todas las filas que componen la señal, columnas originales y enlaces a fuentes oficiales. Esto convierte el producto en una herramienta de periodismo de datos.

---

## 7. Stack técnico

### Frontend

- **Framework:** Angular 18+ (el equipo lo domina; velocidad > novedad).
- **Mapas:** Leaflet o MapLibre con OpenStreetMap (gratis, sin API key).
- **Estilos:** Tailwind o Angular Material.
- **Hosting:** Vercel free tier.

### Backend

- **Runtime:** Node.js + Express (rápido de levantar).
- **Base de datos:** PostgreSQL con extensión PostGIS para datos geográficos.
- **Hosting BD:** Supabase free tier (Postgres + PostGIS incluido, 500MB).

### Procesamiento de datos (ETL)

- **Python 3.12 + Polars** para procesar XLSX/CSV grandes en una máquina (rápido y sin pipelines complejos).
- **Pandas** como respaldo si alguien del equipo no maneja Polars.
- **GeoPandas** para limpieza espacial.

### Capa IA

**[POR DECIDIR EN EQUIPO]** — opciones:
- **Opción A:** Anthropic Claude Haiku 4.5 ($5 USD presupuesto del equipo). Input ~$1/MTok, alcanza para miles de llamadas.
- **Opción B:** Google Gemini free tier (gratuito, ~15 RPM). Cero costo, suficiente para hackathon.

### Lo que NO usamos (decisión consciente)

No usamos Elasticsearch, Kafka, Airflow, Neo4j, microservicios, ni IA generativa en el motor analítico. Razones: en 72h cualquier complejidad extra cuesta tiempo de demo. La narrativa de jurado es más fuerte si pueden decir "el motor es determinista, explicable, auditable".

---

## 8. Fuentes de datos — Plan operativo

### 8.1 Tabla maestra de fuentes

| # | Fuente | Formato | Qué descargar | Dificultad | Cuándo |
|---|---|---|---|---|---|
| 1 | Contraloría — Obras Paralizadas a dic 2025 | XLSX directo | 3 archivos XLSX | Baja | Día -1 |
| 2 | OECE Portal Datos Abiertos (CONOSCE) | CSV/Excel | Procedimientos adjudicados 2024-2025, Proveedores, Órdenes de Compra y Servicios | Media | Día -1 |
| 3 | Portal Contrataciones Abiertas OCDS | JSON/CSV | Dataset Perú 2024-2025 | Media | Día -1 |
| 4 | Infobras DataSets | Por confirmar | Verificar PRIMERO qué hay | Desconocida | Día -2 |
| 5 | INEI Registro Nacional de Municipalidades 2025 | CSV/SPSS | RNM completo | Baja | Día -1 |
| 6 | INEI Mapa de Pobreza 2018 | CSV/Excel | Mapa nacional | Baja | Día -1 (opcional) |
| 7 | INEI Directorio Centros Poblados 2025 | CSV | Directorio completo | Baja | Día -1 (opcional) |
| 8 | SEACE Buscador Público | HTML | NO scrapear, solo deep-link de salida | Muy alta | N/A |
| 9 | Infobras Buscador Web | HTML | NO scrapear, solo deep-link de salida | Muy alta | N/A |
| 10 | MEF Consulta Amigable | HTML | NO usar en MVP | Muy alta | N/A |

### 8.2 URLs concretas

**Contraloría — Obras Paralizadas (la pieza más valiosa por XLSX directo):**
- Página colección: `https://www.gob.pe/institucion/contraloria/colecciones/18230-obras-paralizadas-documentos`
- Informe a diciembre 2025: `https://www.gob.pe/institucion/contraloria/informes-publicaciones/7715417-informe-de-obras-paralizadas-en-el-territorio-nacional-a-diciembre-2025`
- Descargan los 3 XLSX vinculados (53KB, 1.5MB, 2.6MB).

**OECE — Portal de Datos Abiertos (CONOSCE):**
- Página de acceso: `https://www.gob.pe/14272-acceder-al-portal-de-datos-abiertos-del-osce`
- Portal directo (Pentaho): `https://bi.seace.gob.pe/pentaho/api/repos/:public:portal:datosabiertos.html/content?userid=public&password=key`
- Buscar: PAC, Procedimientos Adjudicados, Proveedores Adjudicados, Órdenes de Compra y Servicios. Información acumulada desde 2018.

**Portal de Contrataciones Abiertas OCDS:**
- Página de descargas: `https://contratacionesabiertas.oece.gob.pe/descargas`
- Registro OCP con explicación: `https://data.open-contracting.org/es/publication/135`
- ⚠️ Importante: NO incluye contratos sin procedimiento de selección (menores a 3, 8 o 9 UIT). Útil para obras grandes, no para compras menores.

**Infobras (Contraloría):**
- DataSets a verificar primero: `https://infobras.contraloria.gob.pe/InfobrasWeb/DataSets`
- Buscador público (solo deep-link de salida): `https://infobras.contraloria.gob.pe/infobrasweb`
- Apps ciudadano: `https://apps.contraloria.gob.pe/ciudadano/`
- Patrón de URL de ficha individual: `https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=XXXX`
- ⚠️ Cada ficha tiene un Código Infobras (ej: 52903) que sirve como deep-link directo. Esto facilita el "ver fuente oficial" desde Obras Cerca.

**INEI — datasets de enriquecimiento:**
- Catálogo general 2026: `https://www.gob.pe/institucion/inei/informes-publicaciones/2727403-catalogo-de-base-de-datos-2026`
- Microdatos: `https://proyectos.inei.gob.pe/microdatos/`
- Bases de datos: `https://www.inei.gob.pe/bases-de-datos/`
- Buscar específicamente: Registro Nacional de Municipalidades 2025, Mapa de Pobreza 2018, Directorio Nacional de Municipalidades de Centros Poblados 2025.

**Plataforma Nacional de Datos Abiertos (índice general):**
- `https://www.datosabiertos.gob.pe/`
- Útil para encontrar datasets no listados arriba.

**SEACE Buscador Público (solo deep-link de salida):**
- `https://prodapp2.seace.gob.pe/seacebus-uiwd-pub/buscadorPublico/buscadorPublico.xhtml`
- No scrapear. Solo abrir en nueva pestaña cuando el usuario hace clic en "ver fuente oficial".

### 8.3 Estrategia de pre-carga (NO scraping en vivo)

**Regla de oro:** durante la demo del 15-17 de mayo, ninguna fuente externa se consulta en tiempo real. Todo corre desde el Postgres del equipo.

Cronograma sugerido:
- **Día -2 (martes 12 mayo):** verificar Infobras/DataSets. Si tiene datos buenos, se vuelve fuente principal de obras físicas. Si no, plan B es carga manual curada de 500-1000 obras.
- **Día -1 (miércoles 13 mayo):** descargar todos los XLSX/CSV. Tiempo estimado: 4-6 horas porque algunos archivos OECE pesan cientos de MB.
- **Jueves 14 mayo:** procesar, normalizar, cargar a Postgres, validar.
- **Viernes 15 mayo (kick-off):** todo listo, empezamos a construir UI.

Fuentes "vivas" (SEACE, Infobras buscador, MEF) → solo se usan como botón "ver fuente oficial" que abre la página del Estado en nueva pestaña. El equipo no scrapea ni consulta esas fuentes desde código durante la demo.

---

## 9. Limitaciones honestas

Cosas que el proyecto **NO** hace y que el equipo debe poder explicar al jurado sin avergonzarse:

1. **No cubre todo el Perú al detalle.** Piloto en Lima Metropolitana + Callao. Otras regiones aparecen en mapa de fondo a baja resolución, pero no con ficha completa.
2. **No detecta corrupción.** Detecta señales objetivas para priorizar revisión. Hay diferencia y eso debe ser explícito en UI y en pitch.
3. **No reemplaza a Infobras.** Lo complementa con experiencia ciudadana, geolocalización y cruce de fuentes que Infobras no hace.
4. **No incluye compras menores recientes en su totalidad.** El propio buscador OECE advierte que el módulo nuevo de contratos menores se incorpora progresivamente. Lo que el equipo tiene es lo que el Estado publica.
5. **No hace OCR ni procesa PDFs.** Solo datos estructurados oficiales.
6. **No tiene beneficiarios finales ni redes societarias completas.** El análisis de contratistas se calcula sobre RUC, no sobre persona física beneficiaria.
7. **No actualiza datos en tiempo real.** Refresca cuando los datasets oficiales se actualizan (trimestral en algunos casos).
8. **La calidad del dato depende del Estado.** Si Infobras no se actualiza, Obras Cerca tampoco. Eso es estructural.
9. **La IA solo redacta.** No decide, no califica, no prioriza. Si se apaga, las fichas funcionan con datos crudos.

---

## 10. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Infobras/DataSets no tiene datos útiles en CSV | Media | Alto | Plan B: carga manual curada de 500-1000 obras usando deep-link de fichas individuales |
| OECE Portal CONOSCE cae el día -1 | Baja | Alto | Bajar archivos el martes 12, no esperar al miércoles |
| Coordenadas geográficas faltantes en muchas obras | Alta | Medio | Geocodificar con Nominatim (gratis) usando distrito + dirección; mostrar pin aproximado con disclaimer |
| Tiempo insuficiente para implementar análisis de contratista | Media | Alto | Priorizar mapa + obras detenidas primero; análisis de contratista entra como upgrade el sábado |
| Demo se cae por dependencia externa | Baja si pre-cargan | Crítico | Cero llamadas externas durante demo; deep-link de salida en pestaña nueva |
| Acusaciones implícitas a contratistas reales | Baja si lenguaje correcto | Legal | Disclaimer visible, lenguaje "señal de revisión", nunca "corrupto" |
| Geolocalización del navegador denegada | Media | Bajo | Fallback a buscador manual de distrito |
| Jurado pregunta "¿no es esto lo que ya hace Infobras?" | Alta | Alto | Tener lista la tabla comparativa de sección 4.4 y demo en vivo del "obras cerca de mí" + ficha de contratista cruzada |

---

## 11. Demo de 3 minutos (estructura)

**Minuto 1 — Setup y descubrimiento ciudadano:**

1. Abrir la app, mostrar mapa de Lima Metropolitana.
2. Presionar "usar mi ubicación" → mapa centra en distrito de demo y muestra obras en 1km a la redonda. *Esto Infobras no lo permite hoy.*
3. Filtrar a "obras detenidas" → aparecen puntos rojos.
4. Clic en una obra detenida cercana.

**Minuto 2 — La ficha que ningún ciudadano puede armar solo:**

5. Ficha muestra: obra de S/X millones, detenida hace Y meses, contratista Z.
6. Explicación en lenguaje ciudadano automática.
7. Botón "ver en Infobras" abre fuente oficial en nueva pestaña.
8. Clic en el contratista → su vista dedicada.

**Minuto 3 — El cruce que nadie hace hoy:**

9. Vista de contratista muestra: además de esta obra, recibe X% de compras menores de esa misma entidad.
10. Tabla de evidencia con cada orden, montos y links.
11. Botón "Descargar caso" → CSV listo para periodista.
12. Cierre: *"Esto que acabamos de mostrar tomaría a un vecino horas navegando 4 portales del Estado. Obras Cerca lo hace en 30 segundos, con cada dato trazable a su fuente oficial."*

---

## 12. Principios del producto

1. **Transparencia, no acusación.** El sistema prioriza expedientes para revisión, no señala culpables.
2. **Verificabilidad total.** Cada dato enlaza a su fuente oficial.
3. **Determinismo explicable.** Las alertas tienen fórmula visible. Nada es caja negra.
4. **Lenguaje ciudadano.** El usuario es un vecino, no un auditor.
5. **IA solo redacta.** Nunca decide ni clasifica.
6. **Resiliencia ante caída de servicios.** Si la API IA se cae, la app funciona con datos crudos.
7. **Open source.** Requisito del track. Código en GitHub público desde el día 1.

---

## 13. Por qué encaja con el track Transparency & Corruption

| Criterio del track | Cómo lo cumple Obras Cerca |
|---|---|
| Inspeccionar gasto público, compras, registros públicos | Ficha de obra con monto, contratista, fuente OECE/Infobras |
| Cruzar contratos, proveedores, presupuestos y registros públicos para detectar señales | Vista de contratista que cruza obras + procedimientos + compras menores |
| Dashboards, alertas o herramientas de investigación para ciudadanos, periodistas, auditores | Detección de obras detenidas + exportar evidencia CSV |
| Sistemas que hagan procesos públicos opacos buscables, trazables y comprensibles | Buscador + radio geográfico + lenguaje ciudadano + deep-link |

**Criterios negativos del track evitados:**

- ❌ "Govtech genérica sin ángulo anticorrupción" → tenemos detección de obras detenidas + análisis de concentración de contratistas.
- ❌ "Dashboards sin verificación o valor investigativo real" → cada alerta tiene tabla de evidencia + fuente oficial + exportable.
- ❌ "Campañas de concientización sin producto concreto" → producto deployado y open source.
- ❌ "Proyectos que visualicen datos pero no ayuden a detectar abusos" → detectamos paralización y concentración con fórmula auditable.

---

## 14. Decisiones pendientes antes del kick-off

El equipo necesita cerrar estas dos preguntas antes del miércoles 13 de mayo:

1. **Alcance geográfico exacto:** ¿Lima Metropolitana + Callao completos, o un subset de 5-10 distritos? Recomendación de este documento: Lima Metropolitana + Callao en mapa, profundidad de demo en distritos donde se encuentren los mejores casos.

2. **Capa IA:** ¿$5 USD a Anthropic Claude Haiku o Gemini free tier? Recomendación: Anthropic si el equipo quiere control sobre el output; Gemini si prefieren cero gasto. Ambas opciones son defendibles en pitch.

---

## 15. Próximos pasos operativos

Una vez cerradas las dos decisiones de la sección 14, el siguiente entregable es un **cronograma hora por hora de las 72h** con asignación específica de los 4 miembros del equipo a:

- Pre-carga y ETL (martes 12 + miércoles 13)
- Backend + API (viernes 15)
- Frontend mapa (viernes 15 - sábado 16)
- Frontend fichas + análisis de contratista + IA (sábado 16 - domingo 17)
- Pulido + pitch + video demo (domingo 17)

---

## 16. Frase de cierre para el pitch

> Obras Cerca convierte los miles de obras públicas, contratos y proveedores dispersos en cuatro portales del Estado peruano en una sola vista ciudadana. No acusamos a nadie: priorizamos expedientes basados en datos oficiales para que cualquier vecino, periodista o auditor pueda revisar lo que hoy nadie tiene tiempo de mirar.

---

## Anexo A — Glosario rápido

- **UIT 2026:** Unidad Impositiva Tributaria, S/ 5,500. El umbral de 8 UIT son S/ 44,000.
- **SEACE:** Sistema Electrónico de Contrataciones del Estado. Operado por OECE.
- **OECE:** Organismo Especializado para las Contrataciones Públicas Eficientes (antes OSCE).
- **Infobras:** Sistema Nacional de Información de Obras Públicas, operado por Contraloría. Es la principal fuente de obras físicas en el Perú.
- **Código Infobras:** identificador único de cada obra registrada en Infobras (ej: 52903). Permite construir deep-links a la ficha oficial.
- **Código Único de Inversión (CUI):** identificador del proyecto en el banco de inversiones de Invierte.pe.
- **MEF:** Ministerio de Economía y Finanzas. Su Consulta Amigable muestra ejecución presupuestal.
- **PAC:** Plan Anual de Contrataciones. Cada entidad pública lo publica.
- **OCDS:** Open Contracting Data Standard, estándar internacional de datos de contratación abierta.
- **Obra detenida (definición oficial Contraloría):** obra que tras iniciar ejecución física no registra avance por ≥6 meses.
