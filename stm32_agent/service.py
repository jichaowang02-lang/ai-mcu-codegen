from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from stm32_agent.config import AppConfig
from stm32_agent.generator import (
    FIRMWARE_FULL,
    expected_outputs_for_mode,
    format_generation_mode,
    generate_files,
    save_result,
)
from stm32_agent.llm_client import LlmClient
from stm32_agent.models import GenerationResult, Skill
from stm32_agent.skills import load_skills, select_skills


@dataclass(slots=True)
class ValidationFinding:
    level: str
    message: str


@dataclass(slots=True)
class ValidationReport:
    score: int
    summary: str
    findings: list[ValidationFinding] = field(default_factory=list)


@dataclass(slots=True)
class GenerationRun:
    result: GenerationResult
    output_dir: Path
    manifest_path: Path
    selected_skills: list[Skill]
    validation_report: ValidationReport

    @property
    def selected_skill_names(self) -> list[str]:
        return [skill.name for skill in self.selected_skills]


ProgressCallback = Callable[[int, str], None]


def load_available_skills(skills_dir: Path) -> list[Skill]:
    return load_skills(skills_dir)


def run_generation(
    *,
    spec: str,
    project: str,
    mcu: str,
    generation_mode: str,
    api_key: str | None,
    base_url: str | None,
    model: str | None,
    output_dir: str | None,
    timeout: int | None,
    skills_dir: Path,
    progress_callback: ProgressCallback | None = None,
) -> GenerationRun:
    _emit_progress(progress_callback, 5, "正在读取配置…")
    config = AppConfig.from_env(
        api_key=api_key,
        base_url=base_url,
        model=model,
        output_root=output_dir,
        timeout_seconds=timeout,
    )

    _emit_progress(progress_callback, 15, "正在加载技能模板…")
    skills = load_skills(skills_dir)
    selected = select_skills(f"{spec}\n{mcu}\n{generation_mode}", skills)

    _emit_progress(progress_callback, 28, f"已选择 {len(selected)} 个技能，正在准备模型请求…")
    client = LlmClient(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        timeout_seconds=config.timeout_seconds,
    )

    _emit_progress(progress_callback, 55, f"正在调用模型生成内容（模式：{format_generation_mode(generation_mode)}）…")
    result = generate_files(
        client=client,
        project_name=project,
        target_mcu=mcu,
        user_spec=spec,
        selected_skills=selected,
        generation_mode=generation_mode,
    )

    _emit_progress(progress_callback, 78, "模型已返回结果，正在写入文件…")
    resolved_output_dir = Path(output_dir) if output_dir else config.output_root / project
    manifest_path = save_result(result, resolved_output_dir)

    _emit_progress(progress_callback, 90, "正在执行结果查验…")
    validation_report = validate_generation_run(result, resolved_output_dir)

    _emit_progress(progress_callback, 100, "生成完成，结果已准备好。")
    return GenerationRun(
        result=result,
        output_dir=resolved_output_dir,
        manifest_path=manifest_path,
        selected_skills=selected,
        validation_report=validation_report,
    )


def validate_generation_run(result: GenerationResult, output_dir: Path) -> ValidationReport:
    findings: list[ValidationFinding] = []
    score = 100

    required_paths = expected_outputs_for_mode(result.project_name, result.generation_mode)
    declared_paths = {item.path for item in result.files}

    for path in required_paths:
        if path in declared_paths:
            findings.append(ValidationFinding("pass", f"已生成必需文件：{path}"))
        else:
            findings.append(ValidationFinding("error", f"缺少必需文件：{path}"))
            score -= 15

    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        findings.append(ValidationFinding("pass", "已写出 manifest.json。"))
    else:
        findings.append(ValidationFinding("error", "未找到 manifest.json。"))
        score -= 15

    for item in result.files:
        file_path = output_dir / item.path
        if file_path.exists():
            findings.append(ValidationFinding("pass", f"文件已落盘：{item.path}"))
        else:
            findings.append(ValidationFinding("error", f"文件未成功写入磁盘：{item.path}"))
            score -= 12

    ioc_file = next((item for item in result.files if item.path.endswith(".ioc")), None)
    if ioc_file is None:
        findings.append(ValidationFinding("error", "未生成 `.ioc` 文件。"))
        score -= 20
    else:
        if result.target_mcu and result.target_mcu in ioc_file.content:
            findings.append(ValidationFinding("pass", "`.ioc` 中包含目标 MCU 信息。"))
        else:
            findings.append(ValidationFinding("warning", "`.ioc` 中未明显包含目标 MCU，需要人工核对。"))
            score -= 8

        token_hits = sum(token in ioc_file.content for token in ["RCC", "GPIO", "ProjectManager"])
        if token_hits >= 2:
            findings.append(ValidationFinding("pass", "`.ioc` 中包含基础配置片段。"))
        else:
            findings.append(ValidationFinding("warning", "`.ioc` 内容较弱，建议在 CubeMX 中再次检查。"))
            score -= 10

    if result.generation_mode == FIRMWARE_FULL:
        main_file = next((item for item in result.files if item.path == "Core/Src/main.c"), None)
        if main_file and "main(" in main_file.content and ("while (1)" in main_file.content or "while(1)" in main_file.content):
            findings.append(ValidationFinding("pass", "`main.c` 含有基本主循环结构。"))
        else:
            findings.append(ValidationFinding("warning", "`main.c` 可能不完整，建议在 Keil5 中补全验证。"))
            score -= 10

        if any(item.path == "docs/wiring.md" for item in result.files):
            findings.append(ValidationFinding("pass", "已生成接线方案文档。"))
        else:
            findings.append(ValidationFinding("error", "未生成接线方案文档。"))
            score -= 15

        if any(item.path == "docs/keil5-notes.md" for item in result.files):
            findings.append(ValidationFinding("pass", "已生成 Keil5 使用说明。"))
        else:
            findings.append(ValidationFinding("error", "未生成 Keil5 使用说明。"))
            score -= 12
    else:
        if any(item.path == "docs/generated-notes.md" for item in result.files):
            findings.append(ValidationFinding("pass", "已生成后续操作说明文档。"))
        else:
            findings.append(ValidationFinding("error", "未生成后续操作说明文档。"))
            score -= 12

    if result.assumptions:
        findings.append(ValidationFinding("warning", f"模型做出了 {len(result.assumptions)} 条假设，请人工确认。"))
        score -= min(10, len(result.assumptions) * 2)
    else:
        findings.append(ValidationFinding("pass", "未声明额外假设。"))

    if result.warnings:
        findings.append(ValidationFinding("warning", f"模型给出 {len(result.warnings)} 条风险提醒。"))
        score -= min(12, len(result.warnings) * 2)
    else:
        findings.append(ValidationFinding("pass", "未发现模型主动提示的额外风险。"))

    score = max(0, min(100, score))
    if score >= 85:
        summary = "结果结构完整，可直接作为 Keil5 / CubeMX 后续开发起点。"
    elif score >= 65:
        summary = "结果基本可用，但建议先核对时钟、引脚和外设细节。"
    else:
        summary = "结果存在明显缺项，建议修改需求后重新生成。"

    return ValidationReport(score=score, summary=summary, findings=findings)


def _emit_progress(callback: ProgressCallback | None, percent: int, message: str) -> None:
    if callback is not None:
        callback(percent, message)
