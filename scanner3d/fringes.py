"""Pattern a codice Gray e decodifica: per ogni pixel di camera, quale colonna (o riga) del
proiettore lo illumina.

È la prima parte di docs/issues/03 (ricostruzione a frange). Il phase shifting per
raffinare la posizione sotto la larghezza di una striscia NON è ancora implementato: con il
solo codice Gray la risoluzione è una striscia.

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
