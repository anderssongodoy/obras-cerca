import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { CdkTrapFocus } from '@angular/cdk/a11y';

import { IconButton } from '../../../../shared/ui/icon-button/icon-button';
import { OverlayBackdrop } from '../../../../shared/ui/overlay-backdrop/overlay-backdrop';
import type { FiltroChip } from '../../../../core/models/filtros.model';
import { FiltrosChips } from './filtros-chips';
import { Leyenda } from './leyenda';

@Component({
  selector: 'app-filtros-drawer',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CdkTrapFocus, IconButton, OverlayBackdrop, FiltrosChips, Leyenda],
  templateUrl: './filtros-drawer.html',
  styleUrl: './filtros-drawer.scss',
})
export class FiltrosDrawer {
  readonly open = input<boolean>(false);
  readonly activeChip = input.required<FiltroChip>();
  readonly counts = input.required<Record<FiltroChip, number>>();
  readonly totalVisible = input<number>(0);
  readonly total = input<number>(0);

  readonly closed = output<void>();
  readonly chipChanged = output<FiltroChip>();
  readonly reset = output<void>();
}
