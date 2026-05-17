import { ChangeDetectionStrategy, Component, output } from '@angular/core';

import { FloatButton } from '../../../../shared/ui/float-button/float-button';

@Component({
  selector: 'app-float-controls',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FloatButton],
  templateUrl: './float-controls.html',
  styleUrl: './float-controls.scss',
})
export class FloatControls {
  readonly zoomedIn = output<void>();
  readonly zoomedOut = output<void>();
  readonly layerToggled = output<void>();
}
