// Remote MCP server (thin shell) for the Taiwan workday engine.
//
// Responsibilities are deliberately limited to: parse tool input, call the
// pure workday-engine, and wrap the structured result. NO calculation logic
// lives here (design.md "純運算核心與 MCP 薄殼分離"). Deployed on Cloudflare
// Workers via the agents SDK McpAgent over the Streamable HTTP transport at
// /mcp ("部署於 Cloudflare Workers，使用 agents SDK 的 McpAgent / Streamable HTTP").

import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  addWorkdays,
  countWorkdays,
  findTravelWindows,
  nextMakeupWorkday,
  optimizeLeave,
} from "./engine/index.js";
import { allDays, availableYears, calendarsByYear } from "./data.js";

export interface Env {
  MCP_OBJECT: DurableObjectNamespace;
}

const rangeShape = z
  .object({ start: z.string(), end: z.string() })
  .optional()
  .describe("Optional inclusive date range, YYYY-MM-DD");

/** Wrap any engine result (success object or structured EngineError) as MCP text content. */
function reply(data: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(data) }] };
}

export class WorkdayMCP extends McpAgent<Env> {
  server = new McpServer({
    name: "taiwan-workday",
    version: "1.0.0",
  });

  async init() {
    this.server.tool(
      "count_workdays",
      "Count working days, holidays, and makeup workdays in an inclusive date range. Makeup workdays count as working days.",
      { start: z.string(), end: z.string() },
      async ({ start, end }) => reply(countWorkdays(allDays, start, end)),
    );

    this.server.tool(
      "add_workdays",
      "Return the date N working days from a start date (start date not counted; negative N walks backward).",
      { from: z.string(), workdays: z.number().int() },
      async ({ from, workdays }) => reply(addWorkdays(allDays, from, workdays)),
    );

    this.server.tool(
      "next_makeup_workday",
      "Find the next makeup workday on or after a base date, or all makeup workdays within a range.",
      { from: z.string().optional(), range: rangeShape },
      async ({ from, range }) => reply(nextMakeupWorkday(allDays, { from, range })),
    );

    this.server.tool(
      "optimize_leave",
      "Given a year and available annual-leave days, return leave plans ranked by days-off-per-leave-day efficiency.",
      {
        year: z.number().int(),
        annualLeaveDays: z.number().int(),
        range: rangeShape,
      },
      async ({ year, annualLeaveDays, range }) =>
        reply(optimizeLeave(calendarsByYear, { year, annualLeaveDays, range })),
    );

    this.server.tool(
      "find_travel_windows",
      "Suggest the best travel windows (timing only, no booking data) given available leave days and a minimum trip length.",
      {
        year: z.number().int(),
        annualLeaveDays: z.number().int(),
        minTripLength: z.number().int(),
        range: rangeShape,
      },
      async ({ year, annualLeaveDays, minTripLength, range }) =>
        reply(
          findTravelWindows(calendarsByYear, {
            year,
            annualLeaveDays,
            minTripLength,
            range,
          }),
        ),
    );
  }
}

export default {
  fetch(request: Request, env: Env, ctx: ExecutionContext): Response | Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/mcp") {
      return WorkdayMCP.serve("/mcp").fetch(request, env, ctx);
    }
    if (url.pathname === "/sse" || url.pathname === "/sse/message") {
      return WorkdayMCP.serveSSE("/sse").fetch(request, env, ctx);
    }
    if (url.pathname === "/") {
      return new Response(
        JSON.stringify({
          name: "taiwan-workday-mcp",
          endpoint: "/mcp",
          transport: "streamable-http",
          tools: [
            "count_workdays",
            "add_workdays",
            "next_makeup_workday",
            "optimize_leave",
            "find_travel_windows",
          ],
          availableYears,
        }),
        { headers: { "content-type": "application/json; charset=utf-8" } },
      );
    }
    return new Response("Not found", { status: 404 });
  },
};
