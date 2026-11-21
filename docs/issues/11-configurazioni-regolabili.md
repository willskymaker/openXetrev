# Distanza tra le camere regolabile: più configurazioni di calibrazione
Labels: calibrazione, ui

Secondo quanto riferito dall'utente (da confermare con una misura), la distanza tra le camere
è **regolabile, da circa 100 a 500 mm**. Il manuale parla di campi di scansione da 200, 300,
400 e 500 mm per la testa a due camere. Ogni volta che si cambia la posizione delle camere,
**la calibrazione stereo non vale più**: va rifatta.

## Conseguenze per il software
- [ ] Salvare più calibrazioni, ognuna con un nome (es. "campo 200 mm"), non un solo
      `calibration/stereo.json`. Oggi viene sovrascritto.
- [ ] Nell'interfaccia: scelta della configurazione attiva e avviso se l'ultima calibrazione è
      più vecchia dell'ultima modifica dell'hardware (o se la distanza stimata non coincide).
- [ ] Controllo di coerenza: la distanza tra le camere ricavata dalla calibrazione (`T`) deve
      cadere nell'intervallo 100-500 mm, altrimenti segnalare un errore.
- [ ] Scelta della piastra in base al campo (manuale: piccola < 150x120 mm, media fino a
      250x200 mm, grande oltre): suggerirla in base alla calibrazione precedente.
- [ ] Il rilevamento della piastra deve reggere anche con anelli molto piccoli (campo grande) o
      molto grandi (campo piccolo): provare con la simulazione variando focale e distanza.

## Da confermare
Che cosa significa esattamente "variabile da 500 a 100": distanza tra le camere, distanza dalla
piastra, o campo di scansione? Misurare e correggere questa issue e `devices/devices.json`.
