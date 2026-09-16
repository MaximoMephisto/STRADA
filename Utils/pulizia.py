import pandas as pd
from tqdm import tqdm
import os
from timeit import default_timer as timer
import numpy as np
import csv

path_traffic_volume = 'Dati_Originali/Automated_Traffic_Volume_Counts.csv'
path_vehicle_collision = 'Dati_Originali/INCIDENTI/nypd-motor-vehicle-collisions.csv'
path_taxi = 'Dati_Originali/TAXI/yellow_tripdata_2016-01.csv'
path_meteo = 'Dati_Originali/NYC_Central_Park_weather_1869-2022.csv'

def controlli_dataset(dataset):
    # Legge il dataset e stampa le prime 5 righe con un numero limitato di righe per evitare problemi di memoria
    blocchi = pd.read_csv(dataset, nrows=1000)
    # Prende le prime cinque righe
    prime_righe = blocchi.head()
    # Conta il numero totale di righe e colonne del dataset
    tot_righe = blocchi.shape[0]    
    tot_colonne = blocchi.shape[1]
    # Conta i valori nulli per ogni colonna
    valori_nulli = blocchi.isnull().sum()
    # Conta i duplicati per ogni colonna
    duplicati = blocchi.duplicated().sum()
    
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
    tempo_inizio = timer()  # Inizia il timer per misurare il tempo di esecuzione
    dimensione_blocco = 200_000  # Dimensione del blocco di righe da leggere
    conto_righe = 0  # Contatore per il numero totale di righe elaborate
    primo_giro = True  # Flag per indicare se è il primo giro di lettura
    
    dataset_output = 'Dati_Puliti/Automated_Traffic_Volume_Counts_pulito.csv'
    # Rimuove il file di output se esiste già
    if os.path.exists(dataset_output):
        os.remove(dataset_output)  
    
    blocchi = pd.read_csv(dataset, chunksize=dimensione_blocco, low_memory=False)
    
    with tqdm(desc='Blocchi elaborati', unit=' blocco') as pbar:
        for blocco in blocchi:
            # Rimuove le righe con valori nulli nelle colonne specificate
            blocco = blocco.dropna(subset=['fromSt', 'toSt', 'WktGeom', 'SegmentID'])
            
            # Ottimizza i testi (es. tutto in maiuscolo e senza spazi vuoti inutili)
            colonne_testo = ['street', 'fromSt', 'toSt']
            for col in colonne_testo:
                if col in blocco.columns:
                    blocco[col] = blocco[col].astype("string").str.upper().str.strip()
             
            # Elimina i duplicati all'interno del blocco basandosi sulla colonna 'SegmentID'
            blocco = blocco.drop_duplicates()
            
            # 'mode="a"' aggiunge i dati in coda al file senza sovrascriverlo
            blocco.to_csv(dataset_output, mode="a", index=False, header=primo_giro)
            
            primo_giro = False  # Dopo il primo blocco, non scrivere più l'intestazione
            conto_righe += len(blocco)  # Aggiorna il contatore delle righe elaborate
            pbar.update(1)  # Aggiorna la barra di avanzamento

        tempo_fine = timer()  # Ferma il timer
        tempo_totale = tempo_fine - tempo_inizio  # Calcola il tempo totale
        print(f"\ntraffic_volume_pulizia completata. Il dataset pulito è stato salvato in {dataset_output}.")
        print(f"Tempo totale: {tempo_totale:.2f} secondi per {conto_righe} righe.") 
    

def vehicle_collision_pulizia(dataset):
    tempo_inizio = timer()
    
    df = pd.read_csv(dataset, dtype={'ZIP CODE': str, 'COLLISION_ID': str})
    
    dataset_output = 'Dati_Puliti/nypd-motor-vehicle-collisions_pulito.csv'
    # Rimuove il file di output se esiste già
    if os.path.exists(dataset_output):
        os.remove(dataset_output)  
    
    colonne_numeriche = [
        "NUMBER OF PERSONS INJURED", "NUMBER OF PERSONS KILLED",
        "NUMBER OF PEDESTRIANS INJURED", "NUMBER OF PEDESTRIANS KILLED",
        "NUMBER OF CYCLIST INJURED", "NUMBER OF CYCLIST KILLED",
        "NUMBER OF MOTORIST INJURED", "NUMBER OF MOTORIST KILLED"
    ]
    df[colonne_numeriche] = df[colonne_numeriche].fillna(0).astype("Int64")
    
    # In caso di nulli mettiamo 'non definito'
    df["ACCIDENT DATE"] = pd.to_datetime(df["ACCIDENT DATE"], errors='coerce')
    df["ACCIDENT TIME"] = df["ACCIDENT TIME"].fillna("Non definito")
    df["BOROUGH"] = df["BOROUGH"].str.strip().str.upper()
    df["ZIP CODE"] = df["ZIP CODE"].str.strip()
    
    # Informazioni principali sulla dinamica (Veicoli e cause primarie)
    df["CONTRIBUTING FACTOR VEHICLE 1"] = df["CONTRIBUTING FACTOR VEHICLE 1"].fillna("Non definito").str.upper()
    df["CONTRIBUTING FACTOR VEHICLE 2"] = df["CONTRIBUTING FACTOR VEHICLE 2"].fillna("Non definito").str.upper()
    df["VEHICLE TYPE CODE 1"] = df["VEHICLE TYPE CODE 1"].fillna("Non definito").str.upper()
    df["VEHICLE TYPE CODE 2"] = df["VEHICLE TYPE CODE 2"].fillna("Non definito").str.upper()
    
    # Stato delle coordinate geografiche
    df["Location_Status"] = np.where(
        df["LATITUDE"].notna() & df["LONGITUDE"].notna(), 
        "Coordinate disponibili", 
        "Coordinate non disponibili"
    )
    
    # Elimina i dati non importanti
    colonne_da_tenere = [
        'COLLISION_ID', 'ACCIDENT DATE', 'ACCIDENT TIME', 'BOROUGH', 'ZIP CODE', 
        'LATITUDE', 'LONGITUDE', 'Location_Status',
        'CONTRIBUTING FACTOR VEHICLE 1', 'CONTRIBUTING FACTOR VEHICLE 2',
        'VEHICLE TYPE CODE 1', 'VEHICLE TYPE CODE 2'
    ] + colonne_numeriche
    
    # Filtriamo il DataFrame: eliminerà automaticamente strade secondarie, veicoli 3-4-5 e colonne F39, F40 ecc.
    df = df[[col for col in colonne_da_tenere if col in df.columns]]
    
    # Rimuove duplicati basandosi sull'ID scontro
    df = df.drop_duplicates(subset=['COLLISION_ID'], keep='first')
    
    # Per problemi con TABLEAU, si salva con rinforzo
    df.to_csv(
        dataset_output, 
        index=False, 
        lineterminator='\n'
    )
    
    tempo_fine = timer()
    print(f"\nPulizia completata con successo! Il file leggero è in: {dataset_output}")
    print(f"Sono rimaste {df.shape[1]} colonne pulite e {len(df)} righe.")
    print(f"Tempo impiegato: {tempo_fine - tempo_inizio:.2f} secondi.")


def taxi_pulizia(dataset):
    tempo_inizio = timer()
    conto_righe = 0
    dimensione_blocco = 200_000
    primo_giro = True
    
    dataset_output = 'Dati_Puliti/Taxi_2016-01_pulito.csv'
    if os.path.exists(dataset_output):
        os.remove(dataset_output)
        
    blocchi = pd.read_csv(dataset, chunksize=dimensione_blocco)
    
    with tqdm(desc='Blocchi elaborati', unit=' blocco') as pbar:
        for blocco in blocchi:
            # Converte le colonne 'tpep_pickup_datetime' e 'tpep_dropoff_datetime' in formato datetime, gestendo eventuali errori
            blocco["tpep_pickup_datetime"] = pd.to_datetime(
                blocco["tpep_pickup_datetime"], errors="coerce", format="mixed"
            )
            blocco["tpep_dropoff_datetime"] = pd.to_datetime(
                blocco["tpep_dropoff_datetime"], errors="coerce", format="mixed"
            )
            
            # Converte le colonne numeriche in formato numerico
            colonne_numeriche = [
                        'passenger_count',
                        'trip_distance',
                        'pickup_longitude',
                        'pickup_latitude',
                        'dropoff_longitude',
                        'dropoff_latitude',
                        'fare_amount',
                        'extra',
                        'mta_tax',
                        'tip_amount',
                        'tolls_amount',
                        'improvement_surcharge',
                        'total_amount'
                    ]
            # Convertiamo tutte le colonne presenti in float64 (gestisce anche i NaN)
            dizionario_tipi = {
                col: "float64" for col in colonne_numeriche if col in blocco.columns
            }
            if dizionario_tipi:
                blocco = blocco.astype(dizionario_tipi)
                
            # Sostituisce i valori 0 nelle colonne di longitudine e latitudine con valori nulli (NaN)
            colonne_coordinate = [
                "pickup_longitude",
                "pickup_latitude",
                "dropoff_longitude",
                "dropoff_latitude",
            ]
            for col in colonne_coordinate:
                if col in blocco.columns:
                    blocco[col] = blocco[col].replace(0, np.nan)
                    
            # Ottimizza la colonna 'store_and_fwd_flag' convertendo i valori in stringa, in maiuscolo e rimuovendo spazi vuoti
            blocco['store_and_fwd_flag'] = (
                blocco['store_and_fwd_flag']
                .astype(str)
                .str.upper()
                .str.strip()
            )
            # Rimuove le righe con valori nulli nelle colonne specifiche
            blocco = blocco.dropna(subset=['tpep_pickup_datetime', 'tpep_dropoff_datetime'])
            blocco = blocco.drop_duplicates()
    
            blocco.to_csv(dataset_output, mode='a', index=False, header=primo_giro)
    
            primo_giro = False
            conto_righe += len(blocco)
            pbar.update(1)
        
        tempo_fine = timer()
        tempo_totale = tempo_fine - tempo_inizio
        
        print(f"\ntaxi_pulizia completata. Il dataset pulito è stato salvato in {dataset_output}.")
        print(f"Tempo totale: {tempo_totale:.2f} secondi per {conto_righe} righe.")
            
           
def meteo_pulizia(dataset):
    tempo_inizio = timer()
    dimensione_blocco = 200_000
    conto_righe = 0
    primo_giro = True
    
    dataset_output = 'Dati_Puliti/NYC_Central_Park_weather_1869-2022.csv'
    if os.path.exists(dataset_output):
        os.remove(dataset_output)
    
    blocchi = pd.read_csv(dataset, chunksize=dimensione_blocco)
    
    with tqdm(desc='Blocchi elaborati', unit=' blocco') as pbar:
        for blocco in blocchi:
            blocco['DATE'] = pd.to_datetime(blocco['DATE'], errors='coerce')

            blocco = blocco.dropna(subset=['DATE'])
            blocco = blocco.drop_duplicates(subset=['DATE'])

            blocco.to_csv(dataset_output, mode='a', index=False, header=primo_giro)

            primo_giro = False
            pbar.update(1)

        tempo_fine = timer()
        tempo_totale = tempo_fine - tempo_inizio
        
        print(f"\nMeteo_pulizia completata. Il dataset pulito è stato salvato in {dataset_output}.")
        print(f"Tempo totale: {tempo_totale:.2f} secondi per {conto_righe} righe.")
            
 
if __name__ == "__main__":

    print(f"{'='*40}")
    print("  Cominciamo a visualizzare i dataset  ")
    print(f"{'='*40}")
    
    print("Dataset: Automated_Traffic_Volume_Counts.csv")
    mostra_dataset(path_traffic_volume)
    
    print("Dataset: nypd-motor-vehicle-collisions.csv")
    mostra_dataset(path_vehicle_collision)
    
    print("Dataset: Taxi_2016-01.csv")
    mostra_dataset(path_taxi)
    
    print("Dataset: NYC_Central_Park_weather_1869-2022.csv")
    mostra_dataset(path_meteo)

    print(f"{'='*40}") 
    print("  Cominciamo a pulire i dataset  ")
    print(f"{'='*40}")
    traffic_volume_pulizia(path_traffic_volume)
    vehicle_collision_pulizia(path_vehicle_collision)
    taxi_pulizia(path_taxi)
    meteo_pulizia(path_meteo)