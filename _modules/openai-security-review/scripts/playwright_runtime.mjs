import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

export function loadPlaywright() {
  const require = createRequire(import.meta.url);
  try {
    return require("playwright");
  } catch (error) {
    if (error && error.code === "MODULE_NOT_FOUND") {
      const skillDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
      const message = [
        "Playwright is not installed for openai-security-review.",
        "",
        "Install the skill runtime dependencies:",
        `  cd ${skillDir}`,
        "  npm install",
        "",
        "Then retry this command. If Chromium is missing, run:",
        `  cd ${skillDir}`,
        "  npx playwright install chromium",
      ].join("\n");
      throw new Error(message);
    }
    throw error;
  }
}
