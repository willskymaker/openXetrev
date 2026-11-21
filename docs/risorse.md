# Risorse aperte utili

Progetti e documentazione per lo sviluppo. Ogni voce dice se esiste ed è stata verificata,
oppure se è una conoscenza non controllata. **Prima di riusare codice altrui controlla la
licenza**: qui non è stata verificata.

## Verificate (esistono, pubbliche)

| Risorsa | A cosa serve | Note |
|---|---|---|
| [SLStudio](https://github.com/jakobwilm/slstudio/) | Scanner a luce strutturata completo: pattern, decodifica, triangolazione | Da riferimento (secondo la memoria di chi scrive è C++ con Qt, non Python). Licenza da controllare |
| [3DUNDERWORLD-SLS](https://arxiv.org/pdf/1406.6595) | Articolo su un sistema aperto di scansione a luce strutturata | Teoria e calibrazione camera-proiettore |
| [3DScanner-GrayCode](https://www.github.com/guillaume-charron/3DScanner-GrayCode) | Esempio con codice Gray | Semplice da leggere per partire |
| [OpenCV, modulo structured_light](https://docs.opencv.org/5.x/d1/d90/group__structured__light.html) | `GrayCodePattern`, `SinusoidalPattern` | Probabilmente in `opencv-contrib`, non in `opencv-python`: controllare prima di aggiungerlo a `requirements.txt` |
| [pypylon](https://github.com/basler/pypylon) | Controllo delle camere Basler da Python | Wrapper ufficiale Basler |

## Non verificate in questa ricerca

- **Open3D, trimesh, PyVista**: nuvole di punti, mesh e vista 3D (issue 06). Open3D è già in `requirements.txt`.
- **pySerial**: comunicazione con la tavola (issue 04).
- **Wireshark con USBPcap**: osservare la comunicazione di Vertex Pro con la tavola.
- **MeshLab / pymeshlab**: post-elaborazione e decimazione.

## Ordine consigliato

Non aggiungere tutto subito. Per l'obiettivo di velocità: OpenCV (già presente) e SLStudio
come lettura di riferimento; il resto quando una issue lo richiede.
