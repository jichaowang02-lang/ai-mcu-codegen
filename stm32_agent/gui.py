from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from stm32_agent.config import DEFAULT_BASE_URL, DEFAULT_MODEL
from stm32_agent.generator import CONFIG_ONLY, FIRMWARE_FULL, format_generation_mode
from stm32_agent.service import GenerationRun, load_available_skills, run_generation

WINDOW_BG = "#eef3f8"
PANEL_BG = "rgba(255, 255, 255, 0.82)"
PANEL_STRONG = "rgba(255, 255, 255, 0.94)"
BORDER = "rgba(255, 255, 255, 0.60)"
TEXT = "#16202a"
TEXT_SOFT = "#617085"
ACCENT = "#0a84ff"
SUCCESS = "#30b95f"
ERROR = "#ff453a"

COMMON_MCUS = [
    "STM32F103C8T6",
    "STM32F103RCT6",
    "STM32F401CCU6",
    "STM32F411CEU6",
    "STM32F407VGT6",
    "STM32G030F6P6",
    "STM32G031K8U6",
    "STM32G431CBU6",
    "STM32L031K6T6",
    "STM32L432KCU6",
    "STM32H743VIT6",
]


def _app_stylesheet() -> str:
    return f"""
    QMainWindow {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #f6f8fc, stop:0.45 #eef3f8, stop:1 #e6edf6);
    }}
    QWidget {{
        color: {TEXT};
        font-family: 'SF Pro Text', 'Segoe UI', 'Microsoft YaHei UI';
        font-size: 10pt;
        background: transparent;
    }}
    #GlassCard {{
        background: {PANEL_BG};
        border: 1px solid {BORDER};
        border-radius: 24px;
    }}
    #GlassCardStrong {{
        background: {PANEL_STRONG};
        border: 1px solid {BORDER};
        border-radius: 24px;
    }}
    #MetricCard {{
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(255, 255, 255, 0.62);
        border-radius: 18px;
    }}
    #TitleLabel {{
        font-size: 20pt;
        font-weight: 700;
    }}
    #SubtitleLabel {{
        color: {TEXT_SOFT};
        font-size: 10pt;
    }}
    #SectionTitle {{
        font-size: 11pt;
        font-weight: 650;
    }}
    #HintLabel {{
        color: {TEXT_SOFT};
        font-size: 9pt;
    }}
    #BadgeLabel {{
        background: rgba(10, 132, 255, 0.12);
        color: {ACCENT};
        border: 1px solid rgba(10, 132, 255, 0.16);
        border-radius: 13px;
        padding: 7px 12px;
        font-weight: 650;
    }}
    #MetricValue {{
        font-size: 16pt;
        font-weight: 700;
    }}
    #MetricCaption {{
        color: {TEXT_SOFT};
        font-size: 9pt;
    }}
    QLineEdit, QPlainTextEdit, QComboBox {{
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(180, 196, 214, 0.95);
        border-radius: 14px;
        padding: 10px 12px;
        selection-background-color: {ACCENT};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {ACCENT};
    }}
    QPlainTextEdit {{
        padding: 12px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QPushButton {{
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(190, 204, 220, 0.95);
        border-radius: 14px;
        padding: 10px 14px;
        font-weight: 650;
    }}
    QPushButton:hover {{
        background: rgba(255, 255, 255, 0.98);
    }}
    QPushButton:disabled {{
        color: #95a2b3;
        background: rgba(245, 247, 250, 0.85);
    }}
    #PrimaryButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #0a84ff, stop:1 #62b3ff);
        color: white;
        border: 1px solid rgba(10, 132, 255, 0.35);
    }}
    #PrimaryButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #0b7cf1, stop:1 #4fa8ff);
    }}
    QTabWidget::pane {{
        border: none;
        background: transparent;
    }}
    QTabBar::tab {{
        background: rgba(255, 255, 255, 0.55);
        border: 1px solid rgba(190, 204, 220, 0.88);
        border-radius: 12px;
        padding: 8px 14px;
        margin-right: 8px;
    }}
    QTabBar::tab:selected {{
        background: rgba(255, 255, 255, 0.95);
        color: {ACCENT};
    }}
    QProgressBar {{
        background: rgba(255, 255, 255, 0.75);
        border: 1px solid rgba(190, 204, 220, 0.95);
        border-radius: 10px;
        min-height: 12px;
    }}
    QProgressBar::chunk {{
        border-radius: 9px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #4fa8ff, stop:1 #0a84ff);
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QSplitter::handle {{
        background: transparent;
        width: 10px;
    }}
    """


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progressed = Signal(int, str)

    def __init__(
        self,
        *,
        spec: str,
        project: str,
        mcu: str,
        generation_mode: str,
        api_key: str,
        base_url: str,
        model: str,
        output_dir: str | None,
        timeout: int,
        skills_dir: Path,
    ) -> None:
        super().__init__()
        self.spec = spec
        self.project = project
        self.mcu = mcu
        self.generation_mode = generation_mode
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.output_dir = output_dir
        self.timeout = timeout
        self.skills_dir = skills_dir

    def run(self) -> None:
        try:
            result = run_generation(
                spec=self.spec,
                project=self.project,
                mcu=self.mcu,
                generation_mode=self.generation_mode,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                output_dir=self.output_dir,
                timeout=self.timeout,
                skills_dir=self.skills_dir,
                progress_callback=self.progressed.emit,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class AgentWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STM32 Agent Studio")
        self.resize(1380, 900)
        self.setMinimumSize(1180, 760)
        self.setStyleSheet(_app_stylesheet())

        self.skills_dir = Path("skills")
        self.current_output_dir: Path | None = None
        self.worker_thread: QThread | None = None
        self.worker: Worker | None = None

        self._build_ui()
        self._refresh_skills()
        self._append_log("欢迎使用 STM32 Agent Studio。")

    def _build_ui(self) -> None:
        shell = QWidget()
        root = QVBoxLayout(shell)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(16)
        self.setCentralWidget(shell)

        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([430, 880])
        root.addWidget(splitter, 1)

    def _build_header(self) -> QWidget:
        card = self._card(strong=True)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(6)

        title = QLabel("STM32 Agent Studio")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("把自然语言需求转成 CubeMX / HAL / Keil5 可继续开发的结果")
        subtitle.setObjectName("SubtitleLabel")
        self.hero_label = QLabel("准备就绪，填写需求后即可开始生成")
        self.hero_label.setObjectName("SectionTitle")

        left.addWidget(title)
        left.addWidget(subtitle)
        left.addSpacing(6)
        left.addWidget(self.hero_label)

        right = QVBoxLayout()
        right.setSpacing(10)

        status_row = QHBoxLayout()
        status_row.addStretch(1)
        self.status_badge = QLabel("待命")
        self.status_badge.setObjectName("BadgeLabel")
        status_row.addWidget(self.status_badge)

        self.header_progress = QProgressBar()
        self.header_progress.setRange(0, 100)
        self.header_progress.setValue(0)
        self.header_progress.setTextVisible(False)
        self.header_progress_label = QLabel("等待开始")
        self.header_progress_label.setObjectName("HintLabel")
        self.header_percent_label = QLabel("0%")
        self.header_percent_label.setObjectName("SectionTitle")

        progress_row = QHBoxLayout()
        progress_row.addWidget(self.header_progress_label, 1)
        progress_row.addWidget(self.header_percent_label)

        right.addLayout(status_row)
        right.addWidget(self.header_progress)
        right.addLayout(progress_row)

        layout.addLayout(left, 3)
        layout.addLayout(right, 2)
        return card

    def _build_left_panel(self) -> QWidget:
        card = self._card()
        outer = QVBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)
        outer.addWidget(scroll)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)
        layout.addWidget(self._build_metrics())
        layout.addWidget(self._build_connection_form())
        layout.addWidget(self._build_project_form())
        layout.addWidget(self._build_request_form())
        layout.addWidget(self._build_action_bar())
        layout.addStretch(1)
        return card

    def _build_right_panel(self) -> QWidget:
        card = self._card(strong=True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.tabs = QTabWidget()
        self.summary_text = self._output_text()
        self.review_text = self._output_text()
        self.log_text = self._output_text()
        self.skills_text = self._output_text()

        self.tabs.addTab(self.summary_text, "结果摘要")
        self.tabs.addTab(self.review_text, "结果查验")
        self.tabs.addTab(self.log_text, "运行日志")
        self.tabs.addTab(self.skills_text, "技能总览")
        layout.addWidget(self.tabs)
        return card

    def _build_metrics(self) -> QWidget:
        wrapper = QWidget()
        layout = QGridLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        self.skill_count_label = QLabel("0")
        self.mode_badge_label = QLabel(format_generation_mode(CONFIG_ONLY))
        self.file_count_label = QLabel("0")
        self.output_badge_label = QLabel("尚未生成")

        layout.addWidget(self._metric_card("技能库", self.skill_count_label, "当前可用技能数量"), 0, 0)
        layout.addWidget(self._metric_card("模式", self.mode_badge_label, "本次生成策略"), 0, 1)
        layout.addWidget(self._metric_card("文件数", self.file_count_label, "最近一次输出文件数"), 1, 0)
        layout.addWidget(self._metric_card("输出目录", self.output_badge_label, "最近一次结果位置"), 1, 1)
        return wrapper

    def _build_connection_form(self) -> QWidget:
        card = self._section_card("模型连接", "本地运行，调用你提供的兼容 API 服务")
        layout = card.layout()
        assert isinstance(layout, QVBoxLayout)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("输入 API Key，不会写入代码")
        self.base_url_edit = QLineEdit(DEFAULT_BASE_URL)
        self.model_edit = QLineEdit(DEFAULT_MODEL)
        self.timeout_edit = QLineEdit("120")

        layout.addWidget(self._field("API Key", self.api_key_edit))
        layout.addWidget(self._field("Base URL", self.base_url_edit))
        layout.addWidget(self._field("模型", self.model_edit))
        layout.addWidget(self._field("超时（秒）", self.timeout_edit))
        return card

    def _build_project_form(self) -> QWidget:
        card = self._section_card("工程设定", "选择 MCU、输出目录和生成模式")
        layout = card.layout()
        assert isinstance(layout, QVBoxLayout)

        self.project_edit = QLineEdit("stm32_ai_project")
        self.output_edit = QLineEdit("generated")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("仅生成配置文件", CONFIG_ONLY)
        self.mode_combo.addItem("生成可继续在 Keil5 开发的程序 + 接线方案", FIRMWARE_FULL)
        self.mode_combo.currentIndexChanged.connect(self._sync_mode_badge)

        self.mcu_edit = QComboBox()
        self.mcu_edit.setEditable(True)
        self.mcu_edit.addItems(COMMON_MCUS)
        self.mcu_edit.setCurrentText(COMMON_MCUS[0])

        browse_button = QPushButton("选择目录")
        browse_button.clicked.connect(self._choose_output_dir)
        add_mcu_button = QPushButton("加入常用 MCU")
        add_mcu_button.clicked.connect(self._add_current_mcu)

        output_row = QWidget()
        output_layout = QHBoxLayout(output_row)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.output_edit, 1)
        output_layout.addWidget(browse_button)

        mcu_row = QWidget()
        mcu_layout = QHBoxLayout(mcu_row)
        mcu_layout.setContentsMargins(0, 0, 0, 0)
        mcu_layout.addWidget(self.mcu_edit, 1)
        mcu_layout.addWidget(add_mcu_button)

        layout.addWidget(self._field("项目名", self.project_edit))
        layout.addWidget(self._field("生成模式", self.mode_combo))
        layout.addWidget(self._field("目标 MCU", mcu_row))
        layout.addWidget(self._field("输出根目录", output_row))
        return card

    def _build_request_form(self) -> QWidget:
        card = self._section_card("需求输入", "尽量写清楚时钟、外设、引脚、通信对象和目标功能")
        layout = card.layout()
        assert isinstance(layout, QVBoxLayout)

        self.spec_edit = QPlainTextEdit()
        self.spec_edit.setMinimumHeight(220)
        self.spec_edit.setPlaceholderText(
            "例：\n"
            "使用 STM32F103C8T6，SYSCLK 72MHz，PA9/PA10 做 USART1 调试输出，\n"
            "PB6/PB7 接 I2C OLED，PA0 按键输入，PC13 LED 指示。\n"
            "如果选择完整程序模式，希望生成主循环框架和接线方案。"
        )
        layout.addWidget(self.spec_edit)
        return card

    def _build_action_bar(self) -> QWidget:
        card = self._section_card("执行控制", "这里可以直接看到它有没有在工作")
        layout = card.layout()
        assert isinstance(layout, QVBoxLayout)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress_label = QLabel("等待开始")
        self.progress_label.setObjectName("HintLabel")
        self.progress_percent_label = QLabel("0%")
        self.progress_percent_label.setObjectName("SectionTitle")

        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress_label, 1)
        progress_row.addWidget(self.progress_percent_label)

        buttons = QHBoxLayout()
        self.generate_button = QPushButton("开始生成")
        self.generate_button.setObjectName("PrimaryButton")
        self.generate_button.clicked.connect(self._start_generation)

        refresh_button = QPushButton("刷新技能")
        refresh_button.clicked.connect(self._refresh_skills)
        open_button = QPushButton("打开输出目录")
        open_button.clicked.connect(self._open_output_dir)
        clear_button = QPushButton("清空日志")
        clear_button.clicked.connect(lambda: self.log_text.setPlainText(""))

        buttons.addWidget(self.generate_button, 2)
        buttons.addWidget(refresh_button)
        buttons.addWidget(open_button)
        buttons.addWidget(clear_button)

        layout.addWidget(self.progress)
        layout.addLayout(progress_row)
        layout.addLayout(buttons)
        return card

    def _field(self, title: str, widget: QWidget) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        label = QLabel(title)
        label.setObjectName("SectionTitle")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrapper

    def _metric_card(self, title: str, value_widget: QLabel, caption: str) -> QWidget:
        card = QFrame()
        card.setObjectName("MetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("MetricCaption")
        value_widget.setObjectName("MetricValue")
        value_widget.setWordWrap(True)
        caption_label = QLabel(caption)
        caption_label.setObjectName("MetricCaption")
        caption_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_widget)
        layout.addWidget(caption_label)
        return card

    def _section_card(self, title: str, hint: str) -> QWidget:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        hint_label = QLabel(hint)
        hint_label.setObjectName("HintLabel")
        hint_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(hint_label)
        return card

    def _card(self, *, strong: bool = False) -> QWidget:
        frame = QFrame()
        frame.setObjectName("GlassCardStrong" if strong else "GlassCard")
        return frame

    def _output_text(self) -> QPlainTextEdit:
        edit = QPlainTextEdit()
        edit.setReadOnly(True)
        edit.setFrameShape(QFrame.NoFrame)
        edit.setPlaceholderText("这里会显示结果内容")
        return edit

    def _refresh_skills(self) -> None:
        skills = load_available_skills(self.skills_dir)
        chunks: list[str] = []
        for skill in skills:
            suffix = " [always_on]" if skill.always_on else ""
            keywords = ", ".join(skill.keywords) if skill.keywords else "-"
            chunks.append(f"{skill.name}{suffix}\n说明：{skill.description}\n关键词：{keywords}")
        self.skill_count_label.setText(str(len(skills)))
        self.skills_text.setPlainText("\n\n".join(chunks) if chunks else "未找到技能文件。")
        self._append_log("技能列表已刷新。")

    def _sync_mode_badge(self) -> None:
        self.mode_badge_label.setText(format_generation_mode(self.current_generation_mode()))

    def _choose_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择输出根目录", self.output_edit.text() or str(Path.cwd()))
        if selected:
            self.output_edit.setText(selected)

    def _add_current_mcu(self) -> None:
        mcu = self.mcu_edit.currentText().strip()
        if not mcu:
            QMessageBox.information(self, "提示", "请先输入一个 MCU 型号。")
            return

        existing = {self.mcu_edit.itemText(index) for index in range(self.mcu_edit.count())}
        if mcu not in existing:
            self.mcu_edit.addItem(mcu)
            self._append_log(f"已加入常用 MCU：{mcu}")
        self.mcu_edit.setCurrentText(mcu)

    def current_generation_mode(self) -> str:
        return str(self.mode_combo.currentData())

    def _start_generation(self) -> None:
        spec = self.spec_edit.toPlainText().strip()
        if not spec:
            QMessageBox.warning(self, "缺少需求", "请先输入 STM32 需求描述。")
            return

        timeout_text = self.timeout_edit.text().strip() or "120"
        try:
            timeout = int(timeout_text)
        except ValueError:
            QMessageBox.warning(self, "超时配置错误", "超时时间必须是整数秒。")
            return

        project_name = self.project_edit.text().strip() or "stm32_ai_project"
        output_root = self.output_edit.text().strip()
        resolved_output_dir = str(Path(output_root).expanduser() / project_name) if output_root else None

        self.summary_text.clear()
        self.review_text.clear()
        self._set_busy(True)
        self._set_status("生成中", ACCENT)
        self._handle_progress(1, "任务已提交，正在启动后台工作线程…")
        self.hero_label.setText("正在分析需求、时钟与外设配置")
        self._append_log("开始生成配置文件。")

        self.worker_thread = QThread(self)
        self.worker = Worker(
            spec=spec,
            project=project_name,
            mcu=self.mcu_edit.currentText().strip(),
            generation_mode=self.current_generation_mode(),
            api_key=self.api_key_edit.text().strip(),
            base_url=self.base_url_edit.text().strip(),
            model=self.model_edit.text().strip() or DEFAULT_MODEL,
            output_dir=resolved_output_dir,
            timeout=timeout,
            skills_dir=self.skills_dir,
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progressed.connect(self._handle_progress)
        self.worker.finished.connect(self._handle_success)
        self.worker.failed.connect(self._handle_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._cleanup_worker)
        self.worker_thread.start()

    def _cleanup_worker(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
            self.worker_thread = None

    def _set_busy(self, busy: bool) -> None:
        self.generate_button.setDisabled(busy)
        self.mode_combo.setDisabled(busy)
        self.mcu_edit.setDisabled(busy)
        if not busy and self.progress.value() == 0:
            self.progress_label.setText("等待开始")
            self.header_progress_label.setText("等待开始")

    def _handle_progress(self, percent: int, message: str) -> None:
        percent = max(0, min(100, percent))
        self.progress.setValue(percent)
        self.header_progress.setValue(percent)
        self.progress_percent_label.setText(f"{percent}%")
        self.header_percent_label.setText(f"{percent}%")
        self.progress_label.setText(message)
        self.header_progress_label.setText(message)
        self.hero_label.setText(message)
        self._append_log(message)

    def _set_status(self, text: str, color: str) -> None:
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet(
            f"background: rgba(255,255,255,0.82); color: {color}; border: 1px solid rgba(255,255,255,0.62);"
            "border-radius: 13px; padding: 7px 12px; font-weight: 650;"
        )

    def _handle_success(self, run: object) -> None:
        assert isinstance(run, GenerationRun)
        self.current_output_dir = run.output_dir
        self._set_busy(False)
        self._set_status("已完成", SUCCESS)
        self.hero_label.setText("结果已经生成，右侧可查看摘要、查验和日志")
        self.file_count_label.setText(str(len(run.result.files)))
        self.output_badge_label.setText(str(run.output_dir))
        self.mode_badge_label.setText(format_generation_mode(run.result.generation_mode))
        self.summary_text.setPlainText(self._build_summary(run))
        self.review_text.setPlainText(self._build_validation_report(run))
        self.tabs.setCurrentWidget(self.summary_text)
        self._append_log(f"生成完成：{run.output_dir}")
        QMessageBox.information(self, "完成", f"结果已生成到：\n{run.output_dir}")

    def _handle_error(self, detail: str) -> None:
        self._set_busy(False)
        self._set_status("失败", ERROR)
        self.hero_label.setText("生成未完成，请检查 API 配置或需求描述")
        self._append_log(f"生成失败：{detail}")
        QMessageBox.critical(self, "生成失败", detail)

    def _open_output_dir(self) -> None:
        target = self.current_output_dir or Path(self.output_edit.text()).resolve()
        if not target.exists():
            QMessageBox.information(self, "提示", "输出目录暂时不存在，请先生成一次。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _build_summary(self, run: GenerationRun) -> str:
        lines = [
            f"项目名：{run.result.project_name}",
            f"MCU：{run.result.target_mcu}",
            f"生成模式：{format_generation_mode(run.result.generation_mode)}",
            f"输出目录：{run.output_dir}",
            f"Manifest：{run.manifest_path}",
            f"已选技能：{', '.join(run.selected_skill_names) if run.selected_skill_names else '-'}",
            "",
            "结果摘要：",
            run.result.summary or "-",
            "",
            "假设：",
        ]
        lines.extend(f"- {item}" for item in (run.result.assumptions or ["无"]))
        lines.extend(["", "风险提醒："])
        lines.extend(f"- {item}" for item in (run.result.warnings or ["无"]))
        lines.extend(["", "生成文件："])
        lines.extend(f"- {item.path}（{item.purpose}）" for item in run.result.files)
        return "\n".join(lines)

    def _build_validation_report(self, run: GenerationRun) -> str:
        report = run.validation_report
        level_labels = {
            "pass": "[通过]",
            "warning": "[注意]",
            "error": "[问题]",
        }
        lines = [
            f"查验得分：{report.score}/100",
            f"结论：{report.summary}",
            "",
            "检查项：",
        ]
        for item in report.findings:
            prefix = level_labels.get(item.level, "[信息]")
            lines.append(f"{prefix} {item.message}")
        return "\n".join(lines)

    def _append_log(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        current = self.log_text.toPlainText()
        separator = "" if not current else "\n"
        self.log_text.setPlainText(f"{current}{separator}[{timestamp}] {text}")
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def launch_gui() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = AgentWindow()
    window.show()
    return app.exec()
