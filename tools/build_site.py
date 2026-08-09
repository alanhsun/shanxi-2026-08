#!/usr/bin/env python3
"""Build a responsive, print-friendly static itinerary site."""

from __future__ import annotations

import argparse
import csv
import html
import shutil
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import markdown
    import yaml
except ImportError:
    print("ERROR: 缺少 Markdown 或 PyYAML；请先安装 requirements.lock", file=sys.stderr)
    raise SystemExit(2)


STAGE_LABELS = {
    "intake": "需求建档",
    "outline_review": "路线审核",
    "detailed_review": "详细定稿",
    "social_validation": "社交验证",
    "approved": "已批准发布",
    "published": "已发布",
}
TABLE_LABELS = {
    "transport.csv": ("交通", {
        "date": "日期", "from": "起点", "to": "终点", "mode": "方式",
        "depart_at": "出发", "arrive_at": "抵达", "duration_minutes": "分钟",
        "buffer_minutes": "缓冲", "planned_cost_cny": "预算", "status": "状态",
        "notes": "说明（含规划公里数）",
    }),
    "accommodation.csv": ("住宿", {
        "check_in": "入住", "check_out": "退房", "city": "城市", "area": "区域",
        "property": "候选住宿", "room_basis": "房型口径",
        "planned_low_cny": "低值", "planned_high_cny": "高值",
        "status": "状态", "reason": "理由",
    }),
    "bookings.csv": ("预约与抢票", {
        "item": "项目", "service_date": "使用日期", "channel": "渠道",
        "opens_at": "开放时间", "closes_at": "截止时间",
        "planned_cost_cny": "预算", "refund_rule": "退改",
        "status": "状态", "owner_role": "责任角色",
    }),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def money(value: str | float | int | None) -> str:
    if value is None or str(value).strip() == "":
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    return f"¥{amount:,.0f}" if amount.is_integer() else f"¥{amount:,.2f}"


def markdown_html(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    rendered = markdown.markdown(
        html.escape(text, quote=False),
        extensions=("extra", "sane_lists"),
        output_format="html5",
    )
    # Markdown tables need their own scroll container on narrow screens; without
    # it, a wide itinerary table expands the entire page past the viewport.
    return rendered.replace("<table>", '<div class="table-wrap"><table>').replace(
        "</table>", "</table></div>"
    )


def source_links(rows: list[dict[str, str]]) -> dict[str, str]:
    links: dict[str, str] = {}
    for row in rows:
        url = row.get("url", "")
        if urlparse(url).scheme in {"http", "https"}:
            links[row.get("source_id", "")] = (
                f'<a href="{html.escape(url, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer">{html.escape(row.get("source_id", ""))}</a>'
            )
    return links


def render_table(
    rows: list[dict[str, str]], labels: dict[str, str], sources: dict[str, str],
    transport_links: bool = False,
) -> str:
    if not rows:
        return '<p class="empty">尚无数据。</p>'
    columns = [key for key in labels if any(row.get(key, "").strip() for row in rows)]
    if "source_id" not in columns and any(row.get("source_id", "").strip() for row in rows):
        columns.append("source_id")
    if transport_links and any(row.get("amap_url") or row.get("baidu_url") for row in rows):
        columns.append("_navigation")
    headings = {"source_id": "来源", "_navigation": "导航", **labels}
    head = "".join(f"<th>{html.escape(headings[key])}</th>" for key in columns)
    body_rows = []
    money_columns = {
        "planned_cost_cny", "planned_low_cny", "planned_high_cny", "actual_cny"
    }
    for row in rows:
        cells = []
        for key in columns:
            if key == "source_id":
                value = sources.get(row.get(key, ""), html.escape(row.get(key, "")) or "—")
            elif key == "_navigation":
                nav = []
                for label, field in (("高德", "amap_url"), ("百度", "baidu_url")):
                    url = row.get(field, "")
                    if urlparse(url).scheme in {"http", "https"}:
                        nav.append(
                            f'<a href="{html.escape(url, quote=True)}" target="_blank" '
                            f'rel="noopener noreferrer">{label}</a>'
                        )
                value = " / ".join(nav) or "—"
            elif key in money_columns:
                value = money(row.get(key))
            else:
                value = html.escape(row.get(key, "")) or "—"
            cells.append(f"<td>{value}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="table-wrap"><table><thead><tr>'
        + head
        + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
    )


def render_budget(
    rows: list[dict[str, str]], sources: dict[str, str]
) -> tuple[str, float, float, float]:
    low = high = actual = 0.0
    active = [row for row in rows if row.get("status") != "cancelled"]
    for row in active:
        low += float(row.get("planned_low_cny") or 0)
        high += float(row.get("planned_high_cny") or 0)
        actual += float(row.get("actual_cny") or 0)
    labels = {
        "category": "类别", "item": "项目", "planned_low_cny": "计划低值",
        "planned_high_cny": "计划高值", "actual_cny": "实际",
        "status": "状态", "notes": "备注",
    }
    return render_table(rows, labels, sources), low, high, actual


def render_images(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    body = []
    for row in rows:
        url = row.get("source_url", "")
        source = html.escape(url)
        if urlparse(url).scheme in {"http", "https"}:
            source = (
                f'<a href="{html.escape(url, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer">查看来源</a>'
            )
        body.append(
            "<tr>"
            f"<td>{html.escape(row.get('image_path', ''))}</td>"
            f"<td>{html.escape(row.get('license', ''))}</td>"
            f"<td>{html.escape(row.get('credit', ''))}</td>"
            f"<td>{source}</td>"
            "</tr>"
        )
    return (
        '<section id="images"><h2>图片许可与署名</h2>'
        '<div class="table-wrap"><table><thead><tr>'
        "<th>图片</th><th>许可</th><th>署名</th><th>来源</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div></section>"
    )


def render_route_map(route: dict) -> str:
    """Render an accessible, not-to-scale SVG diagram for one travel day."""
    stops = route.get("stops") or []
    segments = route.get("segments") or []
    if len(stops) < 2 or len(segments) != len(stops) - 1:
        raise ValueError(
            f"{route.get('day_id', 'unknown')}: route stops/segments do not match"
        )

    width = max(720, 110 + len(stops) * 155)
    height = 235
    points = [(70 + index * 155, 108) for index in range(len(stops))]
    day_id = html.escape(str(route.get("day_id", "route")), quote=True)
    title = html.escape(str(route.get("title", "当日路线")))
    marker_id = f"arrow-{day_id}"

    svg_parts = [
        f'<svg class="route-diagram" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-labelledby="{day_id}-title">',
        f'<title id="{day_id}-title">{title}，非比例路线示意图</title>',
        "<defs>",
        f'<marker id="{marker_id}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">',
        '<path d="M0,0 L8,4 L0,8 Z" fill="#b84d2b"/></marker>',
        "</defs>",
    ]
    for index, segment in enumerate(segments):
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        svg_parts.append(
            f'<line x1="{x1 + 13}" y1="{y1}" x2="{x2 - 15}" y2="{y2}" '
            f'class="route-line" marker-end="url(#{marker_id})"/>'
        )
        midpoint = (x1 + x2) / 2
        svg_parts.append(
            f'<text x="{midpoint}" y="151" class="route-segment" text-anchor="middle">'
            f'{html.escape(str(segment))}</text>'
        )

    nav_links = []
    for index, stop in enumerate(stops, start=1):
        x, y = points[index - 1]
        label = html.escape(str(stop.get("label", "")))
        detail = html.escape(str(stop.get("detail", "")))
        svg_parts.extend([
            f'<circle cx="{x}" cy="{y}" r="18" class="route-node"/>',
            f'<text x="{x}" y="114" class="route-number" text-anchor="middle">{index}</text>',
            f'<text x="{x}" y="48" class="route-stop" text-anchor="middle">{label}</text>',
            f'<text x="{x}" y="70" class="route-detail" text-anchor="middle">{detail}</text>',
        ])
        url = str(stop.get("url", ""))
        if urlparse(url).scheme in {"http", "https"}:
            nav_links.append(
                f'<a href="{html.escape(url, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer">高德 · {index} {label}</a>'
            )
    svg_parts.append("</svg>")
    note = html.escape(str(route.get("note", "")))
    links_html = "".join(nav_links)
    return (
        '<details class="route-map">'
        f'<summary><span>查看当日路线示意图</span><small>{len(stops)}站 · 非比例</small></summary>'
        '<div class="route-map-body">'
        f'<div class="route-map-scroll">{"".join(svg_parts)}</div>'
        f'<p class="route-note">{note}</p>'
        f'<div class="route-nav" aria-label="当日高德导航入口">{links_html}</div>'
        '</div></details>'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="构建静态行程网站")
    parser.add_argument("project_dir", nargs="?", default=".", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    project = args.project_dir.resolve()
    output = args.output.resolve()
    data = yaml.safe_load((project / "trip.yaml").read_text(encoding="utf-8")) or {}

    tables = {
        name: read_csv(project / "data" / name)
        for name in (
            "transport.csv", "accommodation.csv", "bookings.csv",
            "budget.csv", "sources.csv", "images.csv",
        )
    }
    sources = source_links(tables["sources.csv"])
    overview = markdown_html(project / "content" / "overview.md")
    dining = markdown_html(project / "content" / "dining-guide.md")
    version_tracking = markdown_html(project / "content" / "version-tracking.md")
    decisions = markdown_html(project / "decisions.md")
    route_data = yaml.safe_load(
        (project / "data" / "day-routes.yaml").read_text(encoding="utf-8")
    ) or {}
    routes = {
        str(route.get("day_id")): route
        for route in route_data.get("routes", [])
        if route.get("day_id")
    }
    days = []
    for path in sorted((project / "content" / "days").glob("day-*.md")):
        day_html = markdown_html(path)
        route = routes.get(path.stem)
        if route is None:
            raise ValueError(f"Missing route diagram data for {path.stem}")
        anchor = "<h2>三餐与时间轴</h2>"
        if anchor not in day_html:
            raise ValueError(f"Missing timeline heading in {path.name}")
        day_html = day_html.replace(anchor, render_route_map(route) + anchor, 1)
        days.append(day_html)
    social = markdown_html(project / "research" / "social-validation.md")
    budget_table, budget_low, budget_high, budget_actual = render_budget(
        tables["budget.csv"], sources
    )

    transport_labels = TABLE_LABELS["transport.csv"][1]
    accommodation_labels = TABLE_LABELS["accommodation.csv"][1]
    booking_labels = TABLE_LABELS["bookings.csv"][1]
    active_transport = [row for row in tables["transport.csv"] if row.get("status") == "confirmed"]
    alternative_transport = [row for row in tables["transport.csv"] if row.get("status") != "confirmed"]
    active_accommodation = [row for row in tables["accommodation.csv"] if row.get("status") == "selected"]
    alternative_accommodation = [row for row in tables["accommodation.csv"] if row.get("status") != "selected"]
    active_bookings = [
        row for row in tables["bookings.csv"]
        if row.get("status") in {"ready", "monitor", "reserved"}
    ]
    inactive_bookings = [
        row for row in tables["bookings.csv"]
        if row.get("status") not in {"ready", "monitor", "reserved"}
    ]
    transport_table = render_table(
        active_transport, transport_labels, sources, transport_links=True
    )
    accommodation_table = render_table(active_accommodation, accommodation_labels, sources)
    booking_table = render_table(active_bookings, booking_labels, sources)

    alternative_tables = ""
    if alternative_transport:
        alternative_tables += (
            "<h3>未采用的交通方案</h3>"
            + render_table(alternative_transport, transport_labels, sources, transport_links=True)
        )
    if alternative_accommodation:
        alternative_tables += (
            "<h3>住宿备选记录</h3>"
            + render_table(alternative_accommodation, accommodation_labels, sources)
        )
    if inactive_bookings:
        alternative_tables += (
            "<h3>无需预约/非当前行动项</h3>"
            + render_table(inactive_bookings, booking_labels, sources)
        )
    source_rows = []
    for row in tables["sources.csv"]:
        source_rows.append({
            "title": row.get("title", ""),
            "source_type": row.get("source_type", ""),
            "verified_at": row.get("verified_at", ""),
            "expires_at": row.get("expires_at", ""),
            "confidence": row.get("confidence", ""),
            "source_id": row.get("source_id", ""),
        })
    source_table = render_table(source_rows, {
        "title": "来源", "source_type": "类型", "verified_at": "核验时间",
        "expires_at": "复查/失效", "confidence": "可信状态",
        "source_id": "原文",
    }, sources)
    image_section = render_images(tables["images.csv"])

    stage = STAGE_LABELS.get(data.get("stage"), data.get("stage", "未知"))
    verified = data.get("last_verified_at") or "尚未完成发布级核验"
    asset_version = "".join(character for character in str(verified) if character.isalnum())
    destination_text = " · ".join(data.get("destinations") or [])
    published_badge = "允许发布" if data.get("publish") else "草稿 / 不发布"
    html_page = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{html.escape(data.get('title', '行程'))}">
  <title>{html.escape(data.get('title', '行程'))}</title>
  <link rel="stylesheet" href="styles.css?v={html.escape(asset_version, quote=True)}">
</head>
<body>
  <header class="hero">
    <div class="hero-inner">
      <p class="eyebrow">{html.escape(destination_text)}</p>
      <h1>{html.escape(data.get('title', '行程'))}</h1>
      <p>{html.escape(str(data.get('start_date', '')))} — {html.escape(str(data.get('end_date', '')))}</p>
      <div class="badges"><span>{html.escape(stage)}</span><span>{html.escape(published_badge)}</span></div>
      <p class="verified">最近核验：{html.escape(str(verified))}</p>
    </div>
  </header>
  <nav class="nav" aria-label="页面导航">
    <a href="#overview">一页总览</a><a href="#days">每日行程</a><a href="#dining">用餐指南</a>
    <a href="#logistics">交通住宿</a><a href="#actions">预约预算</a><a href="#versions">版本追踪</a>
  </nav>
  <main>
    <section id="overview">{overview}</section>
    <section id="days"><h2>逐日安排</h2>{''.join(f'<article class="day">{day}</article>' for day in days)}</section>
    <section id="dining" class="meal-guide">{dining}</section>
    <section id="logistics">
      <h2>交通与住宿</h2>
      <h3>当前住宿</h3>
      {accommodation_table}
      <details class="details-panel"><summary>查看完整点到点交通表（{len(active_transport)}段）</summary>{transport_table}</details>
    </section>
    <section id="actions">
      <h2>预约与预算</h2>
      <details class="details-panel"><summary>查看当前预约行动清单（{len(active_bookings)}项）</summary>{booking_table}</details>
      <div class="summary-grid">
        <div><strong>{money(budget_low)}</strong><span>计划低值</span></div>
        <div><strong>{money(budget_high)}</strong><span>计划高值</span></div>
        <div><strong>{money(budget_actual)}</strong><span>实际花销</span></div>
      </div>
      <details class="details-panel"><summary>查看预算分类明细</summary>{budget_table}</details>
    </section>
    <section id="versions" class="version-section">
      {version_tracking}
      <details class="details-panel"><summary>查看未采用方案与非当前行动项</summary>{alternative_tables}</details>
      <details class="details-panel"><summary>查看社交平台筛选与真实体验证据</summary><div class="details-body">{social}</div></details>
      <details class="details-panel"><summary>查看完整决策记录</summary><div class="details-body">{decisions}</div></details>
      <details class="details-panel"><summary>查看全部来源与核验时间</summary>{source_table}</details>
    </section>
    {image_section}
  </main>
  <footer>本页是公开脱敏的最终行程展示版。票价、班次、开放时间和预约规则仍以出发前实时官方信息为准。</footer>
</body>
</html>
"""
    css_source = Path(__file__).resolve().parent / "site.css"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / "index.html").write_text(html_page, encoding="utf-8")
    if css_source.is_file():
        shutil.copy2(css_source, output / "styles.css")
    else:
        print(f"ERROR: 缺少样式文件：{css_source}", file=sys.stderr)
        return 2
    media = project / "media"
    if media.is_dir():
        shutil.copytree(media, output / "media")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built site: {output / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
