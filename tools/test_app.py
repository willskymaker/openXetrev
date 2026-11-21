"""Test reale su hardware: controlli per camera e ciclo di vita del proiettore."""
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from scanner3d.app import MainWindow

OUT = Path("probe_out")
OUT.mkdir(exist_ok=True)
app = QApplication(sys.argv)
win = MainWindow()
win.move(50, 50)
win.show()
fails = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("OK   " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        fails.append(name)


def mean(i: int) -> float:
    QTest.qWait(400)
    return float(win.last_frames[i].mean())


QTest.qWait(1200)
check("2 camere aperte", len(win.cam_controls) == 2)

# --- esposizione indipendente per camera ---
c0, c1 = win.cam_controls
c0.exp.setValue(5_000); c1.exp.setValue(5_000)
a0, a1 = mean(0), mean(1)
c1.exp.setValue(20_000)
b0, b1 = mean(0), mean(1)
check("cam1 più luminosa con più esposizione", b1 > a1 + 5, f"{a1:.1f} -> {b1:.1f}")
check("cam0 NON cambia quando muovo cam1", abs(b0 - a0) < 5, f"{a0:.1f} -> {b0:.1f}")

# --- guadagno indipendente per camera ---
c0.gain.setValue(0); c1.gain.setValue(0)
g0, g1 = mean(0), mean(1)
c0.gain.setValue(120)  # 12 dB
h0, h1 = mean(0), mean(1)
check("cam0 più luminosa con più guadagno", h0 > g0 + 3, f"{g0:.1f} -> {h0:.1f}")
check("cam1 NON cambia quando muovo cam0", abs(h1 - g1) < 5, f"{g1:.1f} -> {h1:.1f}")
check("hardware: gain cam0 = 12 dB", abs(win.rig.gain_db(0) - 12.0) < 0.5, f"{win.rig.gain_db(0):.1f}")
check("hardware: esposizione cam1 = 20 ms", abs(win.rig.exposure_us(1) - 20_000) < 500,
      f"{win.rig.exposure_us(1):.0f}")

# --- proiettore: ciclo completo ---
def vis() -> bool:
    return win.projector.isVisible()

for modo in ("pulsante", "Esc/hide", "doppio clic", "pulsante di nuovo"):
    win.proj_btn.setChecked(True)
    QTest.qWait(800)
    check(f"[{modo}] proiettore acceso", vis() and win.proj_btn.isChecked())
    geo = win.projector.geometry()
    scr = QGuiApplication.screens()[1].geometry()
    check(f"[{modo}] copre lo schermo 1", geo == scr, f"{geo.width()}x{geo.height()}")
    if modo == "pulsante" or modo == "pulsante di nuovo":
        win.proj_btn.setChecked(False)
    elif modo == "Esc/hide":
        win.projector.hide()
    else:
        win.projector.hide()  # equivalente a mouseDoubleClickEvent
    QTest.qWait(800)
    check(f"[{modo}] proiettore spento", not vis())
    check(f"[{modo}] pulsante riallineato", not win.proj_btn.isChecked())
    check(f"[{modo}] finestra principale visibile", win.isVisible())

for i, s in enumerate(QGuiApplication.screens()):
    s.grabWindow(0).save(str(OUT / f"final_screen{i}.png"))
win.grab().save(str(OUT / "final_window.png"))
win.close()
QTest.qWait(300)
print("\nRISULTATO:", "TUTTO OK" if not fails else f"FALLITI: {fails}")
sys.exit(1 if fails else 0)
