import fs from "node:fs/promises";
import openapiTS, { astToString } from "openapi-typescript";

const input = new URL(
  "../../src/oil_agent/contracts/openapi.json",
  import.meta.url,
);
const output = new URL("../src/generated/api.d.ts", import.meta.url);
const text = astToString(await openapiTS(input));
if (process.argv.includes("--check")) {
  if (
    (await fs.readFile(output, "utf8")).replace(/\r\n/g, "\n") !==
    text.replace(/\r\n/g, "\n")
  ) {
    throw new Error(
      "Generated API types are stale. Run npm run generate after adopting C schema.",
    );
  }
  console.log("Generated API types match authoritative OpenAPI.");
} else {
  await fs.mkdir(new URL("../src/generated/", import.meta.url), {
    recursive: true,
  });
  await fs.writeFile(output, text);
  console.log("Generated src/generated/api.d.ts from authoritative OpenAPI.");
}
