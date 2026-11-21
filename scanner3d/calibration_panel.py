"""Pannello Qt per la calibrazione stereo. Non dipende dalle camere: riceve i frame da fuori."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGroupBox, QLabel, QMessageBox, QPushButton, QVBoxLayout,
)

from .calibration import CalibrationResult, PlateDetection, StereoCalibrator, detect_plate

PLATES = {"Medio (passo 7,5 mm)": 7.5, "Piccolo (passo 5 mm)": 5.0, "Grande (passo 15 mm)": 15.0}
CALIB_FILE = Path("calibration") / "stereo.json"


class CalibrationPanel(QGroupBox):
    MIN_POSES = StereoCalibrator.MIN_POSES

    def __init__(self) -> None:
        super().__init__("Calibrazione")
        self.calibrator = StereoCalibrator(pitch_mm=7.5)
        self.result: CalibrationResult | None = None
        self._dets: list[PlateDetection | None] = [None, None]
        self._skip = 0

        self.plate_box = QComboBox()
        self.plate_box.addItems(list(PLATES))
        self.plate_box.currentTextChanged.connect(self._on_plate)
        self.overlay_box = QCheckBox("Mostra rilevamento sulle camere")
        self.live = QLabel("")
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.btn_add = QPushButton("Acquisisci posa")
        self.btn_undo = QPushButton("Annulla ultima posa")
        self.btn_reset = QPushButton("Azzera pose")
        self.btn_calib = QPushButton("Calcola calibrazione")
        self.btn_add.clicked.connect(self._on_add)
        self.btn_undo.clicked.connect(self._on_undo)
        self.btn_reset.clicked.connect(self._on_reset)
        self.btn_calib.clicked.connect(self._on_calibrate)

        lay = QVBoxLayout(self)
        for w in (QLabel("Piastra"), self.plate_box, self.overlay_box, self.live,
                  self.btn_add, self.btn_undo, self.btn_reset, self.btn_calib, self.status):
            lay.addWidget(w)
        self._frames: list[np.ndarray] = []
        self._load_existing()
        self._refresh()

    # --- stato ---
    def _load_existing(self) -> None:
        if CALIB_FILE.exists():
            try:
                self.result = CalibrationResult.load(CALIB_FILE)
            except Exception:  # noqa: BLE001 - file rovinato: si ricalibra
                self.result = None

    def _refresh(self) -> None:
        n = len(self.calibrator.poses)
        txt = f"Pose acquisite: {n} (ne servono almeno {self.MIN_POSES}, meglio 12-20)."
        if self.result:
            txt += f"\nUltima calibrazione ({self.result.created}):\n{self.result.summary()}"
        elif n < self.MIN_POSES:
            txt += "\nInclina e ruota la piastra a ogni posa; copri tutto il campo."
        self.status.setText(txt)
        self.btn_calib.setEnabled(n >= self.MIN_POSES)
        self.btn_undo.setEnabled(n > 0)
        self.btn_reset.setEnabled(n > 0)

    def _on_plate(self, name: str) -> None:
        self.calibrator.pitch = PLATES[name]
        if self.calibrator.poses:
            self.calibrator.reset()
            self.status.setText("Piastra cambiata: pose azzerate.")
        self._refresh()

    # --- frame in arrivo (chiamato dalla finestra principale) ---
    def feed(self, frames: list[np.ndarray]) -> None:
        self._frames = frames
        if not self.overlay_box.isChecked() or len(frames) < 2:
            self._dets = [None, None]
            self.live.setText("")
            return
        self._skip = (self._skip + 1) % 5          # il rilevamento costa: ~4 volte al secondo
        if self._skip == 0:
            self._dets = [detect_plate(f) for f in frames[:2]]
            ok = [d is not None for d in self._dets]
            common = (len(set(self._dets[0].grid) & set(self._dets[1].grid)) if all(ok) else 0)
            self.live.setText(f"Piastra: sinistra {'sì' if ok[0] else 'NO'}, "
                              f"destra {'sì' if ok[1] else 'NO'} | anelli in comune: {common}")

    def annotate(self, gray: np.ndarray, cam: int) -> np.ndarray | None:
        """Frame BGR con gli anelli rilevati, oppure None se il rilevamento è spento."""
        det = self._dets[cam] if self.overlay_box.isChecked() else None
        if det is None:
            return None
        vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        for (x, y) in det.grid.values():
            cv2.circle(vis, (int(x), int(y)), 5, (0, 255, 0), -1)
        for name, p in zip("BCA", det.markers):
            cv2.putText(vis, name, (int(p[0]) - 10, int(p[1]) + 10), cv2.FONT_HERSHEY_SIMPLEX,
                        1.4, (0, 0, 255), 3, cv2.LINE_AA)
        return vis

    # --- azioni ---
    def capture(self, frames: list[np.ndarray]) -> tuple[bool, str]:
        if len(frames) < 2:
            return False, "Servono due camere attive."
        ok, msg, _, _ = self.calibrator.add_pair(frames[0], frames[1])
        self.status.setText(msg)
        if ok:
            self.result = None                        # le pose sono cambiate: vecchio risultato superato
            self._refresh()
            self.status.setText(msg + "\n" + self.status.text())
        return ok, msg

    def _on_add(self) -> None:
        self.capture(self._frames)

    def _on_undo(self) -> None:
        if self.calibrator.poses:
            self.calibrator.poses.pop()
        self._refresh()

    def _on_reset(self) -> None:
        self.calibrator.reset()
        self._refresh()

    def _on_calibrate(self) -> None:
        try:
            self.result = self.calibrator.calibrate()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Calibrazione", f"Calibrazione non riuscita:\n{exc}")
            return
        self.result.save(CALIB_FILE)
        worst = int(np.argmax(self.result.per_pose_error)) + 1
        self._refresh()
        quality = ("ottima" if self.result.rms_stereo < 0.3 else
                   "buona" if self.result.rms_stereo < 0.6 else "scarsa: rifai le pose peggiori")
        self.status.setText(self.status.text() + f"\nQualità {quality}. Posa peggiore: {worst}.\n"
                            f"Salvata in {CALIB_FILE}")
