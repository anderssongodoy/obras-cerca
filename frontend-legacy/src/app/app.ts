import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header class="border-b border-stone-200 bg-paper/80 backdrop-blur-sm sticky top-0 z-50">
      <div class="max-w-6xl mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <a routerLink="/" class="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div class="w-8 h-8 bg-terracotta rounded-sm flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-stone-50">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
            </div>
            <div>
              <span class="font-serif text-xl text-stone-900 tracking-tight">Obras Cerca</span>
              <span class="hidden sm:inline text-stone-500 text-sm ml-2">Lima Metropolitana y Callao</span>
            </div>
          </a>
          <nav class="flex items-center gap-1">
            <a routerLink="/" routerLinkActive="bg-stone-200 text-stone-900" [routerLinkActiveOptions]="{exact:true}"
               class="px-3 py-1.5 text-sm rounded transition-colors text-stone-600 hover:text-stone-900 hover:bg-stone-100">Inicio</a>
            <a routerLink="/mapa" routerLinkActive="bg-stone-200 text-stone-900"
               class="px-3 py-1.5 text-sm rounded transition-colors text-stone-600 hover:text-stone-900 hover:bg-stone-100">Mapa</a>
            <a routerLink="/senales" routerLinkActive="bg-stone-200 text-stone-900"
               class="px-3 py-1.5 text-sm rounded transition-colors text-stone-600 hover:text-stone-900 hover:bg-stone-100">Señales</a>
          </nav>
        </div>
      </div>
    </header>

    <router-outlet />

    <footer class="border-t border-stone-200 mt-16">
      <div class="max-w-4xl mx-auto px-6 py-8">
        <div class="flex flex-col sm:flex-row justify-between gap-4">
          <div>
            <p class="font-serif text-lg text-stone-900 mb-1">Obras Cerca</p>
            <p class="text-sm text-stone-500">
              Transparencia ciudadana sobre obras públicas en Lima y Callao.
            </p>
          </div>
          <div class="text-sm text-stone-500">
            <p>Datos cruzados: MEF/Invierte.pe · Infobras/Contraloría · SEACE · Pentaho ≤8 UIT</p>
            <p>hack@latam 2026 — Track Transparency &amp; Corruption</p>
          </div>
        </div>
        <p class="text-xs text-stone-400 mt-6">
          Este sitio cruza información pública. No clasificamos ni acusamos — mostramos lo que el Estado dice de sí mismo.
        </p>
      </div>
    </footer>
  `,
})
export class App {}
