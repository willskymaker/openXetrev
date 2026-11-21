"""Pattern a codice Gray e decodifica: per ogni pixel di camera, quale colonna (o riga) del
proiettore lo illumina.

È la prima parte di docs/issues/03 (ricostruzione a frange).

Due livelli:
- solo codice Gray: la posizione è nota a meno di una striscia (grossolana);
- codice Gray + phase shifting: la fase di frange sinusoidali dà la posizione sotto il pixel
  del proiettore, il codice Gray serve solo a sapere in quale periodo ci si trova.

Tutte le coordinate sono in "indici di pixel": il centro del pixel i del proiettore è i.

Compromesso velocità/precisione: `bits` è un parametro. Con meno bit servono meno immagini
(bits + 2 con i riferimenti bianco/nero), ma le strisce sono più larghe e la posizione è più
grossolana. Il massimo utile è `max_bits(size)`: oltre, le strisce sarebbero più strette di
un pixel del proiettore.
"""
from __future__ import annotations

import numpy as np


def max_bits(size: int) -> int:
    """Numero di bit oltre il quale le strisce sono più strette di 1 pixel del proiettore."""
    if size < 2:
        raise ValueError("size deve essere almeno 2")
    return int(np.ceil(np.log2(size)))


def n_images(bits: int) -> int:
    """Immagini da proiettare e catturare: `bits` pattern + bianco + nero."""
    return bits + 2


def stripe_width_px(bits: int, size: int) -> float:
    """Larghezza di una striscia in pixel del proiettore."""
    return size / float(1 << bits)


def _check_bits(bits: int, size: int) -> None:
    if not 1 <= bits <= max_bits(size):
        raise ValueError(f"bits deve essere tra 1 e {max_bits(size)} per size={size}, ricevuto {bits}")


def gray_code_patterns(width: int, height: int, bits: int, axis: str = "x") -> np.ndarray:
    """Pattern binari (0/255), array (bits, height, width) uint8, dal bit più significativo.

    axis="x": strisce verticali (codificano la colonna); axis="y": strisce orizzontali.
    """
    if axis not in ("x", "y"):
        raise ValueError("axis deve essere 'x' o 'y'")
    size = width if axis == "x" else height
    _check_bits(bits, size)
    pos = np.arange(size, dtype=np.int64)
    stripe = (pos * (1 << bits)) // size
    gray = stripe ^ (stripe >> 1)
    out = np.empty((bits, height, width), dtype=np.uint8)
    for i in range(bits):
        line = ((gray >> (bits - 1 - i)) & 1).astype(np.uint8) * 255
        out[i] = line[None, :] if axis == "x" else line[:, None]
    return out


def reference_patterns(width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    """Immagine tutta bianca e tutta nera, per soglia e maschera di qualità."""
    return (np.full((height, width), 255, np.uint8), np.zeros((height, width), np.uint8))


def decode_gray(images, white, black, min_contrast: float = 20.0) -> tuple[np.ndarray, np.ndarray]:
    """Decodifica le immagini della camera.

    images: sequenza di `bits` immagini della camera (stesso ordine dei pattern).
    white, black: immagini della camera con proiettore tutto bianco / tutto nero.
    min_contrast: sotto questo contrasto (bianco - nero) il pixel non è affidabile
                  (ombra, nero assoluto, fuori dal campo del proiettore).

    Ritorna (code, valid): indice della striscia per pixel (int64) e maschera booleana.
    Dove `valid` è False il valore di `code` non va usato.
    """
    stack = np.asarray(images, dtype=np.float64)
    if stack.ndim != 3:
        raise ValueError("images deve avere forma (bits, H, W)")
    bits = stack.shape[0]
    w = np.asarray(white, dtype=np.float64)
    b = np.asarray(black, dtype=np.float64)
    if w.shape != stack.shape[1:] or b.shape != stack.shape[1:]:
        raise ValueError("white e black devono avere la stessa forma delle immagini")
    threshold = (w + b) / 2.0
    valid = (w - b) >= min_contrast
    bit_planes = stack > threshold[None]
    gray = np.zeros(threshold.shape, dtype=np.int64)
    for i in range(bits):
        gray = (gray << 1) | bit_planes[i].astype(np.int64)
    # Da codice Gray a binario
    code = gray.copy()
    mask = gray >> 1
    while np.any(mask):
        code ^= mask
        mask >>= 1
    return code, valid


def code_to_coordinate(code, bits: int, size: int):
    """Coordinata del proiettore (centro della striscia) per un indice di striscia."""
    return (np.asarray(code, dtype=np.float64) + 0.5) * size / float(1 << bits)


# ---------------------------------------------------------------------------------------
# Phase shifting + fase assoluta
# ---------------------------------------------------------------------------------------

def gray_center_index(code, bits: int, size: int):
    """Come `code_to_coordinate`, ma in indici di pixel (centro del pixel i = i)."""
    return code_to_coordinate(code, bits, size) - 0.5


def phase_shift_patterns(width: int, height: int, period_px: float, steps: int = 4,
                         axis: str = "x") -> np.ndarray:
    """Frange sinusoidali I_k = 0.5 + 0.5 cos(2 pi x / period + 2 pi k / steps), come uint8.

    Array (steps, height, width). Più `steps`, meno sensibili al rumore; 4 è il minimo
    comune, 3 il minimo assoluto.
    """
    if axis not in ("x", "y"):
        raise ValueError("axis deve essere 'x' o 'y'")
    if steps < 3:
        raise ValueError("steps deve essere almeno 3")
    if period_px < 4:
        raise ValueError("period_px deve essere almeno 4 pixel")
    size = width if axis == "x" else height
    pos = np.arange(size, dtype=np.float64)
    phi = 2.0 * np.pi * pos / float(period_px)
    out = np.empty((steps, height, width), dtype=np.uint8)
    for k in range(steps):
        line = np.rint((0.5 + 0.5 * np.cos(phi + 2.0 * np.pi * k / steps)) * 255.0).astype(np.uint8)
        out[k] = line[None, :] if axis == "x" else line[:, None]
    return out


def decode_phase(images, min_modulation: float = 10.0):
    """Fase avvolta per pixel dalle immagini con frange sfasate.

    Ritorna (phase, modulation, valid): fase in [0, 2 pi), ampiezza delle frange nel pixel
    (in livelli di grigio) e maschera dei pixel con modulazione >= `min_modulation`.
    """
    stack = np.asarray(images, dtype=np.float64)
    if stack.ndim != 3 or stack.shape[0] < 3:
        raise ValueError("images deve avere forma (steps >= 3, H, W)")
    steps = stack.shape[0]
    delta = 2.0 * np.pi * np.arange(steps) / steps
    s = np.tensordot(np.sin(delta), stack, axes=(0, 0))
    c = np.tensordot(np.cos(delta), stack, axes=(0, 0))
    phase = np.mod(np.arctan2(-s, c), 2.0 * np.pi)
    modulation = (2.0 / steps) * np.hypot(s, c)
    return phase, modulation, modulation >= min_modulation


def absolute_coordinate(phase, x_gray_index, period_px: float):
    """Coordinata assoluta del proiettore (indice di pixel) da fase avvolta e codice Gray.

    Il codice Gray dà una stima grossolana x_gray; la fase la affina scegliendo il periodo
    intero che la rende più vicina. Funziona se l'errore del codice Gray è sotto mezzo
    periodo: usa strisce Gray larghe al massimo mezzo periodo (vedi `images_needed`).
    """
    frac = np.asarray(phase, dtype=np.float64) / (2.0 * np.pi)
    n = np.rint((np.asarray(x_gray_index, dtype=np.float64) - period_px * frac) / period_px)
    return period_px * (n + frac)


def images_needed(size: int, period_px: float, steps: int = 4,
                  with_references: bool = False) -> tuple[int, int]:
    """(bit Gray, immagini totali) per una dimensione `size` del proiettore.

    Le strisce Gray devono essere larghe al massimo mezzo periodo. Le immagini di riferimento
    (bianco e nero) non servono se si usa `decode_gray_from_phase`: la media delle immagini
    sfasate fa le veci della soglia.
    """
    bits = 1
    while stripe_width_px(bits, size) > period_px / 2.0:
        bits += 1
        if bits > max_bits(size):
            raise ValueError("periodo troppo piccolo per questa dimensione")
    return bits, bits + steps + (2 if with_references else 0)


def decode_gray_from_phase(gray_images, phase_images, min_modulation: float = 10.0):
    """Decodifica Gray senza immagini bianco/nero, usando le immagini sfasate.

    La media delle immagini sfasate è la soglia (bianco + nero) / 2 e la modulazione è
    (bianco - nero) / 2, purché i pattern sfasati coprano l'intero intervallo 0..255.
    Ritorna (code, valid).
    """
    stack = np.asarray(phase_images, dtype=np.float64)
    _, modulation, _ = decode_phase(stack, min_modulation=min_modulation)
    mean = stack.mean(axis=0)
    return decode_gray(gray_images, mean + modulation, mean - modulation,
                       min_contrast=2.0 * min_modulation)
