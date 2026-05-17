import { Injectable, computed, inject } from '@angular/core';
import { httpResource } from '@angular/common/http';

import { API_BASE_URL } from '../config/api.config';
import { UBIGEO_CALLAO_DEFAULT } from '../config/map.config';
import type { SenalApi } from '../models/obra.model';

@Injectable({ providedIn: 'root' })
export class SenalesService {
  private readonly apiBase = inject(API_BASE_URL);

  readonly resource = httpResource<SenalApi[]>(() => ({
    url: `${this.apiBase}/api/senales`,
    params: {
      ...(UBIGEO_CALLAO_DEFAULT ? { ubigeo: UBIGEO_CALLAO_DEFAULT } : {}),
      limit: 500,
    },
  }));

  // Set<obra_id> con las obras que tienen al menos una señal activa.
  // Usado por ObrasService para derivar el flag `conSenal` por obra.
  readonly obrasConSenal = computed<Set<number>>(() => {
    const items = this.resource.value() ?? [];
    return new Set(items.map((s) => s.obra_id).filter((id): id is number => id != null));
  });

  readonly isLoading = this.resource.isLoading;
  readonly error = this.resource.error;
}
