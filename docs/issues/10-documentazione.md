# Documentazione: hardware, installazione, procedura di calibrazione
Labels: documentazione, senza-hardware

## Da fare
- [ ] `README.md`: descrizione dello scanner (2 camere Basler a2A1920-160umPRO, proiettore DLP
      Dell M318WL via HDMI, tavola rotante FTDI), installazione su Windows e Linux, avvio.
- [ ] `docs/calibrazione.md`: procedura illustrata (piastra, luce, pose, lettura dell'errore).
- [ ] `docs/architettura.md`: moduli (`cameras`, `projector`, `calibration`, `calibration_panel`,
      `app`) e come si collegano.
- [ ] Spiegare cosa c'è in `devices/` e `tests/data/` e come rigenerarli con `tools/dump_devices.py`.
- [ ] Nota sulla licenza (GPL-3.0) e su cosa **non** è nel repository (file `.optconf`, manuali e
      file di Vertex Pro, che restano privati).
