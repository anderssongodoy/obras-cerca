import { Injectable, inject } from '@angular/core';
import { httpResource } from '@angular/common/http';

import { API_BASE_URL } from '../config/api.config';
import type { SenalApi } from '../models/obra.model';

@Injectable({ providedIn: 'root' })
export class SenalesPageService {
  private readonly apiBase = inject(API_BASE_URL);

  readonly resource = httpResource<SenalApi[]>(() => ({
    url: `${this.apiBase}/api/senales`,
    params: {
      limit: 200,
    },
  }));

  readonly senales = this.resource.value;
  readonly isLoading = this.resource.isLoading;
  readonly error = this.resource.error;
}
