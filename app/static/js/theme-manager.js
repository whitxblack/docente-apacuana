/* ═══════════════════════════════════════════════════════════════
   PORTAL DOCENTE — Theme Manager
   Handles theme (light/dark/auto), accent colors, density,
   and persists preferences in localStorage.
   ═══════════════════════════════════════════════════════════════ */

const ThemeManager = {
  KEYS: {
    theme:    'docente_theme',
    accent:   'docente_accent',
    density:  'docente_density',
    barColor: 'docente_bar_color',
  },

  DEFAULTS: {
    theme:   'light',
    accent:  'emerald',
    density: 'comfortable',
    barColor: '#FFFFFF',
  },

  /** Initialize theme from localStorage on page load */
  init() {
    const theme   = localStorage.getItem(this.KEYS.theme)   || this.DEFAULTS.theme;
    const accent  = localStorage.getItem(this.KEYS.accent)  || this.DEFAULTS.accent;
    const density = localStorage.getItem(this.KEYS.density) || this.DEFAULTS.density;
    const barColor = localStorage.getItem(this.KEYS.barColor);

    this.applyTheme(theme, false);
    this.applyAccent(accent, false);
    this.applyDensity(density, false);
    if (barColor) {
      this.applySidebarColor(barColor, false);
    } else {
      this.applySidebarColor(theme === 'dark' ? '#18181B' : '#FFFFFF', false);
    }

    // Listen for OS theme changes when in auto mode
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (this.getTheme() === 'auto') {
        this.applyTheme('auto', false);
      }
    });
  },

  /** Get current saved theme preference */
  getTheme() {
    return localStorage.getItem(this.KEYS.theme) || this.DEFAULTS.theme;
  },

  getAccent() {
    return localStorage.getItem(this.KEYS.accent) || this.DEFAULTS.accent;
  },

  getDensity() {
    return localStorage.getItem(this.KEYS.density) || this.DEFAULTS.density;
  },

  getBarColor() {
    return localStorage.getItem(this.KEYS.barColor) || (this.getTheme() === 'dark' ? '#18181B' : '#FFFFFF');
  },

  /** Apply theme to DOM */
  applyTheme(theme, save = true) {
    let resolved = theme;
    if (theme === 'auto') {
      resolved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', resolved);
    if (save) localStorage.setItem(this.KEYS.theme, theme);

    // Sync Tailwind config class dark
    if (resolved === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    // Update toggle button icon
    this._updateThemeIcon(resolved);
    
    // Sync dropdown theme switch
    const dropdownCheckbox = document.getElementById('dropdown-theme-checkbox');
    if (dropdownCheckbox) {
      dropdownCheckbox.checked = (resolved === 'dark');
    }
    
    // If no custom bar color is defined, fall back to theme default
    const customBarColor = localStorage.getItem(this.KEYS.barColor);
    if (!customBarColor) {
      this.applySidebarColor(resolved === 'dark' ? '#18181B' : '#FFFFFF', false);
    }
  },

  /** Apply accent color to DOM */
  applyAccent(accent, save = true) {
    // If it starts with # it's a custom color
    if (accent.startsWith('#')) {
      document.documentElement.setAttribute('data-accent', 'custom');
      this._applyCustomColor(accent);
    } else {
      document.documentElement.setAttribute('data-accent', accent);
      // Remove custom properties if previously set
      document.documentElement.style.removeProperty('--color-accent');
      document.documentElement.style.removeProperty('--color-accent-hover');
      document.documentElement.style.removeProperty('--color-accent-subtle');
      document.documentElement.style.removeProperty('--color-accent-text');
      document.documentElement.style.removeProperty('--color-accent-ring');
    }
    if (save) localStorage.setItem(this.KEYS.accent, accent);

    // Update swatch selection in customize panel
    this._updateSwatchSelection(accent);
  },

  /** Apply density */
  applyDensity(density, save = true) {
    document.documentElement.setAttribute('data-density', density);
    if (save) localStorage.setItem(this.KEYS.density, density);
  },

  /** Apply navbar color (sidebar was used in gestor, adapting to top navbar) */
  applySidebarColor(color, save = true) {
    document.documentElement.style.setProperty('--navbar-bg', color);
    
    // Calculate contrast text colors dynamically
    let textColor = '#FFFFFF';
    let textMutedColor = '#D1D5DB';
    let borderHex = 'rgba(255, 255, 255, 0.15)';
    let elementBg = 'rgba(255, 255, 255, 0.08)';
    let elementHover = 'rgba(255, 255, 255, 0.12)';
    let textShadow = '2px 2px 4px rgba(255, 255, 255, 0.6)';
    
    if (color) {
      const hex = color.replace('#', '');
      if (hex.length === 6) {
        const r = parseInt(hex.substring(0,2), 16);
        const g = parseInt(hex.substring(2,4), 16);
        const b = parseInt(hex.substring(4,6), 16);
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
        if (brightness > 200) { // Light color navbar → always use absolute dark values
          // IMPORTANT: Do NOT use var(--color-text-main) here — in dark theme that
          // variable resolves to #FAFAFA (white), making text invisible on white bars.
          textColor = '#111827';
          textMutedColor = '#6B7280';
          borderHex = '#E5E7EB';
          elementBg = '#F9FAFB';
          elementHover = 'rgba(0, 0, 0, 0.05)';
          textShadow = '2px 2px 4px rgba(0, 0, 0, 0.6)';
        }
      }
    }
    
    document.documentElement.style.setProperty('--navbar-text', textColor);
    document.documentElement.style.setProperty('--navbar-text-muted', textMutedColor);
    document.documentElement.style.setProperty('--navbar-border', borderHex);
    document.documentElement.style.setProperty('--navbar-element-bg', elementBg);
    document.documentElement.style.setProperty('--navbar-element-hover', elementHover);
    document.documentElement.style.setProperty('--navbar-text-shadow', textShadow);
    
    if (save) localStorage.setItem(this.KEYS.barColor, color);
  },

  /** Toggle between light and dark */
  toggleTheme() {
    const current = this.getTheme();
    const next = (current === 'dark') ? 'light' : 'dark';
    this.applyTheme(next);
  },

  /** Reset all preferences to defaults */
  resetAll() {
    Object.values(this.KEYS).forEach(k => localStorage.removeItem(k));
    document.documentElement.style.removeProperty('--navbar-bg');
    document.documentElement.style.removeProperty('--navbar-text');
    document.documentElement.style.removeProperty('--navbar-text-muted');
    document.documentElement.style.removeProperty('--navbar-border');
    document.documentElement.style.removeProperty('--navbar-element-bg');
    document.documentElement.style.removeProperty('--navbar-element-hover');
    
    const theme = this.DEFAULTS.theme;
    this.applyTheme(theme);
    this.applyAccent(this.DEFAULTS.accent);
    this.applyDensity(this.DEFAULTS.density);
    this.applySidebarColor(theme === 'dark' ? '#18181B' : '#FFFFFF', false);
  },

  /** Apply custom hex color */
  _applyCustomColor(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);

    document.documentElement.style.setProperty('--color-accent', hex);
    // Darken for hover
    const darken = (c) => Math.max(0, Math.round(c * 0.85));
    document.documentElement.style.setProperty('--color-accent-hover',
      `rgb(${darken(r)}, ${darken(g)}, ${darken(b)})`);
    // Subtle background
    document.documentElement.style.setProperty('--color-accent-subtle',
      `rgba(${r}, ${g}, ${b}, 0.1)`);
    // Text on subtle
    document.documentElement.style.setProperty('--color-accent-text', hex);
    // Focus ring
    document.documentElement.style.setProperty('--color-accent-ring',
      `rgba(${r}, ${g}, ${b}, 0.25)`);
  },

  /** Update the theme toggle icon in header */
  _updateThemeIcon(resolved) {
    const icon = document.getElementById('theme-toggle-icon');
    if (!icon) return;
    if (resolved === 'dark') {
      icon.textContent = 'light_mode';
    } else {
      icon.textContent = 'dark_mode';
    }
  },

  /** Update which color swatch is selected in customize panel */
  _updateSwatchSelection(accent) {
    document.querySelectorAll('.color-swatch[data-accent]').forEach(el => {
      el.classList.toggle('selected', el.dataset.accent === accent);
    });
  }
};

// ─── CUSTOMIZE PANEL CONTROLLER ─────────────────────────────────
const CustomizePanel = {
  isOpen: false,

  toggle() {
    this.isOpen = !this.isOpen;
    const panel = document.getElementById('customize-panel');
    const backdrop = document.getElementById('customize-backdrop');
    if (panel) panel.classList.toggle('open', this.isOpen);
    if (backdrop) backdrop.classList.toggle('open', this.isOpen);

    if (this.isOpen) this._syncUI();
  },

  close() {
    this.isOpen = false;
    const panel = document.getElementById('customize-panel');
    const backdrop = document.getElementById('customize-backdrop');
    if (panel) panel.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
  },

  _syncUI() {
    // Sync theme buttons
    const theme = ThemeManager.getTheme();
    document.querySelectorAll('[data-set-theme]').forEach(el => {
      el.classList.toggle('selected', el.dataset.setTheme === theme);
    });

    // Sync accent swatches
    const accent = ThemeManager.getAccent();
    document.querySelectorAll('.color-swatch[data-accent]').forEach(el => {
      el.classList.toggle('selected', el.dataset.accent === accent);
    });

    // Sync density
    const density = ThemeManager.getDensity();
    document.querySelectorAll('[data-set-density]').forEach(el => {
      el.classList.toggle('selected', el.dataset.setDensity === density);
    });

    // Sync bar color swatches
    const barColor = ThemeManager.getBarColor();
    this._syncSidebarSwatches(barColor);

    // Update bar color picker input value
    const barPicker = document.getElementById('sidebar-color-picker');
    if (barPicker) barPicker.value = barColor.startsWith('#') ? barColor : '#FFFFFF';
  },

  _syncSidebarSwatches(activeColor) {
    const normalizedActive = activeColor.toUpperCase();
    document.querySelectorAll('.sidebar-color-swatch').forEach(el => {
      const swatchColor = (el.dataset.sidebarColor || '').toUpperCase();
      el.classList.toggle('selected', swatchColor === normalizedActive);
    });
  }
};

// Initialize immediately (before DOMContentLoaded to prevent flash)
ThemeManager.init();
