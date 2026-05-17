import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-result-counter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './result-counter.html',
  styleUrl: './result-counter.scss',
})
export class ResultCounter {
  readonly visible = input<boolean>(false);
  readonly shown = input<number>(0);
  readonly total = input<number>(0);
}
