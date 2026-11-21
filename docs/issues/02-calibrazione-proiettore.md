# Calibrazione del proiettore (modello camera inverso)
Labels: calibrazione, ricostruzione

Per triangolare con la luce strutturata serve conoscere il proiettore (il Dell M318WL, 1280x800,
visto come secondo monitor) come una "camera inversa": matrice K, distorsione e posa rispetto
alle camere.

## Approccio proposto
1. Con la piastra in posa nota (già calibrate le camere, issue #1), proiettare frange sinusoidali
   e/o codice Gray in orizzontale e verticale.
2. Decodificare, per ogni pixel della camera, la coordinata (x, y) nel proiettore.
3. Per i punti della piastra (centri degli anelli) prendere la coordinata proiettore interpolata:
   si ottiene l'analogo di `imagePoints` per il proiettore.
4. `cv2.calibrateCamera` + `cv2.stereoCalibrate` camera <-> proiettore, per più pose.

## Senza hardware
Estendere la simulazione di `tools/test_calibration.py`: un proiettore virtuale che proietta
pattern sulla piastra simulata, e verificare che la calibrazione ritrovi i parametri veri.
Dipende dal decodificatore di fase (issue sulla ricostruzione a frange).

## Note
Il proiettore ha un tempo di riscaldamento (Vertex Pro usa 60 s): la luminosità e la deriva
termica influenzano la fase. Misurare la stabilità prima di calibrare.
