from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stm32_agent.generator import CONFIG_ONLY, FIRMWARE_FULL, format_generation_mode
from stm32_agent.service import load_available_skills, run_generation


def _launch_gui() -> int:
    from stm32_agent.gui import launch_gui

    return launch_gui()


def main() -> int:
    if len(sys.argv) == 1:
        return _launch_gui()

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "gui":
        return _launch_gui()
    if args.command == "skills":
        return handle_skills()
    if args.command == "generate":
        return handle_generate(args)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stm32-agent",
        description="根据文字需求生成面向 STM32CubeMX / HAL / Keil5 的工程配置。",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("gui", help="启动桌面图形界面")
    subparsers.add_parser("skills", help="查看当前可用技能")

    generate_parser = subparsers.add_parser("generate", help="在命令行中执行生成")
    generate_parser.add_argument("--spec", required=True, help="自然语言需求描述")
    generate_parser.add_argument("--project", default="stm32_ai_project", help="项目名")
    generate_parser.add_argument("--mcu", default="", help="目标 MCU，例如 STM32F103C8T6")
    generate_parser.add_argument(
        "--mode",
        choices=[CONFIG_ONLY, FIRMWARE_FULL],
        default=CONFIG_ONLY,
        help="生成模式：config_only 仅配置；firmware_full 生成更完整程序与接线方案",
    )
    generate_parser.add_argument("--api-key", default=None, help="LLM API Key")
    generate_parser.add_argument("--base-url", default=None, help="LLM Base URL")
    generate_parser.add_argument("--model", default=None, help="模型名")
    generate_parser.add_argument("--out", default=None, help="输出目录，默认 generated/<project>")
    generate_parser.add_argument("--timeout", type=int, default=None, help="请求超时时间（秒）")
    return parser


def handle_skills() -> int:
    skills = load_available_skills(Path("skills"))
    if not skills:
        print("未找到技能文件。")
        return 1

    print("可用技能：")
    for skill in skills:
        badge = " [always_on]" if skill.always_on else ""
        print(f"- {skill.name}{badge}: {skill.description}")
        if skill.keywords:
            print(f"  keywords: {', '.join(skill.keywords)}")
    return 0


def handle_generate(args: argparse.Namespace) -> int:
    try:
        run = run_generation(
            spec=args.spec,
            project=args.project,
            mcu=args.mcu,
            generation_mode=args.mode,
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
            output_dir=args.out,
            timeout=args.timeout,
            skills_dir=Path("skills"),
            progress_callback=_print_progress,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    print()
    print(f"项目: {run.result.project_name}")
    print(f"模式: {format_generation_mode(run.result.generation_mode)}")
    print(f"MCU: {run.result.target_mcu}")
    print(f"输出目录: {run.output_dir}")
    print(f"Manifest: {run.manifest_path}")
    print(f"查验得分: {run.validation_report.score}/100")
    print(f"查验结论: {run.validation_report.summary}")

    if run.selected_skill_names:
        print(f"已用技能: {', '.join(run.selected_skill_names)}")

    print("生成文件：")
    for item in run.result.files:
        print(f"- {item.path}: {item.purpose}")

    print("查验项：")
    for finding in run.validation_report.findings:
        print(f"- [{finding.level}] {finding.message}")
    return 0


def _print_progress(percent: int, message: str) -> None:
    print(f"[{percent:>3}%] {message}")
