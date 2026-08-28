#!/usr/bin/env node
import fs from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const CHATGPT_HOME = "https://chatgpt.com/";
const BUILDER_URL = "https://chatgpt.com/gpts/editor";
const GPT_URL_PREFIX = "https://chatgpt.com/g/";
const require = createRequire(import.meta.url);

// A saved GPT exposes a chat URL like https://chatgpt.com/g/g-XXXX-name.
// This is the single source of truth for "the GPT was saved", used by both the
// configure capture loop and the smoke target resolver.
function isSavedGptUrl(url) {
  return typeof url === "string" && url.startsWith(GPT_URL_PREFIX);
}

function parseArgs(argv) {
  const result = { command: argv[2], mode: "ui", visibility: "private" };
  for (let i = 3; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const key = arg.slice(2).replaceAll("-", "_");
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      result[key] = true;
    } else {
      result[key] = next;
      i += 1;
    }
  }
  return result;
}

async function readJson(file) {
  return JSON.parse(await fs.readFile(file, "utf8"));
}

async function writeJsonPrivate(file, value) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  if (process.platform !== "win32") {
    await fs.chmod(file, 0o600);
  }
}

function actionBase(config) {
  return String(config.public_base_url || "").replace(/\/+$/, "");
}

function builderPayload(config) {
  const base = actionBase(config);
  return {
    name: "Local Coding Bridge",
    description: "Access and edit one authorized local workspace through a private bearer-protected Action bridge.",
    instructions: [
      "You are my local coding assistant for the workspace exposed through Actions.",
      "Use getWorkspaceStatus only when I ask about the current project, when the active workspace is ambiguous, before switching projects, or when a workspace-related action fails.",
      "When I ask to view or switch projects, call getWorkspaceStatus and then use switchWorkspace only with an authorized workspace name it returns.",
      "At the start of real project work, check whether AGENTS.md or AGENTS.override.md applies at the workspace root, and only look for deeper instruction files when the task moves into a deeper subdirectory.",
      "Use listFiles, readFile, readFiles, searchText, writeFile, applyPatch, execCommand, and pollCommand for project work.",
      "Prefer dedicated file and search tools over equivalent shell commands. Start shallow, read high-signal files, and keep changes scoped.",
      "If execCommand returns a running command session, continue with pollCommand instead of restarting the same command.",
      "When I ask for raw logs, preserve raw stdout and stderr instead of replacing them with a summary.",
      "Do not run destructive commands unless I explicitly ask for that exact action in the current chat.",
    ].join(" "),
    schemaUrl: `${base}/openapi.json`,
    privacyUrl: `${base}/privacy`,
  };
}

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === "object") {
    const result = {};
    for (const [key, item] of Object.entries(value)) {
      const lowered = key.toLowerCase();
      if (/(authorization|cookie|token|api[_-]?key|password|secret)/.test(lowered)) {
        result[key] = "[REDACTED]";
      } else {
        result[key] = redact(item);
      }
    }
    return result;
  }
  if (typeof value !== "string") return value;
  let redacted = value.replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [REDACTED]");
  redacted = redacted.replace(/(session|token|api[_-]?key|password|secret)=([^;&\s]+)/gi, "$1=[REDACTED]");
  try {
    const parsed = JSON.parse(redacted);
    redacted = JSON.stringify(redact(parsed));
  } catch {
    // Keep non-JSON strings as text.
  }
  return redacted;
}

function shouldCapture(url) {
  return /chatgpt\.com/.test(url) && /(backend|gizmo|gpts|actions|aip|conversation|share)/i.test(url);
}

function replayHeaders(headers) {
  const result = {};
  for (const [key, value] of Object.entries(headers || {})) {
    const lowered = key.toLowerCase();
    if (["authorization", "cookie", "set-cookie", "content-length", "host"].includes(lowered)) continue;
    if (String(value).includes("[REDACTED]")) continue;
    result[key] = value;
  }
  return result;
}

function hydrateSecretPlaceholders(value, config) {
  if (Array.isArray(value)) return value.map(item => hydrateSecretPlaceholders(item, config));
  if (value && typeof value === "object") {
    const result = {};
    for (const [key, item] of Object.entries(value)) {
      const lowered = key.toLowerCase();
      if (typeof item === "string" && item === "[REDACTED]" && /(api[_-]?key|token|secret)/.test(lowered)) {
        result[key] = config.token;
      } else {
        result[key] = hydrateSecretPlaceholders(item, config);
      }
    }
    return result;
  }
  return value;
}

function replayBody(postData, config) {
  if (!postData) return undefined;
  try {
    return hydrateSecretPlaceholders(JSON.parse(postData), config);
  } catch {
    return String(postData).replaceAll("[REDACTED]", "");
  }
}

function replayCandidate(routeMap) {
  const captures = Array.isArray(routeMap.captures) ? routeMap.captures : [];
  const requests = captures.filter(item => item.kind === "request" && /^(POST|PUT|PATCH)$/i.test(item.method || ""));
  const preferred = requests.find(item => /gizmo|gpts|actions/i.test(item.url || "") && /Local Coding Bridge|openapi|schema|privacy|api_key|auth/i.test(String(item.postData || "")));
  return preferred || requests.find(item => /gizmo|gpts|actions/i.test(item.url || "")) || null;
}

function startSniffer(context, captures) {
  context.on("request", request => {
    const url = request.url();
    if (!shouldCapture(url)) return;
    captures.push({
      kind: "request",
      at: new Date().toISOString(),
      method: request.method(),
      url,
      headers: redact(request.headers()),
      postData: redact(request.postData() || ""),
    });
  });
  context.on("response", async response => {
    const url = response.url();
    if (!shouldCapture(url)) return;
    const item = {
      kind: "response",
      at: new Date().toISOString(),
      status: response.status(),
      url,
      headers: redact(response.headers()),
      preview: "",
    };
    try {
      const contentType = response.headers()["content-type"] || "";
      if (/json|text/.test(contentType)) {
        item.preview = redact((await response.text()).slice(0, 4000));
      }
    } catch {
      item.preview = "[unavailable]";
    }
    captures.push(item);
  });
}

async function launch(profile) {
  await fs.mkdir(profile, { recursive: true });
  const { chromium } = await loadPlaywright();
  return chromium.launchPersistentContext(profile, {
    headless: false,
    viewport: { width: 1440, height: 1000 },
  });
}

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch (firstError) {
    for (const binDir of String(process.env.PATH || "").split(path.delimiter)) {
      if (!binDir.endsWith(path.join("node_modules", ".bin"))) continue;
      const nodeModules = path.dirname(binDir);
      try {
        const resolved = require.resolve("playwright", { paths: [nodeModules] });
        return await import(pathToFileURL(resolved).href);
      } catch {
        // Try the next PATH entry.
      }
    }
    throw firstError;
  }
}

async function detectBuilder(page) {
  await page.goto(BUILDER_URL, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  const url = page.url();
  const bodyText = await page.locator("body").innerText({ timeout: 10000 }).catch(() => "");
  const loggedIn = !/login|auth\/login|log in|sign up/i.test(url + "\n" + bodyText);
  const hasEditor = /gpts\/editor|builder|configure|配置|添加操作|actions?/i.test(url + "\n" + bodyText);
  const hasActions = /actions?|操作|schema|openapi|authentication|鉴权|api key/i.test(bodyText);
  return { loggedIn, hasEditor, hasActions, url };
}

async function fillFirst(page, labels, value) {
  for (const label of labels) {
    const locator = page.getByLabel(label).first();
    if (await locator.count().catch(() => 0)) {
      await locator.fill(value).catch(async () => {
        await locator.click();
        await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
        await page.keyboard.type(value);
      });
      return true;
    }
  }
  return false;
}

async function configureUi(page, config) {
  const payload = builderPayload(config);
  await page.goto(BUILDER_URL, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});

  // Prefill only the plain text fields. Adding the Action, importing the schema,
  // pasting the bearer token, and saving are intentionally left to the human:
  // the Builder UI for those steps has no stable selectors, so we do not pretend
  // to automate them.
  const prefilled = {
    name: await fillFirst(page, ["Name", "名称", "GPT name"], payload.name),
    description: await fillFirst(page, ["Description", "描述"], payload.description),
    instructions: await fillFirst(page, ["Instructions", "指令"], payload.instructions),
  };

  const pageText = await page.locator("body").innerText({ timeout: 10000 }).catch(() => "");
  return {
    prefilled,
    found_actions_text: /actions?|操作|schema|openapi|authentication|鉴权|api key/i.test(pageText),
    schema_url: payload.schemaUrl,
    privacy_url: payload.privacyUrl,
    page_url: page.url(),
  };
}

// Wait until the editor navigates to a saved GPT URL (https://chatgpt.com/g/...),
// which appears after the human saves the GPT and opens it. Resolves with the URL
// on capture, or null on timeout / Ctrl-C / browser close.
function waitForSavedGptUrl(page, context, maxSeconds) {
  return new Promise(resolve => {
    let settled = false;
    const finish = value => {
      if (settled) return;
      settled = true;
      clearInterval(poll);
      clearTimeout(cap);
      resolve(value);
    };
    const poll = setInterval(() => {
      let url = "";
      try {
        url = page.url();
      } catch {
        finish(null);
        return;
      }
      if (isSavedGptUrl(url)) finish(url);
    }, 1500);
    const cap = setTimeout(() => finish(null), Math.max(5, maxSeconds) * 1000);
    process.once("SIGINT", () => finish(null));
    context.on("close", () => finish(null));
  });
}

async function runOpenLogin(args) {
  const context = await launch(args.profile);
  const page = await context.newPage();
  await page.goto(CHATGPT_HOME, { waitUntil: "domcontentloaded" });
  console.log(JSON.stringify({ ok: true, opened: CHATGPT_HOME, profile: args.profile, next: "Log in manually, then stop this command with Ctrl-C or run builder doctor in another terminal." }, null, 2));
  await page.waitForTimeout(2147483647);
}

async function runDoctor(args) {
  const context = await launch(args.profile);
  const page = await context.newPage();
  const status = await detectBuilder(page);
  await context.close();
  console.log(JSON.stringify({
    ok: status.loggedIn && status.hasEditor,
    ...status,
    detection: "heuristic-text-scan",
    note: "Login/editor/Actions detection is a heuristic page-text scan and can be wrong (the Actions panel may be hidden behind a Configure tab). The reliable confirmation is a successful `builder smoke`.",
    profile: args.profile,
  }, null, 2));
}

async function runSniff(args) {
  const captures = [];
  const context = await launch(args.profile);
  startSniffer(context, captures);
  const page = await context.newPage();
  await page.goto(BUILDER_URL, { waitUntil: "domcontentloaded" });
  const flush = async () => {
    await writeJsonPrivate(args.routes, {
      schema_version: 1,
      captured_at: new Date().toISOString(),
      source: "playwright-same-session-sniffer",
      warning: "Internal ChatGPT routes are not stable. Replay only in the same Playwright session and verify by refreshing the Builder page.",
      captures: captures.map(redact),
    });
    console.log(JSON.stringify({ ok: true, route_map_path: args.routes, captured: captures.length }, null, 2));
  };
  process.once("SIGINT", async () => {
    await flush();
    await context.close();
    process.exit(0);
  });
  console.log(JSON.stringify({ ok: true, opened: BUILDER_URL, route_map_path: args.routes, next: "Perform one Builder save/configure flow, then press Ctrl-C here to save the redacted route map." }, null, 2));
  await page.waitForTimeout(2147483647);
}

async function runConfigure(args) {
  const config = await readJson(args.config);
  const captures = [];
  const context = await launch(args.profile);
  if (args.mode === "hybrid") startSniffer(context, captures);
  const page = await context.newPage();
  let result;
  if (args.mode === "api") {
    const routeMap = await readJson(args.routes).catch(() => null);
    const candidate = routeMap ? replayCandidate(routeMap) : null;
    if (!candidate) {
      result = {
        ok: false,
        mode: "api",
        error: "API replay requires a validated route map with a replayable Builder POST/PUT/PATCH request. Run builder sniff first; this script will not guess undocumented routes.",
        route_map_path: args.routes,
      };
    } else {
      const response = await context.request.fetch(candidate.url, {
        method: candidate.method,
        headers: replayHeaders(candidate.headers),
        data: replayBody(candidate.postData, config),
        failOnStatusCode: false,
      });
      await page.goto(BUILDER_URL, { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
      result = {
        ok: response.status() >= 200 && response.status() < 300,
        mode: "api",
        replayed_url: candidate.url,
        replayed_method: candidate.method,
        status: response.status(),
        route_map_path: args.routes,
        validation_url: page.url(),
        note: "The request was replayed inside the same Playwright browser context and the Builder page was refreshed afterward.",
      };
    }
    await writeJsonPrivate(args.state, {
      schema_version: 1,
      updated_at: new Date().toISOString(),
      last_builder_url: page.url(),
      mode: args.mode,
      visibility: args.visibility,
    });
  } else {
    const ui = await configureUi(page, config);
    const manualSteps = [
      `Add an Action and import the schema URL: ${ui.schema_url}`,
      "Authentication: API key. Auth type: Bearer. Paste the token from `chatgpt-codex token` (not printed here).",
      `Privacy policy URL: ${ui.privacy_url}`,
      `Visibility: save as ${args.visibility === "private" ? "Only me" : args.visibility}.`,
      "Save the GPT, then open it (View GPT) so its /g/ chat URL loads.",
    ];
    const waitSeconds = Number(args.wait_seconds) > 0 ? Number(args.wait_seconds) : 600;

    // Live guidance on stderr so stdout stays a single JSON result for callers.
    process.stderr.write(`${JSON.stringify({
      stage: "prefilled",
      prefilled: ui.prefilled,
      manual_steps_required: manualSteps,
      waiting_seconds: waitSeconds,
      note: "Prefilled text fields. Finish Add Action + token + Save, then open the GPT; this command auto-captures the /g/ URL. Press Ctrl-C to stop without capturing.",
      cn_note: "已预填文本字段。请完成 添加 Action + 填 token + 保存，并打开该 GPT；本命令会自动捕获 /g/ 地址写入 state。Ctrl-C 可随时中止。",
    }, null, 2)}\n`);

    const capturedUrl = await waitForSavedGptUrl(page, context, waitSeconds);

    if (args.mode === "hybrid" && captures.length) {
      await writeJsonPrivate(args.routes, {
        schema_version: 1,
        captured_at: new Date().toISOString(),
        source: "playwright-hybrid-configure",
        captures: captures.map(redact),
      });
    }
    await writeJsonPrivate(args.state, {
      schema_version: 1,
      updated_at: new Date().toISOString(),
      last_builder_url: page.url(),
      ...(capturedUrl ? { gpt_url: capturedUrl } : {}),
      mode: args.mode,
      visibility: args.visibility,
    });
    result = {
      ok: Boolean(capturedUrl),
      mode: args.mode,
      saved: Boolean(capturedUrl),
      gpt_url: capturedUrl || "",
      prefilled: ui.prefilled,
      found_actions_text: ui.found_actions_text,
      schema_url: ui.schema_url,
      privacy_url: ui.privacy_url,
      manual_steps_required: capturedUrl ? [] : manualSteps,
      state_path: args.state,
      note: capturedUrl
        ? "Saved GPT URL captured. `builder smoke` can now open the GPT end to end."
        : "Stopped before a saved GPT URL appeared. Finish Save + open the GPT, then rerun `builder configure` to capture it.",
    };
    if (args.mode === "hybrid" && captures.length) {
      result.route_map_path = args.routes;
      result.captured = captures.length;
    }
  }
  await context.close();
  console.log(JSON.stringify(redact(result), null, 2));
}

async function runSmoke(args) {
  const state = await readJson(args.state).catch(() => ({}));
  const targetUrl = state.gpt_url || state.last_gpt_url || (isSavedGptUrl(state.last_builder_url) ? state.last_builder_url : "");
  const context = await launch(args.profile);
  const page = await context.newPage();
  await page.goto(targetUrl || CHATGPT_HOME, { waitUntil: "domcontentloaded" });
  const result = {
    ok: Boolean(targetUrl),
    opened: targetUrl || CHATGPT_HOME,
    message: targetUrl
      ? "GPT page opened. Ask it to call getWorkspaceStatus; approve the first Action domain prompt if shown."
      : "No GPT URL saved yet. Finish builder configure/save first.",
  };
  await context.close();
  console.log(JSON.stringify(result, null, 2));
}

// Pure-function self-test. Requires no browser/login so it can run in CI; the
// playwright probe is best-effort and does not fail the run when absent.
async function runSelfTest() {
  const checks = [];
  const expect = (name, cond) => checks.push({ name, ok: Boolean(cond) });

  // Saved-GPT-URL detection — the regression that made `builder smoke` dead code.
  expect("saved_gpt_url_detected", isSavedGptUrl("https://chatgpt.com/g/g-abc123-demo"));
  expect("editor_url_not_saved", !isSavedGptUrl("https://chatgpt.com/gpts/editor"));
  expect("empty_url_not_saved", !isSavedGptUrl(""));

  const payload = builderPayload({ public_base_url: "https://actions.example.com/" });
  expect("schema_url", payload.schemaUrl === "https://actions.example.com/openapi.json");
  expect("privacy_url", payload.privacyUrl === "https://actions.example.com/privacy");

  const redacted = JSON.stringify(redact({ headers: { authorization: "Bearer secret-xyz" }, api_key: "secret-xyz" }));
  expect("redacts_secrets", !redacted.includes("secret-xyz"));

  const parsed = parseArgs(["node", "script", "configure", "--mode", "hybrid", "--wait-seconds", "5"]);
  expect("parses_mode", parsed.mode === "hybrid");
  expect("parses_wait_seconds", parsed.wait_seconds === "5");

  let playwrightLoaded = false;
  try {
    await loadPlaywright();
    playwrightLoaded = true;
  } catch {
    playwrightLoaded = false;
  }

  const ok = checks.every(check => check.ok);
  console.log(JSON.stringify({ ok, playwright_loaded: playwrightLoaded, checks }, null, 2));
  if (!ok) process.exit(1);
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.command === "self-test") return runSelfTest();
  if (!args.command || !args.profile || !args.config || !args.state || !args.routes) {
    throw new Error("usage: chatgpt_builder_playwright.mjs <open-login|doctor|sniff|configure|smoke> --config <path> --profile <path> --state <path> --routes <path>");
  }
  if (args.command === "open-login") return runOpenLogin(args);
  if (args.command === "doctor") return runDoctor(args);
  if (args.command === "sniff") return runSniff(args);
  if (args.command === "configure") return runConfigure(args);
  if (args.command === "smoke") return runSmoke(args);
  throw new Error(`unknown command: ${args.command}`);
}

main().catch(error => {
  console.error(JSON.stringify({ ok: false, error: String(error && error.message ? error.message : error) }, null, 2));
  process.exit(1);
});
