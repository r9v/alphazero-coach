/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      screens: {
        'lg': '768px',
        'xl': '992px',
      },
      colors: {
        'board-blue': '#1e3a5f',
        'board-slot': '#0f1b2d',
        'piece-red': '#ef4444',
        'piece-yellow': '#eab308',
        surface: '#111827',
        'surface-alt': '#1f2937',
        border: '#374151',
        'text-primary': '#f9fafb',
        'text-secondary': '#9ca3af',
        accent: '#3b82f6',
      },
    },
  },
  plugins: [],
}
