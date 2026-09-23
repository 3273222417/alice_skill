#!/usr/bin/env node
/**
 * Unified scheduler for the openai-security-review workflow.
 */

import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import readline from "node:readline/promises";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = path.resolve(SCRIPT_DIR, "..");

function parseArgs(argv) {
  const args = { config: "", confirmActive: false, dryRun: false, only: [], skip: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else if (arg === "--config" || arg === "-c") {
      args.config = argv[++i];
    } else if (arg === "--dry-run") {
      args.dryRun = true;
    } else if (arg === "--confirm-active") {
      args.confirmActive = true;
    } else if (arg === "--only") {
      args.only = argv[++i].split(",").map((item) => item.trim()).filter(Boolean);
    } else if (arg === "--skip") {
      args.skip = argv[++i].split(",").map((item) => item.trim()).filter(Boolean);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function usage() {
  return [
    "Usage: node scripts/osr.mjs --config <osr.config.json> [--only workspace,inventory,backend,hypotheses,auth,crawl,source-map,access-matrix,validate,active,report] [--skip auth,crawl,source-map,access-matrix,backend,active] [--confirm-active] [--dry-run]",
    "",
    "Default steps: workspace, inventory, backend(if enabled), hypotheses, auth(if enabled), validate, crawl(if enabled), source-map, access-matrix(if enabled), active-plan/probe(if enabled), report",
  ].join("\n");
}

async function loadConfig(configPath) {
  const resolved = path.resolve(configPath);
  const raw = await fs.readFile(resolved, "utf8");
  const config = JSON.parse(raw);
  return { config, configDir: path.dirname(resolved), configPath: resolved };
}

function resolvePath(configDir, value) {
  if (!value) {
    return "";
  }
  if (path.isAbsolute(value)) {
    return value;
  }
  return path.resolve(configDir, value);
}

function workspaceFromConfig(config, configDir) {
  const explicit = config.workspace?.path || config.output?.workspace;
  if (explicit) {
    return resolvePath(configDir, explicit);
  }
  return path.resolve("/tmp", `openai-security-review-${path.basename(config.target.repo || "repo")}`);
}

function targetUrl(config) {
  return config.target?.url || config.targetUrl || "";
}

function repoPath(config, configDir) {
  const repo = config.target?.repo || config.repo;
  if (!repo) {
    throw new Error("Config must include target.repo");
  }
  return resolvePath(configDir, repo);
}

function stepEnabled(step, args, defaults) {
  const activeAliases = new Set(["active", "active-plan", "active-probe"]);
  const backendAliases = new Set([
    "backend",
    "backend-fingerprint",
    "server-route-map",
    "authz-map",
    "dataflow-risk-map",
    "validation-coverage",
    "server-checks",
    "api-spec-map",
  ]);
  const backendAllAliases = new Set([...backendAliases, "backend-probe"]);
  if (args.only.length > 0) {
    if (args.only.includes("active") && activeAliases.has(step)) {
      return true;
    }
    if (args.only.includes("backend") && backendAliases.has(step)) {
      return true;
    }
    return args.only.includes(step);
  }
  if (args.skip.includes(step) || (activeAliases.has(step) && args.skip.includes("active"))) {
    return false;
  }
  if (backendAllAliases.has(step) && args.skip.includes("backend")) {
    return false;
  }
  return defaults.includes(step);
}

function listValue(value, fallback = "") {
  if (Array.isArray(value)) {
    return value.join(",");
  }
  return value || fallback;
}

function backendStepEnabled(config, key) {
  const backend = config.backend || {};
  return Boolean(backend.enabled) && backend[key] !== false;
}

function isActiveStep(step) {
  return step.gatedByActivePrompt === true;
}

function parseActiveChoice(answer) {
  const normalized = answer.trim().toLowerCase();
  if (normalized === "" || ["2", "not active", "inactive", "skip", "no", "n"].includes(normalized)) {
    return false;
  }
  if (["1", "active", "yes", "y"].includes(normalized)) {
    return true;
  }
  return null;
}

async function confirmActiveIfNeeded(config, args, runtimeState, step) {
  if (!isActiveStep(step)) {
    return true;
  }
  if (runtimeState.activeDecision !== null) {
    return runtimeState.activeDecision;
  }
  if (args.confirmActive) {
    runtimeState.activeDecision = true;
    return true;
  }
  if (!process.stdin.isTTY) {
    throw new Error("Refusing active probes without --confirm-active in non-interactive mode.");
  }
  const active = config.active || {};
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    console.log("\n[osr] Static/passive review stages are complete.");
    console.log("[osr] Active probes send low-risk GET/OPTIONS requests and require explicit authorization.");
    console.log(`Target: ${targetUrl(config)}`);
    console.log(`Classes: ${listValue(active.probeClasses || active.classes, "cors,redirect,xss,error,exposure")}`);
    console.log("[osr] Choose an option:");
    console.log("[osr]   1) ACTIVE");
    console.log("[osr]   2) NOT ACTIVE (default)");
    while (runtimeState.activeDecision === null) {
      const answer = await rl.question("Select 1 or 2 [2]: ");
      const decision = parseActiveChoice(answer);
      if (decision === null) {
        console.log("[osr] Please choose 1 (ACTIVE) or 2 (NOT ACTIVE).");
        continue;
      }
      runtimeState.activeDecision = decision;
    }
    if (!runtimeState.activeDecision) {
      console.log("[osr] Active probing skipped. Continuing to the remaining report steps.");
    }
    return runtimeState.activeDecision;
  } finally {
    rl.close();
  }
}

function runCommand(command, commandArgs, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, commandArgs, {
      cwd: options.cwd || SKILL_DIR,
      env: { ...process.env, ...(options.env || {}) },
      stdio: "inherit",
    });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`${command} ${commandArgs.join(" ")} exited with ${code}`));
      }
    });
  });
}

function commandPlan(config, configDir, args) {
  const repo = repoPath(config, configDir);
  const url = targetUrl(config);
  const workspace = workspaceFromConfig(config, configDir);
  const defaults = ["workspace", "inventory", "hypotheses", "validate", "report"];
  const backend = config.backend || {};
  if (backend.enabled) {
    const beforeHypotheses = [];
    if (backendStepEnabled(config, "fingerprint")) beforeHypotheses.push("backend-fingerprint");
    if (backendStepEnabled(config, "routeMap")) beforeHypotheses.push("server-route-map");
    if (backendStepEnabled(config, "authzMap")) beforeHypotheses.push("authz-map");
    if (backendStepEnabled(config, "dataflowRiskMap")) beforeHypotheses.push("dataflow-risk-map");
    if (backendStepEnabled(config, "validationCoverage")) beforeHypotheses.push("validation-coverage");
    if (backendStepEnabled(config, "serverChecks")) beforeHypotheses.push("server-checks");
    defaults.splice(defaults.indexOf("hypotheses"), 0, ...beforeHypotheses);
  }
  if (config.auth?.enabled) {
    defaults.splice(defaults.indexOf("validate"), 0, "auth");
  }
  if (config.crawl?.enabled !== false && url) {
    defaults.splice(defaults.indexOf("report"), 0, "crawl");
  }
  if (config.sourceMap?.enabled !== false) {
    defaults.splice(defaults.indexOf("report"), 0, "source-map");
  }
  if (backend.enabled && backend.apiSpecMap !== false) {
    defaults.splice(defaults.indexOf("report"), 0, "api-spec-map");
  }
  if (backend.enabled && backend.runtimeValidation && url) {
    defaults.splice(defaults.indexOf("report"), 0, "backend-probe");
  }
  if (config.accessMatrix?.enabled && url) {
    defaults.splice(defaults.indexOf("report"), 0, "access-matrix");
  }
  if (config.active?.enabled && url) {
    const reportIndex = defaults.indexOf("report");
    defaults.splice(reportIndex, 0, "active-plan");
    if (config.active?.executeSafeProbes) {
      defaults.splice(reportIndex + 1, 0, "active-probe");
    }
  }

  const steps = [];
  if (stepEnabled("workspace", args, defaults)) {
    steps.push({
      name: "workspace",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "create_audit_workspace.py"), "--repo", repo, "--target-url", url, "--out", workspace],
    });
  }
  if (stepEnabled("inventory", args, defaults)) {
    steps.push({
      name: "inventory",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "inventory.py"), "--repo", repo, "--workspace", workspace],
    });
  }
  if (stepEnabled("backend-fingerprint", args, defaults)) {
    steps.push({
      name: "backend-fingerprint",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "backend_fingerprint.py"), "--repo", repo, "--workspace", workspace, "--hints", listValue(backend.frameworkHints)],
    });
  }
  if (stepEnabled("server-route-map", args, defaults)) {
    steps.push({
      name: "server-route-map",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "server_route_map.py"), "--repo", repo, "--workspace", workspace],
    });
  }
  if (stepEnabled("authz-map", args, defaults)) {
    steps.push({
      name: "authz-map",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "authz_map.py"), "--repo", repo, "--workspace", workspace],
    });
  }
  if (stepEnabled("dataflow-risk-map", args, defaults)) {
    steps.push({
      name: "dataflow-risk-map",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "dataflow_risk_map.py"), "--repo", repo, "--workspace", workspace],
    });
  }
  if (stepEnabled("validation-coverage", args, defaults)) {
    steps.push({
      name: "validation-coverage",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "validation_coverage.py"), "--repo", repo, "--workspace", workspace],
    });
  }
  if (stepEnabled("server-checks", args, defaults)) {
    steps.push({
      name: "server-checks",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "server_security_checks.py"), "--repo", repo, "--workspace", workspace],
    });
  }
  if (stepEnabled("hypotheses", args, defaults)) {
    steps.push({
      name: "hypotheses",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "hypothesize.py"), "--workspace", workspace],
    });
  }
  if (stepEnabled("auth", args, defaults)) {
    if (!config.auth?.enabled) {
      throw new Error("Auth step requested but auth.enabled is not true in config.");
    }
    const auth = config.auth;
    const authArgs = [
      path.join(SCRIPT_DIR, "auth_login.mjs"),
      "--workspace", workspace,
      "--login-url", auth.loginUrl,
      "--username-env", auth.usernameEnv || "OSR_USERNAME",
      "--password-env", auth.passwordEnv || "OSR_PASSWORD",
      "--username-selector", auth.usernameSelector,
      "--password-selector", auth.passwordSelector,
      "--submit-selector", auth.submitSelector,
    ];
    if (auth.successUrlContains) {
      authArgs.push("--success-url-contains", auth.successUrlContains);
    }
    if (auth.successSelector) {
      authArgs.push("--success-selector", auth.successSelector);
    }
    if (auth.headful) {
      authArgs.push("--headful");
    }
    steps.push({ name: "auth", command: "node", args: authArgs });
  }
  if (stepEnabled("validate", args, defaults) && url) {
    steps.push({
      name: "validate",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "safe_validate.py"), "--target-url", url, "--workspace", workspace, "--timeout", String(config.validation?.timeout || 10)],
    });
  }
  if (stepEnabled("crawl", args, defaults) && url) {
    const crawlArgs = [
      path.join(SCRIPT_DIR, "passive_crawl.mjs"),
      "--url", url,
      "--workspace", workspace,
      "--max-pages", String(config.crawl?.maxPages || 20),
      "--timeout", String(config.crawl?.timeout || 10000),
    ];
    const storageState = config.crawl?.storageState || (config.auth?.enabled ? path.join(workspace, "state", "authenticated-storage-state.json") : "");
    if (storageState) {
      crawlArgs.push("--storage-state", resolvePath(configDir, storageState));
    }
    steps.push({ name: "crawl", command: "node", args: crawlArgs });
  }
  if (stepEnabled("source-map", args, defaults)) {
    steps.push({
      name: "source-map",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "source_api_map.py"), "--repo", repo, "--workspace", workspace],
    });
  }
  if (stepEnabled("api-spec-map", args, defaults)) {
    steps.push({
      name: "api-spec-map",
      command: "python3",
      args: [path.join(SCRIPT_DIR, "api_spec_map.py"), "--repo", repo, "--workspace", workspace, "--spec-paths", listValue(backend.apiSpecPaths)],
    });
  }
  if (stepEnabled("backend-probe", args, defaults) && url) {
    if (!backend.runtimeValidation) {
      throw new Error("Backend runtime validation requires backend.runtimeValidation=true in config.");
    }
    const probeArgs = [
      path.join(SCRIPT_DIR, "backend_probe.mjs"),
      "--url", url,
      "--workspace", workspace,
      "--config", args.configPath || path.resolve(configDir, args.config),
      "--max-endpoints", String(backend.runtimeMaxEndpoints || backend.maxEndpoints || 50),
      "--timeout", String(backend.runtimeTimeout || backend.timeout || 10000),
    ];
    const storageState = backend.storageState || config.crawl?.storageState || (config.auth?.enabled ? path.join(workspace, "state", "authenticated-storage-state.json") : "");
    if (storageState) {
      probeArgs.push("--storage-state", resolvePath(configDir, storageState));
    }
    steps.push({ name: "backend-probe", command: "node", args: probeArgs });
  }
  if (stepEnabled("access-matrix", args, defaults) && url) {
    const access = config.accessMatrix || {};
    if (!access.enabled) {
      throw new Error("Access matrix step requested but accessMatrix.enabled is not true in config.");
    }
    steps.push({
      name: "access-matrix",
      command: "node",
      args: [
        path.join(SCRIPT_DIR, "role_matrix.mjs"),
        "--config", args.configPath || path.resolve(configDir, args.config),
        "--url", url,
        "--workspace", workspace,
        "--max-endpoints", String(access.maxEndpoints || 100),
        "--timeout", String(access.timeout || 10000),
      ],
    });
  }
  if (stepEnabled("active-plan", args, defaults) && url) {
    const active = config.active || {};
    if (!active.enabled || !active.authorized) {
      throw new Error("Active validation requires active.enabled=true and active.authorized=true in config.");
    }
    steps.push({
      name: "active-plan",
      command: "python3",
      args: [
        path.join(SCRIPT_DIR, "active_validate.py"),
        "--workspace", workspace,
        "--target-url", url,
        "--classes", listValue(active.planClasses, "auth,authz,xss,redirect"),
        "--i-am-authorized",
      ],
      gatedByActivePrompt: true,
    });
  }
  if (stepEnabled("active-probe", args, defaults) && url) {
    const active = config.active || {};
    if (!active.enabled || !active.authorized || !active.executeSafeProbes) {
      throw new Error("Active probes require active.enabled=true, active.authorized=true, and active.executeSafeProbes=true in config.");
    }
    const probeArgs = [
      path.join(SCRIPT_DIR, "active_probe.py"),
      "--workspace", workspace,
      "--target-url", url,
      "--classes", listValue(active.probeClasses || active.classes, "cors,redirect,xss,error,exposure"),
      "--timeout", String(active.timeout || 10),
      "--i-am-authorized",
      "--confirm-active",
    ];
    if (active.allowRemote) {
      probeArgs.push("--allow-remote");
    }
    steps.push({ name: "active-probe", command: "python3", args: probeArgs, gatedByActivePrompt: true });
  }
  if (stepEnabled("report", args, defaults)) {
    const reportArgs = [path.join(SCRIPT_DIR, "generate_report.py"), "--workspace", workspace];
    if (config.report?.out) {
      reportArgs.push("--out", resolvePath(configDir, config.report.out));
    }
    steps.push({ name: "report", command: "python3", args: reportArgs });
  }
  return { steps, workspace };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(usage());
    return;
  }
  if (!args.config) {
    throw new Error(usage());
  }
  const { config, configDir, configPath } = await loadConfig(args.config);
  args.configPath = configPath;
  const { steps, workspace } = commandPlan(config, configDir, args);
  const runtimeState = { activeDecision: null };
  console.log(JSON.stringify({ config: configPath, workspace, steps: steps.map((step) => step.name) }, null, 2));
  for (const step of steps) {
    console.log(`\n[osr] ${step.name}`);
    console.log(`${step.command} ${step.args.map((item) => JSON.stringify(item)).join(" ")}`);
    if (!args.dryRun) {
      const shouldRun = await confirmActiveIfNeeded(config, args, runtimeState, step);
      if (!shouldRun) {
        console.log(`[osr] Skipping ${step.name}.`);
        continue;
      }
      await runCommand(step.command, step.args);
    }
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
