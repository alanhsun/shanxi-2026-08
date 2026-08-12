#!/usr/bin/env python3
"""Build a responsive, print-friendly static itinerary site."""

from __future__ import annotations

import argparse
import csv
import html
import re
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


STATUS_LABELS = {
    "confirmed": "已确认",
    "selected": "已订",
    "ready": "待办理",
    "monitor": "待复核",
    "reserved": "已预约",
    "paid": "已支付",
    "planned": "计划中",
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


def markdown_text_html(text: str) -> str:
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


def markdown_html(path: Path) -> str:
    return markdown_text_html(path.read_text(encoding="utf-8"))


def dining_by_day(path: Path) -> dict[str, str]:
    """Split the dining guide into one rendered fragment per day."""
    text = path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^## D(\d+)\b[^\n]*\n", text, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        day_id = f"day-{int(heading.group(1)):02d}"
        sections[day_id] = markdown_text_html(text[heading.end():end].strip())
    return sections


def render_table(
    rows: list[dict[str, str]], labels: dict[str, str], transport_links: bool = False,
) -> str:
    if not rows:
        return '<p class="empty">尚无数据。</p>'
    columns = [key for key in labels if any(row.get(key, "").strip() for row in rows)]
    if transport_links and any(row.get("amap_url") or row.get("baidu_url") for row in rows):
        columns.append("_navigation")
    headings = {"_navigation": "导航", **labels}
    head = "".join(f"<th>{html.escape(headings[key])}</th>" for key in columns)
    body_rows = []
    money_columns = {
        "planned_cost_cny", "planned_low_cny", "planned_high_cny", "actual_cny"
    }
    for row in rows:
        cells = []
        for key in columns:
            if key == "_navigation":
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
            elif key == "status":
                value = STATUS_LABELS.get(row.get(key, ""), html.escape(row.get(key, ""))) or "—"
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


def render_budget(rows: list[dict[str, str]]) -> tuple[str, float, float, float]:
    low = high = actual = 0.0
    active = [row for row in rows if row.get("status") != "cancelled"]
    for row in active:
        low += float(row.get("planned_low_cny") or 0)
        high += float(row.get("planned_high_cny") or 0)
        actual += float(row.get("actual_cny") or 0)
    labels = {
        "category": "类别", "item": "项目", "planned_low_cny": "低值",
        "planned_high_cny": "高值", "actual_cny": "已确认",
    }
    return render_table(active, labels), low, high, actual


def render_route_map(route: dict) -> str:
    """Render an accessible, not-to-scale SVG diagram for one travel day."""
    stops = route.get("stops") or []
    segments = route.get("segments") or []
    if len(stops) < 2 or len(segments) != len(stops) - 1:
        raise ValueError(
            f"{route.get('day_id', 'unknown')}: route stops/segments do not match"
        )

    # A vertical flow keeps long Chinese place names and distance labels legible
    # on both desktop and mobile.  The previous horizontal layout became crowded
    # once every segment gained a distance and duration.
    width = 760
    step = 142
    height = max(310, 92 + (len(stops) - 1) * step)
    points = [(62, 42 + index * step) for index in range(len(stops))]
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
    def wrap_text(value: str, width: int) -> list[str]:
        return [value[index:index + width] for index in range(0, len(value), width)] or [""]

    for index, segment in enumerate(segments):
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        svg_parts.append(
            f'<line x1="{x1}" y1="{y1 + 19}" x2="{x2}" y2="{y2 - 21}" '
            f'class="route-line" marker-end="url(#{marker_id})"/>'
        )
        segment_lines = [part.strip() for part in str(segment).split(" · ") if part.strip()]
        if not segment_lines:
            segment_lines = [str(segment)]
        rendered_lines = []
        for line in segment_lines:
            rendered_lines.extend(wrap_text(line, 22))
        box_height = 18 + len(rendered_lines) * 17
        # Reserve the top half of each row for the stop name and detail, then
        # place its travel card beneath it.  This avoids long details touching
        # the following segment card.
        box_y = y1 + 60
        midpoint = box_y + box_height / 2
        svg_parts.append(
            f'<rect x="260" y="{box_y:.1f}" width="430" height="{box_height}" '
            f'ry="8" class="route-segment-box"/>'
        )
        text_y = midpoint - ((len(rendered_lines) - 1) * 8)
        tspans = "".join(
            f'<tspan x="280" dy="{0 if line_index == 0 else 17}">'
            f'{html.escape(line)}</tspan>'
            for line_index, line in enumerate(rendered_lines)
        )
        svg_parts.append(
            f'<text x="280" y="{text_y:.1f}" class="route-segment">{tspans}</text>'
        )

    nav_links = []
    for index, stop in enumerate(stops, start=1):
        x, y = points[index - 1]
        label = html.escape(str(stop.get("label", "")))
        detail = html.escape(str(stop.get("detail", "")))
        label_lines = wrap_text(str(stop.get("label", "")), 10)
        detail_lines = wrap_text(str(stop.get("detail", "")), 11)
        label_y = y - 8 - (len(label_lines) - 1) * 8
        label_tspans = "".join(
            f'<tspan x="96" dy="{0 if line_index == 0 else 16}">'
            f'{html.escape(line)}</tspan>'
            for line_index, line in enumerate(label_lines)
        )
        detail_y = y + 19 + (len(label_lines) - 1) * 8
        detail_tspans = "".join(
            f'<tspan x="96" dy="{0 if line_index == 0 else 14}">'
            f'{html.escape(line)}</tspan>'
            for line_index, line in enumerate(detail_lines)
        )
        svg_parts.extend([
            f'<circle cx="{x}" cy="{y}" r="18" class="route-node"/>',
            f'<text x="{x}" y="{y + 6}" class="route-number" text-anchor="middle">{index}</text>',
            f'<text x="96" y="{label_y}" class="route-stop">{label_tspans}</text>',
            f'<text x="96" y="{detail_y}" class="route-detail">{detail_tspans}</text>',
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
            "transport.csv", "accommodation.csv", "bookings.csv", "budget.csv",
        )
    }
    overview = markdown_html(project / "content" / "overview.md")
    dining_sections = dining_by_day(project / "content" / "dining-guide.md")
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
        dining_html = dining_sections.get(path.stem)
        if dining_html is None:
            raise ValueError(f"Missing dining guide section for {path.name}")
        day_html += (
            '<div class="day-meals">'
            '<h2>当天美食</h2>' + dining_html + '</div>'
        )
        days.append((path.stem, day_html))
    budget_table, budget_low, budget_high, budget_actual = render_budget(tables["budget.csv"])

    transport_labels = {
        "date": "日期", "from": "起点", "to": "终点", "mode": "方式",
        "depart_at": "出发", "arrive_at": "抵达", "planned_cost_cny": "金额",
        "notes": "距离与提醒",
    }
    accommodation_labels = {
        "check_in": "入住", "check_out": "退房", "city": "区域",
        "property": "酒店", "planned_low_cny": "金额",
    }
    booking_labels = {
        "item": "项目", "service_date": "使用日", "closes_at": "最晚处理",
        "channel": "渠道", "status": "状态",
    }
    active_transport = [row for row in tables["transport.csv"] if row.get("status") == "confirmed"]
    active_accommodation = [row for row in tables["accommodation.csv"] if row.get("status") == "selected"]
    active_bookings = [
        row for row in tables["bookings.csv"]
        if row.get("status") in {"ready", "monitor"}
    ]
    transport_table = render_table(
        active_transport, transport_labels, transport_links=True
    )
    accommodation_table = render_table(active_accommodation, accommodation_labels)
    booking_table = render_table(active_bookings, booking_labels)

    verified = data.get("last_verified_at") or "尚未完成发布级核验"
    verified_display = str(verified).split("T", 1)[0]
    asset_version = "".join(character for character in str(verified) if character.isalnum())
    destination_text = " · ".join(data.get("destinations") or [])
    day_links = "".join(
        f'<a href="#{day_id}">D{index}</a>'
        for index, (day_id, _) in enumerate(days, start=1)
    )
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
      <p class="trip-meta">2成人＋1名8岁儿童 · 1间房 · 轻松自驾</p>
      <p class="verified">信息核验至：{html.escape(verified_display)}</p>
    </div>
  </header>
  <nav class="nav" aria-label="页面导航">
    <a href="#overview">总览</a><a href="#days">每日行程</a>
    <a href="#logistics">交通住宿</a><a href="#actions">预约预算</a>
  </nav>
  <main>
    <section id="overview">{overview}</section>
    <section id="days"><h2>每日行程</h2><div class="day-jump" aria-label="快速跳转每日行程">{day_links}</div>{''.join(f'<article class="day" id="{day_id}">{day}</article>' for day_id, day in days)}</section>
    <section id="logistics">
      <h2>交通与住宿</h2>
      <h3>已订住宿</h3>
      {accommodation_table}
      <details class="details-panel"><summary>展开点到点交通表（{len(active_transport)}段）</summary>{transport_table}</details>
    </section>
    <section id="actions">
      <h2>预约与预算</h2>
      <details class="details-panel"><summary>展开预约行动清单（{len(active_bookings)}项）</summary>{booking_table}</details>
      <div class="summary-grid">
        <div><strong>{money(budget_low)}</strong><span>预算低值</span></div>
        <div><strong>{money(budget_high)}</strong><span>预算高值</span></div>
        <div><strong>{money(budget_actual)}</strong><span>已确认支出</span></div>
      </div>
      <details class="details-panel"><summary>展开预算分类明细</summary>{budget_table}</details>
    </section>
  </main>
  <footer>旅途中以票面、景区公告、天气和实时导航为准；出现冲突时优先保证休息与安全。</footer>
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
