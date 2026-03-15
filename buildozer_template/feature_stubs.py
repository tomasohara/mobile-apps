#! /usr/bin/env python
"""AI Mobile Lab — feature stub widgets for the ten on-device AI R&D demos.

Imported by main.py; call create_feature_tabs() to get the QTabWidget.

Features:
  1. Live Tokenizer           - real-time BPE-style token color-coding
  2. Local Chat Interface     - LLM chat UI with typewriter streaming
  3. Voice-to-Text Dashboard  - animated waveform + ASR simulation
  4. Confidence Gauges        - softmax probability progress-bar display
  5. Embedding Space Viewer   - 2-D scatter plot of word embeddings
  6. File-Based Summarizer    - file-picker + extractive summary
  7. Translation Camera       - AR-style overlay on a simulated camera feed
  8. Performance Heartbeat    - live CPU/NPU/RAM/Temp sparklines
  9. Multi-Modal Input Bar    - unified text + voice + image input
 10. Local Knowledge Vault    - keyword-RAG over an in-app document store
"""

import math
import os
import random
import re
import sys
import time

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QSize
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QTextCharFormat,
    QTextCursor, QLinearGradient,
)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSplitter, QTabWidget, QTextEdit, QVBoxLayout,
    QWidget,
)
from mezcla import debug, system

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
BG     = "#0f0f1a"
PANEL  = "#1a1a2e"
CARD   = "#16213e"
DEEP   = "#0f3460"
RED    = "#e94560"
GREEN  = "#4ade80"
BLUE   = "#38bdf8"
YELLOW = "#facc15"
PURPLE = "#a78bfa"
TEXT   = "#e2e8f0"
MUTED  = "#94a3b8"
TOKEN_COLORS = [RED, "#f97316", YELLOW, GREEN, BLUE, PURPLE, "#f472b6", "#34d399"]

# ---------------------------------------------------------------------------
# Static sample data
# ---------------------------------------------------------------------------
_RESPONSES = [
    "Inference complete. Identified 3 semantic clusters. Token embeddings align with the "
    "'technical' domain (cos-sim 0.91). NPU latency: 38 ms.",
    "Pipeline: tokenize → embed → classify → decode. Confidence: 94.2 %. "
    "Attention head #6 concentrated 73 % weight on the subject token.",
    "Context utilised: 47/512 tokens. Top-5 — ClassA: 82.1 %, ClassB: 11.3 %, "
    "ClassC: 4.7 %, ClassD: 1.5 %, ClassE: 0.4 %. Entropy: 0.62 bits.",
    "RAG retrieval found 2 relevant chunks (similarity > 0.80). Response grounded on "
    "local knowledge. No external API call. Total latency: 112 ms.",
    "Embedding dimension: 768. PCA projection to 2-D explains 61 % variance. "
    "Nearest neighbour: 'transformer' (L2 = 0.24).",
]
_TRANSCRIPTS = [
    "The transformer architecture uses self-attention to process tokens in parallel.",
    "On-device inference with INT8 quantization achieves 94% of FP32 accuracy.",
    "Retrieval-augmented generation grounds model outputs in local documents.",
    "Byte-pair encoding decomposes unknown words into known subword units.",
    "The NPU delivers 38 TOPS, enabling real-time 7-billion-parameter inference.",
]
_DOCUMENTS = [
    ("transformer_arch.txt",
     "Transformer models use self-attention to process tokens in parallel. "
     "Multi-head attention allows the model to attend to multiple representation "
     "subspaces simultaneously. Positional encodings give the model a sense of order."),
    ("quantization.txt",
     "INT8 quantization reduces model size 4× vs FP32 with under 1 % accuracy loss. "
     "Post-training quantization (PTQ) is simpler; quantization-aware training (QAT) "
     "yields better quality on edge cases."),
    ("mobile_inference.txt",
     "Modern smartphone NPUs deliver 30–40 TOPS, enabling real-time inference for "
     "7 B-parameter LLMs at 4-bit precision. ONNX Runtime Mobile and ExecuTorch are "
     "the dominant cross-platform on-device runtimes."),
    ("rag_pipeline.txt",
     "Retrieval-Augmented Generation indexes documents as dense embeddings via a "
     "bi-encoder. At query time, ANN search retrieves the top-k chunks, which are "
     "prepended to the prompt as grounding context."),
    ("bpe_tokenizer.txt",
     "Byte-Pair Encoding iteratively merges the most frequent byte pairs to build a "
     "subword vocabulary. A 32 k-token vocab covers 99.9 % of common words; unknown "
     "strings decompose gracefully into known subwords."),
]
_EMBED_POINTS = [
    ("neural net",      0.15, 0.20, BLUE),
    ("deep learning",   0.20, 0.16, BLUE),
    ("transformer",     0.25, 0.26, BLUE),
    ("attention",       0.18, 0.30, BLUE),
    ("tokenizer",       0.30, 0.62, PURPLE),
    ("vocabulary",      0.35, 0.60, PURPLE),
    ("BPE merge",       0.28, 0.68, PURPLE),
    ("backprop",        0.65, 0.14, GREEN),
    ("optimizer",       0.60, 0.22, GREEN),
    ("gradient",        0.70, 0.18, GREEN),
    ("inference",       0.72, 0.52, RED),
    ("latency",         0.78, 0.58, RED),
    ("quantize",        0.68, 0.64, RED),
    ("mobile AI",       0.75, 0.46, YELLOW),
    ("on-device",       0.80, 0.44, YELLOW),
]
_CAMERA_TEXTS = [
    ("MENU",    0.10, 0.10, "MENÚ"),
    ("OPEN",    0.55, 0.08, "ABIERTO"),
    ("WELCOME", 0.20, 0.40, "BIENVENIDO"),
    ("EXIT",    0.65, 0.70, "SALIDA"),
    ("PRICE",   0.30, 0.75, "PRECIO"),
]

# ---------------------------------------------------------------------------
# Global stylesheet
# ---------------------------------------------------------------------------
APP_STYLE = f"""
QWidget            {{ background-color:{BG}; color:{TEXT}; font-size:13px; }}
QTabWidget::pane   {{ border:1px solid {PANEL}; background:{PANEL}; }}
QTabBar::tab       {{ background:{CARD}; color:{MUTED}; padding:8px 10px;
                      border:none; min-width:55px; }}
QTabBar::tab:selected {{ background:{DEEP}; color:{RED}; font-weight:bold; }}
QLineEdit, QTextEdit {{ background:{CARD}; color:{TEXT};
                        border:1px solid {DEEP}; border-radius:6px; padding:6px; }}
QPushButton        {{ background:{RED}; color:white; border:none;
                      border-radius:6px; padding:8px 14px; font-weight:bold; }}
QPushButton:hover  {{ background:#c73652; }}
QPushButton:disabled {{ background:#3a3a4a; color:{MUTED}; }}
QPushButton#alt    {{ background:{DEEP}; }}
QPushButton#alt:hover {{ background:#1a4a80; }}
QPushButton#ok     {{ background:#16a34a; }}
QPushButton#ok:hover  {{ background:#15803d; }}
QProgressBar       {{ background:{CARD}; border:1px solid {DEEP};
                      border-radius:4px; height:22px; text-align:center; color:{TEXT}; }}
QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {RED},stop:1 {BLUE}); border-radius:3px; }}
QListWidget        {{ background:{CARD}; border:1px solid {DEEP}; border-radius:6px; }}
QListWidget::item  {{ padding:6px; }}
QListWidget::item:selected {{ background:{DEEP}; color:{BLUE}; }}
QScrollBar:vertical {{ background:{CARD}; width:8px; border-radius:4px; }}
QScrollBar::handle:vertical {{ background:{DEEP}; border-radius:4px; min-height:20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QComboBox          {{ background:{CARD}; color:{TEXT}; border:1px solid {DEEP};
                      border-radius:6px; padding:6px; }}
QComboBox::drop-down {{ border:none; }}
"""

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _title(text, color=RED):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{color}; font-size:15px; font-weight:bold; padding:2px 0;")
    return lbl


def _hint(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{MUTED}; font-size:11px;")
    lbl.setWordWrap(True)
    return lbl


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"background:{DEEP}; max-height:1px; margin:4px 0;")
    return f


# ===========================================================================
# Feature 1 — Live Tokenizer
# ===========================================================================
class TokenizerWidget(QWidget):
    """Colour-codes words as they are converted into BPE-style sub-tokens."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_title("⚡  Live Tokenizer"))
        layout.addWidget(_hint(
            "Type below — text is tokenised in real time using a simulated "
            "BPE vocabulary.  Long words are split into sub-word units (## prefix)."))
        layout.addWidget(_sep())

        self._input = QTextEdit()
        self._input.setPlaceholderText("Enter text to tokenise…")
        self._input.setMaximumHeight(90)
        self._input.textChanged.connect(self._schedule)
        layout.addWidget(self._input)

        stat_row = QHBoxLayout()
        self._lbl_count = QLabel("Tokens: 0")
        self._lbl_count.setStyleSheet(f"color:{BLUE};")
        self._lbl_speed = QLabel("Speed: —")
        self._lbl_speed.setStyleSheet(f"color:{GREEN};")
        self._lbl_unique = QLabel("Unique: 0")
        self._lbl_unique.setStyleSheet(f"color:{YELLOW};")
        for w in (self._lbl_count, self._lbl_speed, self._lbl_unique):
            stat_row.addWidget(w)
        stat_row.addStretch()
        layout.addLayout(stat_row)

        layout.addWidget(QLabel("Token visualisation:"))
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            f"background:{PANEL}; font-family:monospace; font-size:13px;")
        layout.addWidget(self._output)

        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._tokenise)
        self._t0 = 0.0

    def _schedule(self):
        self._t0 = time.time()
        self._timer.start(60)

    def _tokenise(self):
        text = self._input.toPlainText()
        if not text.strip():
            self._output.clear()
            self._lbl_count.setText("Tokens: 0")
            self._lbl_speed.setText("Speed: —")
            self._lbl_unique.setText("Unique: 0")
            return

        words = re.findall(r"[\w']+|[^\w\s]", text)
        tokens = []
        for w in words:
            if len(w) > 7 and w.isalpha():
                cut = random.randint(3, len(w) - 2)
                tokens += [w[:cut], "##" + w[cut:]]
            elif len(w) > 4 and w.isalpha() and random.random() < 0.3:
                cut = random.randint(2, len(w) - 1)
                tokens += [w[:cut], "##" + w[cut:]]
            else:
                tokens.append(w)

        elapsed_ms = (time.time() - self._t0) * 1000
        tok_per_sec = len(tokens) / max(elapsed_ms / 1000, 1e-4)
        unique = len(set(tokens))

        self._lbl_count.setText(f"Tokens: {len(tokens)}")
        self._lbl_speed.setText(f"Speed: {elapsed_ms:.1f} ms  |  {tok_per_sec:.0f} tok/s")
        self._lbl_unique.setText(f"Unique: {unique}")

        html_parts = []
        for i, tok in enumerate(tokens):
            col = TOKEN_COLORS[i % len(TOKEN_COLORS)]
            bg = col + "33"
            weight = "normal" if tok.startswith("##") else "bold"
            label = tok.replace("&", "&amp;").replace("<", "&lt;")
            html_parts.append(
                f'<span style="background:{bg}; color:{col}; '
                f'font-weight:{weight}; border-radius:3px; padding:1px 3px;">'
                f'{label}</span> ')

        ids = [random.randint(100, 50000) for _ in tokens]
        id_str = str(ids).replace("&", "&amp;")
        html = "".join(html_parts) + f"<br><br><span style='color:{MUTED};'>IDs: {id_str}</span>"
        self._output.setHtml(html)


# ===========================================================================
# Feature 2 — Local Chat Interface
# ===========================================================================
class ChatWidget(QWidget):
    """Simulated on-device LLM chat with typewriter streaming."""

    _USER_CSS = f"background:{DEEP}; border-radius:10px 10px 2px 10px; padding:8px 12px; color:{TEXT};"
    _AI_CSS   = f"background:{CARD}; border-radius:10px 10px 10px 2px; padding:8px 12px; color:{TEXT};"
    _TYPING   = "▋"

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_title("💬  Local Chat Interface"))
        layout.addWidget(_hint(
            "On-device LLM inference simulation.  Responses stream with a "
            "typewriter effect as if generated token-by-token."))
        layout.addWidget(_sep())

        self._chat = QTextEdit()
        self._chat.setReadOnly(True)
        self._chat.setStyleSheet(f"background:{PANEL}; border:1px solid {DEEP};")
        layout.addWidget(self._chat, stretch=1)

        row = QHBoxLayout()
        self._entry = QLineEdit()
        self._entry.setPlaceholderText("Ask the model something…")
        self._entry.returnPressed.connect(self._send)
        row.addWidget(self._entry, stretch=1)
        self._send_btn = QPushButton("Send ↑")
        self._send_btn.clicked.connect(self._send)
        row.addWidget(self._send_btn)
        layout.addLayout(row)

        self._messages: list[tuple[str, str]] = []   # (role, text)
        self._typing_text = ""
        self._typing_target = ""
        self._typing_timer = QTimer()
        self._typing_timer.timeout.connect(self._type_tick)

        self._add_message("ai", "Hello! I'm running locally on-device. "
                          "No cloud required — ask me anything.")

    # ------------------------------------------------------------------
    def _add_message(self, role: str, text: str):
        self._messages.append((role, text))
        self._render()

    def _render(self, extra_ai: str = ""):
        parts = []
        for role, text in self._messages:
            css = self._AI_CSS if role == "ai" else self._USER_CSS
            align = "left" if role == "ai" else "right"
            icon = "🤖" if role == "ai" else "🧑"
            parts.append(
                f'<div style="text-align:{align}; margin:6px 0;">'
                f'<span style="{css}">{icon} {text}</span></div>')
        if extra_ai:
            parts.append(
                f'<div style="text-align:left; margin:6px 0;">'
                f'<span style="{self._AI_CSS}">🤖 {extra_ai}{self._TYPING}</span></div>')
        self._chat.setHtml("".join(parts))
        self._chat.verticalScrollBar().setValue(
            self._chat.verticalScrollBar().maximum())

    def _send(self):
        text = self._entry.text().strip()
        if not text or self._typing_timer.isActive():
            return
        self._entry.clear()
        self._send_btn.setEnabled(False)
        self._add_message("user", text)
        # Simulate inference latency before streaming begins
        response = random.choice(_RESPONSES)
        QTimer.singleShot(400, lambda: self._start_stream(response))

    def _start_stream(self, target: str):
        self._typing_text = ""
        self._typing_target = target
        self._typing_timer.start(22)

    def _type_tick(self):
        idx = len(self._typing_text)
        if idx < len(self._typing_target):
            # Stream in chunks of 1-3 chars to vary pacing
            chunk = random.randint(1, 3)
            self._typing_text = self._typing_target[: idx + chunk]
            self._render(extra_ai=self._typing_text)
        else:
            self._typing_timer.stop()
            self._add_message("ai", self._typing_target)
            self._render()
            self._send_btn.setEnabled(True)


# ===========================================================================
# Feature 3 — Voice-to-Text Dashboard
# ===========================================================================
class WaveformWidget(QWidget):
    """Animated bar-chart waveform visualiser."""

    _N = 40

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(110)
        self._bars = [0.05] * self._N
        self._recording = False
        self._phase = 0.0
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(35)

    def set_recording(self, on: bool):
        self._recording = on

    def _tick(self):
        if self._recording:
            self._phase += 0.18
            for i in range(self._N):
                base = 0.25 + 0.35 * math.sin(self._phase + i * 0.38)
                self._bars[i] = max(0.04, min(1.0, base + random.gauss(0, 0.07)))
        else:
            for i in range(self._N):
                self._bars[i] = max(0.04, self._bars[i] * 0.88 + random.gauss(0, 0.005))
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(CARD))
        bw = w / self._N
        cy = h / 2
        for i, val in enumerate(self._bars):
            bh = max(4, val * (h - 12))
            x = i * bw
            # Colour interpolates blue → red with amplitude
            r = int(56  + val * 177)
            g = int(189 - val * 152)
            b = int(248 - val * 168)
            painter.fillRect(int(x + 1), int(cy - bh / 2),
                             int(bw - 2), int(bh), QColor(r, g, b))
        painter.end()


class VoiceWidget(QWidget):
    """Voice-to-text with animated waveform and simulated ASR."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_title("🎙  Voice-to-Text Dashboard"))
        layout.addWidget(_hint(
            "Simulates background audio capture and ASR processing.  "
            "Press Record — the waveform animates and text appears incrementally."))
        layout.addWidget(_sep())

        self._wave = WaveformWidget()
        layout.addWidget(self._wave)

        ctrl = QHBoxLayout()
        self._rec_btn = QPushButton("⏺  Start Recording")
        self._rec_btn.setObjectName("ok")
        self._rec_btn.clicked.connect(self._toggle)
        self._conf_lbl = QLabel("ASR confidence: —")
        self._conf_lbl.setStyleSheet(f"color:{YELLOW};")
        ctrl.addWidget(self._rec_btn)
        ctrl.addStretch()
        ctrl.addWidget(self._conf_lbl)
        layout.addLayout(ctrl)

        layout.addWidget(QLabel("Transcription:"))
        self._transcript = QTextEdit()
        self._transcript.setReadOnly(True)
        self._transcript.setStyleSheet(f"background:{PANEL};")
        layout.addWidget(self._transcript, stretch=1)

        self._recording = False
        self._target_sentence = ""
        self._current_words: list[str] = []
        self._word_idx = 0
        self._word_timer = QTimer()
        self._word_timer.timeout.connect(self._next_word)

    def _toggle(self):
        self._recording = not self._recording
        self._wave.set_recording(self._recording)
        if self._recording:
            self._rec_btn.setText("⏹  Stop Recording")
            self._rec_btn.setObjectName("alt")
            self._rec_btn.setStyle(self._rec_btn.style())
            self._target_sentence = random.choice(_TRANSCRIPTS)
            self._current_words = []
            self._word_idx = 0
            self._transcript.clear()
            self._conf_lbl.setText("ASR confidence: processing…")
            self._word_timer.start(250)
        else:
            self._rec_btn.setText("⏺  Start Recording")
            self._rec_btn.setObjectName("ok")
            self._rec_btn.setStyle(self._rec_btn.style())
            self._word_timer.stop()
            conf = random.uniform(91, 99)
            self._conf_lbl.setText(f"ASR confidence: {conf:.1f} %")

    def _next_word(self):
        words = self._target_sentence.split()
        if self._word_idx < len(words):
            self._current_words.append(words[self._word_idx])
            self._word_idx += 1
            self._transcript.setPlainText(" ".join(self._current_words) + " ▋")
        else:
            self._word_timer.stop()
            self._transcript.setPlainText(" ".join(self._current_words))
            conf = random.uniform(91, 99)
            self._conf_lbl.setText(f"ASR confidence: {conf:.1f} %")


# ===========================================================================
# Feature 4 — Confidence & Probability Gauges
# ===========================================================================
class ConfidenceWidget(QWidget):
    """Softmax probability bars that animate on each inference run."""

    _CLASSES = ["Technical", "Creative Writing", "Formal/Legal",
                "Casual Speech", "Source Code"]
    _COLORS = [BLUE, PURPLE, YELLOW, GREEN, RED]

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_title("📊  Confidence & Probability Gauges"))
        layout.addWidget(_hint(
            "Enter any text and click Analyse — the bars animate to show "
            "simulated softmax class probabilities from the model head."))
        layout.addWidget(_sep())

        row = QHBoxLayout()
        self._entry = QLineEdit()
        self._entry.setPlaceholderText("Enter text to classify…")
        self._entry.returnPressed.connect(self._analyse)
        btn = QPushButton("Analyse")
        btn.clicked.connect(self._analyse)
        row.addWidget(self._entry, stretch=1)
        row.addWidget(btn)
        layout.addLayout(row)
        layout.addWidget(_sep())

        self._bars: list[QProgressBar] = []
        self._val_labels: list[QLabel] = []
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, (cls, col) in enumerate(zip(self._CLASSES, self._COLORS)):
            lbl = QLabel(cls)
            lbl.setStyleSheet(f"color:{col}; font-weight:bold;")
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(0)
            bar.setStyleSheet(
                f"QProgressBar::chunk {{ background:{col}; border-radius:3px; }}")
            bar.setFormat("")
            val = QLabel("0.0 %")
            val.setStyleSheet(f"color:{col}; min-width:55px;")
            grid.addWidget(lbl, i, 0)
            grid.addWidget(bar, i, 1)
            grid.addWidget(val, i, 2)
            self._bars.append(bar)
            self._val_labels.append(val)
        layout.addLayout(grid)
        layout.addStretch()

        self._targets: list[float] = [0.0] * 5
        self._current: list[float] = [0.0] * 5
        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._anim_tick)

        self._model_lbl = QLabel("")
        self._model_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        layout.addWidget(self._model_lbl)

    def _analyse(self):
        if not self._entry.text().strip():
            return
        raw = [random.random() ** 0.7 for _ in range(5)]
        total = sum(raw)
        self._targets = [v / total for v in raw]
        self._anim_timer.start(16)
        lat = random.uniform(28, 65)
        self._model_lbl.setText(
            f"Model: distilbert-q4 | Latency: {lat:.1f} ms | Device: NPU")

    def _anim_tick(self):
        done = True
        for i in range(5):
            diff = self._targets[i] - self._current[i]
            if abs(diff) > 0.001:
                self._current[i] += diff * 0.12
                done = False
            else:
                self._current[i] = self._targets[i]
            self._bars[i].setValue(int(self._current[i] * 1000))
            self._val_labels[i].setText(f"{self._current[i] * 100:.1f} %")
        if done:
            self._anim_timer.stop()


# ===========================================================================
# Feature 5 — Embedding Space Viewer
# ===========================================================================
class EmbeddingCanvas(QWidget):
    """2-D scatter plot of word-embedding projections."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(360, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._points: list[tuple[str, float, float, str]] = list(_EMBED_POINTS)

    def add_point(self, label: str, color: str = RED):
        # Perturb an existing cluster centroid slightly
        ref = random.choice(self._points)
        x = min(0.95, max(0.05, ref[1] + random.gauss(0, 0.08)))
        y = min(0.95, max(0.05, ref[2] + random.gauss(0, 0.08)))
        self._points.append((label, x, y, color))
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(CARD))

        # Grid
        painter.setPen(QPen(QColor(DEEP), 1))
        for i in range(1, 10):
            painter.drawLine(int(i * w / 10), 0, int(i * w / 10), h)
            painter.drawLine(0, int(i * h / 10), w, int(i * h / 10))

        # Axis labels
        f = QFont(); f.setPointSize(8)
        painter.setFont(f)
        painter.setPen(QPen(QColor(MUTED)))
        painter.drawText(4, h - 4, "PCA dim-1 →")
        painter.drawText(4, 14, "↑ PCA dim-2")

        # Draw connections between same-colour points (cluster edges)
        clusters: dict[str, list[tuple[int, int]]] = {}
        for label, xf, yf, col in self._points:
            px = int(xf * (w - 40) + 20)
            py = int(yf * (h - 30) + 15)
            clusters.setdefault(col, []).append((px, py))
        for col, pts in clusters.items():
            if len(pts) > 1:
                c = QColor(col); c.setAlpha(30)
                painter.setPen(QPen(c, 1, Qt.PenStyle.DashLine))
                for i in range(len(pts) - 1):
                    painter.drawLine(pts[i][0], pts[i][1],
                                     pts[i+1][0], pts[i+1][1])

        # Points
        f2 = QFont(); f2.setPointSize(8)
        painter.setFont(f2)
        for label, xf, yf, col in self._points:
            px = int(xf * (w - 40) + 20)
            py = int(yf * (h - 30) + 15)
            qc = QColor(col)
            glow = QColor(qc); glow.setAlpha(35)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(px - 11, py - 11, 22, 22)
            painter.setBrush(QBrush(qc))
            painter.setPen(QPen(QColor("white"), 1))
            painter.drawEllipse(px - 6, py - 6, 12, 12)
            painter.setPen(QPen(qc))
            painter.drawText(px + 9, py + 4, label)
        painter.end()


class EmbeddingWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_title("🗺  Embedding Space Viewer"))
        layout.addWidget(_hint(
            "A 2-D PCA projection of word embeddings.  Type a term and click "
            "Embed to place it in the vector space near semantically similar neighbours."))
        layout.addWidget(_sep())

        self._canvas = EmbeddingCanvas()
        layout.addWidget(self._canvas, stretch=1)

        row = QHBoxLayout()
        self._entry = QLineEdit()
        self._entry.setPlaceholderText("Enter a word or phrase to embed…")
        self._entry.returnPressed.connect(self._embed)
        btn = QPushButton("Embed →")
        btn.clicked.connect(self._embed)
        clear_btn = QPushButton("Reset")
        clear_btn.setObjectName("alt")
        clear_btn.clicked.connect(self._reset)
        row.addWidget(self._entry, stretch=1)
        row.addWidget(btn)
        row.addWidget(clear_btn)
        layout.addLayout(row)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        layout.addWidget(self._status)

    def _embed(self):
        text = self._entry.text().strip()
        if not text:
            return
        colors = [BLUE, PURPLE, GREEN, RED, YELLOW]
        col = random.choice(colors)
        self._canvas.add_point(text, col)
        lat = random.uniform(4, 18)
        self._status.setText(
            f'Embedded "{text}" in {lat:.1f} ms  |  '
            f"dim: 768  |  nearest: {random.choice(_EMBED_POINTS)[0]}")
        self._entry.clear()

    def _reset(self):
        self._canvas._points = list(_EMBED_POINTS)
        self._canvas.update()
        self._status.setText("Canvas reset to default corpus.")


# ===========================================================================
# Feature 6 — File-Based Summarizer
# ===========================================================================
class SummarizerWidget(QWidget):
    """Opens a local file, reads it, and produces an extractive summary."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_title("📄  File-Based Summarizer"))
        layout.addWidget(_hint(
            "Pick any .txt / .md / .py file.  The app reads it locally "
            "(no upload), extracts key sentences, and displays a summary."))
        layout.addWidget(_sep())

        ctrl = QHBoxLayout()
        btn = QPushButton("📂  Open File…")
        btn.setObjectName("alt")
        btn.clicked.connect(self._open_file)
        self._file_lbl = QLabel("No file selected")
        self._file_lbl.setStyleSheet(f"color:{MUTED};")
        ctrl.addWidget(btn)
        ctrl.addWidget(self._file_lbl, stretch=1)
        layout.addLayout(ctrl)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self._orig = QTextEdit()
        self._orig.setReadOnly(True)
        self._orig.setPlaceholderText("Original text will appear here…")
        self._orig.setStyleSheet(f"background:{PANEL};")
        self._summ = QTextEdit()
        self._summ.setReadOnly(True)
        self._summ.setPlaceholderText("Summary will appear here…")
        self._summ.setStyleSheet(f"background:{PANEL};")
        splitter.addWidget(self._orig)
        splitter.addWidget(self._summ)
        splitter.setSizes([200, 150])
        layout.addWidget(splitter, stretch=1)

        self._orig_lbl  = QLabel("Original (preview):")
        self._summ_lbl  = QLabel("Extractive summary:")
        layout.insertWidget(3, self._orig_lbl)
        # labels inserted before the splitter:
        layout.addWidget(_hint("Drag the divider to resize panes."))

        self._prog_val = 0
        self._prog_timer = QTimer()
        self._prog_timer.timeout.connect(self._tick_progress)
        self._raw_text = ""

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open text file", os.path.expanduser("~"),
            "Text files (*.txt *.md *.py *.rst *.csv);;All files (*)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                self._raw_text = fh.read()
        except OSError as exc:
            self._file_lbl.setText(f"Error: {exc}")
            return
        name = os.path.basename(path)
        size_kb = os.path.getsize(path) / 1024
        self._file_lbl.setText(f"{name}  ({size_kb:.1f} KB)")
        self._orig.setPlainText(self._raw_text[:2000] +
                                ("…" if len(self._raw_text) > 2000 else ""))
        self._summ.clear()
        self._prog_val = 0
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._prog_timer.start(35)

    def _tick_progress(self):
        self._prog_val = min(100, self._prog_val + random.randint(2, 6))
        self._progress.setValue(self._prog_val)
        if self._prog_val >= 100:
            self._prog_timer.stop()
            self._progress.setVisible(False)
            self._show_summary()

    def _show_summary(self):
        text = self._raw_text
        # Extractive summary: score sentences by keyword density
        sentences = re.split(r'(?<=[.!?])\s+', text)
        keywords = re.findall(r'\b[A-Za-z]{5,}\b', text)
        freq: dict[str, int] = {}
        for kw in keywords:
            freq[kw.lower()] = freq.get(kw.lower(), 0) + 1

        scored = []
        for sent in sentences:
            if 10 < len(sent) < 300:
                words = re.findall(r'\b[A-Za-z]{5,}\b', sent)
                score = sum(freq.get(w.lower(), 0) for w in words)
                scored.append((score, sent))
        scored.sort(reverse=True)
        top = [s for _, s in scored[:5]]
        word_count = len(text.split())
        summary = " ".join(top) if top else "(No extractable sentences found.)"
        self._summ.setPlainText(
            f"[{word_count} words → {len(top)} key sentences extracted]\n\n" + summary)


# ===========================================================================
# Feature 7 — Translation Camera Overlay
# ===========================================================================
class CameraView(QWidget):
    """Simulated live-camera feed with AR translation overlay."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(260)
        self._active = False
        self._lang = "Spanish"
        self._frame = 0
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(80)

    def set_active(self, on: bool):
        self._active = on

    def set_lang(self, lang: str):
        self._lang = lang

    def _tick(self):
        self._frame += 1
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Camera background gradient (dark scene)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor("#1a1a1a"))
        grad.setColorAt(0.5, QColor("#2a2820"))
        grad.setColorAt(1, QColor("#181820"))
        painter.fillRect(0, 0, w, h, QBrush(grad))

        # Scene: a few simple shapes (wall, shelves)
        painter.setBrush(QBrush(QColor("#2a2a2a")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, int(h * 0.6), w, int(h * 0.4))  # floor
        painter.setBrush(QBrush(QColor("#333333")))
        painter.drawRect(int(w * 0.1), int(h * 0.2), int(w * 0.3), int(h * 0.35))

        # Scan-line effect
        scan_y = int((self._frame * 3) % h)
        scan_col = QColor(BLUE); scan_col.setAlpha(30)
        painter.setPen(QPen(scan_col, 2))
        painter.drawLine(0, scan_y, w, scan_y)

        # Text regions
        translations = {
            "Spanish": {"MENU": "MENÚ", "OPEN": "ABIERTO",
                        "WELCOME": "BIENVENIDO", "EXIT": "SALIDA", "PRICE": "PRECIO"},
            "French":  {"MENU": "MENU", "OPEN": "OUVERT",
                        "WELCOME": "BIENVENUE", "EXIT": "SORTIE", "PRICE": "PRIX"},
            "Japanese": {"MENU": "メニュー", "OPEN": "開店",
                         "WELCOME": "ようこそ", "EXIT": "出口", "PRICE": "価格"},
        }
        tr = translations.get(self._lang, translations["Spanish"])

        for src, xf, yf, transl_key in _CAMERA_TEXTS:
            px = int(xf * (w - 80) + 10)
            py = int(yf * (h - 30) + 10)
            translated = tr.get(src, src)
            # Wobble
            px += int(math.sin(self._frame * 0.04 + xf * 10) * 1.5)

            if self._active:
                # Overlay box (translated)
                ol_col = QColor(BLUE); ol_col.setAlpha(170)
                painter.setBrush(QBrush(ol_col))
                painter.setPen(Qt.PenStyle.NoPen)
                fm_w = max(60, len(translated) * 10)
                painter.drawRoundedRect(px, py, fm_w, 24, 4, 4)
                painter.setPen(QPen(QColor("white")))
                f = QFont(); f.setBold(True); f.setPointSize(10)
                painter.setFont(f)
                painter.drawText(px + 5, py + 17, translated)
            else:
                # Original white text box
                bg = QColor("#ffffff"); bg.setAlpha(200)
                painter.setBrush(QBrush(bg))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(px, py, len(src) * 9 + 6, 22)
                painter.setPen(QPen(QColor("#111111")))
                f = QFont(); f.setBold(True); f.setPointSize(10)
                painter.setFont(f)
                painter.drawText(px + 4, py + 16, src)

        # HUD corners
        c = QColor(GREEN); c.setAlpha(180)
        painter.setPen(QPen(c, 2))
        cs = 16
        for cx, cy in [(8, 8), (w - 8 - cs, 8), (8, h - 8 - cs), (w - 8 - cs, h - 8 - cs)]:
            painter.drawLine(cx, cy, cx + cs, cy)
            painter.drawLine(cx, cy, cx, cy + cs)

        painter.end()


class CameraWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_title("📷  Translation Camera Overlay"))
        layout.addWidget(_hint(
            "Simulates a live AR camera feed.  Toggle the overlay to "
            "replace physical text with real-time translations."))
        layout.addWidget(_sep())

        self._cam = CameraView()
        layout.addWidget(self._cam, stretch=1)

        ctrl = QHBoxLayout()
        self._tog_btn = QPushButton("▶  Enable Translation Overlay")
        self._tog_btn.setObjectName("ok")
        self._tog_btn.clicked.connect(self._toggle)
        ctrl.addWidget(self._tog_btn)
        ctrl.addStretch()
        ctrl.addWidget(QLabel("Language:"))
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["Spanish", "French", "Japanese"])
        self._lang_combo.currentTextChanged.connect(self._cam.set_lang)
        ctrl.addWidget(self._lang_combo)
        layout.addLayout(ctrl)

        self._active = False

    def _toggle(self):
        self._active = not self._active
        self._cam.set_active(self._active)
        if self._active:
            self._tog_btn.setText("⏹  Disable Overlay")
            self._tog_btn.setObjectName("alt")
        else:
            self._tog_btn.setText("▶  Enable Translation Overlay")
            self._tog_btn.setObjectName("ok")
        self._tog_btn.setStyle(self._tog_btn.style())


# ===========================================================================
# Feature 8 — Performance Heartbeat
# ===========================================================================
class SparklineWidget(QWidget):
    """Rolling line-chart for a single metric."""

    def __init__(self, color=BLUE):
        super().__init__()
        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._data = [0.0] * 40
        self._color = color

    def push(self, value: float):
        self._data.pop(0)
        self._data.append(value)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(CARD))
        painter.setPen(QPen(QColor(DEEP), 1))
        for i in range(1, 5):
            y = int(i * h / 5)
            painter.drawLine(0, y, w, y)
        n = len(self._data)
        if max(self._data) < 0.01:
            painter.end()
            return
        pts = []
        for i, v in enumerate(self._data):
            x = int(i * (w - 1) / (n - 1))
            y = int(h - 3 - v / 100 * (h - 6))
            pts.append(QPointF(x, y))
        # Fill area under curve
        fill_col = QColor(self._color); fill_col.setAlpha(40)
        painter.setBrush(QBrush(fill_col))
        painter.setPen(Qt.PenStyle.NoPen)
        poly_pts = [QPointF(0, h)] + pts + [QPointF(w - 1, h)]
        from PySide6.QtGui import QPolygonF
        painter.drawPolygon(QPolygonF(poly_pts))
        painter.setPen(QPen(QColor(self._color), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(len(pts) - 1):
            painter.drawLine(pts[i], pts[i + 1])
        painter.end()


class HeartbeatWidget(QWidget):
    """Live CPU / NPU / RAM / Temp monitor with sparklines."""

    _METRICS = [
        ("CPU",  "%",  RED,    (20, 85)),
        ("NPU",  "%",  BLUE,   (5,  70)),
        ("RAM",  "%",  PURPLE, (40, 75)),
        ("Temp", "°C", YELLOW, (35, 62)),
    ]

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.addWidget(_title("💓  Performance Heartbeat"))
        self._model_dot = QLabel("● on-device model active")
        self._model_dot.setStyleSheet(f"color:{GREEN}; font-size:11px;")
        hdr.addStretch()
        hdr.addWidget(self._model_dot)
        layout.addLayout(hdr)
        layout.addWidget(_hint(
            "Simulates hardware telemetry from the mobile SoC.  "
            "Values update every 500 ms with realistic fluctuation."))
        layout.addWidget(_sep())

        self._bars: list[QProgressBar] = []
        self._val_labels: list[QLabel] = []
        self._sparks: list[SparklineWidget] = []
        self._ranges: list[tuple[int, int]] = []
        self._current_vals: list[float] = []

        for name, unit, col, (lo, hi) in self._METRICS:
            row = QHBoxLayout()
            lbl = QLabel(f"{name}")
            lbl.setFixedWidth(40)
            lbl.setStyleSheet(f"color:{col}; font-weight:bold;")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFormat("")
            bar.setStyleSheet(
                f"QProgressBar::chunk {{ background:{col}; border-radius:3px; }}")
            val_lbl = QLabel(f"0 {unit}")
            val_lbl.setFixedWidth(55)
            val_lbl.setStyleSheet(f"color:{col};")
            row.addWidget(lbl)
            row.addWidget(bar, stretch=1)
            row.addWidget(val_lbl)
            layout.addLayout(row)
            spark = SparklineWidget(col)
            layout.addWidget(spark)
            self._bars.append(bar)
            self._val_labels.append(val_lbl)
            self._sparks.append(spark)
            self._ranges.append((lo, hi))
            self._current_vals.append(float(lo))

        self._inf_lbl = QLabel("")
        self._inf_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        layout.addWidget(self._inf_lbl)
        layout.addStretch()

        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(500)
        self._tick()

    def _tick(self):
        _, unit_list = zip(*[(m[0], m[1]) for m in self._METRICS])
        units = [m[1] for m in self._METRICS]
        for i, (lo, hi) in enumerate(self._ranges):
            target = lo + (hi - lo) * (0.5 + 0.4 * math.sin(
                time.time() * (0.3 + i * 0.07)) + random.gauss(0, 0.05))
            target = max(lo, min(hi, target))
            self._current_vals[i] = (self._current_vals[i] * 0.7 + target * 0.3)
            v = self._current_vals[i]
            pct = int((v - lo) / max(hi - lo, 1) * 100)
            self._bars[i].setValue(pct)
            self._val_labels[i].setText(f"{v:.0f} {units[i]}")
            self._sparks[i].push(pct)

        fps = random.uniform(28, 32)
        lat = random.uniform(30, 55)
        self._inf_lbl.setText(
            f"Model inference: {lat:.1f} ms/token  |  Display: {fps:.0f} fps  |  "
            f"Battery: {random.randint(72, 98)} %")


# ===========================================================================
# Feature 9 — Multi-Modal Input Bar
# ===========================================================================
class MultiModalWidget(QWidget):
    """Unified input accepting text, voice, and image, with fused analysis."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_title("🔀  Multi-Modal Input Bar"))
        layout.addWidget(_hint(
            "Simulate fusing text, voice, and image data.  Activate each "
            "modality, then press Fuse & Process to see the combined analysis."))
        layout.addWidget(_sep())

        # Modality toggles
        mod_row = QHBoxLayout()
        self._txt_btn  = QPushButton("📝  Text")
        self._voice_btn = QPushButton("🎙  Voice")
        self._img_btn  = QPushButton("📷  Image")
        for b in (self._txt_btn, self._voice_btn, self._img_btn):
            b.setObjectName("alt")
            b.setCheckable(True)
            mod_row.addWidget(b)
        self._txt_btn.toggled.connect(lambda v: self._on_toggle("text", v))
        self._voice_btn.toggled.connect(lambda v: self._on_toggle("voice", v))
        self._img_btn.toggled.connect(lambda v: self._on_toggle("image", v))
        layout.addLayout(mod_row)

        # Input area
        self._input_area = QWidget()
        ia_layout = QVBoxLayout(self._input_area)
        ia_layout.setContentsMargins(0, 0, 0, 0)

        self._text_input = QLineEdit()
        self._text_input.setPlaceholderText("Type a text input…")
        self._text_input.setVisible(False)
        ia_layout.addWidget(self._text_input)

        self._voice_lbl = QLabel("🎙  Voice input: press Record below to capture")
        self._voice_lbl.setStyleSheet(
            f"color:{MUTED}; background:{CARD}; padding:8px; border-radius:6px;")
        self._voice_lbl.setVisible(False)
        ia_layout.addWidget(self._voice_lbl)

        self._img_lbl = QLabel("📷  Image input: tap to attach a photo")
        self._img_lbl.setStyleSheet(
            f"color:{MUTED}; background:{CARD}; padding:8px; border-radius:6px;")
        self._img_lbl.setVisible(False)
        ia_layout.addWidget(self._img_lbl)

        layout.addWidget(self._input_area)

        # Status chips
        self._status_row = QHBoxLayout()
        self._chips: dict[str, QLabel] = {}
        for mod, col in (("text", BLUE), ("voice", GREEN), ("image", YELLOW)):
            chip = QLabel(f"  {mod}: ○  ")
            chip.setStyleSheet(
                f"color:{col}; background:{CARD}; border:1px solid {col}; "
                f"border-radius:10px; padding:2px 6px; font-size:11px;")
            self._status_row.addWidget(chip)
            self._chips[mod] = chip
        self._status_row.addStretch()
        layout.addLayout(self._status_row)

        btn_row = QHBoxLayout()
        rec_btn = QPushButton("⏺  Record Voice")
        rec_btn.setObjectName("alt")
        rec_btn.clicked.connect(self._fake_record)
        snap_btn = QPushButton("📸  Snap Image")
        snap_btn.setObjectName("alt")
        snap_btn.clicked.connect(self._fake_snap)
        proc_btn = QPushButton("⚡  Fuse & Process")
        proc_btn.clicked.connect(self._process)
        btn_row.addWidget(rec_btn)
        btn_row.addWidget(snap_btn)
        btn_row.addWidget(proc_btn)
        layout.addLayout(btn_row)

        layout.addWidget(_sep())
        layout.addWidget(QLabel("Fused Analysis Output:"))
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(f"background:{PANEL};")
        layout.addWidget(self._output, stretch=1)

        self._active_mods: set[str] = set()
        self._voice_captured = False
        self._img_captured = False

    def _on_toggle(self, mod: str, on: bool):
        chip = self._chips[mod]
        marker = "●" if on else "○"
        chip.setText(f"  {mod}: {marker}  ")
        if on:
            self._active_mods.add(mod)
        else:
            self._active_mods.discard(mod)
        self._text_input.setVisible("text" in self._active_mods)
        self._voice_lbl.setVisible("voice" in self._active_mods)
        self._img_lbl.setVisible("image" in self._active_mods)

    def _fake_record(self):
        self._voice_captured = True
        sent = random.choice(_TRANSCRIPTS)
        self._voice_lbl.setText(f'🎙  Captured: "{sent[:60]}..."')
        self._voice_lbl.setStyleSheet(
            f"color:{GREEN}; background:{CARD}; padding:8px; border-radius:6px;")
        self._voice_btn.setChecked(True)

    def _fake_snap(self):
        self._img_captured = True
        labels = ["coffee mug", "laptop keyboard", "notebook", "street sign", "book cover"]
        self._img_lbl.setText(f"📷  Detected objects: {', '.join(random.sample(labels, 3))}")
        self._img_lbl.setStyleSheet(
            f"color:{YELLOW}; background:{CARD}; padding:8px; border-radius:6px;")
        self._img_btn.setChecked(True)

    def _process(self):
        if not self._active_mods:
            self._output.setPlainText("⚠  No modalities activated.  Toggle at least one above.")
            return
        parts = []
        if "text" in self._active_mods:
            t = self._text_input.text().strip() or "(empty)"
            parts.append(f"Text channel  → '{t}' ({len(t.split())} tokens)")
        if "voice" in self._active_mods:
            parts.append(f"Voice channel → ASR transcript ({random.randint(8,20)} tokens, "
                         f"confidence {random.uniform(91,99):.1f} %)")
        if "image" in self._active_mods:
            parts.append(f"Image channel → ViT patch embeddings (196 patches, "
                         f"dim 768), top object: {random.choice(['text', 'scene', 'face'])}")
        fused = (
            f"Fusion strategy: cross-modal attention (text ↔ vision, voice ↔ text)\n"
            f"Combined embedding dim: 1024\n"
            f"Inference latency: {random.uniform(55,130):.1f} ms  "
            f"| Modalities: {', '.join(sorted(self._active_mods))}\n\n"
            + "\n".join(parts) +
            f"\n\nModel output: {random.choice(_RESPONSES)}")
        self._output.setPlainText(fused)


# ===========================================================================
# Feature 10 — Local Knowledge Vault (RAG)
# ===========================================================================
class KnowledgeVaultWidget(QWidget):
    """Keyword-RAG over an in-app document store."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_title("🗄  Local Knowledge Vault"))
        layout.addWidget(_hint(
            "A local RAG pipeline.  Search the vault with a query — relevant "
            "chunks are retrieved by keyword overlap and fed to the generative model."))
        layout.addWidget(_sep())

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: document list
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("Vault documents:"))
        self._doc_list = QListWidget()
        for name, _ in _DOCUMENTS:
            item = QListWidgetItem(f"📄  {name}")
            self._doc_list.addItem(item)
        ll.addWidget(self._doc_list, stretch=1)
        add_btn = QPushButton("＋  Add Document")
        add_btn.setObjectName("alt")
        add_btn.clicked.connect(self._add_doc)
        ll.addWidget(add_btn)
        splitter.addWidget(left)

        # Right: search + answer
        right = QWidget()
        rl = QVBoxLayout(right)
        search_row = QHBoxLayout()
        self._query = QLineEdit()
        self._query.setPlaceholderText("Ask a question about the vault…")
        self._query.returnPressed.connect(self._search)
        srch_btn = QPushButton("Search ↵")
        srch_btn.clicked.connect(self._search)
        search_row.addWidget(self._query, stretch=1)
        search_row.addWidget(srch_btn)
        rl.addLayout(search_row)

        rl.addWidget(QLabel("Retrieved chunks:"))
        self._chunks = QTextEdit()
        self._chunks.setReadOnly(True)
        self._chunks.setStyleSheet(f"background:{PANEL};")
        self._chunks.setMaximumHeight(130)
        rl.addWidget(self._chunks)

        rl.addWidget(QLabel("AI answer (grounded):"))
        self._answer = QTextEdit()
        self._answer.setReadOnly(True)
        self._answer.setStyleSheet(f"background:{PANEL};")
        rl.addWidget(self._answer, stretch=1)

        self._rag_lbl = QLabel("")
        self._rag_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        rl.addWidget(self._rag_lbl)

        splitter.addWidget(right)
        splitter.setSizes([200, 400])
        layout.addWidget(splitter, stretch=1)

        self._docs = list(_DOCUMENTS)
        self._typing_text = ""
        self._typing_target = ""
        self._typing_timer = QTimer()
        self._typing_timer.timeout.connect(self._type_tick)

    def _search(self):
        query = self._query.text().strip().lower()
        if not query:
            return
        query_words = set(re.findall(r'\b\w{3,}\b', query))
        scored = []
        for name, content in self._docs:
            doc_words = set(re.findall(r'\b\w{3,}\b', content.lower()))
            overlap = len(query_words & doc_words)
            if overlap > 0:
                scored.append((overlap, name, content))
        scored.sort(reverse=True)

        if scored:
            chunk_html = ""
            for rank, (score, name, content) in enumerate(scored[:2], 1):
                sim = min(0.99, 0.55 + score * 0.08 + random.uniform(-0.03, 0.03))
                chunk_html += (
                    f"<b style='color:{BLUE};'>[{rank}] {name}</b> "
                    f"<span style='color:{MUTED};'>(sim={sim:.2f})</span><br>"
                    f"{content[:200]}…<br><br>")
            self._chunks.setHtml(chunk_html)
            context = " ".join(c for _, _, c in scored[:2])
            answer = (
                f"Based on {len(scored[:2])} retrieved document(s) from the local vault:\n\n"
                f"{context[:300]}…\n\n"
                f"[Model inference] {random.choice(_RESPONSES)}")
        else:
            self._chunks.setPlainText("No relevant chunks found for that query.")
            answer = "I could not find relevant information in the local vault for that query."

        lat = random.uniform(40, 130)
        self._rag_lbl.setText(
            f"Retrieval: {len(scored)} docs scored | "
            f"Top-k=2 | Latency: {lat:.1f} ms | Embedding: BM25+dense")
        self._typing_text = ""
        self._typing_target = answer
        self._answer.clear()
        self._typing_timer.start(20)

    def _type_tick(self):
        idx = len(self._typing_text)
        if idx < len(self._typing_target):
            self._typing_text = self._typing_target[:idx + random.randint(1, 4)]
            self._answer.setPlainText(self._typing_text + "▋")
        else:
            self._typing_timer.stop()
            self._answer.setPlainText(self._typing_target)

    def _add_doc(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add document to vault", os.path.expanduser("~"),
            "Text files (*.txt *.md *.py *.rst);;All files (*)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                content = fh.read(1000)
        except OSError:
            return
        name = os.path.basename(path)
        self._docs.append((name, content))
        self._doc_list.addItem(QListWidgetItem(f"📄  {name}"))


# ===========================================================================
# Feature tab factory
# ===========================================================================

def create_feature_tabs():
    """Return a QTabWidget containing all ten AI feature demos."""
    tabs = QTabWidget()
    tabs.setTabPosition(QTabWidget.TabPosition.North)
    feature_list = [
        ("⚡ Tok",   TokenizerWidget()),
        ("💬 Chat",  ChatWidget()),
        ("🎙 ASR",   VoiceWidget()),
        ("📊 Conf",  ConfidenceWidget()),
        ("🗺 Embed", EmbeddingWidget()),
        ("📄 File",  SummarizerWidget()),
        ("📷 AR",    CameraWidget()),
        ("💓 HW",    HeartbeatWidget()),
        ("🔀 Multi", MultiModalWidget()),
        ("🗄 RAG",   KnowledgeVaultWidget()),
    ]
    for tab_name, widget in feature_list:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        tabs.addTab(scroll, tab_name)
    return tabs

