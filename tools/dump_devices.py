"""Salva i settaggi dei dispositivi (camere, proiettore) e immagini di riferimento.

Serve per continuare a sviluppare senza avere lo scanner a disposizione.
Uso (con lo scanner collegato e Vertex Pro chiuso):
    python tools/dump_devices.py [cartella_privata]

Scrive in devices/ (versionato) e in <cartella_privata>/ (NON versionato: file pfs
completi e immagini a piena risoluzione).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from pypylon import genicam, pylon

from scanner3d.projector import ProjectorWindow

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "devices"
PRIV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "scanner3d_private"
(DEV / "cameras").mkdir(parents=True, exist_ok=True)
(PRIV / "cameras").mkdir(parents=True, exist_ok=True)
(PRIV / "images").mkdir(parents=True, exist_ok=True)

FEATURES = [
    "DeviceModelName", "DeviceVendorName", "DeviceFirmwareVersion", "DeviceSerialNumber",
    "SensorWidth", "SensorHeight", "Width", "Height", "OffsetX", "OffsetY",
    "BinningHorizontal", "BinningVertical", "DecimationHorizontal",
    "PixelFormat", "ExposureAuto", "ExposureTime", "GainAuto", "Gain", "BlackLevel",
    "Gamma", "TriggerMode", "TriggerSource", "TriggerActivation",
    "AcquisitionFrameRateEnable", "AcquisitionFrameRate", "AcquisitionMode",
    "DeviceLinkThroughputLimitMode", "DeviceLinkThroughputLimit",
    "UserSetSelector", "UserSetDefault", "SensorBitDepth", "PixelSize",
    "LineSelector", "LineSource", "DeviceTemperature",
]


def read_feature(cam, name):
    try:
        node = getattr(cam, name)
        if not genicam.IsReadable(node.GetNode()):
            return None
        v = node.Value
        return v if isinstance(v, (int, float, str, bool)) else str(v)
    except Exception:  # noqa: BLE001
        return None


def dump_cameras() -> list[dict]:
    factory = pylon.TlFactory.GetInstance()
    out = []
    for dev in sorted(factory.EnumerateDevices(), key=lambda d: d.GetSerialNumber()):
        cam = pylon.InstantCamera(factory.CreateDevice(dev))
        cam.Open()
        serial = dev.GetSerialNumber()
        pfs = PRIV / "cameras" / f"{serial}.pfs"
        pylon.FeaturePersistence.Save(str(pfs), cam.GetNodeMap())
        info = {n: read_feature(cam, n) for n in FEATURES}
        info = {k: v for k, v in info.items() if v is not None}
        info["_usb"] = dev.GetDeviceClass()
        out.append(info)
        cam.Close()
        print(f"camera {serial}: {len(info)} parametri, pfs -> {pfs}")
    return out


def dump_screens(app) -> list[dict]:
    res = []
    for i, s in enumerate(QGuiApplication.screens()):
        g = s.geometry()
        res.append({
            "index": i, "name": s.name(), "manufacturer": s.manufacturer(),
            "model": s.model(), "x": g.x(), "y": g.y(), "width": g.width(),
            "height": g.height(), "refresh_hz": s.refreshRate(),
            "physical_mm": [round(s.physicalSize().width(), 1), round(s.physicalSize().height(), 1)],
            "device_pixel_ratio": s.devicePixelRatio(), "primary": s == app.primaryScreen(),
        })
    return res


def grab_reference_images(app, screens: list[dict]) -> dict:
    """Proietta bianco e salva coppie di immagini a esposizioni diverse."""
    from scanner3d.cameras import CameraRig

    proj_idx = 1 if len(screens) > 1 else 0
    proj = ProjectorWindow()
    proj.show_on_screen(proj_idx)
    proj.show_level(255)
    QTest.qWait(1500)
    rig = CameraRig()
    rig.open()
    summary = {}
    best = None
    for exp in (3000, 6000, 12000, 24000):
        for i in range(len(rig.infos)):
            rig.set_exposure_us(i, exp)
            rig.set_gain_db(i, 0)
        QTest.qWait(500)
        for _ in range(3):  # scarta i frame vecchi
            frames = rig.grab()
        means = [float(f.mean()) for f in frames]
        summary[str(exp)] = means
        for i, f in enumerate(frames):
            cv2.imwrite(str(PRIV / "images" / f"cam{i}_exp{exp}.png"), f)
        score = max(abs(m - 110) for m in means)
        if best is None or score < best[0]:
            best = (score, exp, frames)
        print(f"esposizione {exp} us: luminosita' media {means}")
    _, exp, frames = best
    (ROOT / "tests" / "data").mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(frames):
        cv2.imwrite(str(ROOT / "tests" / "data" / f"plate_cam{i}.png"), f)
    summary["scelta_per_test"] = exp
    rig.close()
    proj.hide()
    return summary


def main() -> None:
    app = QApplication(sys.argv)
    data = {
        "salvato_il": time.strftime("%Y-%m-%d %H:%M"),
        "nota": "Stato corrente delle camere al momento del salvataggio, non i valori di Vertex Pro.",
        "camere": dump_cameras(),
    }
    screens = dump_screens(app)
    data["schermi"] = screens
    data["immagini_riferimento"] = grab_reference_images(app, screens)
    (DEV / "devices.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("scritto", DEV / "devices.json")


if __name__ == "__main__":
    main()
