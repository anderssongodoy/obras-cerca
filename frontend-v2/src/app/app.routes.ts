import type { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'inicio',
    loadComponent: () =>
      import('./features/inicio/inicio.page').then((m) => m.InicioPage),
  },
  {
    path: 'senales',
    loadComponent: () =>
      import('./features/senales/senales.page').then((m) => m.SenalesPage),
  },
  {
    path: 'mapa',
    loadComponent: () =>
      import('./features/mapa/mapa.page').then((m) => m.MapaPage),
  },
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'mapa',
  },
];
