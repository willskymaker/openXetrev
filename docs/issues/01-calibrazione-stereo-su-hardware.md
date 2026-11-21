# Calibrazione stereo: provarla sullo scanner reale
Labels: calibrazione, serve-hardware

Il codice (`scanner3d/calibration.py`, pannello in `calibration_panel.py`) è completo e testato
in simulazione (`tools/test_calibration.py`): sui dati simulati ritrova focale entro 0,01% e
distanza tra le camere entro 0,01%. Manca la prova sullo scanner vero.

## Da fare (serve lo scanner)
- [ ] Piastra MediumField montata, proiettore **bianco** per illuminarla (Pattern "Bianco").
- [ ] Esposizione per camera in modo che gli anelli siano ben contrastati (luminosità media ~110).
- [ ] Spunta "Mostra rilevamento": devono comparire i punti verdi e le lettere B, C, A sui tre cerchi grandi.
- [ ] Acquisire 12-20 pose **inclinando e ruotando** la piastra (±25°), coprendo tutto il campo.
- [ ] "Calcola calibrazione": errore stereo atteso < 0,3 px. Se è più alto, guardare quale posa è la peggiore.
- [ ] Verificare il passo vero della piastra (7,5 mm per MediumField; vedi `devices/devices.json`).
- [ ] Confrontare la distanza tra le camere con una misura a mano.

## Senza hardware
Si può già sviluppare con `tests/data/plate_cam0.png` e `plate_cam1.png` e con la simulazione.
Idee: rilevamento più robusto con luce irregolare (bordo d'ombra del proiettore), calibrazione
con piastre parzialmente visibili, uso delle posizioni misurate della piastra (file
`masters/*.xml` di Vertex Pro) al posto della griglia ideale.

Il risultato viene salvato in `calibration/stereo.json` (non versionato).
