import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { Icon } from '../../../../shared/ui/icon/icon';

@Component({
  selector: 'app-obra-meta',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './obra-meta.html',
  styleUrl: './obra-meta.scss',
})
export class ObraMeta {
  readonly entidad = input.required<string>();
  readonly distrito = input.required<string>();
}
