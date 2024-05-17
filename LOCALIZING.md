## Contributing to Localization

We welcome contributions to help translate SplatTop into various languages! Below are the JSON files that need to be updated for localization (the below are links to the English versions of the files, which you can use as a reference for translation):

- [`faq.json`](https://github.com/cesaregarza/SplatTop/blob/main/src/react_app/public/locales/en/faq.json)
- [`game.json`](https://github.com/cesaregarza/SplatTop/blob/main/src/react_app/public/locales/en/game.json)
- [`main_page.json`](https://github.com/cesaregarza/SplatTop/blob/main/src/react_app/public/locales/en/main_page.json)
- [`navigation.json`](https://github.com/cesaregarza/SplatTop/blob/main/src/react_app/public/locales/en/navigation.json)
- [`player.json`](https://github.com/cesaregarza/SplatTop/blob/main/src/react_app/public/locales/en/player.json)

### Guidelines for Localization

1. **JSON Structure**: Ensure the structure of the JSON files remains unchanged. Only translate the text values.
2. **Formatted Text**: Text enclosed in `%` symbols, such as `%MODE%`, should remain unchanged. These placeholders will be programmatically replaced with appropriate values.
3. **Consistency**: Maintain consistency in terminology and style across all translations.
4. **Top 500**: If it makes sense in the target language, please translate `Top 500` to the equivalent term in the target language. If there is no compact terminology for `Top 500` in the target language that sounds better, you can keep it as `Top 500`. Use your best judgment.
5. **FAQ**: The FAQ section contains formatting in HTML. This might be challenging to translate if you don't have experience with HTML. If this is the case, feel free to use Markdown formatting or some other format that you are comfortable with. We will do the necessary formatting on our end and show you the final result for approval.

### Steps to Contribute

1. **Fork the Repository**: Start by forking the SplatTop repository to your GitHub account.
2. **Clone the Repository**: Clone the forked repository to your local machine.
   ```sh
   git clone https://github.com/your-username/SplatTop.git
   cd SplatTop
   ```
3. **Create a New Branch**: Create a new branch for your localization work.
   ```sh
   git checkout -b add-localization-language-code
   ```
4. **Update JSON Files**: Translate the text values in the relevant JSON files located in `src/react_app/public/locales/`.
5. **Commit Your Changes**: Commit your changes with a descriptive message.
   ```sh
   git add .
   git commit -m "Add localization for language-code"
   ```
6. **Push to GitHub**: Push your changes to your forked repository.
   ```sh
   git push origin add-localization-language-code
   ```
7. **Create a Pull Request**: Open a pull request to the main repository for review.

### Need Help?

If you are not familiar with Git or need assistance, feel free to reach out to us on Twitter [@JoyTheDataNerd](https://twitter.com/JoyTheDataNerd) or on Discord at `pyproject.toml`. We are here to help!

Thank you for contributing to SplatTop's localization efforts!
