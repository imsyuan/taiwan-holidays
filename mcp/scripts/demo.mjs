import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const url = new URL(process.argv[2] ?? "http://localhost:8799/mcp");
const client = new Client({ name: "demo", version: "1.0.0" });
await client.connect(new StreamableHTTPClientTransport(url));

const { tools } = await client.listTools();
console.log("可用工具:", tools.map((t) => t.name).sort().join(", "), "\n");

async function call(label, name, args, top) {
  const res = await client.callTool({ name, arguments: args });
  let data = JSON.parse(res.content[0].text);
  if (Array.isArray(data) && top) data = data.slice(0, top);
  console.log(`▶ ${label}`);
  console.log(`  ${name}(${JSON.stringify(args)})`);
  console.log("  =>", JSON.stringify(data), "\n");
}

await call("這個月有幾個工作日(2026-06)", "count_workdays", { start: "2026-06-01", end: "2026-06-30" });
await call("交付日 = 今天起算 10 個工作日", "add_workdays", { from: "2026-06-02", workdays: 10 });
await call("下一個補班日", "next_makeup_workday", { from: "2026-06-02" });
await call("2026 年有 5 天年假，最佳請假方案(前3名)", "optimize_leave", { year: 2026, annualLeaveDays: 5 }, 3);
await call("2026 想出國(>=4天)，最佳出遊時段(前3名)", "find_travel_windows", { year: 2026, annualLeaveDays: 2, minTripLength: 4 }, 3);
await call("查不存在的年份(錯誤處理)", "optimize_leave", { year: 1999, annualLeaveDays: 3 });

await client.close();
