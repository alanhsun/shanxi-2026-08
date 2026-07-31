#!/usr/bin/env python3
"""Validate a China independent-trip project before review or publication."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:
    print("ERROR: 缺少 PyYAML；请先安装 requirements.lock", file=sys.stderr)
    raise SystemExit(2)


STAGES = (
    "intake",
    "outline_review",
    "detailed_review",
    "social_validation",
    "approved",
    "published",
)
CSV_SCHEMAS = {
    "transport.csv": [
        "segment_id", "date", "from", "to", "mode", "depart_at", "arrive_at",
        "duration_minutes", "buffer_minutes", "planned_cost_cny", "source_id",
        "amap_url", "baidu_url", "status", "notes",
    ],
    "accommodation.csv": [
        "stay_id", "check_in", "check_out", "city", "area", "property",
        "room_basis", "planned_low_cny", "planned_high_cny", "source_id",
        "status", "reason", "notes",
    ],
    "bookings.csv": [
        "booking_id", "item", "service_date", "channel", "opens_at", "closes_at",
        "planned_cost_cny", "refund_rule", "source_id", "status", "owner_role", "notes",
    ],
    "budget.csv": [
        "category", "item", "planned_low_cny", "planned_high_cny", "actual_cny",
        "status", "source_id", "notes",
    ],
    "sources.csv": [
        "source_id", "source_type", "title", "url", "published_at", "verified_at",
        "expires_at", "applies_to", "confidence", "notes",
    ],
    "images.csv": ["image_path", "source_url", "license", "credit", "notes"],
}
PRIVACY_PATTERNS = {
    "中国大陆手机号": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "身份证号": re.compile(r"(?<!\d)\d{17}[\dXx](?!\w)"),
    "个人邮箱": re.compile(
        r"(?<![\w.-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
        re.IGNORECASE,
    ),
    "房号或入住凭证": re.compile(
        r"(?:房号|房间号|入住码)\s*[:：=]\s*[A-Z0-9-]{2,}",
        re.IGNORECASE,
    ),
    "订单或确认凭证": re.compile(
        r"(?:(?:订单号|确认码|取票码|入住码)\s*[:：=]?\s*[A-Z0-9][A-Z0-9-]{5,}"
        r"|(?:booking|confirmation)\s*(?:number|code|id)\s*[:：=]\s*[A-Z0-9-]{6,})",
        re.IGNORECASE,
    ),
    "访问令牌": re.compile(r"(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{12,}"),
}
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|TBD)\b|\[待确认\]|\{\{[^}]+\}\}", re.IGNORECASE)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\((?:<([^>]+)>|([^)]+))\)")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def read_csv(project: Path, name: str, report: Report) -> list[dict[str, str]]:
    path = project / "data" / name
    if not path.is_file():
        report.error(f"缺少 data/{name}")
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = reader.fieldnames or []
        if actual != CSV_SCHEMAS[name]:
            report.error(f"data/{name} 表头不匹配；期望 {','.join(CSV_SCHEMAS[name])}")
            return []
        return [dict(row) for row in reader]


def parse_iso_date(value: object, field: str, report: Report) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        report.error(f"{field} 必须为 YYYY-MM-DD")
        return None


def parse_beijing_datetime(value: object, field: str, report: Report) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        report.error(f"{field} 必须为带 +08:00 的 ISO 时间")
        return None
    if parsed.utcoffset() != timedelta(hours=8):
        report.error(f"{field} 必须使用北京时间 +08:00")
    return parsed


def number(value: object, field: str, report: Report, allow_blank: bool = False) -> float:
    if allow_blank and (value is None or str(value).strip() == ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        report.error(f"{field} 必须是数字")
        return 0.0


def validate_trip_yaml(project: Path, report: Report) -> dict:
    path = project / "trip.yaml"
    if not path.is_file():
        report.error("缺少 trip.yaml")
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        report.error(f"trip.yaml 无法解析：{exc}")
        return {}
    if not isinstance(data, dict):
        report.error("trip.yaml 顶层必须是映射")
        return {}

    required = (
        "schema_version", "trip_id", "title", "timezone", "stage", "publish",
        "start_date", "end_date", "arrival_at", "departure_at", "origin",
        "entry_hub", "exit_hub", "destinations", "party", "rooms",
        "budget_cny", "pace", "lodging_requirements", "preferences",
        "must_visit", "avoid", "constraints", "last_verified_at",
    )
    for key in required:
        if key not in data:
            report.error(f"trip.yaml 缺少字段：{key}")

    if data.get("schema_version") != 1:
        report.error("schema_version 必须为 1")
    if data.get("timezone") != "Asia/Shanghai":
        report.error("timezone 必须为 Asia/Shanghai")
    if data.get("stage") not in STAGES:
        report.error(f"stage 无效：{data.get('stage')}")
    if not isinstance(data.get("publish"), bool):
        report.error("publish 必须为 true 或 false")
    for key in ("trip_id", "title", "origin", "entry_hub", "exit_hub"):
        if not str(data.get(key, "")).strip():
            report.error(f"{key} 不能为空")
    destinations = data.get("destinations")
    if not isinstance(destinations, list) or not destinations:
        report.error("destinations 至少包含一个目的地")

    start = parse_iso_date(data.get("start_date"), "start_date", report)
    end = parse_iso_date(data.get("end_date"), "end_date", report)
    arrival = parse_beijing_datetime(data.get("arrival_at"), "arrival_at", report)
    departure = parse_beijing_datetime(data.get("departure_at"), "departure_at", report)
    if start and end and end < start:
        report.error("end_date 不能早于 start_date")
    if start and arrival and arrival.date() != start:
        report.error("arrival_at 的日期必须等于 start_date")
    if end and departure and departure.date() != end:
        report.error("departure_at 的日期必须等于 end_date")
    if arrival and departure and departure <= arrival:
        report.error("departure_at 必须晚于 arrival_at")

    party = data.get("party")
    if not isinstance(party, dict):
        report.error("party 必须是映射")
    else:
        counts = []
        for key in ("adults", "children", "seniors"):
            value = party.get(key)
            if not isinstance(value, int) or value < 0:
                report.error(f"party.{key} 必须是非负整数")
            else:
                counts.append(value)
        if counts and sum(counts) <= 0:
            report.error("同行人数必须大于 0")
    if not isinstance(data.get("rooms"), int) or data.get("rooms", 0) <= 0:
        report.error("rooms 必须是正整数")
    budget = data.get("budget_cny")
    if not isinstance(budget, dict):
        report.error("budget_cny 必须是映射")
    else:
        low = number(budget.get("low"), "budget_cny.low", report)
        high = number(budget.get("high"), "budget_cny.high", report)
        if low <= 0 or high < low:
            report.error("预算必须为正数，且 high 不能低于 low")
    if data.get("pace") not in {"relaxed", "balanced", "intensive"}:
        report.error("pace 必须为 relaxed、balanced 或 intensive")
    return data


def validate_sources(rows: list[dict[str, str]], publish: bool, report: Report) -> set[str]:
    ids: set[str] = set()
    today = date.today()
    for index, row in enumerate(rows, 2):
        source_id = row["source_id"].strip()
        if not source_id:
            report.error(f"sources.csv 第 {index} 行缺少 source_id")
            continue
        if source_id in ids:
            report.error(f"sources.csv source_id 重复：{source_id}")
        ids.add(source_id)
        if row["source_type"] not in {"official", "commercial", "community", "user"}:
            report.error(f"sources.csv {source_id} 的 source_type 无效")
        parsed = urlparse(row["url"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            report.error(f"sources.csv {source_id} 的 URL 无效")
        if not row["verified_at"].strip():
            report.error(f"sources.csv {source_id} 缺少 verified_at")
        else:
            parse_iso_date(row["verified_at"], f"sources.csv {source_id}.verified_at", report)
        if row["expires_at"].strip():
            expires = parse_iso_date(row["expires_at"], f"sources.csv {source_id}.expires_at", report)
            if expires and expires < today:
                message = f"sources.csv {source_id} 已于 {expires.isoformat()} 过期"
                report.error(message) if publish else report.warn(message)
        if row["confidence"] not in {"high", "medium", "low", "conflict"}:
            report.error(f"sources.csv {source_id} 的 confidence 无效")
        elif publish and row["confidence"] == "conflict":
            report.error(f"sources.csv {source_id} 仍为 conflict")
    return ids


def validate_source_references(
    tables: dict[str, list[dict[str, str]]], source_ids: set[str], publish: bool, report: Report
) -> None:
    for name, rows in tables.items():
        if name in {"sources.csv", "images.csv"}:
            continue
        for index, row in enumerate(rows, 2):
            source_id = row.get("source_id", "").strip()
            if source_id and source_id not in source_ids:
                report.error(f"{name} 第 {index} 行引用不存在的 source_id：{source_id}")
            if publish and name in {"transport.csv", "accommodation.csv", "bookings.csv"}:
                if row.get("status") in {"conflict", "unknown"}:
                    report.error(f"{name} 第 {index} 行仍为 {row.get('status')}")


def validate_budget(data: dict, rows: list[dict[str, str]], report: Report) -> None:
    if not rows:
        report.warn("budget.csv 尚无预算明细")
        return
    low_total = high_total = 0.0
    for index, row in enumerate(rows, 2):
        if row["status"] not in {"estimate", "quoted", "paid", "cancelled"}:
            report.error(f"budget.csv 第 {index} 行 status 无效")
        low = number(row["planned_low_cny"], f"budget.csv 第 {index} 行 planned_low_cny", report)
        high = number(row["planned_high_cny"], f"budget.csv 第 {index} 行 planned_high_cny", report)
        number(row["actual_cny"], f"budget.csv 第 {index} 行 actual_cny", report, allow_blank=True)
        if high < low:
            report.error(f"budget.csv 第 {index} 行高值低于低值")
        if row["status"] != "cancelled":
            low_total += low
            high_total += high
    budget = data.get("budget_cny") or {}
    target_low = number(budget.get("low"), "budget_cny.low", report)
    target_high = number(budget.get("high"), "budget_cny.high", report)
    if abs(low_total - target_low) > 0.01:
        report.error(f"预算低值不平：明细 {low_total:g}，trip.yaml {target_low:g}")
    if abs(high_total - target_high) > 0.01:
        report.error(f"预算高值不平：明细 {high_total:g}，trip.yaml {target_high:g}")


def validate_operational_tables(
    data: dict, tables: dict[str, list[dict[str, str]]], publish: bool, report: Report
) -> None:
    try:
        trip_start = date.fromisoformat(str(data.get("start_date")))
        trip_end = date.fromisoformat(str(data.get("end_date")))
    except ValueError:
        return

    for index, row in enumerate(tables["transport.csv"], 2):
        travel_date = parse_iso_date(
            row["date"], f"transport.csv 第 {index} 行 date", report
        )
        if travel_date and not trip_start <= travel_date <= trip_end:
            report.error(f"transport.csv 第 {index} 行日期不在行程范围内")
        for field in ("duration_minutes", "buffer_minutes", "planned_cost_cny"):
            value = number(row[field], f"transport.csv 第 {index} 行 {field}", report)
            if value < 0:
                report.error(f"transport.csv 第 {index} 行 {field} 不能为负数")
        if row["status"] not in {"candidate", "confirmed", "conflict"}:
            report.error(f"transport.csv 第 {index} 行 status 无效")
        for field in ("amap_url", "baidu_url"):
            url = row[field].strip()
            if url:
                parsed = urlparse(url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    report.error(f"transport.csv 第 {index} 行 {field} 不是有效 URL")
        if publish and not row["source_id"].strip():
            report.error(f"transport.csv 第 {index} 行发布前必须引用来源")

    selected_stays = 0
    for index, row in enumerate(tables["accommodation.csv"], 2):
        check_in = parse_iso_date(
            row["check_in"], f"accommodation.csv 第 {index} 行 check_in", report
        )
        check_out = parse_iso_date(
            row["check_out"], f"accommodation.csv 第 {index} 行 check_out", report
        )
        if check_in and check_out and check_out <= check_in:
            report.error(f"accommodation.csv 第 {index} 行退房日期必须晚于入住日期")
        low = number(
            row["planned_low_cny"],
            f"accommodation.csv 第 {index} 行 planned_low_cny",
            report,
        )
        high = number(
            row["planned_high_cny"],
            f"accommodation.csv 第 {index} 行 planned_high_cny",
            report,
        )
        if low < 0 or high < low:
            report.error(f"accommodation.csv 第 {index} 行价格区间无效")
        if row["status"] not in {"candidate", "selected", "conflict"}:
            report.error(f"accommodation.csv 第 {index} 行 status 无效")
        if row["status"] == "selected":
            selected_stays += 1
        if publish and not row["source_id"].strip():
            report.error(f"accommodation.csv 第 {index} 行发布前必须引用来源")
    if publish and tables["accommodation.csv"] and selected_stays == 0:
        report.error("发布前 accommodation.csv 至少需要一个 selected 住宿")

    booking_statuses = {
        "unknown", "monitor", "ready", "reserved", "not_required", "conflict"
    }
    for index, row in enumerate(tables["bookings.csv"], 2):
        service_date = parse_iso_date(
            row["service_date"], f"bookings.csv 第 {index} 行 service_date", report
        )
        if service_date and not trip_start <= service_date <= trip_end:
            report.error(f"bookings.csv 第 {index} 行使用日期不在行程范围内")
        cost = number(
            row["planned_cost_cny"],
            f"bookings.csv 第 {index} 行 planned_cost_cny",
            report,
        )
        if cost < 0:
            report.error(f"bookings.csv 第 {index} 行预算不能为负数")
        if row["status"] not in booking_statuses:
            report.error(f"bookings.csv 第 {index} 行 status 无效")
        if publish and not row["source_id"].strip():
            report.error(f"bookings.csv 第 {index} 行发布前必须引用来源")


def iter_source_files(project: Path):
    excluded = {".git", "dist", ".venv", "__pycache__"}
    allowed = {".md", ".yaml", ".yml", ".csv", ".json", ".html", ".txt"}
    for path in project.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if path.suffix.lower() in allowed:
            yield path


def validate_text_and_privacy(project: Path, publish: bool, report: Report) -> None:
    for path in iter_source_files(project):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            report.error(f"文件不是 UTF-8：{path.relative_to(project)}")
            continue
        relative = path.relative_to(project)
        for label, pattern in PRIVACY_PATTERNS.items():
            if pattern.search(text):
                report.error(f"{relative} 可能包含{label}")
        if ".github" not in relative.parts and PLACEHOLDER_RE.search(text):
            message = f"{relative} 仍包含阻塞占位符"
            report.error(message) if publish else report.warn(message)


def validate_images(
    project: Path, image_rows: list[dict[str, str]], publish: bool, report: Report
) -> None:
    registry = {row["image_path"].strip(): row for row in image_rows if row["image_path"].strip()}
    for row_path, row in registry.items():
        if publish and (not row["source_url"].strip() or not row["license"].strip() or not row["credit"].strip()):
            report.error(f"images.csv {row_path} 缺少来源、许可或署名")
        if not (project / row_path).is_file():
            report.error(f"images.csv 登记的文件不存在：{row_path}")
    for markdown_path in list((project / "content").rglob("*.md")) + [
        project / "research" / "social-validation.md"
    ]:
        if not markdown_path.is_file():
            continue
        text = markdown_path.read_text(encoding="utf-8")
        for match in IMAGE_RE.finditer(text):
            target = (match.group(1) or match.group(2) or "").strip().split()[0]
            if target.startswith(("http://", "https://", "data:")):
                if publish:
                    report.error(f"{markdown_path.relative_to(project)} 使用了远程或内嵌图片：{target}")
                continue
            normalized = target.replace("\\", "/").lstrip("./")
            if normalized not in registry:
                report.error(
                    f"{markdown_path.relative_to(project)} 的图片未登记到 images.csv：{normalized}"
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="校验中国境内自由行项目")
    parser.add_argument("project_dir", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    project = args.project_dir.resolve()
    report = Report()
    data = validate_trip_yaml(project, report)
    publish = data.get("publish") is True

    tables = {name: read_csv(project, name, report) for name in CSV_SCHEMAS}
    source_ids = validate_sources(tables["sources.csv"], publish, report)
    validate_source_references(tables, source_ids, publish, report)
    validate_budget(data, tables["budget.csv"], report)
    validate_operational_tables(data, tables, publish, report)
    validate_text_and_privacy(project, publish, report)
    validate_images(project, tables["images.csv"], publish, report)

    for required_path in (
        project / "content" / "overview.md",
        project / "research" / "social-validation.md",
        project / "decisions.md",
    ):
        if not required_path.is_file():
            report.error(f"缺少 {required_path.relative_to(project)}")
    if not list((project / "content" / "days").glob("day-*.md")):
        report.error("content/days 中没有逐日文件")

    if publish:
        for required_table in (
            "transport.csv", "accommodation.csv", "bookings.csv",
            "budget.csv", "sources.csv",
        ):
            if not tables[required_table]:
                report.error(f"publish=true 时 data/{required_table} 不能为空")
        if data.get("stage") not in {"approved", "published"}:
            report.error("publish=true 时 stage 必须为 approved 或 published")
        if not data.get("last_verified_at"):
            report.error("publish=true 时必须填写 last_verified_at")
        else:
            parse_beijing_datetime(data.get("last_verified_at"), "last_verified_at", report)

    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    print(f"Validation: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
