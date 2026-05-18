import { ChangeDetectionStrategy, Component, computed, inject, output } from '@angular/core';

import { GeolocationService } from '../../../../core/services/geolocation.service';
import { FloatButton } from '../../../../shared/ui/float-button/float-button';

@Component({
  selector: 'app-float-controls',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FloatButton],
  templateUrl: './float-controls.html',
  styleUrl: './float-controls.scss',
})
export class FloatControls {
  private readonly geolocation = inject(GeolocationService);

  readonly zoomedIn = output<void>();
  readonly zoomedOut = output<void>();
  readonly layerToggled = output<void>();

  protected readonly canLocate = computed(() => this.geolocation.status() === 'granted');

  protected onLocate(): void {
    if (!this.canLocate()) return;
    this.geolocation.centerOnUser();
  }
}
