"""Test della calibrazione senza hardware.

1. Immagini reali salvate in tests/data: il rilevamento deve trovare i marcatori e gli indici.
2. Simulazione: due camere con parametri noti vedono la piastra in molte pose; la
   calibrazione deve ritrovare i parametri veri.

    set PYTHONPATH=.   (PowerShell: $env:PYTHONPATH=".")
    python tools/test_calibration.py
"""
import sys
from pathlib import Path

import cv2
import numpy as np

from scanner3d.calibration import StereoCalibrator, detect_plate

ROOT = Path(__file__).resolve().parents[1]
fails = []


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        fails.append(name)


# ---------------------------------------------------------------- 1. immagini reali
print("== immagini reali")
dets = []
for i in (0, 1):
    img = cv2.imread(str(ROOT / "tests" / "data" / f"plate_cam{i}.png"), cv2.IMREAD_GRAYSCALE)
    det = detect_plate(img)
    check(f"cam{i}: piastra riconosciuta", det is not None)
    dets.append(det)
if all(dets):
    d0, d1 = dets
    check("cam0: almeno 100 anelli con indice", len(d0) >= 100, str(len(d0)))
    check("cam1: almeno 100 anelli con indice", len(d1) >= 100, str(len(d1)))
    common = set(d0.grid) & set(d1.grid)
    check("anelli in comune tra le camere >= 60", len(common) >= 60, str(len(common)))
    # I tre marcatori devono avere gli indici (0,0), (2,0), (0,1) in entrambe le camere
    for nome, d in (("cam0", d0), ("cam1", d1)):
        for key, p in zip([(0, 0), (2, 0), (0, 1)], d.markers):
            q = np.array(d.grid[key])
            check(f"{nome}: indice {key} sul marcatore", np.linalg.norm(q - p) < 2.0)
    # Gli stessi anelli, visti dalle due camere, devono avere sensatamente la stessa posizione
    # relativa: la distanza tra (0,0) e (2,0) è ~2 passi in entrambe
    for nome, d in (("cam0", d0), ("cam1", d1)):
        s = np.linalg.norm(np.array(d.grid[(2, 0)]) - np.array(d.grid[(0, 0)])) / 2
        check(f"{nome}: passo in pixel plausibile (80-140)", 80 < s < 140, f"{s:.1f}")

# ---------------------------------------------------------------- 2. simulazione
print("\n== simulazione con parametri noti")
W, H = 1920, 1200
PITCH = 7.5
K_true = [np.array([[3200, 0, 963], [0, 3200, 598], [0, 0, 1]], float),
          np.array([[3250, 0, 958], [0, 3250, 603], [0, 0, 1]], float)]
D_true = [np.array([-0.08, 0.05, 0, 0, 0.0]), np.array([-0.06, 0.03, 0, 0, 0.0])]
C1 = np.array([80.0, 0, 0])
al = np.arctan2(80, 250)
Rs = np.array([[np.cos(al), 0, np.sin(al)], [0, 1, 0], [-np.sin(al), 0, np.cos(al)]])
Ts = -Rs @ C1
MARKERS = {(0, 0), (2, 0), (0, 1)}
rng = np.random.default_rng(7)


def rot(axis, a):
    c, s = np.cos(a), np.sin(a)
    return {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
            "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]


def render(R0, t0, cam):
    """Immagine della piastra vista dalla camera `cam` (0 o 1)."""
    img = np.full((H, W), 170, np.uint8)
    th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for i in range(-14, 15):
        for j in range(-12, 13):
            big = (i, j) in MARKERS
            for r, col in (((0.38 if big else 0.19) * PITCH, 30), ((0.09 if big else 0.115) * PITCH, 170)):
                pl = np.stack([i * PITCH + r * np.cos(th), j * PITCH + r * np.sin(th), np.zeros_like(th)], 1)
                pc = pl @ R0.T + t0
                if cam == 1:
                    pc = (pc - C1) @ Rs.T
                if (pc[:, 2] < 50).any():
                    continue
                px, _ = cv2.projectPoints(pc.reshape(-1, 1, 3), np.zeros(3), np.zeros(3),
                                          K_true[cam], D_true[cam])
                px = px.reshape(-1, 2)
                if px[:, 0].max() < 0 or px[:, 0].min() > W or px[:, 1].max() < 0 or px[:, 1].min() > H:
                    continue
                cv2.fillPoly(img, [np.round(px * 16).astype(np.int32)], col, cv2.LINE_AA, shift=4)
    img = cv2.GaussianBlur(img, (0, 0), 0.8)
    noisy = img.astype(np.float32) + rng.normal(0, 1.5, img.shape)
    return np.clip(noisy, 0, 255).astype(np.uint8)


def truth_px(R0, t0, cam, key):
    p = np.array([[key[0] * PITCH, key[1] * PITCH, 0.0]]) @ R0.T + t0
    if cam == 1:
        p = (p - C1) @ Rs.T
    px, _ = cv2.projectPoints(p.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), K_true[cam], D_true[cam])
    return px.reshape(2)


Rb = np.diag([1.0, -1.0, -1.0])
cal = StereoCalibrator(pitch_mm=PITCH)
index_err = []
unjustified = []
N_POSES = 14
for n in range(N_POSES):
    R0 = (rot("x", np.radians(rng.uniform(-28, 28))) @ rot("y", np.radians(rng.uniform(-28, 28)))
          @ Rb @ rot("z", np.radians(rng.uniform(-40, 40))))
    t0 = np.array([rng.uniform(-15, 15), rng.uniform(-10, 10), rng.uniform(225, 275)])
    imgs = [render(R0, t0, 0), render(R0, t0, 1)]
    ok, msg, d0, d1 = cal.add_pair(*imgs)
    print(f"  posa {n + 1:2d}: {msg}")
    if not ok:
        # Rifiuto giusto solo se almeno un marcatore grande è fuori dall'immagine di una camera
        vis = all(40 < truth_px(R0, t0, c, k)[0] < W - 40 and 40 < truth_px(R0, t0, c, k)[1] < H - 40
                  for c in (0, 1) for k in MARKERS)
        print(f"          marcatori tutti visibili in entrambe le camere: {vis}")
        if vis:
            unjustified.append(n + 1)
            from scanner3d.calibration import assign_grid, detect_rings, find_markers
            for c in (0, 1):
                rr = detect_rings(imgs[c])
                big = rr[rr[:, 2] > 1.45 * np.median(rr[:, 2])] if len(rr) else rr
                mk = find_markers(rr)
                print(f"          cam{c}: anelli {len(rr)}, raggio mediano "
                      f"{np.median(rr[:, 2]) if len(rr) else 0:.1f}, grandi {len(big)}, "
                      f"marcatori L {'ok' if mk is not None else 'NO'}, "
                      f"griglia {None if mk is None else (len(g) if (g := assign_grid(rr, mk)) else 0)}")
            cv2.imwrite(str(ROOT / "probe_out" / f"sim_fail_pose{n + 1}_cam1.png"), imgs[1])
    if ok:
        for cam, d in enumerate((d0, d1)):
            for key in ((0, 0), (3, 2), (-2, -3)):
                if key in d.grid:
                    index_err.append(np.linalg.norm(np.array(d.grid[key]) - truth_px(R0, t0, cam, key)))

check("nessun rifiuto con i marcatori visibili", not unjustified, f"pose rifiutate a torto: {unjustified}")
check("almeno 10 pose su 14 accettate", len(cal.poses) >= 10, f"{len(cal.poses)}")
check("indici corretti (errore < 1.5 px sui punti di controllo)",
      len(index_err) > 20 and max(index_err) < 1.5,
      f"max {max(index_err):.2f} px su {len(index_err)} punti")

res = cal.calibrate()
print("  " + res.summary())
for cam, (K, dist) in enumerate(((res.K0, res.dist0), (res.K1, res.dist1))):
    fx_err = abs(K[0, 0] / K_true[cam][0, 0] - 1) * 100
    pp_err = np.linalg.norm(K[:2, 2] - K_true[cam][:2, 2])
    check(f"cam{cam}: focale entro 1%", fx_err < 1.0, f"errore {fx_err:.2f}%")
    check(f"cam{cam}: punto principale entro 6 px", pp_err < 6.0, f"errore {pp_err:.1f} px")
base_true = np.linalg.norm(Ts)
check("distanza tra le camere entro 0,5%", abs(res.baseline_mm / base_true - 1) < 0.005,
      f"{res.baseline_mm:.2f} vs {base_true:.2f} mm")
ang = np.degrees(np.arccos(np.clip((np.trace(res.R @ Rs.T) - 1) / 2, -1, 1)))
check("rotazione tra le camere entro 0,2 gradi", ang < 0.2, f"{ang:.3f} gradi")
ang_true = np.degrees(al)                       # toe-in della camera 1 rispetto alla 0
rad_true = 80.0 / (2 * np.sin(al / 2))          # raggio dell'arco equivalente
check("angolo tra le camere entro 0,2 gradi", abs(res.angle_deg - ang_true) < 0.2,
      f"{res.angle_deg:.2f} vs {ang_true:.2f}")
check("raggio dell'arco entro 1%", abs(res.arc_radius_mm / rad_true - 1) < 0.01,
      f"{res.arc_radius_mm:.1f} vs {rad_true:.1f} mm")
check("errore di riproiezione < 0,4 px", max(res.rms0, res.rms1, res.rms_stereo) < 0.4,
      f"{res.rms0:.3f} / {res.rms1:.3f} / {res.rms_stereo:.3f}")

# salvataggio e ricarica
out = ROOT / "probe_out" / "calib_test.json"
res.save(out)
from scanner3d.calibration import CalibrationResult  # noqa: E402
back = CalibrationResult.load(out)
check("salvataggio e ricarica identici", np.allclose(back.K0, res.K0) and np.allclose(back.T, res.T))

# poche pose: deve rifiutare
few = StereoCalibrator(pitch_mm=PITCH)
few.poses = cal.poses[:3]
few.image_size = (W, H)
try:
    few.calibrate()
    check("rifiuta con poche pose", False)
except ValueError:
    check("rifiuta con poche pose", True)

print("\nRISULTATO:", "TUTTO OK" if not fails else f"FALLITI: {fails}")
sys.exit(1 if fails else 0)
