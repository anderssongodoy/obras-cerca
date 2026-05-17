import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HeaderStatsComponent } from './features/header-stats/header-stats.component';
import { MapaComponent } from './features/mapa/mapa.component';
import { FichaObraComponent } from './features/ficha-obra/ficha-obra.component';
import { SenalesPanelComponent } from './features/senales-panel/senales-panel.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HeaderStatsComponent, MapaComponent, FichaObraComponent, SenalesPanelComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent implements OnInit, OnDestroy {
  obraActivaId: number | null = null;
  panelActivo: 'senales' | 'ficha' = 'senales';

  private listener = (e: Event) => {
    this.abrirFicha((e as CustomEvent).detail);
  };

  ngOnInit() {
    document.addEventListener('obra-click', this.listener);
  }

  ngOnDestroy() {
    document.removeEventListener('obra-click', this.listener);
  }

  abrirFicha(id: number) {
    this.obraActivaId = id;
    this.panelActivo = 'ficha';
  }

  cerrarFicha() {
    this.obraActivaId = null;
    this.panelActivo = 'senales';
  }
}
