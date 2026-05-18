import { ChangeDetectionStrategy, Component, inject, input } from '@angular/core';

import { ChatService } from '../../../../core/services/chat.service';
import { Icon } from '../../../../shared/ui/icon/icon';
import type { Obra } from '../../../../core/models/obra.model';

@Component({
  selector: 'app-obra-actions',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './obra-actions.html',
  styleUrl: './obra-actions.scss',
})
export class ObraActions {
  readonly obra = input.required<Obra>();

  private readonly chat = inject(ChatService);
  protected readonly canAsk = this.chat.canAsk;

  protected openChat(): void {
    this.chat.openForObra(this.obra().id);
  }
}
