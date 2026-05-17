import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { Icon } from '../../../../shared/ui/icon/icon';
import type { EstadoObra } from '../../../../core/models/obra.model';

@Component({
  selector: 'app-obra-senal-alert',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './obra-senal-alert.html',
  styleUrl: './obra-senal-alert.scss',
})
export class ObraSenalAlert {
  readonly estado = input.required<EstadoObra>();

  protected readonly copy = computed(() => {
    if (this.estado() === 'senal') {
      return {
        strong: 'Revisión sugerida.',
        body: 'Este punto nace de un reporte ciudadano y debe leerse junto a la fuente oficial disponible.',
      };
    }
    return {
      strong: 'Señal ciudadana de revisión.',
      body: 'Puede requerir contraste con la fuente oficial antes de sacar conclusiones.',
    };
  });
}
