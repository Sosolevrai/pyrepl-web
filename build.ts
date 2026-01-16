import { readFileSync, writeFileSync } from "fs";

// Read the Python code
const pythonCode = readFileSync("src/python/console.py", "utf-8");

// Read the TypeScript source
const tsSource = readFileSync("src/embed.ts", "utf-8");

// Create a version with inlined Python
const inlinedSource = tsSource.replace(
  `const response = await fetch('/python/console.py');
  const consoleCode = await response.text();`,
  `const consoleCode = ${JSON.stringify(pythonCode)};`
);

// Write temporary file
writeFileSync("src/embed.build.ts", inlinedSource);

// Bundle it
const result = await Bun.build({
  entrypoints: ["src/embed.build.ts"],
  outdir: "dist",
  naming: "pyrepl.js",
  minify: true,
});

if (result.success) {
  console.log("Built dist/pyrepl.js");
} else {
  console.error("Build failed:", result.logs);
}

// Clean up temp file
import { unlinkSync } from "fs";
unlinkSync("src/embed.build.ts");