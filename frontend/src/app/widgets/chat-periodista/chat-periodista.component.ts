import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  ViewChild,
  computed,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

/**
 * Componente standalone para chat RAG sobre informes de Contraloría.
 *
 * NO toca ningún archivo del frontend principal — vive aislado en widgets/.
 *
 * Para usarlo, tu compañero (o tú) importas el componente donde quieras:
 *
 *   import { ChatPeriodistaComponent } from './widgets/chat-periodista/chat-periodista.component';
 *
 *   @Component({
 *     // ...
 *     imports: [..., ChatPeriodistaComponent],
 *     template: `... <app-chat-periodista [obraId]="obra.id" /> ...`,
 *   })
 *
 * El componente:
 *   - Detecta automáticamente la URL del API (localhost en dev, api.obrascerca.trinitylabs.app en prod)
 *   - Verifica si la obra tiene informes indexados (oculta el chat si no)
 *   - Carga 4 preguntas sugeridas contextuales (chips clicables)
 *   - Permite preguntas libres con input
 *   - Muestra respuesta + fuentes citables con link al PDF
 *   - Maneja loading, errores, y degradación graceful
 */
interface Fuente {
  informe_id: number;
  nro_informe: string;
  titulo: string;
  pagina: number | null;
  url_pdf: string | null;
}

interface QA {
  pregunta: string;
  respuesta: string;
  fuentes: Fuente[];
  cache?: boolean;
  provider?: string;
  loading: boolean;
  error?: string;
}

interface HealthResponse {
  obra_id: number;
  chunks_indexados: number;
  informes_indexados: number;
  puede_preguntar: boolean;
}

interface SugerenciasResponse {
  obra_id: number;
  puede_preguntar: boolean;
  sugerencias: string[];
}

interface PreguntarResponse {
  respuesta: string;
  fuentes: Fuente[];
  cache: boolean;
  provider?: string;
  modelo?: string;
}

function resolveApiBase(): string {
  if (typeof window === 'undefined') return 'http://localhost:8000';
  const host = window.location.hostname;
  if (host === 'localhost' || host === '127.0.0.1' || host.startsWith('192.168.')) {
    return 'http://localhost:8000';
  }
  return 'https://api.obrascerca.trinitylabs.app';
}

@Component({
  selector: 'app-chat-periodista',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="border border-stone-200 rounded-lg bg-paper overflow-hidden">

      <!-- HEADER -->
      <header class="px-5 py-4 border-b border-stone-200 bg-white flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" class="text-terracotta shrink-0">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
          </svg>
          <h3 class="font-serif text-base text-stone-900 leading-tight">
            Preguntar a los informes
          </h3>
        </div>
        <span *ngIf="health()?.puede_preguntar" class="text-[10px] uppercase tracking-wide text-stone-500 font-medium shrink-0">
          {{ health()?.informes_indexados }} informe{{ (health()?.informes_indexados ?? 0) === 1 ? '' : 's' }}
        </span>
      </header>

      <!-- ESTADO: NO DISPONIBLE -->
      <div *ngIf="health() && !health()!.puede_preguntar" class="px-5 py-8 text-center">
        <p class="text-sm text-stone-500 mb-1">
          Esta obra todavía no tiene informes de Contraloría indexados para consulta.
        </p>
        <p class="text-xs text-stone-400">
          Cuando estén indexados, podrás preguntar sobre ellos acá.
        </p>
      </div>

      <!-- ESTADO: CARGANDO META -->
      <div *ngIf="!health()" class="px-5 py-6 text-center">
        <p class="text-sm text-stone-400">Cargando…</p>
      </div>

      <!-- CHAT (sólo si puede_preguntar) -->
      <div *ngIf="health()?.puede_preguntar">

        <!-- SUGERENCIAS (solo si no hay historial) -->
        <div *ngIf="historial().length === 0 && sugerencias().length > 0" class="px-5 py-4 border-b border-stone-100">
          <p class="text-[10px] uppercase tracking-wide text-stone-500 font-medium mb-2.5">
            Preguntas sugeridas
          </p>
          <div class="flex flex-col gap-1.5">
            <button
              *ngFor="let s of sugerencias()"
              type="button"
              (click)="enviarSugerencia(s)"
              [disabled]="enviando()"
              class="text-left px-3 py-2 text-sm text-stone-700 bg-stone-50 hover:bg-stone-100 border border-stone-200 rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
              {{ s }}
            </button>
          </div>
        </div>

        <!-- HISTORIAL -->
        <div #scroller class="max-h-[420px] overflow-y-auto px-5 py-4 space-y-5" [class.border-b]="historial().length > 0" [class.border-stone-100]="historial().length > 0">
          <article *ngFor="let qa of historial(); trackBy: trackByIdx" class="space-y-2">

            <!-- Pregunta del periodista -->
            <div class="flex justify-end">
              <div class="bg-stone-900 text-stone-50 rounded-lg rounded-br-sm px-3.5 py-2 text-sm max-w-[88%]">
                {{ qa.pregunta }}
              </div>
            </div>

            <!-- Respuesta del agente -->
            <div class="flex">
              <div class="bg-stone-50 border border-stone-200 rounded-lg rounded-bl-sm px-3.5 py-2.5 max-w-[92%]">
                <!-- Loading -->
                <div *ngIf="qa.loading" class="flex items-center gap-2 text-xs text-stone-500">
                  <span class="inline-block w-1.5 h-1.5 bg-stone-400 rounded-full animate-pulse"></span>
                  <span class="inline-block w-1.5 h-1.5 bg-stone-400 rounded-full animate-pulse" style="animation-delay:0.2s"></span>
                  <span class="inline-block w-1.5 h-1.5 bg-stone-400 rounded-full animate-pulse" style="animation-delay:0.4s"></span>
                  <span class="ml-1">Buscando en los informes…</span>
                </div>

                <!-- Error -->
                <div *ngIf="qa.error" class="text-sm text-terracotta">
                  ⚠ {{ qa.error }}
                </div>

                <!-- Respuesta exitosa -->
                <div *ngIf="!qa.loading && !qa.error">
                  <p class="text-sm text-stone-800 leading-relaxed whitespace-pre-wrap">{{ qa.respuesta }}</p>

                  <!-- Metadata -->
                  <div *ngIf="qa.cache || qa.provider === 'fallback' || qa.provider === 'stub'"
                       class="mt-2 text-[10px] text-stone-400 italic">
                    <span *ngIf="qa.cache">Respuesta cacheada</span>
                    <span *ngIf="qa.provider === 'fallback' || qa.provider === 'stub'">
                      Respuesta degradada (el redactor automático no respondió)
                    </span>
                  </div>

                  <!-- Fuentes -->
                  <div *ngIf="qa.fuentes && qa.fuentes.length > 0" class="mt-3 pt-2.5 border-t border-stone-200">
                    <p class="text-[10px] uppercase tracking-wide text-stone-500 font-medium mb-1.5">
                      Fuentes ({{ qa.fuentes.length }})
                    </p>
                    <ul class="space-y-1">
                      <li *ngFor="let f of dedupFuentes(qa.fuentes)" class="text-xs">
                        <a *ngIf="f.url_pdf" [href]="f.url_pdf" target="_blank" rel="noopener"
                           class="text-stone-700 hover:text-terracotta underline-offset-2 hover:underline">
                          Informe {{ f.nro_informe }}<span *ngIf="f.pagina">, pág. {{ f.pagina }}</span>
                        </a>
                        <span *ngIf="!f.url_pdf" class="text-stone-600">
                          Informe {{ f.nro_informe }}<span *ngIf="f.pagina">, pág. {{ f.pagina }}</span>
                        </span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

          </article>
        </div>

        <!-- INPUT -->
        <form (ngSubmit)="preguntar()" class="px-5 py-3 border-t border-stone-100 bg-white">
          <div class="flex gap-2">
            <input
              type="text"
              [(ngModel)]="preguntaInput"
              name="pregunta"
              [disabled]="enviando()"
              placeholder="Pregunta sobre los informes…"
              maxlength="500"
              autocomplete="off"
              class="flex-1 px-3 py-2 text-sm border border-stone-300 rounded focus:outline-none focus:border-stone-700 disabled:opacity-50 disabled:bg-stone-50"
            />
            <button
              type="submit"
              [disabled]="enviando() || !preguntaInput.trim()"
              class="px-3 py-2 bg-stone-900 text-stone-50 text-sm rounded hover:bg-stone-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5">
              <svg *ngIf="!enviando()" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
              </svg>
              <svg *ngIf="enviando()" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="animate-spin">
                <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
              </svg>
              <span class="hidden sm:inline">Preguntar</span>
            </button>
          </div>
          <p class="text-[10px] text-stone-400 mt-1.5">
            Respuestas basadas en informes oficiales de Contraloría. Las fuentes están al final de cada respuesta.
          </p>
        </form>
      </div>

    </section>
  `,
})
export class ChatPeriodistaComponent {
  readonly obraId = input.required<number>();

  @ViewChild('scroller') private scrollerRef?: ElementRef<HTMLDivElement>;

  private http = inject(HttpClient);
  private apiBase = resolveApiBase();

  protected health = signal<HealthResponse | null>(null);
  protected sugerencias = signal<string[]>([]);
  protected historial = signal<QA[]>([]);
  protected enviando = signal<boolean>(false);

  // Bound al input vía ngModel — no es signal porque ngModel necesita property simple
  protected preguntaInput = '';

  constructor() {
    effect(() => {
      const id = this.obraId();
      if (typeof id === 'number' && id > 0) {
        this.cargarMeta(id);
      }
    });

    // Auto-scroll cuando se agrega al historial
    effect(() => {
      const _ = this.historial(); // dep tracking
      queueMicrotask(() => {
        const el = this.scrollerRef?.nativeElement;
        if (el) el.scrollTop = el.scrollHeight;
      });
    });
  }

  protected trackByIdx(i: number) { return i; }

  /**
   * Quita fuentes duplicadas por (informe_id, pagina) — el vector search puede devolver
   * varios chunks de la misma página, no necesitamos repetir el link.
   */
  protected dedupFuentes(fuentes: Fuente[]): Fuente[] {
    const seen = new Set<string>();
    const out: Fuente[] = [];
    for (const f of fuentes) {
      const key = `${f.informe_id}-${f.pagina}`;
      if (!seen.has(key)) {
        seen.add(key);
        out.push(f);
      }
    }
    return out;
  }

  protected enviarSugerencia(pregunta: string) {
    this.preguntaInput = pregunta;
    this.preguntar();
  }

  protected preguntar() {
    const pregunta = (this.preguntaInput || '').trim();
    if (!pregunta || this.enviando()) return;

    this.enviando.set(true);
    const placeholder: QA = {
      pregunta,
      respuesta: '',
      fuentes: [],
      loading: true,
    };
    this.historial.update(h => [...h, placeholder]);
    this.preguntaInput = '';

    this.http
      .post<PreguntarResponse>(
        `${this.apiBase}/api/obras/${this.obraId()}/preguntar`,
        { pregunta },
      )
      .subscribe({
        next: (resp) => {
          this.historial.update(h => {
            const copy = [...h];
            copy[copy.length - 1] = {
              pregunta,
              respuesta: resp.respuesta,
              fuentes: resp.fuentes || [],
              cache: resp.cache,
              provider: resp.provider,
              loading: false,
            };
            return copy;
          });
          this.enviando.set(false);
        },
        error: (err) => {
          const msg =
            err?.status === 404
              ? 'Esta obra no existe en el sistema.'
              : err?.status === 422
              ? 'La pregunta es muy corta o muy larga.'
              : 'No se pudo procesar la pregunta. Reintentá en un momento.';
          this.historial.update(h => {
            const copy = [...h];
            copy[copy.length - 1] = {
              ...copy[copy.length - 1],
              loading: false,
              error: msg,
            };
            return copy;
          });
          this.enviando.set(false);
        },
      });
  }

  private cargarMeta(obraId: number) {
    this.http
      .get<HealthResponse>(`${this.apiBase}/api/obras/${obraId}/preguntar/health`)
      .subscribe({
        next: (h) => this.health.set(h),
        error: () => this.health.set({
          obra_id: obraId,
          chunks_indexados: 0,
          informes_indexados: 0,
          puede_preguntar: false,
        }),
      });

    this.http
      .get<SugerenciasResponse>(`${this.apiBase}/api/obras/${obraId}/preguntar/sugerencias`)
      .subscribe({
        next: (s) => this.sugerencias.set(s.sugerencias || []),
        error: () => this.sugerencias.set([]),
      });
  }
}
