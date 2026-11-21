"""Finestra sul proiettore (visto dal PC come secondo monitor).

Niente showFullScreen(): su Windows può cambiare la modalità del monitor secondario e
lasciare una schermata grigia. Si usa invece una finestra senza bordi grande quanto lo
schermo, che non ruba il focus alla finestra principale.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ProjectorWindow(QWidget):
    closed = Signal()  # emesso quando la finestra sparisce, per qualsiasi motivo

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setStyleSheet("background: black;")
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignCenter)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._label)
        # Uscite di sicurezza (funzionano se la finestra ha il focus)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.hide)

    def show_on_screen(self, screen_index: int) -> None:
        screens = QGuiApplication.screens()
        screen = screens[min(screen_index, len(screens) - 1)]
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.show()
        self.setGeometry(screen.geometry())  # dopo show(), per sicurezza su Windows

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        self.closed.emit()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.hide()

    @property
    def size_px(self) -> tuple[int, int]:
        return self.width(), self.height()

    def show_gray(self, image: np.ndarray) -> None:
        """Mostra un'immagine in scala di grigi (uint8, HxW) a risoluzione nativa."""
        img = np.ascontiguousarray(image, dtype=np.uint8)
        h, w = img.shape
        qimg = QImage(img.data, w, h, w, QImage.Format_Grayscale8).copy()
        self._label.setPixmap(QPixmap.fromImage(qimg))

    def show_level(self, level: int) -> None:
        w, h = self.size_px
        self.show_gray(np.full((h, w), level, np.uint8))
