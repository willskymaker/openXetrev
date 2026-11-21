"""Test del pannello di calibrazione senza camere (usa le immagini in tests/data)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from scanner3d.app import to_pixmap  # noqa: E402
from scanner3d.calibration_panel import CalibrationPanel  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
fails = []


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        fails.append(name)


app = QApplication(sys.argv)
frames = [cv2.imread(str(ROOT / "tests" / "data" / f"plate_cam{i}.png"), cv2.IMREAD_GRAYSCALE)
          for i in (0, 1)]
panel = CalibrationPanel()
check("stato iniziale: 0 pose, calcolo disattivato", len(panel.calibrator.poses) == 0
      and not panel.btn_calib.isEnabled())

# rilevamento live
panel.overlay_box.setChecked(True)
for _ in range(6):
    panel.feed(frames)
check("anteprima: piastra riconosciuta in entrambe", "sinistra sì" in panel.live.text()
      and "destra sì" in panel.live.text(), panel.live.text())
vis = panel.annotate(frames[0], 0)
check("annotazione a colori BGR", vis is not None and vis.ndim == 3 and vis.shape[2] == 3)
check("to_pixmap accetta BGR e grigi", not to_pixmap(vis, 400).isNull() and not to_pixmap(frames[0], 400).isNull())
panel.overlay_box.setChecked(False)
check("senza spunta: nessuna annotazione", panel.annotate(frames[0], 0) is None)

# acquisizione
ok, msg = panel.capture(frames)
check("acquisizione valida", ok and len(panel.calibrator.poses) == 1, msg)
ok, msg = panel.capture([np.full((1200, 1920), 128, np.uint8)] * 2)
check("frame senza piastra rifiutati con messaggio", (not ok) and "non riconosciuta" in msg, msg)
ok, msg = panel.capture(frames[:1])
check("una sola camera rifiutata", not ok, msg)
check("il rifiuto non aggiunge pose", len(panel.calibrator.poses) == 1)

# annulla / azzera / cambio piastra
panel._on_undo()
check("annulla ultima posa", len(panel.calibrator.poses) == 0)
panel.capture(frames)
panel.plate_box.setCurrentIndex(2)
check("cambio piastra azzera le pose e imposta il passo",
      len(panel.calibrator.poses) == 0 and panel.calibrator.pitch == 15.0)
panel.plate_box.setCurrentIndex(0)
check("passo tornato a 7,5 mm", panel.calibrator.pitch == 7.5)
panel.capture(frames)
panel._on_reset()
check("azzera pose", len(panel.calibrator.poses) == 0)

print("\nRISULTATO:", "TUTTO OK" if not fails else f"FALLITI: {fails}")
sys.exit(1 if fails else 0)
