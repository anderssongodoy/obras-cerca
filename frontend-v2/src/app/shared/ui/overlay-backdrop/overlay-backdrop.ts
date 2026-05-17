import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-overlay-backdrop',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '',
  styleUrl: './overlay-backdrop.scss',
  host: {
    '[class.open]': 'open()',
    tabindex: '-1',
    '(click)': 'dismissed.emit()',
  },
})
export class OverlayBackdrop {
  readonly open = input<boolean>(false);
  readonly dismissed = output<void>();
}
