import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { Icon } from '../../../../shared/ui/icon/icon';

@Component({
  selector: 'app-topbar-strip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './topbar-strip.html',
  styleUrl: './topbar-strip.scss',
})
export class TopbarStrip {
  readonly total = input<number>(0);
  readonly source = input<string>('INFObras + SEACE + Contraloría');
}
