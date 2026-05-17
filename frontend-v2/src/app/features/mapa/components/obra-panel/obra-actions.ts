import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { Icon } from '../../../../shared/ui/icon/icon';
import type { Obra } from '../../../../core/models/obra.model';

@Component({
  selector: 'app-obra-actions',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './obra-actions.html',
  styleUrl: './obra-actions.scss',
})
export class ObraActions {
  readonly obra = input.required<Obra>();
}
