# STRADA - Sistema Trafficologico di Rilievo e Analisi Dati Associati

STRADA è una piattaforma web integrata per l'analisi e la visualizzazione dei dati sul traffico, gli incidenti stradali, le condizioni meteorologiche e i flussi dei trasporti nella città di New York (NYC).

---

## 1. Architettura e Organizzazione del Progetto

Il progetto è strutturato secondo un'architettura modulare a tre livelli: **Integrazione Dati (ETL)**, **Database Relazionale Cloud** e **Applicazione Web (Dashboard)**.

### Estrazione e Struttura dei File:
* **`inserimento_dati.py`**: Lo script Python principale incaricato dell'estrazione dei file CSV, della trasformazione al volo dei tipi di dato e del caricamento batch all'interno del database Oracle Cloud.
* **`app.py`**: Il server web sviluppato con Flask. Gestisce la logica di business, riceve i parametri inviati dall'utente, esegue le query SQL sul database e restituisce le pagine web dinamiche.
* **`crea_DB.py`**: Script per l'inizializzazione della struttura del database e delle tabelle relazionali.
* **`templates/`**: Cartella contenente i file HTML (`index.html`, `dashboard.html`, ecc.) che definiscono l'interfaccia utente visiva, i moduli di filtro e i contenitori per i grafici e le tabelle.
* **`static/`**: Contiene le risorse grafiche, i fogli di stile CSS per il layout e gli script JavaScript per il rendering dei grafici interattivi.
* **`dati/`**: Directory locale destinata al posizionamento dei file CSV originali e puliti.

---

## 2. Gestione e Dimensione dei Dati (CSV & Pulizia)

### I Dataset Gestiti:
1. **Collisioni Stradali (`nypd-motor-vehicle-collisions_pulito.csv`)**: Registrazioni dettagliate degli incidenti con coordinate geografiche, fattori contribuenti, feriti e veicoli coinvolti.
2. **Volumi di Traffico (`Automated_Traffic_Volume_Counts_pulito.csv`)**: Conteggi automatizzati del flusso dei veicoli distribuiti per varie arterie stradali e fasce orarie.
3. **Dati Meteorologici (`NYC_Central_Park_weather_1869-2022.csv`)**: Registrazioni storiche del meteo (pioggia, neve, temperature) rilevate a Central Park.
4. **Trasporti e Taxi (`Taxi_2016-01_pulito.csv`)**: Dati sui flussi di mobilità e spostamenti urbani.

### Perché il Modulo Nativo `csv` invece di `Pandas` per l'Inserimento?
Mentre **Pandas** è stato utilizzato nelle fasi preliminari per l'esplorazione e la prima pulizia, la fase di caricamento massivo nel Database Oracle è stata affidata al modulo nativo **`csv`** di Python abbinato alla vettorializzazione di `oracledb`.
* **Efficienza della Memoria RAM**: `Pandas` carica l'intero dataset (milioni di righe) in memoria prima dell'elaborazione. Per CSV di grandi dimensioni, questo può causare il saturamento della memoria (Out of Memory). Il modulo `csv` legge il file linea per linea tramite uno *stream* continuo.
* **Processamento a Blocchi (Chunking / Bulk Insert)**: Utilizzando lo streaming del modulo `csv`, lo script crea blocchi di `20.000` righe per volta trasmettendole al DB. Ciò garantisce un'occupazione di memoria costante e minima, con un'elevata velocità di trasmissione.

---

## 3. Database ed Integrazione con Oracle Cloud

I dati vengono salvati e gestiti su un'istanza cloud **Oracle Autonomous Database**.

### Differenze Chiave tra Dialetto MySQL e Oracle SQL nel Progetto:
* **Segnaposto dei Parametri (Bind Variables)**:
  * In MySQL si utilizza solitamente la sintassi `%s` o `?`.
  * In Oracle SQL si utilizzano i segnaposto numerati o nominati come `:1, :2, :3`.
* **Funzioni di Gestione Data e Ora**:
  * In Oracle la conversione esplicita da stringa a data avviene tramite `TO_DATE('2026-01-01', 'YYYY-MM-DD')` o `TO_TIMESTAMP(...)`, anziché `STR_TO_DATE()` di MySQL.
* **Tipi di Dato ed Esecuzione Bulk**:
  * In Oracle i valori vuoti o spazi nelle stringhe vengono interpretati rigorosamente; lo script gestisce quindi l'equivalente `None` di Python affinché venga registrato il valore SQL `NULL` ed evitare errori di conversioni di tipo.
* **Impaginazione dei Risultati**:
  * In Oracle si utilizza la sintassi `FETCH FIRST N ROWS ONLY` anziché la clausola `LIMIT N` usata in MySQL.

---

## 4. Applicazione Web con Flask (Interazione GET & POST)

L'applicazione si basa sul framework leggero **Flask**, che fa da ponte tra le richieste del browser dell'utente e il database Oracle.

### Come Funziona lo Scambio Dati (GET vs POST):
1. **Richiesta GET (Visualizzazione e Filtri)**:
   * Quando l'utente visita la pagina principale o seleziona un filtro (es. un intervallo di date o un quartiere), il browser invia una richiesta `GET`.
   * Flask legge i parametri dall'URL, formula una query SQL verso Oracle Cloud, formatta i dati e restituisce la pagina HTML con i risultati richiesti.
2. **Richiesta POST (Invio Moduli e Interazioni Complessa)**:
   * Quando l'utente compila un modulo form (es. invia una query personalizzata o parametri di analisi complessi), i dati vengono impacchettati nel corpo della richiesta HTTP `POST`.
   * Flask elabora questi dati senza esporli direttamente nell'URL, aggiorna la sessione o interroga il DB e restituisce un feedback aggiornato all'utente.

---

## 5. Analisi dei Dati e Query al Database

La pagina web presenta diverse sezioni analitiche che permettono di comprendere il comportamento del traffico e degli incidenti a New York:

* **Analisi della Sicurezza Stradale**: Mappe e conteggi sulle zone con il maggior numero di incidenti, incrociati con i principali fattori causali (es. distrazione del conducente, precedenza non rispettata).
* **Correlazione Meteo - Incidenti**: Confronto tra il volume degli incidenti e le giornate con precipitazioni piovose o nevose rilevate dalla stazione meteo di Central Park.
* **Evoluzione Temporale e Flussi**: Grafici che mostrano come variano i volumi di traffico e le corse dei taxi nelle diverse ore del giorno e nei giorni della settimana.

---

## 6. Tempistiche e Prestazioni

L'architettura del sistema è stata ottimizzata per ridurre al minimo i tempi d'attesa:

* **Pulizia e Inserimento Bulk**: Grazie alla lettura a blocchi di `20.000` record e all'uso del metodo `executemany` del driver Oracle, l'inserimento di centinaia di migliaia di record impiega indicativamente tra i **10 e i 20 minuti** totali (a seconda della larghezza di banda verso la region cloud).
* **Tempi di Risposta Web**: Le query inviate al DB Oracle Cloud sfruttano chiavi primarie, indici e limiti sui risultati (`FETCH FIRST`), garantendo tempi di risposta delle pagine web e dei grafici inferiori a **1-2 secondi** per interazione.