import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { ObrasService } from '../../../../core/services/obras.service';

@Component({
  selector: 'app-radio-selector',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [],
  templateUrl: './radio-selector.html',
  styleUrl: './radio-selector.scss',
})
export class RadioSelector {
  private readonly obras = inject(ObrasService);

  // radioM en metros (1000–10000). El slider trabaja en km (1–10).
  protected readonly radioKm = computed(() => this.obras.radioM() / 1000);

  protected onSliderChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const km = Number(input.value);
    this.obras.radioM.set(km * 1000);
    // Actualiza la CSS var que pinta el progreso del track en webkit
    const pct = ((km - 1) / 9) * 100;
    input.style.setProperty('--pct', `${pct}%`);
  }
}
