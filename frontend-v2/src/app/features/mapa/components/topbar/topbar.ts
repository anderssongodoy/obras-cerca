import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { Icon } from '../../../../shared/ui/icon/icon';

@Component({
  selector: 'app-topbar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, RouterLink, RouterLinkActive],
  templateUrl: './topbar.html',
  styleUrl: './topbar.scss',
})
export class Topbar {
  readonly searchValue = input<string>('');
  readonly hasActiveFilter = input<boolean>(false);
  readonly filterCount = input<number>(0);
  readonly filtersOpen = input<boolean>(false);
  readonly showMapControls = input<boolean>(true);

  readonly searchChanged = output<string>();
  readonly filtrosOpened = output<void>();
  readonly locationCentered = output<void>();

  protected onSearch(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.searchChanged.emit(target.value);
  }
}
