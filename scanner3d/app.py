"""Interfaccia principale: anteprima camere, controllo proiettore, salvataggio frame."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QComboBox, QGroupBox, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from .cameras import CameraRig
from .projector import ProjectorWindow


def to_pixmap(gray: np.ndarray, width: int) -> QPixmap:
    h, w = gray.shape
    img = QImage(np.ascontiguousarray(gray).data, w, h, w, QImage.Format_Grayscale8).copy()
    return QPixmap.fromImage(img).scaledToWidth(width, Qt.SmoothTransformation)


class CameraControls(QGroupBox):
    """Esposizione e guadagno di una singola camera."""

    def __init__(self, rig: CameraRig, index: int, title: str) -> None:
        super().__init__(title)
        self.rig, self.index = rig, index
        lay = QVBoxLayout(self)

        self.exp_label = QLabel()
        self.exp = QSlider(Qt.Horizontal)
        lo, hi = rig.exposure_range_us(index)
        self.exp.setRange(int(lo), int(hi))
        self.exp.setValue(int(min(max(rig.exposure_us(index), lo), hi)))
        self.exp.valueChanged.connect(self._on_exp)
        self._on_exp(self.exp.value())

        self.gain_label = QLabel()
        self.gain = QSlider(Qt.Horizontal)
        glo, ghi = rig.gain_range_db(index)
        self.gain.setRange(int(glo * 10), int(ghi * 10))  # passi da 0,1 dB
        self.gain.setValue(int(rig.gain_db(index) * 10))
        self.gain.valueChanged.connect(self._on_gain)
        self._on_gain(self.gain.value())

        for w in (self.exp_label, self.exp, self.gain_label, self.gain):
            lay.addWidget(w)

    def _on_exp(self, value: int) -> None:
        self.exp_label.setText(f"Esposizione: {value / 1000:.1f} ms")
        self.rig.set_exposure_us(self.index, value)

    def _on_gain(self, value: int) -> None:
        self.gain_label.setText(f"Guadagno: {value / 10:.1f} dB")
        self.rig.set_gain_db(self.index, value / 10)


class MainWindow(QMainWindow):
    PREVIEW_W = 560

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scanner 3D")
        self.rig = CameraRig()
        self.projector = ProjectorWindow()
        self.projector.closed.connect(self._on_projector_closed)
        self.last_frames: list[np.ndarray] = []
        self.cam_controls: list[CameraControls] = []

        self.views = [QLabel("Camera sinistra"), QLabel("Camera destra")]
        for v in self.views:
            v.setFixedSize(self.PREVIEW_W, int(self.PREVIEW_W * 1200 / 1920))
            v.setAlignment(Qt.AlignCenter)
            v.setStyleSheet("background:#111;color:#888;")
        views_row = QHBoxLayout()
        for v in self.views:
            views_row.addWidget(v)

        # Proiettore
        self.screen_box = QComboBox()
        for i, s in enumerate(QGuiApplication.screens()):
            g = s.geometry()
            self.screen_box.addItem(f"Schermo {i}: {g.width()}x{g.height()}", i)
        if self.screen_box.count() > 1:
            self.screen_box.setCurrentIndex(1)
        self.pattern_box = QComboBox()
        self.pattern_box.addItems(["Bianco", "Grigio", "Nero", "Griglia"])
        self.pattern_box.currentIndexChanged.connect(self._update_projection)
        self.proj_btn = QPushButton("Accendi proiettore")
        self.proj_btn.setCheckable(True)
        self.proj_btn.toggled.connect(self._toggle_projector)

        proj_group = QGroupBox("Proiettore")
        pl = QVBoxLayout(proj_group)
        pl.addWidget(self.screen_box)
        pl.addWidget(self.pattern_box)
        pl.addWidget(self.proj_btn)

        save = QPushButton("Salva coppia di immagini")
        save.clicked.connect(self._save_pair)

        self.controls_layout = QVBoxLayout()
        self.controls_layout.addWidget(proj_group)
        self.controls_layout.addWidget(save)
        self.controls_layout.addStretch(1)

        self.status = QLabel("")
        root = QWidget()
        lay = QVBoxLayout(root)
        top = QHBoxLayout()
        top.addLayout(views_row, 1)
        top.addLayout(self.controls_layout)
        lay.addLayout(top)
        lay.addWidget(self.status)
        self.setCentralWidget(root)

        # Esc nella finestra principale spegne il proiettore
        QShortcut(QKeySequence(Qt.Key_Escape), self,
                  activated=lambda: self.proj_btn.setChecked(False))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._start_cameras()

    # --- camere ---
    def _start_cameras(self) -> None:
        try:
            self.rig.open()
        except Exception as exc:  # noqa: BLE001
            self.status.setText(f"Camere non disponibili: {exc}")
            QMessageBox.warning(self, "Camere", f"Impossibile aprire le camere:\n{exc}\n\n"
                                "Chiudi altri programmi che le usano (es. Vertex Pro).")
            return
        names = ["Camera sinistra", "Camera destra"]
        for i, info in enumerate(self.rig.infos):
            title = f"{names[i] if i < len(names) else f'Camera {i}'} ({info.serial})"
            self.rig.set_exposure_us(i, 10_000)
            ctl = CameraControls(self.rig, i, title)
            self.cam_controls.append(ctl)
            self.controls_layout.insertWidget(i, ctl)
        self.status.setText("Camere: " + ", ".join(i.serial for i in self.rig.infos))
        self.timer.start(40)

    def _tick(self) -> None:
        try:
            self.last_frames = self.rig.grab(timeout_ms=500)
        except Exception as exc:  # noqa: BLE001
            self.status.setText(f"Errore acquisizione: {exc}")
            return
        for view, frame in zip(self.views, self.last_frames):
            view.setPixmap(to_pixmap(frame, self.PREVIEW_W))

    def _save_pair(self) -> None:
        if len(self.last_frames) < 2:
            return
        out = Path("captures") / time.strftime("%Y%m%d_%H%M%S")
        out.mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(self.last_frames):
            cv2.imwrite(str(out / f"cam{i}.png"), f)
        self.status.setText(f"Salvate in {out}")

    # --- proiettore ---
    def _toggle_projector(self, on: bool) -> None:
        if on:
            self.projector.show_on_screen(self.screen_box.currentData())
            self._update_projection()
            self.proj_btn.setText("Spegni proiettore")
        else:
            self.projector.hide()
            self.proj_btn.setText("Accendi proiettore")
        self.raise_()
        self.activateWindow()

    def _on_projector_closed(self) -> None:
        """La finestra del proiettore è sparita (Esc, doppio clic, sistema): riallinea il pulsante."""
        if self.proj_btn.isChecked():
            self.proj_btn.setChecked(False)

    def _update_projection(self) -> None:
        if not self.projector.isVisible():
            return
        w, h = self.projector.size_px
        name = self.pattern_box.currentText()
        if name == "Griglia":
            img = np.zeros((h, w), np.uint8)
            img[::40, :] = 255
            img[:, ::40] = 255
            self.projector.show_gray(img)
        else:
            self.projector.show_level({"Bianco": 255, "Grigio": 128, "Nero": 0}[name])

    def closeEvent(self, event) -> None:  # noqa: N802
        self.timer.stop()
        self.projector.closed.disconnect(self._on_projector_closed)
        self.projector.close()
        self.rig.close()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
