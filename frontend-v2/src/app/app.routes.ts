import type { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/mapa/mapa.page').then((m) => m.MapaPage),
  },
];
