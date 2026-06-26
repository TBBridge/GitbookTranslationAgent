import { globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = [
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "coverage/**",
    "next-env.d.ts",
    "node_modules/**",
    "playwright-report/**",
    "test-results/**"
  ])
];

export default eslintConfig;
