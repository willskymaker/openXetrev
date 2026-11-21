"""Tavola rotante: interfaccia comune, simulatore e backend seriale (non ancora funzionante).

Il protocollo seriale della tavola reale NON è noto (vedi docs/issues/04). Per questo:
- `SimulatedTurntable` permette di sviluppare e testare il flusso di scansione senza hardware;
- `SerialTurntable` non invia nessun comando: ogni movimento solleva `ProtocolUnknownError`,
  così la tavola non può muoversi per sbaglio finché il protocollo non è documentato.

Tutte le implementazioni hanno la stessa interfaccia (`Turntable`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class TurntableError(Exception):
    """Errore generico della tavola."""


class ProtocolUnknownError(TurntableError):
    """Il protocollo dei comandi non è ancora stato ricavato: nessun comando viene inviato."""


class LimitError(TurntableError):
    """Angolo richiesto fuori dai limiti consentiti."""


@runtime_checkable
class Turntable(Protocol):
    """Interfaccia minima che il flusso di scansione si aspetta da una tavola."""

    @property
    def angle(self) -> float:
        """Angolo corrente in gradi, rispetto alla posizione di home."""

    @property
    def is_homed(self) -> bool: ...

    def home(self) -> None:
        """Ricerca della posizione zero. Va fatta prima di ogni scansione."""

    def rotate_to(self, degrees: float) -> None:
        """Ruota fino all'angolo assoluto indicato (rispetto alla home)."""

    def rotate_by(self, degrees: float) -> None:
        """Ruota di un angolo relativo a quello corrente."""

    def wait_idle(self, timeout_s: float = 30.0) -> None:
        """Torna solo quando la tavola è ferma."""


def rotation_plan(positions: int, step_deg: float, start_deg: float = 0.0) -> list[float]:
    """Angoli assoluti di una scansione a giro: `positions` viste distanziate di `step_deg`.

    Esempio: positions=8, step_deg=30 (valori usati da Vertex Pro) copre 210 gradi.
    Meno posizioni e passo più largo sono più veloci ma lasciano zone non viste.
    """
    if positions < 1:
        raise ValueError("positions deve essere almeno 1")
    if step_deg <= 0:
        raise ValueError("step_deg deve essere positivo")
    return [start_deg + i * step_deg for i in range(positions)]


def coverage_deg(positions: int, step_deg: float) -> float:
    """Angolo totale spazzato dalla sequenza di viste (da prima a ultima, escluso il campo di vista)."""
    return max(0, positions - 1) * step_deg


@dataclass
class SimulatedTurntable:
    """Tavola simulata, senza porta seriale.

    `deg_per_s` e `settle_s` sono parametri della simulazione, NON misure della tavola
    reale: servono a confrontare piani di scansione tra loro, non a prevedere i tempi veri.
    Il tempo è simulato (nessuna attesa reale): si legge in `elapsed_s`.
    """

    deg_per_s: float = 30.0
    settle_s: float = 0.5
    limit_min_deg: float | None = None
    limit_max_deg: float | None = None
    elapsed_s: float = 0.0
    history: list[tuple[str, float]] = field(default_factory=list)
    _angle: float = 0.0
    _homed: bool = False

    @property
    def angle(self) -> float:
        return self._angle

    @property
    def is_homed(self) -> bool:
        return self._homed

    def home(self) -> None:
        # Si assume una ricerca di home che, in media, costa un mezzo giro
        self.elapsed_s += 180.0 / self.deg_per_s
        self._angle = 0.0
        self._homed = True
        self.history.append(("home", 0.0))

    def rotate_to(self, degrees: float) -> None:
        if not self._homed:
            raise TurntableError("tavola non in home: chiama home() prima di muovere")
        if self.limit_min_deg is not None and degrees < self.limit_min_deg:
            raise LimitError(f"{degrees} sotto il limite {self.limit_min_deg}")
        if self.limit_max_deg is not None and degrees > self.limit_max_deg:
            raise LimitError(f"{degrees} sopra il limite {self.limit_max_deg}")
        self.elapsed_s += abs(degrees - self._angle) / self.deg_per_s + self.settle_s
        self._angle = float(degrees)
        self.history.append(("rotate_to", self._angle))

    def rotate_by(self, degrees: float) -> None:
        self.rotate_to(self._angle + degrees)

    def wait_idle(self, timeout_s: float = 30.0) -> None:
        # Il movimento simulato è istantaneo: la tavola è sempre ferma
        return None


class SerialTurntable:
    """Tavola reale via USB/FTDI (COM, 115200 baud 8N1, nessun controllo di flusso).

    Protocollo non noto: questa classe NON apre la porta e NON invia comandi. È un segnaposto
    che rispetta l'interfaccia, da completare dopo aver documentato i comandi
    (docs/issues/04-tavola-rotante-protocollo.md).
    """

    def __init__(self, port: str = "COM3", baud: int = 115200) -> None:
        self.port = port
        self.baud = baud

    @property
    def angle(self) -> float:
        raise ProtocolUnknownError("lettura dell'angolo non implementata: protocollo ignoto")

    @property
    def is_homed(self) -> bool:
        return False

    def home(self) -> None:
        raise ProtocolUnknownError("home non implementato: protocollo ignoto")

    def rotate_to(self, degrees: float) -> None:
        raise ProtocolUnknownError("rotate_to non implementato: protocollo ignoto")

    def rotate_by(self, degrees: float) -> None:
        raise ProtocolUnknownError("rotate_by non implementato: protocollo ignoto")

    def wait_idle(self, timeout_s: float = 30.0) -> None:
        raise ProtocolUnknownError("wait_idle non implementato: protocollo ignoto")


def run_scan_sequence(table: Turntable, angles: list[float], on_position=None) -> list[float]:
    """Porta la tavola in home e poi su ogni angolo, chiamando `on_position(angle)` a tavola ferma.

    `on_position` è dove il chiamante proietta i pattern e cattura le immagini.
    Ritorna gli angoli effettivamente raggiunti.
    """
    table.home()
    reached: list[float] = []
    for a in angles:
        table.rotate_to(a)
        table.wait_idle()
        if on_position is not None:
            on_position(table.angle)
        reached.append(table.angle)
    return reached
