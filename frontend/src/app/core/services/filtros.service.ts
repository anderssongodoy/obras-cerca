import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { UBIGEO_CALLAO_DEFAULT } from '../config/map.config';
import type { FiltroChip, FiltrosState } from '../models/filtros.model';

@Injectable({ providedIn: 'root' })
export class FiltrosService {
  private readonly router = inject(Router);

  readonly estado = signal<FiltroChip>('todas');
  readonly texto = signal<string>('');
  readonly ubigeo = signal<string | null>(UBIGEO_CALLAO_DEFAULT);

  readonly state = computed<FiltrosState>(() => ({
    estado: this.estado(),
    texto: this.texto(),
    ubigeo: this.ubigeo(),
  }));

  readonly hasActiveFilter = computed(
    () => this.estado() !== 'todas' || this.texto().trim().length > 0,
  );

  constructor() {
    this.initFromUrl();
    effect(() => {
      const qp = this.toQueryParams();
      void this.router.navigate([], {
        queryParams: qp,
        queryParamsHandling: 'merge',
        replaceUrl: true,
      });
    });
  }

  setEstado(chip: FiltroChip): void {
    this.estado.set(chip);
  }

  setTexto(value: string): void {
    this.texto.set(value);
  }

  reset(): void {
    this.estado.set('todas');
    this.texto.set('');
  }

  toQueryParams(): Record<string, string | null> {
    const s = this.state();
    return {
      estado: s.estado === 'todas' ? null : s.estado,
      q: s.texto.trim() || null,
      ubigeo: s.ubigeo,
    };
  }

  private initFromUrl(): void {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const e = params.get('estado');
    if (e && this.isFiltroChip(e)) this.estado.set(e);
    const q = params.get('q');
    if (q) this.texto.set(q);
    const u = params.get('ubigeo');
    if (u) this.ubigeo.set(u);
  }

  private isFiltroChip(value: string): value is FiltroChip {
    return (
      value === 'todas' ||
      value === 'en_ejecucion' ||
      value === 'en_licitacion' ||
      value === 'verificada' ||
      value === 'informativo' ||
      value === 'senal' ||
      value === 'con_senal'
    );
  }
}
