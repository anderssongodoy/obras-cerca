# Brief para v0 — Obras Cerca

> **Workflow:** abre https://v0.dev/chat, pega el brief completo abajo en UN solo mensaje, deja que v0 proponga arquitectura, páginas, paleta y diseño. Después iteras con feedback corto.

> **Tono al pedir cambios:** tratá a v0 como diseñador senior, no como ejecutor. *"Esa paleta se siente fintech, queremos algo más editorial."* — no *"cambia slate-900 a stone-900"*.

---

## El prompt (copy-paste en v0)

```
Sos un diseñador senior de producto digital. Te contrato para diseñar la interfaz de un
proyecto cívico, no técnico. Quiero que decidas vos la arquitectura, paleta, páginas,
tipografía y estructura. No te voy a dar layouts — te doy contexto y dejás que tu
criterio resuelva.

---

CONTEXTO DEL PRODUCTO

Obras Cerca es una herramienta de transparencia ciudadana sobre obras públicas en Lima
Metropolitana y Callao (Perú). El Estado peruano gasta S/24 mil millones al año en obras
de las que ~S/43 mil millones están paralizadas. La información existe pero está dispersa
en cuatro portales oficiales, todos diseñados en los 2000s, todos prácticamente ilegibles
para un vecino común. La gente no audita porque no puede leer lo que el Estado publica.

Lo que hacemos: cruzamos en tiempo real 3 fuentes oficiales (MEF/Invierte.pe, Infobras de
Contraloría, SEACE) y mostramos la verdad. Cuando las 3 coinciden, lo afirmamos. Cuando
difieren —que es lo más común— marcamos la señal: tal vez Infobras dice "obra activa"
pero MEF la tiene desactivada permanentemente desde hace años, y Contraloría tiene un
informe de control en PDF que explica por qué.

La propuesta de valor no es "otro dashboard de obras". Es "te muestro las contradicciones
entre lo que dice el Estado de sí mismo".

---

AUDIENCIA REAL (en orden de probabilidad de uso)

1. Periodistas de datos peruanos (Ojo Público, Convoca, IDL Reporteros, Salud con Lupa).
   Necesitan: encontrar señales, exportar evidencia, links a fuentes oficiales para citar.

2. Regidores y consejeros distritales que quieren munición política para sus sesiones
   municipales. Necesitan: filtrar por su distrito, ver montos paralizados, presentar
   casos concretos.

3. Activistas y ONGs anticorrupción (Proética, Vigila Perú).

4. Vecinos curiosos. Caso edge: alguien que ve una obra parada en su cuadra y la busca.

NO es para auditores de Contraloría — ellos ya tienen acceso interno.
NO es para funcionarios públicos.
NO es para el gobierno mismo.

---

PREGUNTAS QUE EL USUARIO TRAE EN LA CABEZA

"¿Hay obras paradas cerca de mí ahora mismo?"
"¿Quién es el contratista de esta obra y a qué más se ha presentado?"
"¿Cuánta plata se está dejando de gastar bien en mi distrito?"
"¿Esta paralización es real hoy o el dato está desactualizado?"
"¿Hay informe de Contraloría sobre esta obra?"
"¿Por qué la entidad dice una cosa y otro sistema dice otra?"

Si el diseño no responde estas preguntas en 3 clics o menos, falla.

---

CASOS REALES QUE LA APP YA TIENE (mostralos en mockups, no inventes):

JUNTA NACIONAL DE JUSTICIA — sede paralizada
  - 12 años de obra, S/41M aprobados, hoy cuesta S/88M actualizado (sobrecosto +114%).
  - MEF dice activa. Contraloría WFS dice paralizada. Infobras dice "en ejecución".
  - Tres saldos de obra hijos al 0% de avance — el contratista original quebró el contrato
    y los nuevos no han empezado.
  - 5 informes de Contraloría documentando el problema.

SEDAPAL — colector Chorrillos
  - Contrato firmado en 2007. 0% de avance en 18 años.
  - MEF la tiene como DESACTIVADO PERMANENTE.
  - Infobras la sigue mostrando como "En Ejecución" (sus datos están sucios).
  - Contraloría hizo un Control Concurrente en 2019 — eso probablemente la mató.

PROTEGE SERVICIOS S.A. — RUC 20600182197
  - Recibió 195 órdenes de compra ≤8 UIT del Ministerio de Justicia en 12 meses.
  - Eso es 25.07% del monto total de compras menores del ministerio.
  - No es ilegal pero es un patrón que un periodista quiere ver.

---

LO QUE EL BACKEND YA DEVUELVE (API REST en localhost:8000)

Resumen general:
  GET /api/stats → totales: proyectos, obras, paralizadas, saldos, informes, señales.

Geografía:
  GET /api/distritos → los 50 distritos del ámbito MVP con lat/lon.

Obras (lo central):
  GET /api/obras → listado con filtros: ubigeo, paralizadas_wfs, inactivas_mef,
    con_saldos, contratista_ruc, q (texto libre), lat+lon+radio_m (cerca de mí).
    Cada obra trae: estado MEF, estado WFS, estado Infobras, avances (MEF e Infobras),
    sobrecosto%, monto, contratista, distrito, latitud/longitud.

  GET /api/obras/{id} → ficha completa con:
    - Los 3 estados oficiales lado a lado (suelen contradecirse)
    - Saldos de obra (NOBR_IDs hijos cuando el contrato original quebró)
    - Procedimientos SEACE (contratistas, PDFs)
    - Paralizaciones oficiales declaradas en MEF
    - Informes de Control de Contraloría (con URLs a PDFs oficiales)
    - Señales detectadas con fórmula auditable
    - URLs para verificar manualmente en MEF/Infobras/Contraloría

  GET /api/obras/{id}/verificar → cruce LIVE: pregunta a MEF + Infobras + Contraloría
    en tiempo real y devuelve qué dice cada fuente AHORA. Útil para mostrar:
    "no es data vieja — esto viene de la API oficial hace 2 segundos."

  GET /api/obras/{id}/explicacion → texto generado por IA en lenguaje ciudadano (la IA
    solo redacta, jamás clasifica ni decide).

  GET /api/obras/{id}/exportar → CSV con toda la evidencia para periodistas.

Contratistas:
  GET /api/contratistas/{ruc} → perfil + obras + concentración en compras ≤8 UIT.
  GET /api/contratistas/sospechosos/top → top concentración.

Señales:
  GET /api/senales → feed priorizado. Tipos: sobrecosto, discrepancia_avance,
    paralizacion_real, paralizada_zombie, inactiva_mef, saldos_pendientes,
    concentracion_menores.

Cada señal trae: titulo, resumen, score, formula (la regla SQL que la detectó en
lenguaje natural) y evidencia JSONB (los datos crudos para auditar).

---

ANTI-PATRONES QUE NO QUIERO

❌ Dark mode genérico de fintech (slate-950 + sky-400). Lo veo en 9 de cada 10 mockups
   de IA y se siente como Linear/Vercel/Stripe. Esta app no es SaaS B2B.

❌ Grid de 4 KPI cards al inicio. Es el patrón cookie-cutter de "dashboard de admin".

❌ Tags pill con colores semáforo (rojo/amarillo/verde). Nuestro mensaje no es alarma,
   es "mira lo que pasa". Más cerca a investigación periodística que a Pagerduty.

❌ Sidebar fijo izquierdo + main content. Inflado, web 2010.

❌ Replicar el look de Infobras (el portal estatal actual: tablas ASP.NET anidadas,
   azul corporativo gobierno, sin tipografía decente). Si nos parecemos a Infobras
   nadie va a entender por qué somos distintos.

❌ Hero centrado con título gigante + "Sign up" / "Get started". No es un SaaS.

❌ Tipografía Inter para todo. Es la tipografía default de la IA.

❌ Gradientes purple-blue.

❌ Emojis grandes 🚨 en los avisos. Es serio, no Slack.

❌ Iconografía corporativa de Heroicons / Lucide en todos lados.

---

INSPIRACIÓN DE TONO (NO COPIES, ENTIENDE)

El feel debería estar más cerca de:
 - Sitios de periodismo investigativo como ProPublica, OCCRP Aleph, El Faro El Salvador,
   La Nación Data Argentina, Quinto Elemento Lab.
 - Bellingcat Investigations.
 - Datasette de Simon Willison (los datos hablan, el chrome desaparece).
 - The Pudding (storytelling con datos).
 - 18F / GOV.UK (funcional y honesto, sin chrome).

Algunas decisiones que distinguirían el producto:
 - Una tipografía editorial (serif o slab serif) para titulares de obras y entidades —
   evoca "esto es periodismo, no un dashboard".
 - Una paleta que no sea ni "gobierno azul" ni "fintech oscuro" — algo terroso, papel,
   o casi monocromo con un acento muy puntual.
 - Información narrativa, no celdas. Una obra contada en prosa con números embebidos.
 - Dejar respirar la página. No llenar todo el viewport.
 - Tablas densas SOLO cuando el usuario las pide (periodista que quiere ver 200 obras).
   En vista normal, una obra es una historia.

---

DECISIONES QUE QUIERO QUE TÚ TOMES

1. La paleta exacta (HEX), justificada por el tono editorial cívico.
2. La tipografía (probablemente una serif para títulos + una sans para UI).
3. Qué páginas tiene el producto (mínimo 4, máximo 7) y cómo se enlazan entre sí.
4. La estructura de cada página: qué se ve primero, qué requiere scroll, qué requiere
   acción del usuario.
5. Cómo mostrar las contradicciones entre fuentes oficiales (el corazón del producto).
6. Cómo se ve una "señal de revisión" individualmente — no en un grid de cards
   iguales, sino como noticia.
7. Cómo se ve la verificación LIVE (cuando el usuario clickea "verificar ahora" y
   esperamos 3 segundos mientras 3 APIs oficiales responden).
8. La home: ¿landing tradicional o ya muestra contenido?
9. El estado vacío (cuando un distrito no tiene señales aún).
10. La estética del mapa (Leaflet es la lib, pero el estilo es decisión tuya).

---

ENTREGA INICIAL

Una sola página HTML autocontenida con todas las pantallas apiladas verticalmente
(separadas por hr o título de sección). Tailwind por CDN. Inline SVG si necesitas
íconos. Tipografía vía Google Fonts. NADA de imports de librerías de componentes
(sin shadcn, sin Radix, sin imports). Datos hardcodeados con los casos reales que
te di arriba (JNJ, SEDAPAL, PROTEGE).

Empezá explicándome tu visión en 4-5 líneas (qué historia cuenta el producto, cuál
es la paleta y por qué, qué páginas decidiste y por qué). Después generás el HTML.
```

---

## 🔁 Cómo iterar después

v0 te va a entregar un primer render. **No le digas qué cambiar**, decile **qué sentiste**:

| En vez de... | Decile... |
|---|---|
| "Quita los emojis 🚨" | "Esto se siente alarmista, queremos un tono más periodístico" |
| "Cambia slate-900 a stone-900" | "La paleta sigue sintiendo fintech, prueba algo más editorial / papel" |
| "Pon el sidebar a la derecha" | "El sidebar pelea por atención con el contenido, qué tal si la lista de obras es la página y el mapa entra cuando lo pido" |
| "Más espacio" | "La densidad es de admin panel, queremos respiración tipo The Atlantic" |
| "Hazlo más bonito" | "Mostrame 2 propuestas con estéticas opuestas y elegimos" |

## Cuando me pases lo que v0 te dé

Mandame los HTMLs y los adapto a Angular 18 standalone manteniendo el ApiService que ya construí. Yo me encargo de:
- Instalar Tailwind en el proyecto Angular
- Convertir templates v0 → componentes Angular
- Conectar al backend FastAPI corriendo en :8000
- Mantener el routing y dejar todo testeable

**Tip final:** si después del primer prompt v0 te entrega algo genérico, no aceptes. Pedile *"esto se siente cookie-cutter de IA, dame algo que un crítico de diseño consideraría arriesgado"*. La IA tiene a regresar al promedio si no la fuerzas.
