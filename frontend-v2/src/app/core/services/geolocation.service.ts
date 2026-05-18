import { Injectable, computed, effect, inject, signal } from '@angular/core';

import { DistritosService } from './distritos.service';
import { MapService } from './map.service';
import { ObrasService } from './obras.service';

export type GeoStatus = 'idle' | 'requesting' | 'granted' | 'denied' | 'unavailable';

@Injectable({ providedIn: 'root' })
export class GeolocationService {
  private readonly mapService = inject(MapService);
  private readonly distritos = inject(DistritosService);
  private readonly obras = inject(ObrasService);

  readonly status = signal<GeoStatus>('idle');
  readonly position = signal<GeolocationPosition | null>(null);

  readonly userUbigeo = computed<string | null>(() => {
    const pos = this.position();
    if (!pos) return null;
    return this.distritos.ubigeoFromCoords(pos.coords.latitude, pos.coords.longitude);
  });



  constructor() {
    if (!('geolocation' in navigator)) {
      this.status.set('unavailable');
    }

    // Marker de ubicación — también observa initialized() para re-sincronizar
    // cuando el mapa se destruye y recrea al navegar entre rutas.
    effect(() => {
      const pos = this.position();
      if (!this.mapService.initialized()) return;
      if (pos) {
        this.mapService.addUserMarker(pos.coords.latitude, pos.coords.longitude);
      } else {
        this.mapService.removeUserMarker();
      }
    });

    // Círculo de radio — reacciona a posición, radioM E initialized()
    effect(() => {
      const pos = this.position();
      const radioM = this.obras.radioM();
      if (!this.mapService.initialized()) return;
      if (pos) {
        this.mapService.syncRadiusCircle(pos.coords.latitude, pos.coords.longitude, radioM);
      } else {
        this.mapService.removeRadiusCircle();
      }
    });
  }

  requestPermission(): void {
    if (this.status() === 'unavailable') return;
    this.status.set('requesting');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.position.set(pos);
        this.status.set('granted');
        this.obras.userLat.set(pos.coords.latitude);
        this.obras.userLon.set(pos.coords.longitude);
        this.centerOnUser();
      },
      () => {
        this.status.set('denied');
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
    );
  }

  skip(): void {
    this.status.set('denied');
  }

  centerOnUser(): void {
    const pos = this.position();
    if (!pos) return;
    this.mapService.flyTo(pos.coords.latitude, pos.coords.longitude, 15);
  }
}
