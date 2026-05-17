import { Injectable, inject } from '@angular/core';

import { MapService } from './map.service';

@Injectable({ providedIn: 'root' })
export class GeolocationService {
  private readonly map = inject(MapService);

  centerOnCallao(): void {
    this.map.flyToCallao();
  }
}
