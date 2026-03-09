from __future__ import annotations

from pathlib import Path

from stm32_agent.models import Skill


def load_skills(skills_dir: Path) -> list[Skill]:
    skills: list[Skill] = []
    for path in sorted(skills_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        skills.append(_parse_skill(path, text))
    return skills


def select_skills(user_text: str, skills: list[Skill]) -> list[Skill]:
    lowered = user_text.lower()
    selected: list[Skill] = []

    for skill in skills:
        if skill.always_on:
            selected.append(skill)
            continue

        if any(keyword.lower() in lowered for keyword in skill.keywords):
            selected.append(skill)

    if not selected:
        selected = [skill for skill in skills if skill.always_on] or skills[:2]

    seen: set[str] = set()
    unique_selected: list[Skill] = []
    for skill in selected:
        if skill.name not in seen:
            unique_selected.append(skill)
            seen.add(skill.name)
    return unique_selected


def _parse_skill(path: Path, text: str) -> Skill:
    header, instruction = _split_header(text)
    meta: dict[str, str] = {}
    for line in header.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        meta[key.strip().lower()] = value.strip()

    name = meta.get("name", path.stem)
    description = meta.get("description", "")
    keywords = [item.strip() for item in meta.get("keywords", "").split(",") if item.strip()]
    always_on = meta.get("always_on", "false").lower() == "true"

    return Skill(
        name=name,
        description=description,
        keywords=keywords,
        instruction=instruction.strip(),
        always_on=always_on,
    )


def _split_header(text: str) -> tuple[str, str]:
    marker = "---\n"
    if text.startswith(marker):
        end = text.find(marker, len(marker))
        if end != -1:
            return text[len(marker):end], text[end + len(marker):]
    return "", text
