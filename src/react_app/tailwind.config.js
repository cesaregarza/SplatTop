module.exports = {
  purge: ['./src/**/*.{js,jsx,ts,tsx}', './public/index.html'],
  darkMode: 'class', // Enable dark mode
  theme: {
    extend: {
      colors: {
        purple: '#ab5ab7', // Add the custom purple color
        purpledark: '#7b28a4'
      },
    },
  },
  variants: {
    extend: {},
  },
  plugins: [],
};