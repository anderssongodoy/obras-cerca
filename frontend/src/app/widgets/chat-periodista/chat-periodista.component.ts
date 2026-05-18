import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  ViewChild,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

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
    @if (health() && health()!.puede_preguntar) {

      <!-- FAB flotante -->
      @if (!isOpen()) {
        <button
          type="button"
          class="fab"
          (click)="open()"
          aria-label="Abrir chat con IA"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
          </svg>
          <span class="fab-label">Preguntar a la IA</span>
        </button>
      }

      <!-- Modal flotante de chat -->
      @if (isOpen()) {
        <div class="chat-window" role="dialog" aria-label="Chat con IA sobre informes de Contraloría">

          <header class="chat-header">
            <div class="chat-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="chat-icon">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
              </svg>
              <div>
                <div class="chat-name">Preguntar a Contraloría</div>
                <div class="chat-sub">{{ health()!.informes_indexados }} informe{{ health()!.informes_indexados === 1 ? '' : 's' }} indexado{{ health()!.informes_indexados === 1 ? '' : 's' }}</div>
              </div>
            </div>
            <button type="button" class="chat-close" (click)="close()" aria-label="Cerrar chat">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </header>

          <div #scroller class="chat-body">
            @if (historial().length === 0 && sugerencias().length > 0) {
              <div class="sugerencias">
                <p class="sugerencias-label">Preguntas sugeridas</p>
                @for (s of sugerencias(); track s) {
                  <button type="button" class="chip" (click)="enviarSugerencia(s)" [disabled]="enviando()">{{ s }}</button>
                }
              </div>
            }

            @for (qa of historial(); track $index) {
              <article class="qa">
                <div class="msg msg-user">
                  <div class="bubble bubble-user">{{ qa.pregunta }}</div>
                </div>
                <div class="msg msg-ai">
                  <div class="bubble bubble-ai">
                    @if (qa.loading) {
                      <div class="typing">
                        <span></span><span></span><span></span>
                        <em>Buscando en los informes…</em>
                      </div>
                    } @else if (qa.error) {
                      <span class="msg-error">⚠ {{ qa.error }}</span>
                    } @else {
                      <div class="msg-text">{{ qa.respuesta }}</div>
                      @if (qa.cache) {
                        <div class="msg-meta">Respuesta cacheada</div>
                      }
                      @if (qa.fuentes.length > 0) {
                        <div class="fuentes">
                          <p class="fuentes-label">Fuentes</p>
                          @for (f of dedupFuentes(qa.fuentes); track f) {
                            <a *ngIf="f.url_pdf" [href]="f.url_pdf" target="_blank" rel="noopener" class="fuente-link">
                              Informe {{ f.nro_informe }}<span *ngIf="f.pagina">, pág. {{ f.pagina }}</span>
                            </a>
                          }
                        </div>
                      }
                    }
                  </div>
                </div>
              </article>
            }
          </div>

          <form class="chat-input" (ngSubmit)="preguntar()">
            <input
              type="text"
              [(ngModel)]="preguntaInput"
              name="pregunta"
              [disabled]="enviando()"
              placeholder="Escribe tu pregunta…"
              maxlength="500"
              autocomplete="off"
            />
            <button type="submit" [disabled]="enviando() || !preguntaInput.trim()" aria-label="Enviar">
              @if (!enviando()) {
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
              } @else {
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
              }
            </button>
          </form>

        </div>
      }
    }
  `,
  styles: `
    :host { display: contents; }

    .fab {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9000;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 14px 20px;
      background: #9f5442;
      color: #fafaf9;
      border: none;
      border-radius: 999px;
      font-family: inherit;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .fab:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(0, 0, 0, 0.24); }
    .fab svg { flex-shrink: 0; }
    @media (max-width: 640px) {
      .fab { padding: 14px; }
      .fab .fab-label { display: none; }
    }

    .chat-window {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: min(380px, calc(100vw - 32px));
      height: min(560px, calc(100vh - 100px));
      max-height: 80vh;
      z-index: 9000;
      display: flex;
      flex-direction: column;
      background: #faf8f5;
      border: 1px solid #d6d3d1;
      border-radius: 16px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.22);
      overflow: hidden;
      animation: chatIn 0.18s ease-out;
    }
    @keyframes chatIn {
      from { opacity: 0; transform: translateY(12px) scale(0.97); }
      to   { opacity: 1; transform: translateY(0) scale(1); }
    }

    .chat-header {
      padding: 14px 16px;
      background: #1c1917;
      color: #fafaf9;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .chat-title { display: flex; align-items: center; gap: 10px; min-width: 0; }
    .chat-icon { color: #c4926a; flex-shrink: 0; }
    .chat-name { font-size: 14px; font-weight: 600; line-height: 1.2; }
    .chat-sub { font-size: 11px; opacity: 0.65; margin-top: 2px; }
    .chat-close {
      background: none;
      border: none;
      color: #fafaf9;
      cursor: pointer;
      padding: 4px;
      opacity: 0.7;
      transition: opacity 0.15s;
    }
    .chat-close:hover { opacity: 1; }

    .chat-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .sugerencias { display: flex; flex-direction: column; gap: 8px; }
    .sugerencias-label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #78716c;
      font-weight: 600;
      margin: 0 0 4px;
    }
    .chip {
      text-align: left;
      padding: 10px 12px;
      background: #fff;
      border: 1px solid #e5e5e5;
      border-radius: 8px;
      font-family: inherit;
      font-size: 13px;
      color: #1c1917;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .chip:hover { background: #f5f5f4; border-color: #9f5442; }
    .chip:disabled { opacity: 0.5; cursor: not-allowed; }

    .qa { display: flex; flex-direction: column; gap: 6px; }
    .msg { display: flex; }
    .msg-user { justify-content: flex-end; }
    .msg-ai { justify-content: flex-start; }

    .bubble {
      max-width: 86%;
      padding: 10px 14px;
      border-radius: 16px;
      font-size: 13px;
      line-height: 1.5;
    }
    .bubble-user {
      background: #1c1917;
      color: #fafaf9;
      border-bottom-right-radius: 4px;
    }
    .bubble-ai {
      background: #fff;
      color: #1c1917;
      border: 1px solid #e5e5e5;
      border-bottom-left-radius: 4px;
    }
    .msg-text { white-space: pre-wrap; }
    .msg-meta { margin-top: 6px; font-size: 10px; color: #a8a29e; font-style: italic; }
    .msg-error { color: #b00; font-size: 13px; }

    .typing { display: flex; align-items: center; gap: 4px; color: #78716c; font-size: 12px; }
    .typing span {
      width: 6px; height: 6px; background: #a8a29e; border-radius: 50%;
      animation: typing 1s infinite;
    }
    .typing span:nth-child(2) { animation-delay: 0.15s; }
    .typing span:nth-child(3) { animation-delay: 0.3s; }
    .typing em { font-style: normal; margin-left: 6px; }
    @keyframes typing {
      0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
      30% { opacity: 1; transform: translateY(-3px); }
    }

    .fuentes {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #e5e5e5;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .fuentes-label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #78716c;
      font-weight: 600;
      margin: 0;
    }
    .fuente-link {
      font-size: 11px;
      color: #57534e;
      text-decoration: none;
      padding: 2px 0;
    }
    .fuente-link:hover { color: #9f5442; text-decoration: underline; }

    .chat-input {
      display: flex;
      gap: 8px;
      padding: 12px;
      border-top: 1px solid #e5e5e5;
      background: #fff;
    }
    .chat-input input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid #d6d3d1;
      border-radius: 999px;
      font-family: inherit;
      font-size: 13px;
      color: #1c1917;
      outline: none;
      transition: border-color 0.15s;
    }
    .chat-input input:focus { border-color: #9f5442; }
    .chat-input input:disabled { opacity: 0.5; background: #f5f5f4; }
    .chat-input button {
      width: 40px;
      height: 40px;
      background: #9f5442;
      color: #fafaf9;
      border: none;
      border-radius: 50%;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s, opacity 0.15s;
      flex-shrink: 0;
    }
    .chat-input button:hover:not(:disabled) { background: #8a4738; }
    .chat-input button:disabled { opacity: 0.4; cursor: not-allowed; }
    .spin { animation: spin 1s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  `,
})
export class ChatPeriodistaComponent {
  readonly obraId = input.required<number>();

  @ViewChild('scroller') private scrollerRef?: ElementRef<HTMLDivElement>;

  private http = inject(HttpClient);
  private apiBase = resolveApiBase();

  protected isOpen = signal<boolean>(false);
  protected health = signal<HealthResponse | null>(null);
  protected sugerencias = signal<string[]>([]);
  protected historial = signal<QA[]>([]);
  protected enviando = signal<boolean>(false);
  protected preguntaInput = '';

  constructor() {
    effect(() => {
      const id = this.obraId();
      if (typeof id === 'number' && id > 0) {
        this.cargarMeta(id);
      }
    });

    effect(() => {
      this.historial();
      queueMicrotask(() => {
        const el = this.scrollerRef?.nativeElement;
        if (el) el.scrollTop = el.scrollHeight;
      });
    });
  }

  protected open() { this.isOpen.set(true); }
  protected close() { this.isOpen.set(false); }

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
    this.historial.update(h => [...h, { pregunta, respuesta: '', fuentes: [], loading: true }]);
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
            err?.status === 404 ? 'Esta obra no existe en el sistema.'
            : err?.status === 422 ? 'La pregunta es muy corta o muy larga.'
            : 'No se pudo procesar la pregunta. Intenta de nuevo.';
          this.historial.update(h => {
            const copy = [...h];
            copy[copy.length - 1] = { ...copy[copy.length - 1], loading: false, error: msg };
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
        error: () => this.health.set({ obra_id: obraId, chunks_indexados: 0, informes_indexados: 0, puede_preguntar: false }),
      });

    this.http
      .get<SugerenciasResponse>(`${this.apiBase}/api/obras/${obraId}/preguntar/sugerencias`)
      .subscribe({
        next: (s) => this.sugerencias.set(s.sugerencias || []),
        error: () => this.sugerencias.set([]),
      });
  }
}
