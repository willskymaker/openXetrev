"""Gestione delle due camere Basler (coppia stereo)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pypylon import pylon


@dataclass
class CameraInfo:
    index: int
    model: str
    serial: str


class CameraRig:
    """Apre tutte le camere Basler collegate e le legge in modo continuo."""

    def __init__(self) -> None:
        self._cams: list[pylon.InstantCamera] = []
        self.infos: list[CameraInfo] = []

    def open(self) -> None:
        factory = pylon.TlFactory.GetInstance()
        devices = sorted(factory.EnumerateDevices(), key=lambda d: d.GetSerialNumber())
        if not devices:
            raise RuntimeError("Nessuna camera Basler trovata.")
        for i, dev in enumerate(devices):
            cam = pylon.InstantCamera(factory.CreateDevice(dev))
            cam.Open()
            cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            self._cams.append(cam)
            self.infos.append(CameraInfo(i, dev.GetModelName(), dev.GetSerialNumber()))

    def close(self) -> None:
        for cam in self._cams:
            if cam.IsGrabbing():
                cam.StopGrabbing()
            if cam.IsOpen():
                cam.Close()
        self._cams.clear()
        self.infos.clear()

    def set_exposure_us(self, index: int, microseconds: float) -> None:
        cam = self._cams[index]
        try:
            cam.ExposureAuto.Value = "Off"
        except Exception:  # noqa: BLE001 - non tutte le camere lo espongono
            pass
        lo, hi = cam.ExposureTime.Min, cam.ExposureTime.Max
        cam.ExposureTime.Value = float(min(max(microseconds, lo), hi))

    def exposure_range_us(self, index: int) -> tuple[float, float]:
        cam = self._cams[index]
        return float(cam.ExposureTime.Min), float(min(cam.ExposureTime.Max, 200_000))

    def exposure_us(self, index: int) -> float:
        return float(self._cams[index].ExposureTime.Value)

    def set_gain_db(self, index: int, gain: float) -> None:
        cam = self._cams[index]
        try:
            cam.GainAuto.Value = "Off"
        except Exception:  # noqa: BLE001
            pass
        lo, hi = cam.Gain.Min, cam.Gain.Max
        cam.Gain.Value = float(min(max(gain, lo), hi))

    def gain_range_db(self, index: int) -> tuple[float, float]:
        cam = self._cams[index]
        return float(cam.Gain.Min), float(cam.Gain.Max)

    def gain_db(self, index: int) -> float:
        return float(self._cams[index].Gain.Value)

    def grab(self, timeout_ms: int = 1000) -> list[np.ndarray]:
        """Ultimo frame di ogni camera (immagini Mono8)."""
        frames = []
        for cam in self._cams:
            res = cam.RetrieveResult(timeout_ms, pylon.TimeoutHandling_ThrowException)
            try:
                if not res.GrabSucceeded():
                    raise RuntimeError(res.ErrorDescription)
                frames.append(res.Array.copy())
            finally:
                res.Release()
        return frames
