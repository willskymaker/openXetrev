# Compatibilità Linux
Labels: linux

L'obiettivo è che tutto funzioni su Windows e Linux.

## Da verificare
- [ ] `pypylon` su Linux (esistono wheel per x86_64 e aarch64) e regole `udev` per le camere
      Basler USB3: senza, le camere si vedono solo da root.
- [ ] Proiettore come secondo schermo: comportamento di `ProjectorWindow` su X11 e Wayland
      (su Wayland il posizionamento delle finestre è limitato: valutare `QT_QPA_PLATFORM=xcb`).
- [ ] Porta seriale della tavola: `/dev/ttyUSB0`, gruppo `dialout`; rendere configurabile
      la porta (oggi non esiste ancora il modulo, vedi issue sulla tavola).
- [ ] Impostazione USB3: `usbcore.usbfs_memory_mb=1000` per evitare perdita di frame.
- [ ] Percorsi e codifica dei file (nessun percorso con `\`).
- [ ] Documentare l'installazione in `README.md`.

## Senza hardware
Si possono già eseguire su Linux `tools/test_calibration.py` e `tools/test_panel.py`
(non servono camere).
