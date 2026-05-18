import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  viewChild,
} from '@angular/core';

import { MapService } from '../../../../core/services/map.service';

@Component({
  selector: 'app-leaflet-map',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<div #host class="leaflet-host"></div>',
  styles: `
    :host { display: block; position: fixed; inset: 0; z-index: 0; }
    .leaflet-host { width: 100%; height: 100%; }
  `,
})
export class LeafletMap {
  private readonly host = viewChild.required<ElementRef<HTMLDivElement>>('host');
  private readonly map = inject(MapService);
  private readonly destroyRef = inject(DestroyRef);

  constructor() {
    afterNextRender(() => {
      this.map.init(this.host().nativeElement);
      this.destroyRef.onDestroy(() => this.map.destroy());
    });
  }
}
