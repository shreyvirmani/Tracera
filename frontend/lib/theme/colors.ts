export const colors = {
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

  // Semantic colors
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
} as const;

export type ColorKey = keyof typeof colors;