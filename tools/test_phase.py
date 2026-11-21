"""Test di phase shifting + fase assoluta, senza hardware.

Stessa camera simulata di test_fringes.py: ogni pixel vede una posizione nota del proiettore,
con luce ambiente, rumore, riflettanza variabile e una zona in ombra. Si misura quanto la
coordinata ritrovata si discosta da quella vera e quante immagini servono.

    set PYTHONPATH=.   (PowerShell: $env:PYTHONPATH=".")
    python tools/test_phase.py
"""
import sys

import cv2
import numpy as np

from scanner3d.fringes import (
    absolute_coordinate,
    decode_gray,
    decode_gray_from_phase,
    decode_phase,
    gray_center_index,
    gray_code_patterns,
    images_needed,
    phase_shift_patterns,
    reference_patterns,
    stripe_width_px,
)

fails = []
PW, PH = 1280, 800


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


def simulate_camera(pattern, xp, yp, albedo, ambient, noise, rng):
    sampled = cv2.remap(pattern, xp.astype(np.float32), yp.astype(np.float32), cv2.INTER_LINEAR)
    img = ambient + albedo * (0.7 * sampled.astype(np.float64))
    return np.clip(img + rng.normal(0.0, noise, img.shape), 0, 255)


print("== proprieta' dei pattern sinusoidali")
P = 16.0
ph = phase_shift_patterns(PW, PH, P, steps=4)
check("forma e tipo", ph.shape == (4, PH, PW) and ph.dtype == np.uint8, str(ph.shape))
check("passo 0 in x=0 e' al massimo (255)", ph[0, 0, 0] == 255)
check("passo 0 in x=periodo/2 e' al minimo (0)", ph[0, 0, 8] == 0)
check("la somma dei 4 passi e' costante (media)",
      np.ptp(ph.astype(np.int32).sum(axis=0)[0, :40]) <= 2)
check("steps < 3 rifiutato", raises(ValueError, lambda: phase_shift_patterns(PW, PH, P, steps=2)))
check("periodo < 4 px rifiutato", raises(ValueError, lambda: phase_shift_patterns(PW, PH, 2)))

print("== andata e ritorno (camera = proiettore, senza rumore)")
phase, mod, valid = decode_phase(ph)
bits, _ = images_needed(PW, P)
gray = gray_code_patterns(PW, PH, bits)
white, black = reference_patterns(PW, PH)
code, gvalid = decode_gray(gray, white, black)
xg = gray_center_index(code, bits, PW)
xabs = absolute_coordinate(phase, xg, P)
err = np.abs(xabs[0] - np.arange(PW))
check("tutti i pixel validi", valid.all() and gvalid.all())
check("errore massimo < 0,05 px", err.max() < 0.05, f"{err.max():.4f} px")

print("== camera simulata con rumore, ambiente e ombra")
rng = np.random.default_rng(11)
CW, CH = 480, 360
u, v = np.meshgrid(np.arange(CW), np.arange(CH))
xp = 100.0 + 2.2 * u + 0.1 * v
yp = 50.0 + 1.8 * v
albedo = 0.6 + 0.4 * np.sin(u / 40.0) ** 2
albedo[100:180, 200:300] = 0.01
ambient, noise = 12.0, 2.0
shadow = albedo < 0.1


def acquire(period, steps=4, with_references=False):
    bits, total = images_needed(PW, period, steps, with_references)
    g = [simulate_camera(p, xp, yp, albedo, ambient, noise, rng) for p in gray_code_patterns(PW, PH, bits)]
    f = [simulate_camera(p, xp, yp, albedo, ambient, noise, rng)
         for p in phase_shift_patterns(PW, PH, period, steps)]
    ref = None
    if with_references:
        wh, bl = reference_patterns(PW, PH)
        ref = (simulate_camera(wh, xp, yp, albedo, ambient, noise, rng),
               simulate_camera(bl, xp, yp, albedo, ambient, noise, rng))
    return bits, total, g, f, ref


def reconstruct(period, steps=4, with_references=False):
    bits, total, g, f, ref = acquire(period, steps, with_references)
    phase, mod, pvalid = decode_phase(f, min_modulation=10.0)
    if ref is None:
        code, gvalid = decode_gray_from_phase(g, f, min_modulation=10.0)
    else:
        code, gvalid = decode_gray(g, ref[0], ref[1], min_contrast=20.0)
    xg = gray_center_index(code, bits, PW)
    x = absolute_coordinate(phase, xg, period)
    # Coerenza: Gray e fase devono concordare entro una striscia, altrimenti il pixel e' dubbio
    consistent = np.abs(xg - x) <= stripe_width_px(bits, PW)
    valid = pvalid & gvalid & consistent
    return x, valid, total, bits


tabella = {}
for period in (16.0, 32.0, 64.0):
    x, valid, total, bits = reconstruct(period)
    e = np.abs(x - xp)[valid]
    rms = float(np.sqrt(np.mean(e**2)))
    tabella[period] = (total, rms, float(e.max()), float(valid.mean()))
    check(f"periodo {period:g}: zona in ombra scartata", not valid[shadow].any())
    check(f"periodo {period:g}: >= 90% dei pixel illuminati validi",
          valid[~shadow].mean() >= 0.9, f"{valid[~shadow].mean():.3f}")
    # L'errore di fase e' costante, quindi l'errore in pixel cresce con il periodo: si controlla
    # l'errore relativo al periodo (misurato ~0,33%), non un valore assoluto
    check(f"periodo {period:g}: errore RMS < 1% del periodo", rms < 0.01 * period,
          f"{rms:.3f} px = {100 * rms / period:.2f}%")

print("== senza immagini bianco/nero")
xa, va, ta, _ = reconstruct(16.0, with_references=False)
xb, vb, tb, _ = reconstruct(16.0, with_references=True)
ea = float(np.sqrt(np.mean(np.abs(xa - xp)[va] ** 2)))
eb = float(np.sqrt(np.mean(np.abs(xb - xp)[vb] ** 2)))
check("2 immagini in meno", ta == tb - 2, f"{ta} contro {tb}")
check("precisione paragonabile (entro 0,05 px RMS)", abs(ea - eb) < 0.05,
      f"{ea:.3f} contro {eb:.3f} px")

print("== compromesso velocita'/precisione (periodo delle frange)")
print("     periodo   immagini   errore RMS   errore max   pixel validi")
for period, (total, rms, mx, frac) in tabella.items():
    print(f"     {period:6g} px   {total:5d}      {rms:7.3f} px   {mx:7.3f} px     {frac:.3f}")
check("periodo piu' lungo = meno immagini", tabella[64.0][0] < tabella[16.0][0])
check("periodo piu' lungo = errore RMS maggiore", tabella[64.0][1] > tabella[16.0][1],
      f"{tabella[64.0][1]:.3f} > {tabella[16.0][1]:.3f}")
rel = [tabella[p][1] / p for p in (16.0, 32.0, 64.0)]
check("errore proporzionale al periodo (rapporti entro 25%)", max(rel) / min(rel) < 1.25,
      f"{[round(r, 4) for r in rel]}")

print()
if fails:
    print(f"FALLITI {len(fails)}: {fails}")
    sys.exit(1)
print("tutto ok")
