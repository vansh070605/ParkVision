/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: '#0f172a',
          blue: '#1e293b',
          light: '#f8fafc',
          rose: '#f43f5e',
          roseDark: '#e11d48',
        },
        accent: {
          green: '#10b981',
          red: '#ef4444',
          blue: '#3b82f6',
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 20px 40px -15px rgba(0,0,0,0.05)',
      }
    },
  },
  plugins: [],
}
// Trigger rebuild
