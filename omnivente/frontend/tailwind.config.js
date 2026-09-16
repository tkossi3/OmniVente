/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Palette OmniVente — modifiez ces valeurs pour changer toute l'identite.
        ink: {
          900: '#0A111C',
          800: '#0F1826',
          700: '#162133',
          600: '#1D2B40',
          500: '#33465F',
        },
        paper: {
          50: '#FBFBFA',
          100: '#F3F4F2',
          200: '#E6E8E4',
          300: '#D3D6D0',
        },
        brand: {
          50: '#E8F7F3',
          100: '#C4EBE2',
          300: '#6BCFBB',
          500: '#0E9C8A',
          600: '#0B7E71',
          700: '#085E55',
        },
        saffron: {
          400: '#F5B942',
          500: '#EDA013',
          600: '#C77F05',
        },
        channel: {
          whatsapp: '#25D366',
          instagram: '#E1306C',
          messenger: '#0084FF',
          email: '#64748B',
        },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        card: '14px',
      },
      boxShadow: {
        lane: '0 1px 2px rgba(10, 17, 28, 0.06)',
      },
      keyframes: {
        rise: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        rise: 'rise 220ms ease-out',
      },
    },
  },
  plugins: [],
}
