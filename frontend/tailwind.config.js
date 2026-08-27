/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#0A0D11',
          950: '#07090C',
          900: '#0A0D11',
          800: '#12161B',
          700: '#171C22',
          600: '#1D2329',
          500: '#232931',
          400: '#2E353E',
        },
        fog: {
          DEFAULT: '#8B95A1',
          soft: '#5C6673',
          bright: '#E8ECEF',
        },
        signal: {
          allow: '#34D399',
          'allow-dim': '#1B4332',
          hold: '#F5B942',
          'hold-dim': '#4A3A16',
          block: '#F0596B',
          'block-dim': '#4A1B24',
        },
        steel: {
          DEFAULT: '#5B8DEF',
          bright: '#7FA4F2',
          dim: '#1E2A44',
        },
      },
      fontFamily: {
        display: ['var(--font-display)', 'system-ui', 'sans-serif'],
        body: ['var(--font-body)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
      },
      backgroundImage: {
        'grid-fade': 'linear-gradient(to bottom, rgba(232,236,239,0.04) 1px, transparent 1px), linear-gradient(to right, rgba(232,236,239,0.04) 1px, transparent 1px)',
      },
      keyframes: {
        pulseNode: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.35 },
        },
        rise: {
          '0%': { opacity: 0, transform: 'translateY(6px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
      },
      animation: {
        pulseNode: 'pulseNode 1.1s ease-in-out infinite',
        rise: 'rise 0.25s ease-out',
      },
    },
  },
  plugins: [],
};
