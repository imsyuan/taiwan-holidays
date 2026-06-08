// 獨立的健康檢查 Worker：每天 cron 觸發，從外部 fetch 正式 MCP 端點，
// 異常時打 Discord webhook。刻意與 taiwan-workday-mcp 分開部署，
// 這樣即使 MCP Worker 整個掛掉，這支監控仍會照常執行並通知。

export interface Env {
  // 監控目標（vars，可在 wrangler.jsonc 改）
  TARGET_URL: string;
  // Discord webhook（secret：wrangler secret put DISCORD_WEBHOOK）
  DISCORD_WEBHOOK?: string;
}

interface CheckResult {
  ok: boolean;
  url: string;
  status: number;
  error?: string;
}

const DEFAULT_TARGET = "https://mcp.tw-holidays.gooliya.com/";

async function check(env: Env): Promise<CheckResult> {
  const url = env.TARGET_URL || DEFAULT_TARGET;
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(15000) });
    const body = await res.text();
    // 健康 = 200 且回應 JSON 含 tools 欄位（不只是任意 200）
    const ok = res.status === 200 && body.includes('"tools"');
    return { ok, url, status: res.status };
  } catch (e) {
    return { ok: false, url, status: 0, error: String(e) };
  }
}

async function notifyDiscord(env: Env, result: CheckResult): Promise<void> {
  if (!env.DISCORD_WEBHOOK) return;
  const payload = {
    username: "MCP Healthcheck",
    embeds: [
      {
        title: "🔴 Taiwan Workday MCP 異常",
        description: "正式端點未正常回應，請檢查 Cloudflare Worker。",
        color: 15158332,
        fields: [
          { name: "Endpoint", value: result.url },
          { name: "HTTP", value: String(result.status), inline: true },
          ...(result.error
            ? [{ name: "Error", value: result.error.slice(0, 500), inline: true }]
            : []),
        ],
      },
    ],
  };
  await fetch(env.DISCORD_WEBHOOK, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export default {
  // Cron Trigger：排程一到自動跑
  async scheduled(_event: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(
      (async () => {
        const result = await check(env);
        if (!result.ok) await notifyDiscord(env, result);
      })(),
    );
  },

  // 公開的唯讀健康查詢：現在就檢查一次並回 JSON。
  // 刻意「不」從這裡發 Discord——通知只由 cron 觸發，避免任何人打這個
  // 公開網址就能灌爆通知頻道。
  async fetch(req: Request, env: Env): Promise<Response> {
    const u = new URL(req.url);
    if (u.pathname === "/check") {
      const result = await check(env);
      return Response.json(result, { status: result.ok ? 200 : 503 });
    }
    return new Response(
      "tw-holidays-monitor — GET /check 回傳目前健康狀態（唯讀，不發通知）\n",
      { headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  },
};
