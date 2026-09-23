#!/usr/bin/env node
/**
 * Create an authenticated Playwright storage state from a test account.
 *
 * Secrets are read from environment variables only. They are never written to
 * workspace notes, JSON summaries, or reports.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadPlaywright } from "./playwright_runtime.mjs";

function parseArgs(argv) {
  const args = {
    config: "",
    headful: false,
    loginUrl: "",
    passwordEnv: "OSR_PASSWORD",
    passwordSelector: "",
    storageState: "",
    submitSelector: "",
    successSelector: "",
    successUrlContains: "",
    timeout: 15000,
    usernameEnv: "OSR_USERNAME",
    usernameSelector: "",
    workspace: "",
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else if (arg === "--config") {
      args.config = argv[++i];
    } else if (arg === "--headful") {
      args.headful = true;
    } else if (arg === "--login-url") {
      args.loginUrl = argv[++i];
    } else if (arg === "--username-env") {
      args.usernameEnv = argv[++i];
    } else if (arg === "--password-env") {
      args.passwordEnv = argv[++i];
    } else if (arg === "--username-selector") {
      args.usernameSelector = argv[++i];
    } else if (arg === "--password-selector") {
      args.passwordSelector = argv[++i];
    } else if (arg === "--submit-selector") {
      args.submitSelector = argv[++i];
    } else if (arg === "--success-url-contains") {
      args.successUrlContains = argv[++i];
    } else if (arg === "--success-selector") {
      args.successSelector = argv[++i];
    } else if (arg === "--storage-state") {
      args.storageState = argv[++i];
    } else if (arg === "--timeout") {
      args.timeout = Number(argv[++i]);
    } else if (arg === "--workspace") {
      args.workspace = argv[++i];
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function usage() {
  const script = path.basename(fileURLToPath(import.meta.url));
  return `Usage: node ${script} --workspace <audit-workspace> --login-url <url> --username-selector <selector> --password-selector <selector> --submit-selector <selector> [--success-url-contains /dashboard | --success-selector <selector>]`;
}

async function readConfig(configPath) {
  if (!configPath) {
    return {};
  }
  return JSON.parse(await fs.readFile(path.resolve(configPath), "utf8"));
}

function mergeConfig(args, config) {
  return {
    ...args,
    ...Object.fromEntries(Object.entries(config).filter(([, value]) => value !== undefined && value !== "")),
  };
}

async function updateManifest(workspace) {
  const manifestPath = path.join(workspace, "state", "manifest.json");
  try {
    const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
    manifest.stages = manifest.stages || {};
    manifest.stages.auth_session = "completed";
    await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  } catch {
    // Workspace may not have a manifest; login can still create storage state.
  }
}

async function main() {
  const rawArgs = parseArgs(process.argv.slice(2));
  if (rawArgs.help) {
    console.log(usage());
    return;
  }
  const config = await readConfig(rawArgs.config);
  const args = mergeConfig(rawArgs, config);
  if (!args.workspace || !args.loginUrl || !args.usernameSelector || !args.passwordSelector || !args.submitSelector) {
    throw new Error(usage());
  }

  const username = process.env[args.usernameEnv];
  const password = process.env[args.passwordEnv];
  if (!username) {
    throw new Error(`Missing username environment variable: ${args.usernameEnv}`);
  }
  if (!password) {
    throw new Error(`Missing password environment variable: ${args.passwordEnv}`);
  }

  const { chromium } = loadPlaywright();
  const workspace = path.resolve(args.workspace);
  const stateDir = path.join(workspace, "state");
  const evidenceDir = path.join(workspace, "evidence");
  await fs.mkdir(stateDir, { recursive: true });
  await fs.mkdir(evidenceDir, { recursive: true });
  const storageState = path.resolve(args.storageState || path.join(stateDir, "authenticated-storage-state.json"));

  const browser = await chromium.launch({ headless: !args.headful });
  const context = await browser.newContext();
  const page = await context.newPage();
  const events = [];

  page.on("request", (request) => {
    events.push({ type: "request", method: request.method(), url: request.url() });
  });

  await page.goto(args.loginUrl, { waitUntil: "domcontentloaded", timeout: args.timeout });
  await page.fill(args.usernameSelector, username, { timeout: args.timeout });
  await page.fill(args.passwordSelector, password, { timeout: args.timeout });
  await Promise.all([
    page.waitForLoadState("domcontentloaded", { timeout: args.timeout }).catch(() => undefined),
    page.click(args.submitSelector, { timeout: args.timeout }),
  ]);

  let success = false;
  let successReason = "";
  if (args.successUrlContains) {
    await page.waitForURL((url) => url.href.includes(args.successUrlContains), { timeout: args.timeout });
    success = true;
    successReason = `url_contains:${args.successUrlContains}`;
  } else if (args.successSelector) {
    await page.waitForSelector(args.successSelector, { timeout: args.timeout });
    success = true;
    successReason = `selector:${args.successSelector}`;
  } else {
    success = true;
    successReason = "submitted_without_explicit_success_condition";
  }

  await context.storageState({ path: storageState });
  const finalUrl = page.url();
  await context.close();
  await browser.close();

  const summary = {
    login_url: args.loginUrl,
    final_url: finalUrl,
    success,
    success_reason: successReason,
    username_env: args.usernameEnv,
    password_env: args.passwordEnv,
    storage_state: storageState,
    request_count: events.length,
    note: "Secrets were read from environment variables and were not recorded.",
  };
  await fs.writeFile(path.join(stateDir, "auth_session.json"), `${JSON.stringify(summary, null, 2)}\n`);
  await fs.writeFile(
    path.join(evidenceDir, "auth_session.md"),
    [
      "# Auth Session",
      "",
      `- Login URL: ${summary.login_url}`,
      `- Final URL: ${summary.final_url}`,
      `- Success: ${summary.success}`,
      `- Success reason: ${summary.success_reason}`,
      `- Username env: ${summary.username_env}`,
      `- Password env: ${summary.password_env}`,
      `- Storage state: ${summary.storage_state}`,
      "",
      "Secrets were not recorded.",
      "",
    ].join("\n"),
  );
  await updateManifest(workspace);
  console.log(JSON.stringify({ storageState, success, finalUrl }));
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
