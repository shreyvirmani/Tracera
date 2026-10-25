export const theme = {
  colors: {
    background: '#09090B',
    surface: '#111827',
    card: '#18181B',
    border: '#27272A',

    blue: '#3B82F6',
    purple: '#8B5CF6',
    green: '#22C55E',
    yellow: '#F59E0B',
    red: '#EF4444',

    text: {
      primary: '#FAFAFA',
      secondary: '#A1A1AA',
      muted: '#71717A',
    },

    primary: {
      DEFAULT: '#3B82F6',
      hover: '#2563EB',
      light: '#1E3A5F',
    },
    secondary: {
      DEFAULT: '#8B5CF6',
      hover: '#7C3AED',
      light: '#2E1A47',
    },
    success: {
      DEFAULT: '#22C55E',
      hover: '#16A34A',
      light: '#14532D',
    },
    warning: {
      DEFAULT: '#F59E0B',
      hover: '#D97706',
      light: '#78350F',
    },
    danger: {
      DEFAULT: '#EF4444',
      hover: '#DC2626',
      light: '#7F1D1D',
    },
  },

  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
    '3xl': '4rem',
  },

  typography: {
    fontFamily: {
      sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
      mono: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
      '4xl': '2.25rem',
      '5xl': '3rem',
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.75,
    },
  },

  borderRadius: {
    none: '0',
    sm: '0.25rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem',
    '2xl': '1rem',
    full: '9999px',
  },

  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
  },

  transitions: {
    fast: '150ms ease',
    normal: '200ms ease',
    slow: '300ms ease',
  },

  zIndex: {
    dropdown: 50,
    sticky: 100,
    modal: 200,
    popover: 300,
    tooltip: 400,
  },

  breakpoints: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },

  sidebar: {
    width: '280px',
    collapsedWidth: '72px',
  },
} as const;

export type Theme = typeof theme;