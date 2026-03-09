<div align="center">

# 🤖 AI MCU Codegen

**AI-powered desktop tool that generates MCU project files from natural language.**

Currently supports **STM32** (CubeMX + HAL + Keil5), with more platforms coming soon.

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/jichaowang02-lang/ai-mcu-codegen)

</div>

---

## 📖 简介

AI MCU Codegen 是一个本地桌面应用，通过自然语言描述硬件需求，调用大语言模型（兼容 OpenAI Chat Completions API），**自动生成面向嵌入式开发的工程配置和代码骨架**。

你只需要用一句话描述你想做什么，工具就会为你生成 `.ioc` 配置文件、HAL 初始化代码、接线方案和开发说明文档——开箱即可在 CubeMX / Keil5 中继续开发。

### ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🗣️ **自然语言输入** | 用中文或英文描述你的硬件需求 |
| 🔀 **双模式生成** | `config_only` 仅生成配置 / `firmware_full` 生成完整固件骨架 |
| 🧠 **智能技能系统** | 自动匹配时钟规划、外设映射、HAL 配置等专业技能 |
| ✅ **自动结果查验** | 生成后自动对结果进行完整性分析，给出评分和改进建议 |
| 🖥️ **桌面 GUI** | 基于 PySide6 的图形界面，可视化进度、日志、结果标签页 |
| ⌨️ **CLI 支持** | 命令行批处理，适合集成到自动化流程 |
| 🔌 **模型可切换** | 兼容任何 OpenAI API 格式的模型服务 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    用户界面层                          │
│           ┌──────────┐    ┌──────────┐               │
│           │  GUI      │    │  CLI     │               │
│           │ (gui.py)  │    │ (cli.py) │               │
│           └─────┬─────┘    └────┬─────┘               │
│                 └───────┬───────┘                      │
├─────────────────────────┼──────────────────────────────┤
│                    服务层 │                              │
│              ┌──────────┴──────────┐                   │
│              │   service.py         │                   │
│              │  (编排 + 结果查验)    │                    │
│              └──────────┬──────────┘                   │
├─────────────────────────┼──────────────────────────────┤
│                    核心层 │                              │
│     ┌───────────────────┼───────────────────┐          │
│     │                   │                   │          │
│ ┌───┴────────┐  ┌───────┴───────┐  ┌───────┴───────┐  │
│ │ skills.py  │  │ generator.py  │  │ llm_client.py │  │
│ │ 技能加载    │  │ Prompt 构建   │  │ API 通信       │  │
│ │ + 匹配      │  │ + 结果解析    │  │ + JSON 提取    │  │
│ └────────────┘  └───────────────┘  └───────────────┘  │
├────────────────────────────────────────────────────────┤
│                    数据层                               │
│  ┌────────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │ models.py  │  │ config.py │  │ skills/*.md      │  │
│  │ 数据结构    │  │ 配置管理   │  │ 技能模板文件       │  │
│  └────────────┘  └───────────┘  └──────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## 🔀 两种生成模式

### 模式一：`config_only` — 仅生成配置

适合你后续自己在 CubeMX / Keil5 中继续搭建工程。

**输出文件：**

| 文件 | 说明 |
|------|------|
| `<project>.ioc` | STM32CubeMX 配置草稿 |
| `Core/Inc/ai_board_config.h` | 面向应用层的配置摘要头文件 |
| `Core/Src/ai_board_config.c` | 配置实现源文件 |
| `docs/generated-notes.md` | 后续操作说明和注意事项 |

### 模式二：`firmware_full` — 生成完整固件骨架

让 AI 直接生成可在 Keil5 中继续开发的程序框架，并附带接线方案。

**输出文件：**

| 文件 | 说明 |
|------|------|
| `<project>.ioc` | STM32CubeMX 配置草稿 |
| `Core/Inc/main.h` | 主程序头文件 |
| `Core/Src/main.c` | 包含 `main()`、系统初始化、外设初始化、主循环框架 |
| `Core/Inc/ai_board_config.h` | 板级配置头文件 |
| `Core/Src/ai_board_config.c` | 板级配置实现 |
| `docs/wiring.md` | 接线方案（引脚连接、供电、通信接口） |
| `docs/keil5-notes.md` | Keil5 导入和后续开发指南 |

> **注意：** 若未提供板级晶振频率、外设型号等细节，AI 会在结果中明确标注"假设"和"风险提醒"。

---

## 🧠 技能系统

技能系统通过 `skills/` 目录下的 Markdown 文件定义，AI 会根据用户需求自动匹配并激活相关技能。

| 技能 | 类型 | 功能 |
|------|------|------|
| **hal-conf** | 🟢 始终启用 | HAL 模块启用建议、驱动依赖分析 |
| **ioc-writer** | 🟢 始终启用 | 组织 `.ioc` 文件结构和最终输出 |
| **clock-planning** | 🔵 按需激活 | 时钟树推导（PLL、SYSCLK、HCLK、PCLK） |
| **peripheral-mapping** | 🔵 按需激活 | 外设引脚复用方案和 GPIO 映射 |

你也可以自定义技能：在 `skills/` 目录下创建新的 `.md` 文件即可，格式参考已有技能模板。

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 一个兼容 OpenAI Chat Completions API 的模型服务 + API Key

### 安装

```bash
git clone https://github.com/jichaowang02-lang/ai-mcu-codegen.git
cd ai-mcu-codegen
pip install -r requirements.txt
```

### 配置

复制环境变量模板并填入你的 API Key：

```bash
cp .env.example .env
```

`.env` 文件内容：

```ini
STM32_AGENT_API_KEY=your_api_key_here       # 必填
STM32_AGENT_BASE_URL=https://your-api.com/v1  # 可选，有默认值
STM32_AGENT_MODEL=gpt-5.3-codex              # 可选，有默认值
STM32_AGENT_OUTPUT_DIR=generated              # 可选，输出目录
STM32_AGENT_TIMEOUT=120                       # 可选，请求超时(秒)
```

---

## 💻 使用方式

### 图形界面（推荐）

```bash
python main.py
```

界面功能：
- 📊 顶部固定进度条，实时显示生成状态
- 📝 左侧滚动表单，支持需求输入、MCU 选择、模式切换
- 🔽 内置常用 MCU 下拉列表，支持自定义添加
- 📑 右侧多标签页：结果摘要、结果查验、运行日志、技能总览

### 命令行

```bash
# 基础用法
python main.py generate --spec "你的需求描述"

# 完整参数示例
python main.py generate ^
  --project smart_lock ^
  --mcu STM32F103C8T6 ^
  --mode firmware_full ^
  --spec "使用 USART1 输出调试信息，I2C1 驱动 OLED，PA0 按键输入，PC13 LED，SYSCLK 72MHz，并生成接线方案。"

# 查看可用技能
python main.py skills
```

**CLI 参数说明：**

| 参数 | 是否必填 | 说明 |
|------|---------|------|
| `--spec` | ✅ | 自然语言需求描述 |
| `--project` | ❌ | 项目名（默认 `stm32_ai_project`） |
| `--mcu` | ❌ | 目标 MCU 型号 |
| `--mode` | ❌ | `config_only`（默认）或 `firmware_full` |
| `--api-key` | ❌ | LLM API Key（也可通过环境变量） |
| `--base-url` | ❌ | LLM 服务地址 |
| `--model` | ❌ | 模型名称 |
| `--out` | ❌ | 输出目录 |
| `--timeout` | ❌ | 请求超时时间（秒） |

---

## ✅ 自动结果查验

每次生成完成后，工具会自动执行多维度质量评估：

| 检查项 | 说明 |
|--------|------|
| 文件完整性 | 检查必需文件是否全部生成 |
| 磁盘写入 | 验证文件是否成功写入磁盘 |
| `.ioc` 质量 | 检查 MCU 信息、RCC/GPIO/ProjectManager 等基础配置 |
| `main.c` 结构 | 验证主函数和主循环是否完整（firmware_full 模式） |
| 文档生成 | 检查接线方案、Keil5 说明等文档是否齐全 |
| 假设与风险 | 汇总模型做出的假设和风险提醒 |

评估结果为 **0-100 分**：
- **≥ 85 分**：结果完整，可直接用于后续开发
- **65-84 分**：基本可用，建议核对关键参数
- **< 65 分**：存在明显缺项，建议修改需求重新生成

---

## 📁 项目结构

```
ai-mcu-codegen/
├── main.py                 # 应用入口
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── skills/                 # 技能模板目录
│   ├── clock-planning.md   #   时钟规划技能
│   ├── hal-conf.md         #   HAL 配置技能（始终启用）
│   ├── ioc-writer.md       #   IOC 文件生成技能（始终启用）
│   └── peripheral-mapping.md #  外设映射技能
└── stm32_agent/            # 核心代码包
    ├── __init__.py          #   版本信息 (v0.1.0)
    ├── cli.py               #   命令行接口
    ├── config.py            #   配置管理（环境变量 + 参数）
    ├── generator.py         #   Prompt 构建 + 代码生成 + 结果解析
    ├── gui.py               #   PySide6 图形界面
    ├── llm_client.py        #   LLM API 客户端（兼容 OpenAI 格式）
    ├── models.py            #   数据模型定义
    ├── service.py           #   服务编排 + 结果查验引擎
    └── skills.py            #   技能加载 + 智能匹配
```

---

## 🗺️ Roadmap

- [x] STM32 (CubeMX + HAL + Keil5) 支持
- [x] 双模式生成（config_only / firmware_full）
- [x] 智能技能系统
- [x] 自动结果查验
- [ ] ESP32 (ESP-IDF / Arduino) 支持
- [ ] Arduino 平台支持
- [ ] RISC-V (CH32V) 支持
- [ ] 多轮对话式生成
- [ ] 本地模型支持（Ollama 等）
- [ ] 生成结果历史管理

---

## 🤝 Contributing

欢迎提交 Issue 和 Pull Request！

---

## 📄 License

本项目采用 [MIT License](LICENSE) 开源。
