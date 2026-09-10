import pandas as pd
from tqdm import tqdm
import os

path_traffic_volume = 'Dati_Originali/Automated_Traffic_Volume_Counts.csv'
path_vehicle_collision = 'Dati_Originali/INCIDENTI/nypd-motor-vehicle-collisions.csv'

def controlli_dataset(dataset):
    # Legge il dataset e stampa le prime 5 righe con un numero limitato di righe per evitare problemi di memoria
    df = pd.read_csv(dataset, nrows=1000)
    # Prende le prime cinque righe
    prime_righe = df.head()
    # Conta il numero totale di righe e colonne del dataset
    tot_righe = df.shape[0]    
    tot_colonne = df.shape[1]
    # Conta i valori nulli per ogni colonna
    valori_nulli = df.isnull().sum()
    # Conta i duplicati per ogni colonna
    duplicati = df.duplicated().sum()
    
    return prime_righe, tot_righe, tot_colonne, valori_nulli, duplicati


def mostra_dataset(dataset):
    prime_righe, righe, colonne, valori_nulli, duplicati = controlli_dataset(dataset)
    print(f"Prime righe:\n{prime_righe}\n")
    print(f"{'-'*36}")
    print(f"  Nelle prime {righe} righe, ci sono:  ")
    print(f"Colonne: {colonne}")
    print(f"Valori nulli:\n{valori_nulli}\n")
    print(f"Duplicati: {duplicati}")


def traffic_volume_pulizia(dataset):
    dimensione_blocco = 200_000  # Dimensione del blocco di righe da leggere
    primo_giro = True  # Flag per indicare se è il primo giro di lettura
    
    dataset_output = 'Dati_Puliti/Automated_Traffic_Volume_Counts_pulito.csv'
    # Rimuove il file di output se esiste già
    if os.path.exists(dataset_output):
        os.remove(dataset_output)  
    
    blocchi = pd.read_csv(dataset, chunksize=dimensione_blocco)
    
    with tqdm(desc='Blocchi elaborati', unit=' blocco') as pbar:
        for blocco in blocchi:
            # Rimuove le righe con valori nulli nelle colonne specificate
            blocco = blocco.dropna(subset=['fromSt', 'toSt', 'WktGeom', 'SegmentID'])  
            
            # Ottimizza i testi (es. tutto in maiuscolo e senza spazi vuoti inutili)
            for colomna in ['street', 'fromSt', 'toSt']:
                blocco[colomna] = blocco[colomna].astype(str).str.upper().str.strip()
                
            # Elimina i duplicati all'interno del blocco basandosi sulla colonna 'SegmentID'
            blocco = blocco.drop_duplicates(subset=['SegmentID'])
            
            # 'mode="a"' aggiunge i dati in coda al file senza sovrascriverlo
            blocco.to_csv(dataset_output, mode="a", index=False, header=primo_giro)
            
            primo_giro = False  # Dopo il primo blocco, non scrivere più l'intestazione
            pbar.update(1)  # Aggiorna la barra di avanzamento

        print(f"\ntraffic_volume_pulizia completata. Il dataset pulito è stato salvato in {dataset_output}.")
    

def vehicle_collision_pulizia(dataset):
    dimensione_blocco = 200_000  # Dimensione del blocco di righe da leggere
    primo_giro = True  # Flag per indicare se è il primo giro di lettura
    
    dataset_output = 'Dati_Puliti/nypd-motor-vehicle-collisions_pulito.csv'
    # Rimuove il file di output se esiste già
    if os.path.exists(dataset_output):
        os.remove(dataset_output)  
    
    blocchi = pd.read_csv(dataset, chunksize=dimensione_blocco)
    
    with tqdm(desc='Blocchi elaborati', unit=' blocco') as pbar:
        for blocco in blocchi:
            # Rimuove le righe con valori nulli nelle colonne specificate
            blocco = blocco.dropna(subset=['DATE', 'TIME', 'BOROUGH', 'ZIP CODE'])  
            
            # Ottimizza i testi (es. tutto in maiuscolo e senza spazi vuoti inutili)
            for colomna in ['BOROUGH']:
                blocco[colomna] = blocco[colomna].astype(str).str.upper().str.strip()
                
            # Elimina i duplicati all'interno del blocco basandosi sulle colonne 'DATE' e 'TIME'
            blocco = blocco.drop_duplicates(subset=['DATE', 'TIME'])
            
            # 'mode="a"' aggiunge i dati in coda al file senza sovrascriverlo
            blocco.to_csv(dataset_output, mode="a", index=False, header=primo_giro)
            
            primo_giro = False  # Dopo il primo blocco, non scrivere più l'intestazione
            pbar.update(1)  # Aggiorna la barra di avanzamento

        print(f"\nvehicle_collision_pulizia completata. Il dataset pulito è stato salvato in {dataset_output}.")


if __name__ == "__main__":

    print(f"{'='*40}")
    print("  Cominciamo a visualizzare i dataset  ")
    print(f"{'='*40}")
    
    print("Dataset: Automated_Traffic_Volume_Counts.csv")
    mostra_dataset(path_traffic_volume)
    
    print("Dataset: nypd-motor-vehicle-collisions.csv")
    mostra_dataset(path_vehicle_collision)

    print(f"{'='*40}")
    print("  Cominciamo a pulire il dataset  ")
    print(f"{'='*40}")
    #traffic_volume_pulizia(path_traffic_volume)