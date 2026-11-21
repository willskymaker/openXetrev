"""Test reale: accende/spegne il proiettore e fotografa gli schermi in ogni fase."""
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


def snap(tag: str) -> None:
    for i, s in enumerate(QGuiApplication.screens()):
        s.grabWindow(0).save(str(OUT / f"{tag}_screen{i}.png"))
    vis = [w.windowTitle() or type(w).__name__ for w in QApplication.topLevelWidgets()
           if w.isVisible()]
    print(f"[{tag}] finestre visibili: {vis}")


QTest.qWait(1500)
snap("1_avvio")
win.proj_btn.setChecked(True)
QTest.qWait(1500)
snap("2_acceso")
win.proj_btn.setChecked(False)
QTest.qWait(1500)
snap("3_spento")
win.close()
QTest.qWait(500)
snap("4_chiuso")
