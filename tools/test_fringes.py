"""Test dei pattern a codice Gray, senza hardware.

La camera è simulata: ogni pixel vede una posizione nota del proiettore, con luce ambiente,
rumore, riflettanza variabile e una zona in ombra. Si controlla che la decodifica ritrovi la
posizione vera entro i limiti attesi dalla teoria (mezza striscia, più un pixel di
arrotondamento) e che la zona in ombra venga scartata.

    set PYTHONPATH=.   (PowerShell: $env:PYTHONPATH=".")
    python tools/test_fringes.py
"""
import sys

import cv2
import numpy as np

from scanner3d.fringes import (
    code_to_coordinate,
    decode_gray,
    gray_code_patterns,
    max_bits,
    n_images,
    reference_patterns,
    stripe_width_px,
)

fails = []
PW, PH = 1280, 800  # proiettore (devices/devices.json)


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


def simulate_camera(pattern, xp, yp, albedo, ambient, noise, rng, interp):
    """Immagine della camera: ambiente + riflettanza * pattern campionato nel punto visto."""
    sampled = cv2.remap(pattern, xp.astype(np.float32), yp.astype(np.float32), interp)
    img = ambient + albedo * (0.7 * sampled.astype(np.float64))
    img = img + rng.normal(0.0, noise, img.shape)
    return np.clip(img, 0, 255)


print("== proprieta' dei pattern")
p6 = gray_code_patterns(PW, PH, 6)
check("forma e tipo", p6.shape == (6, PH, PW) and p6.dtype == np.uint8, str(p6.shape))
check("solo 0 e 255", set(np.unique(p6)) <= {0, 255})
# Proprieta' del codice Gray: tra colonne adiacenti cambia al piu' un pattern
diff = (np.diff(p6[:, 0, :].astype(np.int32), axis=1) != 0).sum(axis=0)
check("colonne adiacenti differiscono al massimo di 1 bit", diff.max() <= 1, f"max {diff.max()}")
py = gray_code_patterns(PW, PH, 5, axis="y")
check("axis='y': strisce orizzontali", np.all(py[:, :, 0:1] == py[:, :, 5:6]))
check("max_bits 1280 = 11, 800 = 10", max_bits(1280) == 11 and max_bits(800) == 10)
check("bits fuori scala rifiutati", raises(ValueError, lambda: gray_code_patterns(PW, PH, 12)))
check("bits 0 rifiutato", raises(ValueError, lambda: gray_code_patterns(PW, PH, 0)))
check("axis non valido rifiutato", raises(ValueError, lambda: gray_code_patterns(PW, PH, 4, axis="z")))
check("n_images = bits + 2", n_images(8) == 10)

print("== andata e ritorno esatta (camera = proiettore, senza rumore)")
white, black = reference_patterns(PW, PH)
for bits in range(1, max_bits(PW) + 1):
    pats = gray_code_patterns(PW, PH, bits)
    code, valid = decode_gray(pats, white, black)
    pos = np.arange(PW)
    atteso = (pos * (1 << bits)) // PW
    ok = valid.all() and np.array_equal(code[0], atteso)
    if not ok:
        check(f"bits={bits}: decodifica esatta", False)
check("decodifica esatta per bits da 1 a 11", not any("decodifica esatta" in f for f in fails))

print("== camera simulata con rumore, ambiente e ombra")
rng = np.random.default_rng(7)
CW, CH = 480, 360
u, v = np.meshgrid(np.arange(CW), np.arange(CH))
xp = 100.0 + 2.2 * u + 0.1 * v  # colonna del proiettore vista dal pixel (u, v)
yp = 50.0 + 1.8 * v
albedo = 0.6 + 0.4 * np.sin(u / 40.0) ** 2  # riflettanza non uniforme
albedo[100:180, 200:300] = 0.01  # zona in ombra
ambient = 12.0
results = {}
for bits in (7, 10):
    pats = gray_code_patterns(PW, PH, bits)
    wh, bl = reference_patterns(PW, PH)
    cam_w = simulate_camera(wh, xp, yp, albedo, ambient, 2.0, rng, cv2.INTER_LINEAR)
    cam_b = simulate_camera(bl, xp, yp, albedo, ambient, 2.0, rng, cv2.INTER_LINEAR)
    cam = [simulate_camera(p, xp, yp, albedo, ambient, 2.0, rng, cv2.INTER_LINEAR) for p in pats]
    code, valid = decode_gray(cam, cam_w, cam_b, min_contrast=20.0)
    coord = code_to_coordinate(code, bits, PW)
    err = np.abs(coord - xp)
    sw = stripe_width_px(bits, PW)
    results[bits] = (err[valid].mean(), err[valid].max(), valid.mean(), sw)
    check(f"bits={bits}: zona in ombra scartata", not valid[100:180, 200:300].any())
    check(f"bits={bits}: almeno 90% dei pixel illuminati validi",
          valid[~(albedo < 0.1)].mean() > 0.9, f"{valid[~(albedo < 0.1)].mean():.3f}")
    # Teoria: errore medio ~ un quarto di striscia, errore massimo ~ una striscia (un bit
    # sbagliato sul bordo sposta di una sola striscia grazie al codice Gray)
    check(f"bits={bits}: errore medio <= mezza striscia + 1 px",
          err[valid].mean() <= sw / 2 + 1.0, f"{err[valid].mean():.2f} px, striscia {sw:.1f} px")
    check(f"bits={bits}: errore massimo <= 1,5 strisce + 1 px",
          err[valid].max() <= 1.5 * sw + 1.0, f"{err[valid].max():.2f} px")

print("== compromesso velocita'/precisione")
for bits, (m, mx, frac, sw) in results.items():
    print(f"     bits={bits}: {n_images(bits)} immagini, striscia {sw:.1f} px, "
          f"errore medio {m:.2f} px, massimo {mx:.2f} px, validi {frac:.3f}")
check("meno bit = meno immagini", n_images(7) < n_images(10))
check("meno bit = errore medio maggiore", results[7][0] > results[10][0],
      f"{results[7][0]:.2f} > {results[10][0]:.2f}")

print()
if fails:
    print(f"FALLITI {len(fails)}: {fails}")
    sys.exit(1)
print("tutto ok")
