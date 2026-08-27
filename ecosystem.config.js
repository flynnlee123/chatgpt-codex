const fs = require("fs");
const path = require("path");

const repoRoot = __dirname;
const configuredPython = process.env.CHATGPT_CODEX_PYTHON || "";
const venvPython = path.join(repoRoot, ".venv", "bin", "python");
const python = configuredPython || (fs.existsSync(venvPython) ? venvPython : "python3");
const cloudflared = process.env.CHATGPT_CODEX_CLOUDFLARED || "cloudflared";
const cloudflaredConfig = process.env.CHATGPT_CODEX_CLOUDFLARED_CONFIG || path.join(process.env.HOME || "", ".cloudflared", "config.yml");
const tunnelName = process.env.CHATGPT_CODEX_TUNNEL_NAME || "lynx";
const port = process.env.CHATGPT_CODEX_PORT || "8767";

module.exports = {
  apps: [
    {
      name: "chatgpt-codex-server",
      cwd: repoRoot,
      script: python,
      args: `-m chatgpt_codex serve --host 127.0.0.1 --port ${port}`,
      interpreter: "none",
      autorestart: true,
      restart_delay: 3000,
      kill_timeout: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "chatgpt-codex-tunnel",
      cwd: repoRoot,
      script: cloudflared,
      args: `tunnel --config ${cloudflaredConfig} run ${tunnelName}`,
      interpreter: "none",
      autorestart: true,
      restart_delay: 5000,
      kill_timeout: 5000,
    },
  ],
};
