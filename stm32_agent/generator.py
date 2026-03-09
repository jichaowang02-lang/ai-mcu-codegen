from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stm32_agent.llm_client import LlmClient
from stm32_agent.models import GeneratedFile, GenerationResult, Skill

CONFIG_ONLY = "config_only"
FIRMWARE_FULL = "firmware_full"

GENERATION_MODE_LABELS = {
    CONFIG_ONLY: "仅生成配置文件",
    FIRMWARE_FULL: "生成可继续在 Keil5 开发的程序 + 接线方案",
}

EXPECTED_OUTPUTS = {
    CONFIG_ONLY: [
        "<project>.ioc",
        "Core/Inc/ai_board_config.h",
        "Core/Src/ai_board_config.c",
        "docs/generated-notes.md",
    ],
    FIRMWARE_FULL: [
        "<project>.ioc",
        "Core/Inc/main.h",
        "Core/Src/main.c",
        "Core/Inc/ai_board_config.h",
        "Core/Src/ai_board_config.c",
        "docs/wiring.md",
        "docs/keil5-notes.md",
    ],
}


def generate_files(
    client: LlmClient,
    project_name: str,
    target_mcu: str,
    user_spec: str,
    selected_skills: list[Skill],
    generation_mode: str,
) -> GenerationResult:
    mode = _normalize_mode(generation_mode)
    system_prompt = _build_system_prompt(mode)
    user_prompt = _build_user_prompt(project_name, target_mcu, user_spec, selected_skills, mode)

    payload = client.complete_json(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    payload.setdefault("project_name", project_name)
    payload.setdefault("target_mcu", target_mcu or "UNKNOWN_MCU")
    payload.setdefault("generation_mode", mode)
    payload.setdefault("selected_skills", [skill.name for skill in selected_skills])
    return _to_generation_result(payload)


def save_result(result: GenerationResult, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    for item in result.files:
        file_path = output_dir / item.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(item.content, encoding="utf-8")

    manifest_path = output_dir / "manifest.json"
    manifest_payload = {
        "project_name": result.project_name,
        "target_mcu": result.target_mcu,
        "generation_mode": result.generation_mode,
        "summary": result.summary,
        "assumptions": result.assumptions,
        "warnings": result.warnings,
        "selected_skills": result.selected_skills,
        "files": [{"path": item.path, "purpose": item.purpose} for item in result.files],
    }
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def format_generation_mode(mode: str) -> str:
    return GENERATION_MODE_LABELS.get(_normalize_mode(mode), GENERATION_MODE_LABELS[CONFIG_ONLY])


def expected_outputs_for_mode(project_name: str, generation_mode: str) -> list[str]:
    normalized = _normalize_mode(generation_mode)
    return [item.replace("<project>", project_name) for item in EXPECTED_OUTPUTS[normalized]]


def _build_system_prompt(generation_mode: str) -> str:
    common = """
你是 STM32 + HAL + STM32CubeMX + Keil5 项目生成助手。
你必须只输出一个 JSON 对象，不要输出 Markdown，不要解释，不要代码围栏。

JSON 结构必须是：
{
  "project_name": "项目名",
  "target_mcu": "MCU 型号",
  "generation_mode": "config_only 或 firmware_full",
  "summary": "整体结果摘要",
  "assumptions": ["模型做出的假设"],
  "warnings": ["需要用户注意的限制"],
  "selected_skills": ["技能名"],
  "files": [
    {
      "path": "相对路径",
      "purpose": "该文件用途",
      "content": "完整文件内容"
    }
  ]
}

硬性要求：
1. 所有文件内容都要完整，不能写“略”“省略”“示例同上”。
2. 如果用户信息不足，必须在 assumptions 里明确列出你的假设。
3. 如果某项内容无法百分百保证真实硬件可直接运行，必须写入 warnings。
4. `.ioc` 需要体现 MCU、时钟、GPIO、外设初始化思路，格式尽量贴近 CubeMX 可读风格。
5. 所有代码都按 STM32 HAL 风格输出，面向用户后续在 Keil5 中继续开发。
6. 生成的文件路径必须使用正斜杠。
""".strip()

    if generation_mode == FIRMWARE_FULL:
        extra = """
当前模式：firmware_full

目标：让 AI 直接生成一个面向 Keil5 的完整起步工程骨架，包含可继续编写、编译和烧录前准备的关键文件，并额外给出接线方案。

至少必须生成这些文件：
- `<project>.ioc`
- `Core/Inc/main.h`
- `Core/Src/main.c`
- `Core/Inc/ai_board_config.h`
- `Core/Src/ai_board_config.c`
- `docs/wiring.md`
- `docs/keil5-notes.md`

附加要求：
1. `main.c` 需要包含 `main()`、系统初始化流程、外设初始化调用、主循环框架。
2. `docs/wiring.md` 需要写明引脚连接、供电、通信接口、注意事项。
3. `docs/keil5-notes.md` 需要告诉用户如何导入、如何补全启动文件、如何在 Keil5 中继续。
4. 如果用户要求“可直接烧录”，你可以生成尽可能完整的程序骨架，但若缺少实际板级信息、晶振参数、传感器具体型号，必须在 warnings 中说明仍需人工确认。
""".strip()
    else:
        extra = """
当前模式：config_only

目标：只生成配置文件和说明文件，让用户下一步能在 CubeMX / Keil5 中继续开发。

至少必须生成这些文件：
- `<project>.ioc`
- `Core/Inc/ai_board_config.h`
- `Core/Src/ai_board_config.c`
- `docs/generated-notes.md`

附加要求：
1. `.ioc` 要体现时钟树、GPIO、关键外设和调试接口配置意图。
2. `generated-notes.md` 需要说明下一步如何在 CubeMX / Keil5 中继续操作。
3. 该模式不要伪造完整固件工程，只输出配置导向的结果。
""".strip()

    return f"{common}\n\n{extra}"


def _build_user_prompt(
    project_name: str,
    target_mcu: str,
    user_spec: str,
    selected_skills: list[Skill],
    generation_mode: str,
) -> str:
    skill_block = "\n\n".join(
        f"[技能] {skill.name}\n说明: {skill.description}\n指令:\n{skill.instruction}"
        for skill in selected_skills
    )
    if not skill_block:
        skill_block = "无额外技能。"

    return f"""
项目名: {project_name}
目标 MCU: {target_mcu or '未指定，需模型自行假设并写入 assumptions'}
生成模式: {generation_mode}

用户需求：
{user_spec}

可用技能：
{skill_block}

请严格按指定 JSON 返回。
""".strip()


def _to_generation_result(payload: dict[str, Any]) -> GenerationResult:
    files: list[GeneratedFile] = []
    for item in payload.get("files", []):
        files.append(
            GeneratedFile(
                path=str(item.get("path", "output.txt")),
                purpose=str(item.get("purpose", "generated file")),
                content=str(item.get("content", "")),
            )
        )

    return GenerationResult(
        project_name=str(payload.get("project_name", "stm32_ai_project")),
        target_mcu=str(payload.get("target_mcu", "UNKNOWN_MCU")),
        summary=str(payload.get("summary", "")),
        generation_mode=_normalize_mode(str(payload.get("generation_mode", CONFIG_ONLY))),
        assumptions=[str(item) for item in payload.get("assumptions", [])],
        warnings=[str(item) for item in payload.get("warnings", [])],
        selected_skills=[str(item) for item in payload.get("selected_skills", [])],
        files=files,
    )


def _normalize_mode(mode: str) -> str:
    return FIRMWARE_FULL if mode == FIRMWARE_FULL else CONFIG_ONLY
