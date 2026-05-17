import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

@Component({
  selector: 'app-chip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './chip.html',
  styleUrl: './chip.scss',
})
export class Chip {
  readonly pressed = input<boolean>(false);
  readonly label = input.required<string>();
  readonly count = input<number | null>(null);
  readonly dotColor = input<string | null>(null);
  readonly toggled = output<boolean>();

  protected readonly ariaPressed = computed(() => (this.pressed() ? 'true' : 'false'));

  protected onClick(): void {
    this.toggled.emit(!this.pressed());
  }
}
