/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        alba: {
          50: '#eef7ff',
          100: '#d9ecff',
          200: '#bcdfff',
          300: '#8ecbff',
          400: '#59adff',
          500: '#338bfb',
          600: '#1c6df0',
          700: '#1557dd',
          800: '#1847b3',
          900: '#1a408d',
        },
        gold: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        dark: {
          950: '#030712',
          900: '#0a0a0a',
          850: '#0f1115',
          800: '#15191e',
          700: '#1e2329',
          600: '#2a3038',
        }
      },
      boxShadow: {
        'gold': '0 0 20px rgba(245, 158, 11, 0.15)',
        'gold-lg': '0 0 40px rgba(245, 158, 11, 0.2)',
        'inner-gold': 'inset 0 1px 0 rgba(245, 158, 11, 0.15)',
      },
      fontFamily: {
        display: ['"EB Garamond"', '"Playfair Display"', 'Georgia', 'serif'],
        body: ['"EB Garamond"', '"Playfair Display"', 'Georgia', 'serif'],
        sans: ['"EB Garamond"', '"Playfair Display"', 'Georgia', 'serif'],
      }
    },
  },
  plugins: [],
}
