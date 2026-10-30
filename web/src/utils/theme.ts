export type ThemeMode = 'system' | 'light' | 'dark';

export const THEME_STORAGE_KEY = 'now-workbench-theme';

let currentMode: ThemeMode = 'system';
let mediaListenerAttached = false;

function handleSystemThemeChange(e: MediaQueryListEvent): void {
  if (currentMode === 'system') {
    applyResolvedTheme(e.matches ? 'dark' : 'light');
  }
}

function applyResolvedTheme(theme: 'light' | 'dark'): void {
  if (typeof document !== 'undefined') {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      document.body?.classList.add('now-lux-dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
      document.body?.classList.remove('now-lux-dark');
    }
  }
}

export function getStoredTheme(): ThemeMode {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === 'light' || stored === 'dark' || stored === 'system') {
        return stored;
      }
    } catch {
      // ignore security / storage quota errors
    }
  }
  return 'system';
}

export function applyTheme(mode: ThemeMode = 'system'): void {
  currentMode = mode;
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, mode);
    } catch {
      // ignore quota or privacy errors
    }
  }

  if (!mediaListenerAttached && typeof window !== 'undefined' && window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    if (mq.addEventListener) {
      mq.addEventListener('change', handleSystemThemeChange);
    }
    mediaListenerAttached = true;
  }

  if (mode === 'dark') {
    applyResolvedTheme('dark');
  } else if (mode === 'light') {
    applyResolvedTheme('light');
  } else {
    const prefersDark =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyResolvedTheme(prefersDark ? 'dark' : 'light');
  }
}

// Immediately apply stored theme upon module evaluation
if (typeof window !== 'undefined') {
  applyTheme(getStoredTheme());
}
