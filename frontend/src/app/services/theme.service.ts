import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_KEY = 'user-theme-preference';
  private isDark = false;

  constructor() {
    this.initTheme();
  }

  /**
   * Initialise le thème au chargement
   */
  private initTheme(): void {
    const savedTheme = localStorage.getItem(this.THEME_KEY);
    if (savedTheme) {
      this.isDark = savedTheme === 'dark';
    } else {
      // Détecte la préférence du système d'exploitation par défaut
      this.isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    this.applyTheme();
  }

  /**
   * Bascule entre mode clair et mode sombre
   */
  toggleTheme(): void {
    this.isDark = !this.isDark;
    localStorage.setItem(this.THEME_KEY, this.isDark ? 'dark' : 'light');
    this.applyTheme();
  }

  /**
   * Indique si le mode sombre est actif
   */
  isDarkMode(): boolean {
    return this.isDark;
  }

  /**
   * Applique la classe .dark-theme sur le <body>
   */
  private applyTheme(): void {
    if (this.isDark) {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }
  }
}