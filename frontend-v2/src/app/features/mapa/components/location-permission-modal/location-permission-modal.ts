import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  afterNextRender,
  computed,
  inject,
  viewChild,
} from '@angular/core';

import { GeolocationService } from '../../../../core/services/geolocation.service';

@Component({
  selector: 'app-location-permission-modal',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [],
  templateUrl: './location-permission-modal.html',
  styleUrl: './location-permission-modal.scss',
})
export class LocationPermissionModal {
  private readonly geolocation = inject(GeolocationService);

  protected readonly status = this.geolocation.status;
  protected readonly visible = computed(() => this.status() === 'idle');

  private readonly allowBtn = viewChild<ElementRef<HTMLButtonElement>>('allowBtn');

  constructor() {
    afterNextRender(() => {
      if (this.visible()) {
        this.allowBtn()?.nativeElement.focus();
      }
    });
  }

  @HostListener('keydown.escape')
  protected onEscape(): void {
    if (this.visible()) {
      this.geolocation.skip();
    }
  }

  protected onAllow(): void {
    this.geolocation.requestPermission();
  }

  protected onSkip(): void {
    this.geolocation.skip();
  }
}
