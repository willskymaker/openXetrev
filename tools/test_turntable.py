"""Test del modulo tavola rotante, senza hardware.

    set PYTHONPATH=.   (PowerShell: $env:PYTHONPATH=".")
    python tools/test_turntable.py
"""
import sys

from scanner3d.turntable import (
    LimitError,
    ProtocolUnknownError,
    SerialTurntable,
    SimulatedTurntable,
    Turntable,
    TurntableError,
    coverage_deg,
    rotation_plan,
    run_scan_sequence,
)

fails = []


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        fails.append(name)


def raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


print("== piano di rotazione")
plan = rotation_plan(8, 30)
check("8 posizioni da 30 gradi", plan == [0, 30, 60, 90, 120, 150, 180, 210], str(plan))
check("copertura 210 gradi", coverage_deg(8, 30) == 210)
check("posizioni < 1 rifiutate", raises(ValueError, lambda: rotation_plan(0, 30)))
check("passo <= 0 rifiutato", raises(ValueError, lambda: rotation_plan(4, 0)))

print("== simulatore")
t = SimulatedTurntable()
check("rispetta l'interfaccia Turntable", isinstance(t, Turntable))
check("non in home all'inizio", not t.is_homed)
check("muovere senza home e' vietato", raises(TurntableError, lambda: t.rotate_to(10)))
t.home()
check("dopo home: angolo 0 e in home", t.angle == 0 and t.is_homed)
t.rotate_to(45)
t.rotate_by(15)
check("angolo assoluto e relativo", t.angle == 60, str(t.angle))

lim = SimulatedTurntable(limit_min_deg=-30, limit_max_deg=30)
lim.home()
lim.rotate_to(30)
check("limite superiore incluso", lim.angle == 30)
check("oltre il limite superiore", raises(LimitError, lambda: lim.rotate_to(31)))
check("sotto il limite inferiore", raises(LimitError, lambda: lim.rotate_to(-31)))

print("== sequenza di scansione")
sim = SimulatedTurntable()
visti = []
raggiunti = run_scan_sequence(sim, rotation_plan(8, 30), on_position=visti.append)
check("8 viste catturate", len(visti) == 8, str(len(visti)))
check("angoli raggiunti = piano", raggiunti == rotation_plan(8, 30))
check("home prima del primo movimento", sim.history[0][0] == "home")

print("== piano piu' veloce costa meno (nel simulatore)")
lento = SimulatedTurntable()
run_scan_sequence(lento, rotation_plan(12, 30))
veloce = SimulatedTurntable()
run_scan_sequence(veloce, rotation_plan(6, 60))
check("6 viste da 60 gradi < 12 viste da 30", veloce.elapsed_s < lento.elapsed_s,
      f"{veloce.elapsed_s:.1f}s vs {lento.elapsed_s:.1f}s")

print("== backend seriale: nessun comando inviato")
s = SerialTurntable()
check("rispetta l'interfaccia", isinstance(s, Turntable))
check("home solleva ProtocolUnknownError", raises(ProtocolUnknownError, s.home))
check("rotate_to solleva ProtocolUnknownError", raises(ProtocolUnknownError, lambda: s.rotate_to(10)))
check("angle solleva ProtocolUnknownError", raises(ProtocolUnknownError, lambda: s.angle))

print()
if fails:
    print(f"FALLITI {len(fails)}: {fails}")
    sys.exit(1)
print("tutto ok")
