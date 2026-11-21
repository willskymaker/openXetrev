# Ricostruzione 3D con frange: proiezione, decodifica di fase, triangolazione
Labels: ricostruzione, senza-hardware

Cuore dello scanner: da una sequenza di pattern proiettati e dalle due camere calibrate si ricava
una nuvola di punti.

## Da fare
- [ ] Generatore di pattern: frange sinusoidali a più frequenze (phase shifting, 4 passi) + codice
      Gray per risolvere l'ambiguità di fase; proiezione a risoluzione nativa 1280x800 con
      `ProjectorWindow.show_gray`.
- [ ] Acquisizione sincronizzata: proiettare, attendere che l'immagine sia a schermo (latenza del
      proiettore), catturare da entrambe le camere. Misurare la latenza reale.
- [ ] Decodifica: fase assoluta per pixel, maschera di qualità (modulazione).
- [ ] Triangolazione: corrispondenze camera sinistra <-> destra tramite la fase (anche senza
      calibrare il proiettore) con `cv2.triangulatePoints`; poi variante camera <-> proiettore.
- [ ] Nuvola di punti `open3d.geometry.PointCloud`, filtro dei punti isolati.
- [ ] Esportazione PLY.

## Senza hardware (consigliato per iniziare da casa)
Sviluppare tutto su una **scena simulata**: stessa tecnica di `tools/test_calibration.py`, ma con
un oggetto 3D (sfera, piano inclinato) illuminato da frange. Errore atteso: sotto 0,1 mm sulla
sfera. Si possono usare i parametri reali in `devices/devices.json` e quelli di calibrazione veri
quando saranno disponibili.
