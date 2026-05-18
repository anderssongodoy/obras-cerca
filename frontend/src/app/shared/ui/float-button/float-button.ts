import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { Icon } from '../icon/icon';

@Component({
  selector: 'app-float-button',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './float-button.html',
  styleUrl: './float-button.scss',
})
export class FloatButton {
  readonly icon = input.required<string>();
  readonly ariaLabel = input.required<string>();
  readonly clicked = output<void>();

  protected onClick(): void {
    this.clicked.emit();
  }
}
