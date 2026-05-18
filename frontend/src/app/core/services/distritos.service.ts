import { Injectable, computed, inject } from '@angular/core';
import { httpResource } from '@angular/common/http';

import { API_BASE_URL } from '../config/api.config';
import type { DistritoCentroide } from '../models/distrito-centroide';
import { haversineKm } from '../utils/haversine-distance';

@Injectable({ providedIn: 'root' })
export class DistritosService {
  private readonly apiBase = inject(API_BASE_URL);

  readonly resource = httpResource<DistritoCentroide[]>(() => ({
    url: `${this.apiBase}/api/distritos`,
  }));

  readonly distritos = computed<DistritoCentroide[]>(() => this.resource.value() ?? []);
  readonly loading = computed(() => this.resource.isLoading());
  readonly error = computed(() => this.resource.error());

  ubigeoFromCoords(lat: number, lon: number): string | null {
    const list = this.distritos();
    if (!list.length) return null;

    let best: { ubigeo: string; dist: number } | null = null;
    for (const d of list) {
      const km = haversineKm(lat, lon, d.lat, d.lon);
      if (best === null || km < best.dist) {
        best = { ubigeo: d.ubigeo, dist: km };
      }
    }
    if (!best || best.dist > 50) return null;
    return best.ubigeo;
  }
}
