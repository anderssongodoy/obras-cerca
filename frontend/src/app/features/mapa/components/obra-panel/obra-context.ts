import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import type { EstadoObra } from '../../../../core/models/obra.model';

@Component({
  selector: 'app-obra-context',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './obra-context.html',
  styleUrl: './obra-context.scss',
})
export class ObraContext {
  readonly estado = input.required<EstadoObra>();

  protected readonly text = computed(() => {
    switch (this.estado()) {
      case 'en_ejecucion':
        return 'Obra en <strong>construcción</strong>. Avance reportado por INFObras.';
      case 'en_licitacion':
        return 'En proceso de <strong>selección de contratista</strong> a través del SEACE.';
      case 'verificada':
        return 'Información <strong>contrastada</strong> con informes oficiales de Contraloría.';
      case 'informativo':
        return 'Hito o información <strong>referencial</strong> sin avance asociado.';
      case 'senal':
        return 'Señal ciudadana — <strong>requiere contraste</strong> con fuente oficial.';
      default:
        return '';
    }
  });
}
