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
        "category": "类别", "item": "包含内容", "planned_low_cny": "预计低值",
        "planned_high_cny": "预计高值", "actual_cny": "已确认",
    }
    return render_table(active, labels), low, high, actual


def render_route_map(route: dict) -> str:
    """Render a compact, responsive vertical route flow for one travel day."""
    stops = route.get("stops") or []
    segments = route.get("segments") or []
    if len(stops) < 2 or len(segments) != len(stops) - 1:
        raise ValueError(
            f"{route.get('day_id', 'unknown')}: route stops/segments do not match"
        )

    branches_by_stop: dict[int, list[dict]] = {}
    for branch in route.get("branches") or []:
        after_stop = int(branch.get("after_stop") or 0)
        if after_stop < 1 or after_stop >= len(stops):
            raise ValueError(
                f"{route.get('day_id', 'unknown')}: invalid branch position"
            )
        branches_by_stop.setdefault(after_stop, []).append(branch)

    flow_parts = ['<ol class="route-flow">']
    for index, stop in enumerate(stops, start=1):
        label = html.escape(str(stop.get("label", "")))
        detail = html.escape(str(stop.get("detail", "")))
        url = str(stop.get("url", ""))
        nav_html = ""
        if urlparse(url).scheme in {"http", "https"}:
            nav_html = (
                f'<a class="route-stop-nav" href="{html.escape(url, quote=True)}" '
                f'target="_blank" rel="noopener noreferrer" '
                f'aria-label="打开{label}的高德导航">高德导航</a>'
            )
        flow_parts.append(
            '<li class="route-step">'
            f'<span class="route-node" aria-hidden="true">{index}</span>'
            '<div class="route-stop">'
            f'<div class="route-stop-title"><strong>{label}</strong>{nav_html}</div>'
            f'<span>{detail}</span>'
            '</div>'
            '</li>'
        )

        for branch in branches_by_stop.get(index, []):
            branch_title = html.escape(str(branch.get("title", "现场决策")))
            option_parts = []
            for option in branch.get("options") or []:
                option_label = html.escape(str(option.get("label", "路线")))
                option_detail = html.escape(str(option.get("detail", "")))
                option_class = " optional" if option.get("optional") else ""
                option_url = str(option.get("url", ""))
                option_nav = ""
                if urlparse(option_url).scheme in {"http", "https"}:
                    option_nav = (
                        f'<a class="route-stop-nav" href="{html.escape(option_url, quote=True)}" '
                        f'target="_blank" rel="noopener noreferrer">高德导航</a>'
                    )
                option_parts.append(
                    f'<li class="route-choice-option{option_class}">'
                    f'<div class="route-stop-title"><strong>{option_label}</strong>{option_nav}</div>'
                    f'<span>{option_detail}</span></li>'
                )
            flow_parts.append(
                '<li class="route-choice">'
                f'<strong class="route-choice-title">{branch_title}</strong>'
                f'<ul>{"".join(option_parts)}</ul></li>'
            )

        if index <= len(segments):
            segment = segments[index - 1]
            segment_text = str(segment.get("text", "")) if isinstance(segment, dict) else str(segment)
            segment_parts = [part.strip() for part in segment_text.split(" · ") if part.strip()]
            if not segment_parts:
                segment_parts = [segment_text]
            badges = "".join(f"<span>{html.escape(part)}</span>" for part in segment_parts)
            flow_parts.append(
                '<li class="route-transfer" aria-label="下一段交通">'
                f'{badges}</li>'
            )
    flow_parts.append("</ol>")

    note = html.escape(str(route.get("note", "")))
    summary = html.escape(str(route.get("summary", f"{len(stops)}站 · 非比例")))
    reference_html = ""
    reference_image = str(route.get("reference_image", ""))
    if reference_image:
        reference_alt = html.escape(str(route.get("reference_alt", "参考路线图")), quote=True)
        reference_caption = html.escape(str(route.get("reference_caption", "仅作方向参考")))
        reference_html = (
            '<details class="reference-map"><summary>查看参考路线大图</summary>'
            f'<img src="{html.escape(reference_image, quote=True)}" alt="{reference_alt}" loading="lazy">'
            f'<p>{reference_caption}</p></details>'
        )
    return (
        '<details class="route-map">'
        f'<summary class="route-map-header"><span>当日路线图</span><small>{summary}</small></summary>'
        '<div class="route-map-body">'
        f'{"".join(flow_parts)}'
        f'<p class="route-note">{note}</p>'
        f'{reference_html}'
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
        anchor = "<h2>行程时间轴</h2>"
        if anchor not in day_html:
            raise ValueError(f"Missing timeline heading in {path.name}")
        day_html = day_html.replace(anchor, render_route_map(route) + anchor, 1)
        dining_html = dining_sections.get(path.stem)
        if dining_html is None:
            raise ValueError(f"Missing dining guide section for {path.name}")
        dining_block = (
            '<div class="day-meals">'
            '<h2>当天美食</h2>' + dining_html + '</div>'
        )
        detail_anchor = "<h2>看点与现场提醒</h2>"
        reminder_anchor = "<h2>当日提醒</h2>"
        if detail_anchor in day_html:
            day_html = day_html.replace(detail_anchor, dining_block + detail_anchor, 1)
        elif reminder_anchor in day_html:
            day_html = day_html.replace(reminder_anchor, dining_block + reminder_anchor, 1)
        else:
            day_html += dining_block
        days.append((path.stem, day_html))
    budget_table, budget_low, budget_high, budget_actual = render_budget(tables["budget.csv"])
    budget_remaining_low = max(0.0, budget_low - budget_actual)
    budget_remaining_high = max(0.0, budget_high - budget_actual)

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
      <h3>费用总盘</h3>
      <div class="summary-grid budget-grid">
        <div><strong>{money(budget_actual)}</strong><span>已确认 / 已预订</span></div>
        <div><strong>{money(budget_remaining_low)}–{money(budget_remaining_high)}</strong><span>尚待支出</span></div>
        <div><strong>{money(budget_low)}–{money(budget_high)}</strong><span>当前总支出预测</span></div>
      </div>
      <p class="budget-note">总额按3人、1间房计算；已确认金额是已知订单与送机费用。尚待支出包含其余门票景交、自驾运行、市内接驳、餐饮及¥1,500–¥3,000弹性备用，备用金无需花完。</p>
      <details class="details-panel" open><summary>预算分类明细</summary>{budget_table}</details>
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
