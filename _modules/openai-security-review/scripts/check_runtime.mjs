#!/usr/bin/env node
import { loadPlaywright } from "./playwright_runtime.mjs";

try {
  const { chromium } = loadPlaywright();
  const executablePath = chromium.executablePath();
  console.log(JSON.stringify({ ok: true, playwright: true, chromium: executablePath }));
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
