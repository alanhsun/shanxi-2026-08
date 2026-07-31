#!/usr/bin/env python3
"""Create a single-trip Markdown/YAML/CSV project from the bundled template."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "project-template"
TOOL_NAMES = (
    "init_trip.py",
    "validate_trip.py",
    "build_site.py",
    "publish_state.py",
    "site.css",
)


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"日期必须为 YYYY-MM-DD：{value}") from exc


def parse_china_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"时间必须为带时区的 ISO 格式，例如 2026-09-12T10:00+08:00：{value}"
        ) from exc
    if parsed.utcoffset() != timedelta(hours=8):
        raise argparse.ArgumentTypeError(f"时间必须使用北京时间 +08:00：{value}")
    return value


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_list(values: list[str], indent: int = 0) -> str:
    prefix = " " * indent
    if not values:
        return f"{prefix}[]"
    return "\n".join(f"{prefix}- {yaml_string(value)}" for value in values)


def build_trip_yaml(args: argparse.Namespace, destinations: list[str]) -> str:
    return f"""schema_version: 1
trip_id: {yaml_string(args.slug)}
title: {yaml_string(args.title)}
timezone: Asia/Shanghai
stage: intake
publish: false
start_date: {yaml_string(args.start_date.isoformat())}
end_date: {yaml_string(args.end_date.isoformat())}
arrival_at: {yaml_string(args.arrival_at)}
departure_at: {yaml_string(args.departure_at)}
origin: {yaml_string(args.origin)}
entry_hub: {yaml_string(args.entry_hub)}
exit_hub: {yaml_string(args.exit_hub)}
destinations:
{yaml_list(destinations, 2)}
party:
  adults: {args.party_adults}
  children: {args.party_children}
  seniors: {args.party_seniors}
rooms: {args.rooms}
budget_cny:
  low: {args.budget_low}
  high: {args.budget_high}
pace: {args.pace}
lodging_requirements: []
preferences: []
must_visit: []
avoid: []
constraints: []
last_verified_at: null
"""


def day_markdown(day_number: int, day: date, destination: str) -> str:
    return f"""# D{day_number} · {day.isoformat()} · {destination}

## 今日目标

[待确认]

## 时间轴

| 时间 | 安排 | 移动与缓冲 | 费用 | 来源 |
|---|---|---|---:|---|
| 上午 | [待确认] | [待确认] | 0 | |
| 下午 | [待确认] | [待确认] | 0 | |
| 晚间 | [待确认] | [待确认] | 0 | |

## 景点背景与拍照点

[待确认]

## 餐饮与手信

[待确认]

## 替代方案

[待确认]
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="创建中国境内单行程项目")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--start-date", required=True, type=parse_date)
    parser.add_argument("--end-date", required=True, type=parse_date)
    parser.add_argument("--arrival-at", required=True, type=parse_china_datetime)
    parser.add_argument("--departure-at", required=True, type=parse_china_datetime)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--entry-hub", required=True)
    parser.add_argument("--exit-hub", required=True)
    parser.add_argument("--destinations", required=True, help="逗号分隔")
    parser.add_argument("--party-adults", type=int, default=2)
    parser.add_argument("--party-children", type=int, default=0)
    parser.add_argument("--party-seniors", type=int, default=0)
    parser.add_argument("--rooms", type=int, default=1)
    parser.add_argument("--budget-low", type=float, required=True)
    parser.add_argument("--budget-high", type=float, required=True)
    parser.add_argument("--pace", choices=("relaxed", "balanced", "intensive"), default="balanced")
    args = parser.parse_args()

    destinations = [item.strip() for item in args.destinations.split(",") if item.strip()]
    errors: list[str] = []
    if not destinations:
        errors.append("至少需要一个目的地")
    if args.end_date < args.start_date:
        errors.append("结束日期不能早于开始日期")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.slug):
        errors.append("slug 只能使用小写字母、数字和连字符")
    if args.party_adults + args.party_children + args.party_seniors <= 0:
        errors.append("同行人数必须大于 0")
    if min(args.party_adults, args.party_children, args.party_seniors) < 0:
        errors.append("人数不能为负数")
    if args.rooms <= 0:
        errors.append("房间数必须大于 0")
    if args.budget_low <= 0 or args.budget_high < args.budget_low:
        errors.append("预算必须为正数，且高值不能低于低值")
    if datetime.fromisoformat(args.arrival_at).date() != args.start_date:
        errors.append("抵达时间的日期必须等于开始日期")
    if datetime.fromisoformat(args.departure_at).date() != args.end_date:
        errors.append("离开时间的日期必须等于结束日期")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        print(f"ERROR: 目标目录不是空目录：{output}", file=sys.stderr)
        return 2
    if not TEMPLATE_ROOT.is_dir():
        print(f"ERROR: 缺少项目模板：{TEMPLATE_ROOT}", file=sys.stderr)
        return 2

    if output.exists():
        shutil.copytree(TEMPLATE_ROOT, output, dirs_exist_ok=True)
    else:
        shutil.copytree(TEMPLATE_ROOT, output)

    (output / "trip.yaml").write_text(build_trip_yaml(args, destinations), encoding="utf-8")
    days_dir = output / "content" / "days"
    days_dir.mkdir(parents=True, exist_ok=True)
    total_days = (args.end_date - args.start_date).days + 1
    for offset in range(total_days):
        day = args.start_date + timedelta(days=offset)
        destination = destinations[min(offset * len(destinations) // total_days, len(destinations) - 1)]
        filename = days_dir / f"day-{offset + 1:02d}.md"
        filename.write_text(day_markdown(offset + 1, day, destination), encoding="utf-8")

    tools_dir = output / "tools"
    tools_dir.mkdir(exist_ok=True)
    for tool_name in TOOL_NAMES:
        shutil.copy2(Path(__file__).resolve().parent / tool_name, tools_dir / tool_name)

    print(f"Created trip project: {output}")
    print("Next:")
    print(f'  python "{tools_dir / "validate_trip.py"}" "{output}"')
    print(f'  python "{tools_dir / "build_site.py"}" "{output}" --output "{output / "dist"}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
