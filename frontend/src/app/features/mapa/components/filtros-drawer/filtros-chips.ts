import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { Chip } from '../../../../shared/ui/chip/chip';
import type { FiltroChip } from '../../../../core/models/filtros.model';

interface ChipDef {
  chip: FiltroChip;
  label: string;
  dot: string | null;
}

@Component({
  selector: 'app-filtros-chips',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Chip],
  templateUrl: './filtros-chips.html',
  styleUrl: './filtros-chips.scss',
})
export class FiltrosChips {
  readonly activeChip = input.required<FiltroChip>();
  readonly counts = input.required<Record<FiltroChip, number>>();
  readonly chipChanged = output<FiltroChip>();

  protected readonly chips: readonly ChipDef[] = [
    { chip: 'todas',         label: 'Todas',                dot: null },
    { chip: 'en_ejecucion',  label: 'En ejecución',         dot: 'var(--state-ejecucion)' },
    { chip: 'en_licitacion', label: 'En licitación',        dot: 'var(--state-licitacion)' },
    { chip: 'verificada',    label: 'Información contrastada', dot: 'var(--state-verificada)' },
    { chip: 'con_senal',     label: 'Con señal ciudadana',  dot: 'var(--state-senal)' },
  ];

  protected onChipClick(chip: FiltroChip): void {
    this.chipChanged.emit(chip);
  }
}
