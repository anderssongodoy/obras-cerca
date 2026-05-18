import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  Injector,
  afterNextRender,
  computed,
  effect,
  inject,
  signal,
  viewChild,
} from '@angular/core';

import { ChatService } from '../../../../core/services/chat.service';
import { Icon } from '../../../../shared/ui/icon/icon';
import { IconButton } from '../../../../shared/ui/icon-button/icon-button';

@Component({
  selector: 'app-obra-chat',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, IconButton],
  templateUrl: './obra-chat.html',
  styleUrl: './obra-chat.scss',
  host: {
    '[class.is-open]':    'chat.isOpen()',
    '[attr.aria-hidden]': 'chat.isOpen() ? null : "true"',
    '[attr.inert]':       'chat.isOpen() ? null : ""',
    '(document:keydown.escape)': 'onEscape()',
  },
})
export class ObraChat {
  protected readonly chat = inject(ChatService);
  private readonly injector   = inject(Injector);
  private readonly scrollHost = viewChild<ElementRef<HTMLElement>>('scrollHost');
  private readonly inputEl    = viewChild<ElementRef<HTMLTextAreaElement>>('inputEl');

  protected readonly draft   = signal('');
  protected readonly canSend = computed(
    () => this.draft().trim().length >= 3 && !this.chat.isLoading(),
  );

  constructor() {
    // Auto-scroll al fondo cuando crece la lista de mensajes
    effect(() => {
      this.chat.messages(); // dependencia — se ejecuta cada vez que messages cambia
      afterNextRender(
        () => {
          const host = this.scrollHost()?.nativeElement;
          if (host) host.scrollTop = host.scrollHeight;
        },
        { injector: this.injector },
      );
    });

    // Foco al input cuando el panel se abre
    effect(() => {
      if (this.chat.isOpen()) {
        afterNextRender(
          () => this.inputEl()?.nativeElement.focus(),
          { injector: this.injector },
        );
      }
    });
  }

  protected onClose(): void {
    this.chat.closeChat();
  }

  protected onEscape(): void {
    if (this.chat.isOpen()) this.chat.closeChat();
  }

  protected async onSend(): Promise<void> {
    const q = this.draft().trim();
    if (q.length < 3 || this.chat.isLoading()) return;
    this.draft.set('');
    await this.chat.ask(q);
  }

  protected onChipClick(sugerencia: string): void {
    this.draft.set(sugerencia);
    void this.onSend();
  }

  protected onKeydown(e: KeyboardEvent): void {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void this.onSend();
    }
  }
}
