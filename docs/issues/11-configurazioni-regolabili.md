# Camere su un arco con distanza regolabile: più configurazioni di calibrazione
Labels: calibrazione, ui

Secondo quanto riferito dall'utente (da confermare con una misura), le due camere si trovano su
una **semicirconferenza** e la distanza tra loro è **regolabile, da circa 100 a 500 mm**, sempre
puntate verso il centro. Il manuale parla di campi di scansione da 200, 300, 400 e 500 mm.

Ogni volta che si sposta una camera **la calibrazione stereo non vale più** e va rifatta.
Con la distanza cambia anche l'**angolo tra le camere** (da pochi gradi fino a diverse decine),
quindi cambia quanta parte della piastra vedono entrambe.

## Geometria dell'arco
Il raggio non si può misurare a mano: **si ricava dalla calibrazione**. Il riepilogo
(`CalibrationResult.summary()`) riporta distanza tra le camere, angolo tra gli assi ottici e
raggio dell'arco equivalente (corda / 2 sin(angolo/2)).
- [ ] Calibrare a 100 e a 500 mm e annotare in `devices/devices.json` i valori ricavati.
- [ ] Verificare se le camere si muovono simmetricamente o una sola (dalla posa della piastra
      rispetto a ciascuna camera).

## Conseguenze per il software
- [ ] **Simulazione con basi larghe**: `tools/test_calibration.py` usa 80 mm. Aggiungere scenari
      con 100 e 500 mm su arco (camere simmetriche, toe-in fino a ~40° ciascuna) e verificare che
      rilevamento dei marcatori L, indici e calibrazione reggano. Con angoli grandi la piastra è
      molto scorciata in una camera: la soglia `min_common` (15 anelli) potrebbe non bastare.
- [ ] Salvare **più calibrazioni**, ognuna con un nome (es. "campo 200 mm"): oggi
      `calibration/stereo.json` viene sovrascritto.
- [ ] Interfaccia: scelta della configurazione attiva; avviso se la distanza stimata dalla
      calibrazione (`T`) non coincide con quella attesa, cioè le camere sono state mosse.
- [ ] Controllo di coerenza: `|T|` deve cadere nell'intervallo 100-500 mm.
- [ ] Scelta della piastra in base al campo (manuale: piccola < 150x120 mm, media fino a
      250x200 mm, grande oltre).
- [ ] Il rilevamento deve reggere anelli molto piccoli (campo grande) o molto grandi (campo piccolo).
- [ ] Con basi larghe la fase delle frange è più sensibile alla geometria: tenerne conto nella
      ricostruzione.
