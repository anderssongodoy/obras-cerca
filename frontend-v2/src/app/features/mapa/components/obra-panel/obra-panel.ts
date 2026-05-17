import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { EstadoPill } from '../../../../shared/ui/estado-pill/estado-pill';
import { IconButton } from '../../../../shared/ui/icon-button/icon-button';
import type { Obra } from '../../../../core/models/obra.model';
import { ObraActions } from './obra-actions';
import { ObraContext } from './obra-context';
import { ObraMeta } from './obra-meta';
import { ObraSenalAlert } from './obra-senal-alert';

@Component({
  selector: 'app-obra-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EstadoPill, IconButton, ObraMeta, ObraSenalAlert, ObraContext, ObraActions],
  templateUrl: './obra-panel.html',
  styleUrl: './obra-panel.scss',
})
export class ObraPanel {
  readonly obra = input<Obra | null>(null);
  readonly closed = output<void>();

  protected onClose(): void {
    this.closed.emit();
  }
}
