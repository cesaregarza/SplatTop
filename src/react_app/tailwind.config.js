/**
 * Tailwind CSS configuration (v4-compatible) for the React app.
 * Using the conventional filename so CRA/PostCSS auto-detects it
 * without relying on the @config directive.
 */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}', './public/index.html'],
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

