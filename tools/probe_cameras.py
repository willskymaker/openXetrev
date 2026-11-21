"""Elenca le camere Basler e salva un frame da ciascuna in ./probe_out."""
from pathlib import Path

import cv2
from pypylon import pylon

OUT = Path("probe_out")
OUT.mkdir(exist_ok=True)

factory = pylon.TlFactory.GetInstance()
devices = factory.EnumerateDevices()
print(f"Camere trovate: {len(devices)}")

for i, info in enumerate(devices):
    print(f"[{i}] {info.GetModelName()}  serial={info.GetSerialNumber()}  "
          f"interfaccia={info.GetDeviceClass()}")
    cam = pylon.InstantCamera(factory.CreateDevice(info))
    try:
        cam.Open()
        print(f"    risoluzione {cam.Width.Value}x{cam.Height.Value}, "
              f"pixel format {cam.PixelFormat.Value}")
        cam.StartGrabbingMax(1)
        res = cam.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if res.GrabSucceeded():
            img = res.Array
            path = OUT / f"cam{i}_{info.GetSerialNumber()}.png"
            cv2.imwrite(str(path), img)
            print(f"    frame salvato: {path} ({img.shape}, media {img.mean():.1f})")
        res.Release()
    except Exception as exc:  # noqa: BLE001
        print(f"    ERRORE: {exc}")
    finally:
        cam.Close()
