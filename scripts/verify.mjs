import { findRepoPython, resolveNpm, runStep } from "./common.mjs";

const python = findRepoPython();
const npm = resolveNpm();

runStep("Backend tests", python, ["-m", "pytest"]);
runStep("Frontend tests", npm, ["test", "--prefix", "frontend", "--", "--run"]);
runStep("Frontend build", npm, ["run", "build", "--prefix", "frontend"]);

console.log("\nVerification complete.");
