# Scanner 3D

Software aperto per scanner 3D a luce strutturata: due camere Basler USB3 e un
proiettore DMD collegato come secondo monitor. Funziona su Windows e Linux.

Stato: in sviluppo. Per ora c'è l'anteprima delle camere (esposizione e guadagno per
camera), il controllo del proiettore e il salvataggio di coppie di immagini.
Calibrazione e ricostruzione 3D sono da fare.

## Avvio

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m scanner3d.app
```

Chiudi altri programmi che usano le camere: le aprono in modo esclusivo.

## Test (richiedono l'hardware collegato)

```
set PYTHONPATH=.
python tools\test_app.py
```
