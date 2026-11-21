"""Calibrazione stereo con la piastra di anelli.

La piastra (MediumField: passo 7,5 mm) è una griglia regolare di anelli neri su fondo
chiaro. Tre marcatori più grandi, a forma di L con rami da 1 e da 2 passi, fissano
origine e orientamento: così ogni anello ha un indice intero (i, j) e quindi una
posizione 3D nota (i*passo, j*passo, 0), indipendente dalla porzione di piastra inquadrata.

Sistema di coordinate della piastra:
    B = vertice della L          -> (0, 0)
    C = fine del ramo lungo      -> (2, 0)   (asse u)
    A = fine del ramo corto      -> (0, 1)   (asse v)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

Grid = dict[tuple[int, int], tuple[float, float]]


# --------------------------------------------------------------------------- rilevamento
def detect_rings(gray: np.ndarray, min_area: float = 80.0) -> np.ndarray:
    """Trova gli anelli. Ritorna un array Nx3 con (x, y, raggio) in pixel."""
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    blur = cv2.GaussianBlur(gray, (0, 0), 1.2)
    bw = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 101, 10)
    contours, hier = cv2.findContours(bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return np.empty((0, 3))
    hier = hier[0]
    rings = []
    for i, c in enumerate(contours):
        if hier[i][3] != -1 or len(c) < 20:      # solo contorni esterni con almeno 20 punti
            continue
        child = hier[i][2]
        if child == -1:
            continue
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        x, y, bw_, bh = cv2.boundingRect(c)
        if x <= 1 or y <= 1 or x + bw_ >= w - 1 or y + bh >= h - 1:  # tagliati dal bordo
            continue
        # buco interno più grande tra i figli
        best, best_area = None, 0.0
        while child != -1:
            a = cv2.contourArea(contours[child])
            if a > best_area and len(contours[child]) >= 5:
                best, best_area = contours[child], a
            child = hier[child][0]
        if best is None or not (0.02 < best_area / area < 0.7):
            continue
        (cxo, cyo), (ao, bo), _ = cv2.fitEllipse(c)
        (cxi, cyi), _, _ = cv2.fitEllipse(best)
        if min(ao, bo) / max(ao, bo) < 0.45:
            continue
        rings.append(((cxo + cxi) / 2, (cyo + cyi) / 2, np.sqrt(ao * bo) / 2))
    return np.array(rings, dtype=np.float64).reshape(-1, 3)


def find_markers(rings: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Individua i tre marcatori grandi e li ordina come (B, C, A). None se non trovati."""
    if len(rings) < 12:
        return None
    # Un marcatore è "grande" rispetto ai suoi vicini, non rispetto a tutta l'immagine:
    # con la piastra inclinata gli anelli vicini alla camera appaiono più grandi di quelli lontani.
    xy, r = rings[:, :2], rings[:, 2]
    dist = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2)
    np.fill_diagonal(dist, np.inf)
    nearest = np.argsort(dist, axis=1)[:, :10]
    ratio = r / np.median(r[nearest], axis=1)
    top = np.argsort(ratio)[::-1][:4]
    if ratio[top[2]] < 1.4 or (len(top) > 3 and ratio[top[3]] > 0.85 * ratio[top[2]]):
        return None                                  # non ci sono esattamente tre marcatori netti
    pts = xy[top[:3]]
    best = None
    for v in range(3):
        o = [k for k in range(3) if k != v]
        a, b = pts[o[0]] - pts[v], pts[o[1]] - pts[v]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if min(na, nb) < 1:
            continue
        score = abs(max(na, nb) / min(na, nb) - 2.0) + abs(a @ b) / (na * nb)
        if best is None or score < best[0]:
            best = (score, v, o, na, nb)
    score, v, o, na, nb = best
    if score > 0.8:                                # tolleranza per la prospettiva
        return None
    short, long_ = (o[0], o[1]) if na < nb else (o[1], o[0])
    return pts[v], pts[long_], pts[short]


@dataclass
class PlateDetection:
    grid: Grid                      # (i, j) -> (x, y) in pixel
    markers: np.ndarray             # 3x2: B, C, A
    n_rings: int

    def __len__(self) -> int:
        return len(self.grid)


def assign_grid(rings: np.ndarray, markers, tol: float = 0.3) -> Grid | None:
    """Assegna a ogni anello il suo indice (i, j) facendo crescere un'omografia dai marcatori."""
    B, C, A = markers
    M = cv2.getAffineTransform(np.float32([[0, 0], [2, 0], [0, 1]]), np.float32([B, C, A]))
    H = np.vstack([M, [0.0, 0.0, 1.0]])           # griglia -> immagine
    pts = rings[:, :2].astype(np.float64).reshape(-1, 1, 2)
    for radius in (4, 7, 11, 16, 26, 60):          # la regione accettata cresce a ogni giro
        g = cv2.perspectiveTransform(pts, np.linalg.inv(H)).reshape(-1, 2)
        idx = np.round(g)
        err = np.linalg.norm(g - idx, axis=1)
        ok = (err < tol) & (np.linalg.norm(idx - np.array([1.0, 0.5]), axis=1) < radius)
        if ok.sum() < 8:
            return None
        order = np.argsort(err)                    # in caso di doppioni vince l'errore minore
        seen, keep = set(), []
        for k in order:
            key = (int(idx[k, 0]), int(idx[k, 1]))
            if ok[k] and key not in seen:
                seen.add(key)
                keep.append(k)
        keep = np.array(keep)
        newH, _ = cv2.findHomography(idx[keep], rings[keep, :2], cv2.RANSAC, 3.0)
        if newH is None:
            return None
        H = newH
    g = cv2.perspectiveTransform(pts, np.linalg.inv(H)).reshape(-1, 2)
    idx, err = np.round(g), np.linalg.norm(g - np.round(g), axis=1)
    grid: Grid = {}
    for k in np.argsort(err):
        key = (int(idx[k, 0]), int(idx[k, 1]))
        if err[k] < tol and key not in grid:
            grid[key] = (float(rings[k, 0]), float(rings[k, 1]))
    return grid


def detect_plate(gray: np.ndarray, min_points: int = 20) -> PlateDetection | None:
    rings = detect_rings(gray)
    markers = find_markers(rings)
    if markers is None:
        return None
    grid = assign_grid(rings, markers)
    if grid is None or len(grid) < min_points:
        return None
    return PlateDetection(grid, np.array(markers), len(rings))


# --------------------------------------------------------------------------- calibrazione
@dataclass
class CalibrationResult:
    image_size: tuple[int, int]
    pitch_mm: float
    K0: np.ndarray
    dist0: np.ndarray
    K1: np.ndarray
    dist1: np.ndarray
    R: np.ndarray                   # camera 0 -> camera 1
    T: np.ndarray                   # mm
    rms0: float
    rms1: float
    rms_stereo: float
    n_poses: int
    per_pose_error: list[float] = field(default_factory=list)
    created: str = ""

    @property
    def baseline_mm(self) -> float:
        return float(np.linalg.norm(self.T))

    def summary(self) -> str:
        return (f"{self.n_poses} pose | errore camere {self.rms0:.3f} / {self.rms1:.3f} px | "
                f"errore stereo {self.rms_stereo:.3f} px | distanza tra le camere {self.baseline_mm:.1f} mm")

    def to_json(self) -> dict:
        return {
            "creato": self.created, "image_size": list(self.image_size),
            "pitch_mm": self.pitch_mm, "n_pose": self.n_poses,
            "K0": self.K0.tolist(), "dist0": self.dist0.ravel().tolist(),
            "K1": self.K1.tolist(), "dist1": self.dist1.ravel().tolist(),
            "R": self.R.tolist(), "T": self.T.ravel().tolist(),
            "rms0": self.rms0, "rms1": self.rms1, "rms_stereo": self.rms_stereo,
            "errore_per_posa": self.per_pose_error,
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), indent=2), encoding="utf-8")

    @staticmethod
    def load(path: str | Path) -> "CalibrationResult":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return CalibrationResult(
            tuple(d["image_size"]), d["pitch_mm"],
            np.array(d["K0"]), np.array(d["dist0"]), np.array(d["K1"]), np.array(d["dist1"]),
            np.array(d["R"]), np.array(d["T"]).reshape(3, 1),
            d["rms0"], d["rms1"], d["rms_stereo"], d["n_pose"],
            d.get("errore_per_posa", []), d.get("creato", ""))


class StereoCalibrator:
    """Raccoglie le pose della piastra viste da entrambe le camere e calcola la calibrazione."""

    MIN_POSES = 8

    def __init__(self, pitch_mm: float = 7.5, min_common: int = 15) -> None:
        self.pitch = pitch_mm
        self.min_common = min_common
        self.poses: list[tuple[Grid, Grid]] = []
        self.image_size: tuple[int, int] | None = None   # (larghezza, altezza)

    def reset(self) -> None:
        self.poses.clear()

    def add_pair(self, img0: np.ndarray, img1: np.ndarray):
        """Prova ad aggiungere una posa. Ritorna (ok, messaggio, det0, det1)."""
        h, w = img0.shape[:2]
        if self.image_size is not None and self.image_size != (w, h):
            return False, "Dimensione immagini diversa dalle pose precedenti.", None, None
        d0, d1 = detect_plate(img0), detect_plate(img1)
        if d0 is None or d1 is None:
            if d0 is None and d1 is None:
                dove = "in nessuna delle due camere"
            else:
                dove = "nella camera " + ("sinistra" if d0 is None else "destra")
            return False, f"Piastra non riconosciuta {dove}: controlla luce e inquadratura " \
                          "(devono vedersi i tre cerchi grandi).", d0, d1
        common = set(d0.grid) & set(d1.grid)
        if len(common) < self.min_common:
            return False, f"Solo {len(common)} anelli in comune tra le due camere (servono almeno " \
                          f"{self.min_common}): avvicina la piastra al centro del campo.", d0, d1
        self.image_size = (w, h)
        self.poses.append((d0.grid, d1.grid))
        return True, f"Posa {len(self.poses)} acquisita: {len(common)} anelli in comune.", d0, d1

    def _obj(self, keys) -> np.ndarray:
        return np.array([[i * self.pitch, j * self.pitch, 0.0] for i, j in keys], np.float32)

    def calibrate(self) -> CalibrationResult:
        if len(self.poses) < self.MIN_POSES:
            raise ValueError(f"Servono almeno {self.MIN_POSES} pose, ne hai {len(self.poses)}.")
        size = self.image_size
        mono = []
        for cam in (0, 1):
            objs, imgs = [], []
            for pose in self.poses:
                g = pose[cam]
                keys = sorted(g)
                objs.append(self._obj(keys))
                imgs.append(np.array([g[k] for k in keys], np.float32).reshape(-1, 1, 2))
            flags = cv2.CALIB_ZERO_TANGENT_DIST | cv2.CALIB_FIX_K3
            rms, K, dist, _, _, _, _, per_view = cv2.calibrateCameraExtended(
                objs, imgs, size, None, None, flags=flags)
            mono.append((rms, K, dist, per_view.ravel()))
        objs, i0, i1 = [], [], []
        for g0, g1 in self.poses:
            keys = sorted(set(g0) & set(g1))
            objs.append(self._obj(keys))
            i0.append(np.array([g0[k] for k in keys], np.float32).reshape(-1, 1, 2))
            i1.append(np.array([g1[k] for k in keys], np.float32).reshape(-1, 1, 2))
        crit = (cv2.TERM_CRITERIA_COUNT + cv2.TERM_CRITERIA_EPS, 100, 1e-7)
        out = cv2.stereoCalibrate(objs, i0, i1, mono[0][1], mono[0][2], mono[1][1], mono[1][2],
                                  size, flags=cv2.CALIB_FIX_INTRINSIC, criteria=crit)
        rms_stereo, R, T = out[0], out[5], out[6]
        per_pose = ((mono[0][3] + mono[1][3]) / 2).tolist()
        return CalibrationResult(size, self.pitch, mono[0][1], mono[0][2], mono[1][1], mono[1][2],
                                 R, T, mono[0][0], mono[1][0], rms_stereo, len(self.poses),
                                 per_pose, time.strftime("%Y-%m-%d %H:%M"))
