# Test automatici e integrazione continua
Labels: infrastruttura, senza-hardware

Oggi i test sono script in `tools/` che stampano OK/FAIL. Quelli che non richiedono hardware
(`test_calibration.py`, `test_panel.py`) possono girare automaticamente a ogni push.

## Da fare
- [ ] Convertire i test in `pytest` (cartella `tests/`), tenendo separati quelli con hardware
      (`@pytest.mark.hardware`, esclusi di default).
- [ ] GitHub Actions su Windows e Linux: installare le dipendenze, eseguire i test senza hardware
      con `QT_QPA_PLATFORM=offscreen`.
- [ ] Fotocamera finta (`FakeCameraRig`) che restituisce le immagini di `tests/data`, per provare
      l'interfaccia completa senza scanner.
- [ ] Analisi statica (ruff) e formattazione.
- [ ] Verificare che `tests/data` resti piccolo (due PNG, ~2 MB).
