import { findRepoPython, resolveNpm, runStep } from "./common.mjs";

const python = findRepoPython();
const npm = resolveNpm();
const extraArgs = process.argv.slice(2);

runStep("Frontend build", npm, ["run", "build", "--prefix", "frontend"]);
runStep("Web app", python, ["-m", "living_storyworld.cli", "web", ...extraArgs]);
