# Interfaccia semplice: flusso guidato "Scansiona"
Labels: ui, senza-hardware

L'obiettivo è una UI semplice e intuitiva. Oggi la finestra mostra tutti i controlli insieme.

## Proposta
Un flusso a passi, con una sola azione evidente per volta:
1. **Collega**: stato di camere, proiettore e tavola (verde/rosso), con messaggi chiari.
2. **Calibra** (solo se manca o è vecchia): guida le pose con un indicatore "posa 5 di 12" e una
   mappa del campo coperto; avvisa se la posa è troppo simile alle altre.
3. **Prepara**: esposizione automatica per ciascuna camera, anteprima.
4. **Scansiona**: un pulsante, barra di avanzamento, annullamento.
5. **Risultato**: vista 3D e esportazione.

Modalità "avanzata" con i controlli attuali (esposizione, guadagno, pattern) nascosta di default.

## Altri miglioramenti
- [ ] Esposizione/guadagno automatici (target di luminosità) con pulsante "Auto".
- [ ] Ricordare le impostazioni (schermo del proiettore, esposizioni) tra una sessione e l'altra.
- [ ] Traduzione/lingua (oggi in italiano nel codice).
- [ ] Test automatici dell'interfaccia con `QT_QPA_PLATFORM=offscreen` (vedi `tools/test_panel.py`).
