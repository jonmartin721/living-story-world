import { existsSync } from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
export const ROOT = path.resolve(path.dirname(__filename), "..");

export function findRepoPython() {
  const candidates = [
    path.join(ROOT, ".venv", "Scripts", "python.exe"),
    path.join(ROOT, ".venv", "bin", "python"),
  ];

  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }

  return process.env.PYTHON || "python";
}

export function resolveNpm() {
  return process.platform === "win32" ? "npm.cmd" : "npm";
}

export function runStep(title, command, args) {
  console.log(`\n==> ${title}`);
  console.log([command, ...args].join(" "));

  const options = {
    cwd: ROOT,
    stdio: "inherit",
    shell: false,
  };

  const result =
    process.platform === "win32" && command.toLowerCase().endsWith(".cmd")
      ? spawnSync(process.env.ComSpec || "cmd.exe", ["/d", "/s", "/c", command, ...args], options)
      : spawnSync(command, args, options);

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}
