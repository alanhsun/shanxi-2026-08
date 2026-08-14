#!/usr/bin/env python3
"""Build one offline-friendly PDF for each itinerary day."""

from __future__ import annotations

import argparse
import re
from html import escape
from pathlib import Path

import yaml
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


INK = colors.HexColor("#1f2923")
MUTED = colors.HexColor("#667068")
ACCENT = colors.HexColor("#a94b2c")
GREEN = colors.HexColor("#245a4a")
PAPER = colors.HexColor("#fbf8f1")
LINE = colors.HexColor("#d8d0c2")
LIGHT_GREEN = colors.HexColor("#edf4ef")
LIGHT_ORANGE = colors.HexColor("#f8eee5")

DAY_DATES = {
    1: "2026-08-15", 2: "2026-08-16", 3: "2026-08-17",
    4: "2026-08-18", 5: "2026-08-19", 6: "2026-08-20",
    7: "2026-08-21", 8: "2026-08-22", 9: "2026-08-23",
}


def ascii_hyphens(value: str) -> str:
    return value.translate(str.maketrans({
        "–": "-", "—": "-", "−": "-", "‑": "-", "‒": "-",
    }))


def inline_markup(value: str) -> str:
    value = ascii_hyphens(value.strip())
    value = escape(value, quote=True)
    value = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        lambda m: f'<link href="{m.group(2)}" color="#245a4a"><u>{m.group(1)}</u></link>',
        value,
    )
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`([^`]+)`", r"<font name=\"MSYH\">\1</font>", value)
    return value


def register_fonts() -> None:
    regular = Path(r"C:\Windows\Fonts\msyh.ttc")
    bold = Path(r"C:\Windows\Fonts\msyhbd.ttc")
    if not regular.is_file() or not bold.is_file():
        raise FileNotFoundError("Microsoft YaHei font files are required")
    pdfmetrics.registerFont(TTFont("MSYH", str(regular), subfontIndex=0))
    pdfmetrics.registerFont(TTFont("MSYH-Bold", str(bold), subfontIndex=0))
    pdfmetrics.registerFontFamily("MSYH", normal="MSYH", bold="MSYH-Bold")


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover": ParagraphStyle("cover", parent=base["Title"], fontName="MSYH-Bold", fontSize=24,
                                leading=32, textColor=INK, alignment=TA_LEFT, spaceAfter=6 * mm),
        "cover_sub": ParagraphStyle("cover_sub", parent=base["Normal"], fontName="MSYH", fontSize=11,
                                    leading=18, textColor=MUTED, spaceAfter=4 * mm),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="MSYH-Bold", fontSize=18,
                             leading=25, textColor=INK, spaceBefore=6 * mm, spaceAfter=4 * mm,
                             keepWithNext=True),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="MSYH-Bold", fontSize=14,
                             leading=20, textColor=GREEN, spaceBefore=5 * mm, spaceAfter=3 * mm,
                             borderPadding=(0, 0, 1.5 * mm, 0), borderColor=LINE, borderWidth=0,
                             borderBottomWidth=.7, keepWithNext=True),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName="MSYH-Bold", fontSize=11.5,
                             leading=17, textColor=ACCENT, spaceBefore=4 * mm, spaceAfter=2 * mm,
                             keepWithNext=True),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="MSYH", fontSize=9.2,
                               leading=15.2, textColor=INK, spaceAfter=2.3 * mm, wordWrap="CJK"),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="MSYH", fontSize=7.6,
                                leading=11.5, textColor=MUTED, wordWrap="CJK"),
        "table": ParagraphStyle("table", parent=base["BodyText"], fontName="MSYH", fontSize=7.2,
                                leading=10.6, textColor=INK, wordWrap="CJK"),
        "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName="MSYH-Bold",
                                     fontSize=7.4, leading=10.6, textColor=colors.white,
                                     alignment=TA_CENTER, wordWrap="CJK"),
        "callout": ParagraphStyle("callout", parent=base["BodyText"], fontName="MSYH", fontSize=9.2,
                                  leading=15, textColor=INK, backColor=LIGHT_ORANGE,
                                  borderColor=colors.HexColor("#d9a579"), borderWidth=.8,
                                  borderPadding=7, spaceAfter=4 * mm, wordWrap="CJK"),
        "route_title": ParagraphStyle("route_title", parent=base["BodyText"], fontName="MSYH-Bold",
                                      fontSize=10, leading=15, textColor=GREEN, wordWrap="CJK"),
        "route_detail": ParagraphStyle("route_detail", parent=base["BodyText"], fontName="MSYH",
                                       fontSize=8, leading=12, textColor=MUTED, wordWrap="CJK"),
        "caption": ParagraphStyle("caption", parent=base["BodyText"], fontName="MSYH", fontSize=7.5,
                                  leading=11, textColor=MUTED, alignment=TA_CENTER, spaceAfter=3 * mm,
                                  wordWrap="CJK"),
    }


def extract_dining_section(path: Path, day_number: int) -> str:
    text = path.read_text(encoding="utf-8")
    start = re.search(rf"^## D{day_number}\b.*$", text, flags=re.MULTILINE)
    if not start:
        raise ValueError(f"Missing dining section D{day_number}")
    next_heading = re.search(r"^## D\d+\b.*$", text[start.end():], flags=re.MULTILINE)
    end = start.end() + (next_heading.start() if next_heading else len(text[start.end():]))
    return text[start.end():end].strip()


def image_flowable(project: Path, target: str, alt: str, styles: dict[str, ParagraphStyle]):
    source = project / target
    if not source.is_file() or source.suffix.lower() == ".svg":
        return [Paragraph(f"图片：{inline_markup(alt)}", styles["caption"])]
    with PILImage.open(source) as im:
        width, height = im.size
    max_w, max_h = 176 * mm, 125 * mm
    scale = min(max_w / width, max_h / height, 1.0)
    img = Image(str(source), width=width * scale, height=height * scale)
    img.hAlign = "CENTER"
    return [Spacer(1, 1.5 * mm), img, Paragraph(inline_markup(alt), styles["caption"])]


def table_flowable(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> Table:
    columns = max(len(row) for row in rows)
    padded = [row + [""] * (columns - len(row)) for row in rows]
    rendered = []
    for row_index, row in enumerate(padded):
        style = styles["table_head"] if row_index == 0 else styles["table"]
        rendered.append([Paragraph(inline_markup(cell), style) for cell in row])
    available = 182 * mm
    if columns == 4:
        widths = [25 * mm, 47 * mm, 82 * mm, 28 * mm]
    elif columns == 3:
        widths = [36 * mm, 58 * mm, 88 * mm]
    elif columns == 2:
        widths = [46 * mm, 136 * mm]
    else:
        widths = [available / columns] * columns
    table = Table(rendered, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), .35, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def markdown_flowables(text: str, project: Path, styles: dict[str, ParagraphStyle], skip_h1: bool = False):
    lines = ascii_hyphens(text).splitlines()
    flow = []
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        if not line.strip():
            index += 1
            continue
        image_match = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", line.strip())
        if image_match:
            flow.extend(image_flowable(project, image_match.group(2), image_match.group(1), styles))
            index += 1
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            if not (skip_h1 and level == 1):
                style_name = "h1" if level == 1 else "h2" if level == 2 else "h3"
                flow.append(Paragraph(inline_markup(heading.group(2)), styles[style_name]))
            index += 1
            continue
        if line.lstrip().startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = []
            for table_line in table_lines:
                cells = [cell.strip() for cell in table_line.strip("|").split("|")]
                if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    continue
                rows.append(cells)
            if rows:
                flow.append(table_flowable(rows, styles))
                flow.append(Spacer(1, 3 * mm))
            continue
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while index < len(lines) and re.match(r"^\s*[-*]\s+", lines[index]):
                item = re.sub(r"^\s*[-*]\s+", "", lines[index]).strip()
                items.append(ListItem(Paragraph(inline_markup(item), styles["body"]), leftIndent=4 * mm))
                index += 1
            flow.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=6 * mm,
                                     bulletFontName="MSYH", bulletFontSize=7, spaceAfter=2 * mm))
            continue
        if line.startswith(">"):
            quote = []
            while index < len(lines) and lines[index].startswith(">"):
                quote.append(lines[index].lstrip("> "))
                index += 1
            flow.append(Paragraph(inline_markup(" ".join(quote)), styles["callout"]))
            continue
        paragraph = [line.strip()]
        index += 1
        while index < len(lines):
            nxt = lines[index].rstrip()
            if (not nxt.strip() or re.match(r"^(#{1,4})\s+", nxt) or
                    re.match(r"^\s*[-*]\s+", nxt) or nxt.lstrip().startswith("|") or
                    re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", nxt.strip()) or nxt.startswith(">")):
                break
            paragraph.append(nxt.strip())
            index += 1
        flow.append(Paragraph(inline_markup(" ".join(paragraph)), styles["body"]))
    return flow


def route_flowables(route: dict, styles: dict[str, ParagraphStyle]):
    flow = [Paragraph("当日路线速查", styles["h2"])]
    flow.append(Paragraph(inline_markup(str(route.get("summary", ""))), styles["callout"]))
    flow.append(Paragraph(inline_markup(str(route.get("note", ""))), styles["body"]))
    rows = [["节点", "地点与执行", "下一段"]]
    stops = route.get("stops", [])
    segments = route.get("segments", [])
    for idx, stop in enumerate(stops, start=1):
        segment = segments[idx - 1] if idx - 1 < len(segments) else "结束"
        rows.append([
            str(idx),
            f"{stop.get('label', '')}\n{stop.get('detail', '')}",
            str(segment),
        ])
    flow.append(table_flowable(rows, styles))
    for branch in route.get("branches", []):
        options = "；".join(f"{opt.get('label', '')}：{opt.get('detail', '')}" for opt in branch.get("options", []))
        flow.append(Spacer(1, 2 * mm))
        flow.append(Paragraph(inline_markup(f"{branch.get('title', '现场分支')} - {options}"), styles["callout"]))
    return flow


def first_page(canvas, doc, day_label: str):
    canvas.saveState()
    canvas.setFillColor(GREEN)
    canvas.rect(0, A4[1] - 18 * mm, A4[0], 18 * mm, fill=1, stroke=0)
    canvas.setFont("MSYH-Bold", 9)
    canvas.setFillColor(colors.white)
    canvas.drawString(14 * mm, A4[1] - 11.5 * mm, f"山西九日家庭自由行 · {day_label} · 最终执行版")
    footer(canvas, doc)
    canvas.restoreState()


def later_page(canvas, doc, day_label: str):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(14 * mm, A4[1] - 13 * mm, A4[0] - 14 * mm, A4[1] - 13 * mm)
    canvas.setFont("MSYH", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(14 * mm, A4[1] - 10 * mm, f"{day_label} · 离线备查")
    footer(canvas, doc)
    canvas.restoreState()


def footer(canvas, doc):
    canvas.setStrokeColor(LINE)
    canvas.line(14 * mm, 12 * mm, A4[0] - 14 * mm, 12 * mm)
    canvas.setFont("MSYH", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(14 * mm, 7 * mm, "最终版 2026-08-14 · 票面、官方公告与实时导航优先")
    canvas.drawRightString(A4[0] - 14 * mm, 7 * mm, f"第 {doc.page} 页")


def build_one(project: Path, output: Path, day_number: int, route: dict, styles):
    day_path = project / "content" / "days" / f"day-{day_number:02d}.md"
    day_text = day_path.read_text(encoding="utf-8")
    first_heading = re.search(r"^#\s+(.+)$", day_text, flags=re.MULTILINE)
    title = ascii_hyphens(first_heading.group(1) if first_heading else f"D{day_number}")
    date = DAY_DATES[day_number]
    output_path = output / f"day-{day_number:02d}-{date}.pdf"
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=23 * mm, bottomMargin=18 * mm, title=title,
        author="山西九日家庭自由行", subject="每日离线行程备查",
    )
    story = [Spacer(1, 7 * mm), Paragraph(inline_markup(title), styles["cover"])]
    story.append(Paragraph("2成人 + 1名8岁儿童 · 轻松节奏 · 正餐尽量不辣", styles["cover_sub"]))
    story.append(Paragraph("本页为离线备查。出现航变、预警、道路管制、景区公告或身体不适时，立即以安全和休息优先。", styles["callout"]))
    story.extend(route_flowables(route, styles))
    story.append(PageBreak())
    detail_marker = "\n## 看点与现场提醒\n"
    if detail_marker in day_text:
        before_details, after_details = day_text.split(detail_marker, 1)
    else:
        before_details, after_details = day_text, ""
    story.extend(markdown_flowables(before_details, project, styles, skip_h1=True))
    story.append(Paragraph("当天美食", styles["h2"]))
    dining_text = extract_dining_section(project / "content" / "dining-guide.md", day_number)
    story.extend(markdown_flowables(dining_text, project, styles))
    if after_details:
        story.extend(markdown_flowables("## 看点与现场提醒\n" + after_details, project, styles))
    day_label = f"D{day_number} · {date}"
    doc.build(
        story,
        onFirstPage=lambda c, d: first_page(c, d, day_label),
        onLaterPages=lambda c, d: later_page(c, d, day_label),
    )
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="生成D1-D9每日离线PDF")
    parser.add_argument("project_dir", nargs="?", default=".", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output/pdf"))
    args = parser.parse_args()
    project = args.project_dir.resolve()
    output = (project / args.output).resolve() if not args.output.is_absolute() else args.output
    output.mkdir(parents=True, exist_ok=True)
    register_fonts()
    styles = make_styles()
    route_data = yaml.safe_load((project / "data" / "day-routes.yaml").read_text(encoding="utf-8"))
    routes = {item["day_id"]: item for item in route_data["routes"]}
    built = []
    for day_number in range(1, 10):
        day_id = f"day-{day_number:02d}"
        built.append(build_one(project, output, day_number, routes[day_id], styles))
    for path in built:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
