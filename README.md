# STM32 Agent Studio

这是一个本地运行的桌面软件：你输入自然语言需求，它调用兼容 OpenAI Chat Completions 的模型，自动生成面向 `STM32CubeMX + HAL + Keil5` 的结果文件。

界面基于 `PySide6`，支持可视化进度、运行日志、结果查验、常用 MCU 选择与自定义添加。

## 两种生成模式

### 1. `config_only`
只生成配置导向文件，适合你后续自己继续在 CubeMX / Keil5 中补工程。

输出至少包括：
- `<project>.ioc`
- `Core/Inc/ai_board_config.h`
- `Core/Src/ai_board_config.c`
- `docs/generated-notes.md`

### 2. `firmware_full`
让 AI 直接生成更完整的程序骨架，并额外给出接线方案，方便你下一步直接在 Keil5 中继续开发。

输出至少包括：
- `<project>.ioc`
- `Core/Inc/main.h`
- `Core/Src/main.c`
- `Core/Inc/ai_board_config.h`
- `Core/Src/ai_board_config.c`
- `docs/wiring.md`
- `docs/keil5-notes.md`

说明：
- 该模式会尽量生成可继续编译和烧录前准备的程序框架。
- 但若你没有提供板级晶振、外设型号、驱动细节，AI 仍会把不确定项写进“假设”和“风险提醒”。

## 默认模型配置

- `Base URL`: `https://newapi.sansun.eu.cc/v1`
- `Model`: `gpt-5.3-codex`

程序不会把 API Key 写死在代码中，你可以在界面里输入，或通过环境变量提供。

## 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 启动图形界面

```powershell
python main.py
```

## 命令行用法

```powershell
python main.py generate ^
  --project smart_lock ^
  --mcu STM32F103C8T6 ^
  --mode firmware_full ^
  --spec "使用 USART1 输出调试信息，I2C1 驱动 OLED，PA0 按键输入，PC13 LED，SYSCLK 72MHz，并生成接线方案。"
```

## 界面功能

- 顶部固定进度条，能看到是否正在工作
- 左侧滚动表单，短屏幕也能完整操作
- 常用 MCU 下拉选择，也可自行输入后加入列表
- 右侧标签页查看结果摘要、结果查验、运行日志、技能总览
- 自动执行结果查验，提示缺失文件和潜在风险
