import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', loadComponent: () => import('./home/home.component').then(m => m.HomeComponent) },
  { path: 'mapa', loadComponent: () => import('./mapa/mapa.component').then(m => m.MapaComponent) },
  { path: 'senales', loadComponent: () => import('./senales/senales.component').then(m => m.SenalesComponent) },
  { path: 'obra/:id', loadComponent: () => import('./obra/obra.component').then(m => m.ObraComponent) },
  { path: 'contratista/:ruc', loadComponent: () => import('./contratista/contratista.component').then(m => m.ContratistaComponent) },
  { path: '**', redirectTo: '' },
];
