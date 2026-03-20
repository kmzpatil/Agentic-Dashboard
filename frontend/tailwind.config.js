/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // shadcn-compatible CSS variable colors (used by userJourney)
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border: 'hsl(var(--border))',
        ring: 'hsl(var(--ring))',
        // Custom userJourney brand colors
        brand: {
          primary: 'hsl(var(--brand-primary))',
          red: 'hsl(var(--brand-red))',
          'blue-light': 'hsl(var(--brand-blue-light))',
        },
        // Custom frammer text scale
        frammer: {
          'text-pure': '#ffffff',
          'text-primary': 'rgba(255,255,255,0.96)',
          'text-secondary': 'rgba(255,255,255,0.80)',
          'text-muted': 'rgba(255,255,255,0.48)',
          'text-faint': 'rgba(255,255,255,0.24)',
          'text-faintest': 'rgba(255,255,255,0.16)',
        },
      },
    },
  },
  plugins: [],
}

