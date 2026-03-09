from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Skill:
    name: str
    description: str
    keywords: list[str]
    instruction: str
    always_on: bool = False


@dataclass(slots=True)
class GeneratedFile:
    path: str
    purpose: str
    content: str


@dataclass(slots=True)
class GenerationResult:
    project_name: str
    target_mcu: str
    summary: str
    generation_mode: str = "config_only"
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    selected_skills: list[str] = field(default_factory=list)
    files: list[GeneratedFile] = field(default_factory=list)
