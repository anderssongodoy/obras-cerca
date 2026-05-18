import { Injectable } from '@angular/core';
import { httpResource } from '@angular/common/http';

import type { Tramo } from '../models/obra.model';

@Injectable({ providedIn: 'root' })
export class TramosService {
  readonly resource = httpResource<Tramo[]>(() => '/assets/mock/tramos.callao.json');

  readonly tramos = this.resource.value;
  readonly isLoading = this.resource.isLoading;
  readonly error = this.resource.error;
}
