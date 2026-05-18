import { Injectable, inject } from '@angular/core';
import { httpResource } from '@angular/common/http';

import { API_BASE_URL } from '../config/api.config';
import type { StatsApi } from '../models/home.model';

@Injectable({ providedIn: 'root' })
export class HomeService {
  private readonly apiBase = inject(API_BASE_URL);

  readonly resource = httpResource<StatsApi>(() => ({
    url: `${this.apiBase}/api/stats`,
  }));

  readonly stats = this.resource.value;
  readonly isLoading = this.resource.isLoading;
  readonly error = this.resource.error;
}
