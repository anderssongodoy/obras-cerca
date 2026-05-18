import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { API_BASE_URL } from '../config/api.config';
import type {
  ChatFuente,
  ChatHealth,
  ChatMessage,
  ChatResponse,
  ChatSugerencias,
  PreguntaIn,
} from '../models/chat.model';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly http = inject(HttpClient);
  private readonly apiBase = inject(API_BASE_URL);

  private readonly _isOpen      = signal(false);
  private readonly _obraId      = signal<number | null>(null);
  private readonly _messages    = signal<ChatMessage[]>([]);
  private readonly _health      = signal<ChatHealth | null>(null);
  private readonly _sugerencias = signal<string[]>([]);
  private readonly _isLoading   = signal(false);

  readonly isOpen      = this._isOpen.asReadonly();
  readonly obraId      = this._obraId.asReadonly();
  readonly messages    = this._messages.asReadonly();
  readonly health      = this._health.asReadonly();
  readonly sugerencias = this._sugerencias.asReadonly();
  readonly isLoading   = this._isLoading.asReadonly();

  readonly canAsk   = computed(() => this._health()?.puede_preguntar ?? false);
  readonly showChips = computed(
    () => this._messages().length === 0 && this._sugerencias().length > 0,
  );

  // --- ciclo de vida ---

  /**
   * Precarga health y sugerencias para una obra sin abrir el panel.
   * Si la obra ya está activa y health no es null, no hace nada (cache).
   */
  prefetchForObra(obraId: number): void {
    if (this._obraId() === obraId && this._health() !== null) return;
    const obraChanged = this._obraId() !== obraId;
    this._obraId.set(obraId);
    this._health.set(null);
    this._sugerencias.set([]);
    if (obraChanged) {
      this._messages.set([]);
    }
    void this.loadHealth(obraId);
    void this.loadSugerencias(obraId);
  }

  /**
   * Abre el chat para una obra.
   * Si ya estaba abierto en la misma obra → solo abre sin resetear.
   * Si la obra cambia → prefetch + abre.
   */
  openForObra(obraId: number): void {
    if (this._obraId() === obraId) {
      this._isOpen.set(true);
      return;
    }
    this.prefetchForObra(obraId);
    this._isOpen.set(true);
  }

  /** Cierra el panel SIN borrar mensajes (re-open preserva historial). */
  closeChat(): void {
    this._isOpen.set(false);
  }

  /**
   * Cambia la obra activa mientras el chat ya está abierto.
   * Limpia mensajes y recarga health + sugerencias.
   */
  resetForObra(obraId: number): void {
    this._obraId.set(obraId);
    this._messages.set([]);
    this._health.set(null);
    this._sugerencias.set([]);
    void this.loadHealth(obraId);
    void this.loadSugerencias(obraId);
  }

  // --- API calls (fire & forget; errores degradan al signal) ---

  private async loadHealth(obraId: number): Promise<void> {
    try {
      const r = await firstValueFrom(
        this.http.get<ChatHealth>(
          `${this.apiBase}/api/obras/${obraId}/preguntar/health`,
        ),
      );
      if (this._obraId() === obraId) this._health.set(r);
    } catch {
      // fail-safe: dejar health=null → canAsk()=false → botón oculto
      if (this._obraId() === obraId) this._health.set(null);
    }
  }

  private async loadSugerencias(obraId: number): Promise<void> {
    try {
      const r = await firstValueFrom(
        this.http.get<ChatSugerencias>(
          `${this.apiBase}/api/obras/${obraId}/preguntar/sugerencias`,
        ),
      );
      if (this._obraId() === obraId) {
        this._sugerencias.set(r.sugerencias ?? []);
      }
    } catch {
      if (this._obraId() === obraId) this._sugerencias.set([]);
    }
  }

  /**
   * Envía una pregunta al RAG backend.
   * Append optimístico + placeholder loading + replace al recibir.
   */
  async ask(pregunta: string): Promise<void> {
    const obraId = this._obraId();
    const text   = pregunta.trim();
    if (obraId == null || text.length < 3 || this._isLoading()) return;

    const userMsg: ChatMessage = {
      role: 'user',
      text,
      timestamp: Date.now(),
    };
    const aiPlaceholder: ChatMessage = {
      role: 'ai',
      text: '',
      loading: true,
      timestamp: Date.now() + 1,
    };

    this._messages.update((m) => [...m, userMsg, aiPlaceholder]);
    this._isLoading.set(true);

    try {
      const r = await firstValueFrom(
        this.http.post<ChatResponse>(
          `${this.apiBase}/api/obras/${obraId}/preguntar`,
          { pregunta: text } satisfies PreguntaIn,
        ),
      );
      if (this._obraId() !== obraId) return; // obra cambió mid-request
      this._messages.update((m) => {
        const copy = [...m];
        const aiMsg: ChatMessage = {
          role: 'ai',
          text: r.respuesta,
          fuentes: (r.fuentes ?? []) as ChatFuente[],
          cached: r.cache,
          timestamp: Date.now(),
        };
        copy[copy.length - 1] = aiMsg;
        return copy;
      });
    } catch {
      if (this._obraId() !== obraId) return;
      this._messages.update((m) => {
        const copy = [...m];
        const errMsg: ChatMessage = {
          role: 'ai',
          text: 'No pude responder ahora mismo. Intentá de nuevo en unos segundos.',
          isError: true,
          timestamp: Date.now(),
        };
        copy[copy.length - 1] = errMsg;
        return copy;
      });
    } finally {
      if (this._obraId() === obraId) this._isLoading.set(false);
    }
  }
}
