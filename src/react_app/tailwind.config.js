/**
 * Tailwind CSS configuration (v4-compatible) for the React app.
 * Loaded explicitly from index.css so Vite and Tailwind scan the same sources.
 */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}', './index.html'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        purple: '#ab5ab7',
        purpledark: '#7b28a4',
        purplelight: '#c183e1',
      },
    },
  },
  plugins: [],
};
