# Tavola rotante: ricavare il protocollo seriale
Labels: hardware, serve-hardware

La tavola è collegata via USB con un convertitore FTDI (VID 0403, PID 6001), vista come COM3,
**115200 baud, 8N1**, nessun controllo di flusso (vedi `devices/devices.json`). Il protocollo
dei comandi **non è noto**.

## Da fare
- [ ] Registrare la comunicazione seriale mentre Vertex Pro muove la tavola (monitor seriale per
      COM3, o cattura USB con USBPcap + Wireshark). Annotare i comandi per: ricerca della
      posizione zero ("home"), rotazione di un angolo, velocità, lettura dello stato.
- [ ] Documentare i comandi in `docs/tavola-protocollo.md` con esempi.
- [ ] Modulo `scanner3d/turntable.py` con interfaccia `home()`, `rotate_to(gradi)`, `wait_idle()`.
- [ ] **Simulatore** della tavola (stessa interfaccia, nessuna porta) per sviluppare e testare
      il flusso di scansione senza hardware.

## Attenzione
**Non inviare comandi a caso alla tavola**: si muove. Prima osservare, poi provare comandi
corti e reversibili con la tavola vuota e libera.

Parametri usati da Vertex Pro (in `devices/devices.json`): passo 30°, 8 posizioni, velocità 2,
limiti ±30°, ricerca di home prima della scansione, ritardo 2 s.
