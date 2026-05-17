import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import type { EstadoObra } from '../../../core/models/obra.model';
import {
  estadoColorVar,
  estadoColorVarSoft,
  estadoLabel,
} from '../../../features/mapa/utils/estado-catalog';

@Component({
  selector: 'app-estado-pill',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './estado-pill.html',
  styleUrl: './estado-pill.scss',
})
export class EstadoPill {
  readonly estado = input.required<EstadoObra>();

  protected readonly label = computed(() => estadoLabel[this.estado()]);
  protected readonly color = computed(() => estadoColorVar[this.estado()]);
  protected readonly bg = computed(() => estadoColorVarSoft[this.estado()]);
}
