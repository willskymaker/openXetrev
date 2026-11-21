"""Rileva la piastra in un'immagine e salva una copia con l'esito disegnato sopra.

    python tools/detect_demo.py tests/data/plate_cam0.png probe_out/det0.png
"""
import sys

import cv2

from scanner3d.calibration import detect_plate, detect_rings, find_markers

src, dst = sys.argv[1], sys.argv[2]
gray = cv2.imread(src, cv2.IMREAD_GRAYSCALE)
rings = detect_rings(gray)
print(f"anelli trovati: {len(rings)}")
markers = find_markers(rings)
print("marcatori L:", None if markers is None else [tuple(map(float, m.round(1))) for m in markers])
det = detect_plate(gray)
vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
for x, y, r in rings:
    cv2.circle(vis, (int(x), int(y)), int(r + 4), (0, 200, 255), 1)
if det is None:
    print("piastra NON riconosciuta")
else:
    print(f"piastra riconosciuta: {len(det)} anelli con indice")
    for (i, j), (x, y) in det.grid.items():
        cv2.circle(vis, (int(x), int(y)), 3, (0, 255, 0), -1)
        cv2.putText(vis, f"{i},{j}", (int(x) - 14, int(y) - 16), cv2.FONT_HERSHEY_SIMPLEX,
                    0.38, (0, 255, 0), 1, cv2.LINE_AA)
    for name, p in zip("BCA", det.markers):
        cv2.putText(vis, name, (int(p[0]) - 8, int(p[1]) + 8), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 0, 255), 2, cv2.LINE_AA)
cv2.imwrite(dst, vis)
