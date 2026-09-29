const { createTransformer } = require("@swc/jest");

const transformer = createTransformer({
  jsc: {
    parser: {
      syntax: "ecmascript",
      jsx: true,
    },
    transform: {
      react: {
        runtime: "automatic",
      },
    },
  },
  module: {
    type: "commonjs",
  },
});

const normalizeSource = (sourceText, sourcePath) =>
  sourcePath.includes("/node_modules/react-router/")
    ? sourceText.replaceAll("import.meta.hot", "false")
    : sourceText;

module.exports = {
  process(sourceText, sourcePath, transformOptions) {
    return transformer.process(
      normalizeSource(sourceText, sourcePath),
      sourcePath,
      transformOptions
    );
  },
  getCacheKey(sourceText, sourcePath, transformOptions) {
    return transformer.getCacheKey(
      normalizeSource(sourceText, sourcePath),
      sourcePath,
      transformOptions
    );
  },
};
