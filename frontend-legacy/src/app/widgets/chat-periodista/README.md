# Chat Periodista (RAG sobre informes de Contraloría)

Componente Angular standalone que permite a un periodista preguntar sobre los
informes de Contraloría de UNA obra específica. Las respuestas vienen del backend
(`/api/obras/{id}/preguntar`) que hace RAG: vector search + LLM (Minimax).

## Características

- **Standalone**, sin dependencias del resto del frontend
- **Detecta automáticamente** la URL del API (localhost en dev, EC2 en prod)
- **Verifica disponibilidad** — si la obra no tiene informes indexados, muestra un mensaje claro y oculta el chat
- **4 preguntas sugeridas contextuales** (basadas en el estado de la obra: paralizada, saldo, etc.)
- **Cache server-side** — repetir la misma pregunta sobre la misma obra devuelve la respuesta cacheada (<100 ms)
- **Manejo de errores** y modo degradado si el LLM no responde
- **Citas con link a PDF** original del informe de Contraloría
- **Loading state animado** mientras espera respuesta

## Uso

### En cualquier componente

```typescript
import { ChatPeriodistaComponent } from './widgets/chat-periodista/chat-periodista.component';

@Component({
  // ...
  imports: [..., ChatPeriodistaComponent],
  template: `
    <!-- ... otros bloques ... -->
    <app-chat-periodista [obraId]="obra.id" />
  `,
})
```

Eso es todo. El componente se autoconfigura, llama al backend para verificar
si la obra tiene chunks indexados, carga las sugerencias, y se muestra solo
si hay algo que consultar.

### Inputs

| Input | Tipo | Required | Descripción |
|---|---|---|---|
| `obraId` | `number` | Sí | ID de la obra en la BD (campo `obra.id`, NO `nobr_id` ni `cui`) |

### Outputs

Ninguno por ahora. Todo el estado vive dentro del componente.

## Endpoints del backend que usa

| Método | Endpoint | Cuándo lo llama |
|---|---|---|
| `GET` | `/api/obras/:id/preguntar/health` | Al montarse — verifica si hay chunks |
| `GET` | `/api/obras/:id/preguntar/sugerencias` | Al montarse — 4 preguntas contextuales |
| `POST` | `/api/obras/:id/preguntar` | Cada vez que el usuario hace una pregunta |

## Personalización

El componente usa Tailwind v4 + la paleta editorial del proyecto (`paper`,
`terracotta`, `stone-*`). Si querés cambiar colores, edita el `template:` directo.

Para ajustes de altura del scroll del historial: línea con `max-h-[420px]`.

## Diseño

Pensado para ir **dentro de la ficha de obra** (`/obra/:id`), como un panel más
en el flujo del periodista. No es flotante por defecto, pero podés envolverlo
en un `<aside class="fixed top-20 right-4 w-96">...</aside>` si querés que lo sea.

## Limitaciones conocidas

- **Solo obras con chunks indexados** muestran chat. Las que no, ven un mensaje "todavía no hay informes indexados".
- **Sin streaming** — la respuesta llega completa (típicamente 1-3 seg). Para streaming SSE sería un refactor moderado.
- **Sin contexto entre preguntas** — cada Q&A es independiente, no hay conversación. Suficiente para investigación periodística.
- **Idioma fijo: español neutro** (configurado en el system prompt del backend).
