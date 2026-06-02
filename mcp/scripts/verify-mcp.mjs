// Ad-hoc runtime verification against a running `wrangler dev` (not part of the
// test suite). Connects over Streamable HTTP, lists tools, and calls each once.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const url = new URL(process.argv[2] ?? "http://localhost:8799/mcp");
const client = new Client({ name: "verify", version: "1.0.0" });
await client.connect(new StreamableHTTPClientTransport(url));

const { tools } = await client.listTools();
console.log("TOOLS:", tools.map((t) => t.name).sort().join(", "));

async function call(name, args) {
  const res = await client.callTool({ name, arguments: args });
  console.log(name, "->", res.content[0].text);
}

await call("count_workdays", { start: "2025-02-06", end: "2025-02-12" });
await call("add_workdays", { from: "2026-01-02", workdays: 1 });
await call("next_makeup_workday", { from: "2025-01-01" });
await call("optimize_leave", { year: 2026, annualLeaveDays: 5 });
await call("find_travel_windows", { year: 2026, annualLeaveDays: 5, minTripLength: 10 });
// error paths
await call("optimize_leave", { year: 1999, annualLeaveDays: 3 });
await call("count_workdays", { start: "bad", end: "2025-02-12" });

await client.close();
