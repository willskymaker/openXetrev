# Calibrazione dell'asse della tavola e allineamento delle viste
Labels: calibrazione, ricostruzione

Per fondere scansioni a angoli diversi serve conoscere l'asse di rotazione della tavola nel
sistema delle camere, oppure allineare le viste tra loro.

## Da fare
- [ ] Calibrazione dell'asse: piastra appoggiata sulla tavola, scansione a più angoli, adattare
      un cerchio ai centri degli anelli (asse = normale al piano del cerchio per il suo centro).
- [ ] Allineamento a marcatori: gli anelli della piastra danno una trasformazione esatta tra viste.
- [ ] Allineamento ICP (`open3d.pipelines.registration`) per rifinire, partendo dall'asse.
- [ ] Fusione delle viste e controllo dell'errore residuo.

## Senza hardware
Simulare una tavola con asse noto e viste dello stesso oggetto a angoli diversi; verificare che
l'asse e l'allineamento vengano ritrovati. Dipende dal protocollo della tavola solo per la parte
reale (issue sul protocollo).
