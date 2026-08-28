const fs = require("fs");
const path = require("path");

const repoRoot = __dirname;
const stateDir = path.join(repoRoot, ".chatgpt-labs");
const configFile = process.env.CHATGPT_CODEX_LABS_CONFIG || path.join(stateDir, "config.json");
const configuredPython = process.env.CHATGPT_CODEX_LABS_PYTHON || process.env.CHATGPT_CODEX_PYTHON || "";
const venvPython = path.join(repoRoot, ".venv", "bin", "python");
const python = configuredPython || (fs.existsSync(venvPython) ? venvPython : "python3");
const cloudflared = process.env.CHATGPT_CODEX_LABS_CLOUDFLARED || process.env.CHATGPT_CODEX_CLOUDFLARED || "cloudflared";
const cloudflaredConfig = process.env.CHATGPT_CODEX_LABS_CLOUDFLARED_CONFIG || process.env.CHATGPT_CODEX_CLOUDFLARED_CONFIG || path.join(process.env.HOME || "", ".cloudflared", "config.yml");
const tunnelCredentials = process.env.CHATGPT_CODEX_LABS_TUNNEL_CREDENTIALS || process.env.CHATGPT_CODEX_TUNNEL_CREDENTIALS || "";
const tunnelName = process.env.CHATGPT_CODEX_LABS_TUNNEL_NAME || process.env.CHATGPT_CODEX_TUNNEL_NAME || "lynx";
const port = process.env.CHATGPT_CODEX_LABS_PORT || "8768";
const tunnelArgs = tunnelCredentials
  ? `tunnel --config ${cloudflaredConfig} run --credentials-file ${tunnelCredentials} ${tunnelName}`
  : `tunnel --config ${cloudflaredConfig} run ${tunnelName}`;

module.exports = {
  apps: [
    {
      name: "chatgpt-labs",
      cwd: repoRoot,
      script: python,
      args: `-m chatgpt_codex --config ${configFile} serve --host 127.0.0.1 --port ${port}`,
      interpreter: "none",
      autorestart: true,
      restart_delay: 3000,
      kill_timeout: 5000,
      merge_logs: true,
      out_file: path.join(stateDir, "server-out.log"),
      error_file: path.join(stateDir, "server-error.log"),
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "chatgpt-labs-tunnel",
      cwd: repoRoot,
      script: cloudflared,
      args: tunnelArgs,
      interpreter: "none",
      autorestart: true,
      restart_delay: 5000,
      kill_timeout: 5000,
      merge_logs: true,
      out_file: path.join(stateDir, "tunnel-out.log"),
      error_file: path.join(stateDir, "tunnel-error.log"),
    },
  ],
};
