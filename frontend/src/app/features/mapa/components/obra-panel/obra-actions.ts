import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icon } from '../../../../shared/ui/icon/icon';
import type { Obra } from '../../../../core/models/obra.model';

@Component({
  selector: 'app-obra-actions',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, RouterLink],
  templateUrl: './obra-actions.html',
  styleUrl: './obra-actions.scss',
})
export class ObraActions {
  readonly obra = input.required<Obra>();
}
