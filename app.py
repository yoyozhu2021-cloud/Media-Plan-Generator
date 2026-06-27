from __future__ import annotations

import argparse
import csv
import html
import io
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs

from media_plan_generator import HEADERS, StrategyValidationError, generate_media_plan, validate_strategy

DEFAULT_STRATEGY = {
    "market_insight": {
        "SEA": "high intent, low CPC, strong Google search behavior",
        "LATAM": "Meta-heavy, price-sensitive buyers",
        "EU_US": "high CPC, high quality buyers",
    },
    "funnel": {
        "TOF": ["TikTok", "Meta Video"],
        "MOF": ["Meta Traffic", "Google PMax"],
        "BOF": ["Google Search", "Meta Lead Ads"],
    },
    "budget_split": {"TOF": 0.3, "MOF": 0.25, "BOF": 0.45},
    "channel_strategy": {
        "Google": {"role": "high intent conversion", "priority": "BOF"},
        "Meta": {"role": "lead generation", "priority": "MOF/BOF"},
        "TikTok": {"role": "awareness", "priority": "TOF"},
    },
    "kpi_forecast": {
        "ctr_range": "1.5%-4%",
        "cpc_range": {"google": "8-25 RMB", "meta": "3-10 RMB"},
        "cvr_range": "2%-6%",
        "cpl_range": "50-120 RMB",
    },
    "creative_strategy": {
        "angles": ["industry sourcing", "scale & credibility", "supply chain advantage"],
        "formats": ["video", "static", "testimonial"],
    },
}

STYLE = """
:root { font-family: Inter, Segoe UI, Arial, sans-serif; color: #17202a; background: #f4f7f9; --accent: #176b87; --accent-dark: #0f4f63; --line: #d7dde3; --muted: #617181; --panel: #fff; }
* { box-sizing: border-box; }
body { margin: 0; }
header { padding: 24px 32px 16px; background: #fff; border-bottom: 1px solid var(--line); }
h1 { margin: 0 0 8px; font-size: 24px; }
p { margin: 0; color: var(--muted); }
main { padding: 24px 32px 44px; display: grid; gap: 18px; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }
label { display: block; margin-bottom: 8px; font-weight: 700; font-size: 14px; }
textarea { width: 100%; min-height: 300px; resize: vertical; border: 1px solid var(--line); border-radius: 8px; padding: 14px; font: 13px/1.45 Consolas, Menlo, monospace; color: #17202a; background: #fbfcfd; }
.actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 12px; }
button, .button { border: 0; border-radius: 7px; padding: 10px 14px; background: var(--accent); color: #fff; font-weight: 700; cursor: pointer; text-decoration: none; font-size: 14px; }
button:hover, .button:hover { background: var(--accent-dark); }
.secondary { background: #e9eef2; color: #1c2b38; }
.secondary:hover { background: #dce4ea; }
.error { background: #fff4f0; color: #9a3412; border: 1px solid #ffd6c8; border-radius: 8px; padding: 12px 14px; }
.meta { color: var(--muted); font-size: 13px; }
.table-wrap { overflow: auto; border: 1px solid var(--line); border-radius: 8px; background: #fff; }
table { width: 100%; min-width: 1180px; border-collapse: collapse; }
th, td { padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 13px; }
th { position: sticky; top: 0; background: #173247; color: #fff; font-size: 12px; }
tr:nth-child(even) td { background: #fbfcfd; }
"""


def default_strategy_text() -> str:
    return json.dumps(DEFAULT_STRATEGY, indent=2, ensure_ascii=False)


def parse_strategy(strategy_text: str) -> dict[str, Any]:
    strategy = json.loads(strategy_text)
    validate_strategy(strategy)
    return strategy


def render_page(strategy_text: str, rows: list[list[Any]] | None = None, error: str | None = None) -> bytes:
    rows = rows or []
    escaped_strategy = html.escape(strategy_text)
    error_html = f'<div class="error">{html.escape(error)}</div>' if error else ""
    meta_html = f'<span class="meta">已生成 {len(rows)} 行</span>' if rows else ""
    download_button = '<button type="submit" formaction="/download">下载 CSV</button>' if rows else ""
    table_html = ""

    if rows:
        header_cells = "".join(f"<th>{html.escape(header)}</th>" for header in HEADERS)
        body_rows = []
        for row in rows:
            cells = "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row)
            body_rows.append(f"<tr>{cells}</tr>")
        table_html = f'<section class="table-wrap"><table><thead><tr>{header_cells}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></section>'

    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Media Plan Generator</title>
  <style>{STYLE}</style>
</head>
<body>
  <header>
    <h1>Media Plan Generator</h1>
    <p>粘贴 Strategy JSON，自动生成结构化 Media Plan。</p>
  </header>
  <main>
    <section class="panel">
      <form method="post">
        <label for="strategy_json">Strategy JSON</label>
        <textarea id="strategy_json" name="strategy_json" spellcheck="false">{escaped_strategy}</textarea>
        <div class="actions">
          <button type="submit">生成 Media Plan</button>
          {download_button}
          <a class="button secondary" href="/">恢复示例</a>
          {meta_html}
        </div>
      </form>
    </section>
    {error_html}
    {table_html}
  </main>
</body>
</html>"""
    return page.encode("utf-8")


def rows_to_csv(rows: list[list[Any]]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(HEADERS)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


class MediaPlanHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return
        strategy_text = default_strategy_text()
        rows = generate_media_plan(DEFAULT_STRATEGY)
        self.send_html(render_page(strategy_text, rows))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = parse_qs(body)
        strategy_text = form.get("strategy_json", [""])[0]

        try:
            rows = generate_media_plan(parse_strategy(strategy_text))
        except json.JSONDecodeError as exc:
            self.send_html(render_page(strategy_text, error="JSON 格式不正确：" + str(exc)))
            return
        except (StrategyValidationError, TypeError, KeyError) as exc:
            self.send_html(render_page(strategy_text, error="策略结构不完整：" + str(exc)))
            return

        if self.path == "/download":
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=media_plan.csv")
            self.end_headers()
            self.wfile.write(rows_to_csv(rows))
            return

        self.send_html(render_page(strategy_text, rows))

    def send_html(self, content: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local media plan web app.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), MediaPlanHandler)
    print(f"Open this URL in your browser: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
