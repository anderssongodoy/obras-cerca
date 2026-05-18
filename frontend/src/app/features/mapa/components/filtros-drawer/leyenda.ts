import { ChangeDetectionStrategy, Component } from '@angular/core';

import { Icon } from '../../../../shared/ui/icon/icon';

@Component({
  selector: 'app-leyenda',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './leyenda.html',
  styleUrl: './leyenda.scss',
})
export class Leyenda {
  protected readonly items = [
    { color: 'var(--state-ejecucion)',   icon: 'construction', label: 'En ejecución' },
    { color: 'var(--state-licitacion)',  icon: 'gavel',        label: 'En licitación' },
    { color: 'var(--state-verificada)',  icon: 'verified',     label: 'Información contrastada' },
    { color: 'var(--state-informativo)', icon: 'info',         label: 'Informativo' },
    { color: 'var(--state-senal)',       icon: 'flag',         label: 'Señal ciudadana' },
  ] as const;
}
