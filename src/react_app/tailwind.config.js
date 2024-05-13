module.exports = {
  purge: ['./src/**/*.{js,jsx,ts,tsx}', './public/index.html'],
  darkMode: 'class', // Enable dark mode
  theme: {
    extend: {
      colors: {
        purple: '#ab5ab7',
        purpledark: '#7b28a4',
        purplelight: '#c183e1',
      },
    },
  },
  variants: {
    extend: {},
  },
  plugins: [],
};