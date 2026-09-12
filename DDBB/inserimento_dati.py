# Perche CSV e non Pandas?
# Pandas a differenza di CSV nativo di Python, Pandas carica tutto il file nella memoria RAM,
# mentre CSV legge il file riga per riga, occupando pochissimi Megabyte di RAM independentemente dalle dimensioni del file
import csv
from tqdm import tqdm
from connessione import connessione_al_db
from timeit import default_timer as timer
from crea_DB import crea_db

file_traffico = 'Dati_puliti/Automated_Traffic_Volume_Counts_pulito.csv'
file_meteo = 'Dati_puliti/NYC_Central_Park_weather_1869-2022.csv'
file_incidenti = 'Dati_puliti/nypd-motor-vehicle-collisions_pulito.csv'
file_taxi = 'Dati_puliti/Taxi_2016-01_pulito.csv'

# BULK INSERT: Un comando SQL utilizzato per importare rapidamente grandi volumi di dati
def inserimento_incidenti(file, dimensione_blocco=20_000):
    conn = connessione_al_db()
    if conn is None:
        print("Connessione al database fallita.")
        return
    
    cursor = conn.cursor()
    
    # A differenza di MySQL, Oracle utilizza :[posizione partendo da 1] al posto di '%s'
    query_incidenti = """
    INSERT INTO incidenti (
        id_incidente, accident_date, accident_time, borough, zip_code,
        latitude, longitude, on_street_name, cross_street_name, off_street_name,
        persons_injured, persons_killed, pedestrians_injured, pedestrians_killed,
        cyclist_injured, cyclist_killed, motorist_injured, motorist_killed
    ) VALUES (:1, TO_DATE(:2, 'YYYY-MM-DD'), :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15, :16, :17, :18)
    """
    
    query_fattori = "INSERT INTO incidenti_fattori (id_incidente, contributing_factor) VALUES (:1, :2)"
    query_veicoli = "INSERT INTO incidenti_veicoli (id_incidente, vehicle_type) VALUES (:1, :2)"
    
    lista_incidenti, lista_fattori, lista_veicoli = [], [], []
    
    # Funzione di inserimento
    def svuota_envia():
        if not lista_incidenti:
            return
        
        try:
            cursor.executemany(query_incidenti, lista_incidenti)
            if lista_fattori: 
                cursor.executemany(query_fattori, lista_fattori)
            if lista_veicoli: 
                cursor.executemany(query_veicoli, lista_veicoli)
            conn.commit()
        
        except Exception as e:
            print(f"Errore al cercare di inserire i dati: {e}")
            conn.rollback()

        finally:
            # Una volta raggiunti i 20_000 dati, si svuota per evitare duplicati
            lista_incidenti.clear()
            lista_fattori.clear()
            lista_veicoli.clear()
        
    with open(file, mode='r', encoding='utf-8') as f:
        lettore = csv.DictReader(f)
        
        for riga in lettore:
            id_inc = int(riga['COLLISION_ID'])

            lista_incidenti.append((
                id_inc, 
                riga['ACCIDENT DATE'], 
                riga['ACCIDENT TIME'], 
                riga['BOROUGH'], 
                riga['ZIP CODE'],
                float(riga['LATITUDE']) if riga['LATITUDE'] else None,
                float(riga['LONGITUDE']) if riga['LONGITUDE'] else None,
                riga['ON STREET NAME'], 
                riga['CROSS STREET NAME'], 
                riga['OFF STREET NAME'],
                int(riga['NUMBER OF PERSONS INJURED']) if riga['NUMBER OF PERSONS INJURED'] else 0, 
                int(riga['NUMBER OF PERSONS KILLED']) if riga['NUMBER OF PERSONS KILLED'] else 0,
                int(riga['NUMBER OF PEDESTRIANS INJURED']) if riga['NUMBER OF PEDESTRIANS INJURED'] else 0, 
                int(riga['NUMBER OF PEDESTRIANS KILLED']) if riga['NUMBER OF PEDESTRIANS KILLED'] else 0,
                int(riga['NUMBER OF CYCLIST INJURED']) if riga['NUMBER OF CYCLIST INJURED'] else 0, 
                int(riga['NUMBER OF CYCLIST KILLED']) if riga['NUMBER OF CYCLIST KILLED'] else 0,
                int(riga['NUMBER OF MOTORIST INJURED']) if riga['NUMBER OF MOTORIST INJURED'] else 0, 
                int(riga['NUMBER OF MOTORIST KILLED']) if riga['NUMBER OF MOTORIST KILLED'] else 0
            ))

            # Tenendo in considerazione le cinque columne riferite a le stesse cose,
            # prende tutti i dati referenti
            for i in range(1, 6):
                campo_fattore = f'CONTRIBUTING FACTOR VEHICLE {i}'
                if riga.get(campo_fattore) and riga[campo_fattore].strip():
                    lista_fattori.append((id_inc, riga[campo_fattore]))

            for i in range(1, 6):
                campo_veicolo = f'VEHICLE TYPE CODE {i}'
                if riga.get(campo_veicolo) and riga[campo_veicolo].strip():
                    lista_veicoli.append((id_inc, riga[campo_veicolo]))
            
            if len(lista_incidenti) >= dimensione_blocco:
                svuota_envia()
        
        # Si svuota la funzione per gli ultimi record rimasugli
        svuota_envia()
    
    cursor.close()
    conn.close()
    print("Inserimento Incidenti completato.")

    
def inserimento_meteo(file, dimensione_blocco=20000):
    conn = connessione_al_db()
    if conn is None:
        print("Connessione al database fallita.")
        return
    
    cursor = conn.cursor()
    
    query_meteo = """
        INSERT INTO meteo (
            precipitazioni, data_meteo, neve, neve_suolo, temperatura_min, temperatura_max
        ) VALUES (:1, TO_DATE(:2, 'YYYY-MM-DD'), :3, :4, :5, :6)
    """
    
    lista_meteo = []
    
    def svuota_e_invia():
        if not lista_meteo: return
        try:
            cursor.executemany(query_meteo, lista_meteo)
            conn.commit()
        except Exception as e:
            print(f"Errore al cercare di inserire i dati: {e}")
            conn.rollback()
        finally:
            lista_meteo.clear()

    with open(file, mode='r', encoding='utf-8') as f:
        lettore = csv.DictReader(f)
        for riga in lettore:
            lista_meteo.append((
                float(riga['PRCP']) if riga['PRCP'] else None,
                riga['DATE'], # Posizionato come secondo elemento per matchare il TO_DATE(:2)
                float(riga['SNOW']) if riga['SNOW'] else None,
                float(riga['SNWD']) if riga['SNWD'] else None,
                float(riga['TMIN']) if riga['TMIN'] else None,
                float(riga['TMAX']) if riga['TMAX'] else None
            ))
            
            if len(lista_meteo) >= dimensione_blocco:
                svuota_e_invia()
                
        svuota_e_invia() 
    
    cursor.close()
    conn.close()
    print("Inserimento Meteo completato.")


def inserimento_traffico(file, dimensione_blocco=20000):
    conn = connessione_al_db()
    if conn is None:
        print("Connessione al database fallita.")
        return
    
    cursor = conn.cursor()
    
    query_traffico = """
        INSERT INTO volume_traffico (
            request_id, boro, anno, mese, giorno, ora, minuto, volume, segment_id, street, from_st, to_st, direction
        ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13)
    """
    
    lista_traffico = []
    
    def svuota_e_invia():
        if not lista_traffico: return True
        try:
            cursor.executemany(query_traffico, lista_traffico)
            conn.commit()
            return True
        except Exception as e:
            print(f"\n[ERRORE CRITICO] Errore durante l'inserimento dei dati: {e}")
            conn.rollback()
            return False 
        finally:
            lista_traffico.clear()

    with open(file, mode='r', encoding='utf-8') as f:
        lettore = csv.DictReader(f)
        for riga in tqdm(lettore, desc="Caricamento Traffico"):
            lista_traffico.append((
                int(riga['RequestID']) if riga['RequestID'] else None,
                riga['Boro'],
                int(riga['Yr']) if riga['Yr'] else None,
                int(riga['M']) if riga['M'] else None,
                int(riga['D']) if riga['D'] else None,
                int(riga['HH']) if riga['HH'] else None,
                int(riga['MM']) if riga['MM'] else None,
                int(riga['Vol']) if riga['Vol'] else None,
                int(riga['SegmentID']) if riga['SegmentID'] else None,
                riga['street'],
                riga['fromSt'],
                riga['toSt'][:100] if riga['toSt'] else None, # 🔴 Protezione ORA-12899 aggiunta qui
                riga['Direction']
            ))
            
            if len(lista_traffico) >= dimensione_blocco:
                # Se l'inserimento fallisce, interrompiamo il ciclo immediatamente
                if not svuota_e_invia():
                    print("Processo interrotto per errore.")
                    cursor.close()
                    conn.close()
                    return
                
        # Invia l'ultimo blocco residuo
        svuota_e_invia()
        
    cursor.close()
    conn.close()
    print("Inserimento Traffico completato.")


def inserimento_taxi(file, dimensione_blocco=20000):
    conn = connessione_al_db()
    if conn is None:
        print("Connessione al database fallita.")
        return
    
    cursor = conn.cursor()
    
    query_taxi = """
        INSERT INTO taxi (
            vendor_id, pickup_datetime, dropoff_datetime, passenger_count, trip_distance,
            pickup_longitude, pickup_latitude, dropoff_longitude, dropoff_latitude,
            ratecode_id, payment_type, fare_amount, tip_amount, tolls_amount, total_amount
        ) VALUES (:1, TO_TIMESTAMP(:2, 'YYYY-MM-DD HH24:MI:SS'), TO_TIMESTAMP(:3, 'YYYY-MM-DD HH24:MI:SS'), :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15)
    """
    
    lista_taxi = []
    
    def svuota_e_invia():
        if not lista_taxi: return
        try:
            cursor.executemany(query_taxi, lista_taxi)
            conn.commit()
        except Exception as e:
            print(f"Errore al cercare di inserire i dati: {e}")
            conn.rollback()
        finally:
            lista_taxi.clear()

    with open(file, mode='r', encoding='utf-8') as f:
        lettore = csv.DictReader(f)
        for riga in lettore:
            lista_taxi.append((
                int(float(riga['VendorID'])) if riga['VendorID'] else None,
                riga['tpep_pickup_datetime'],
                riga['tpep_dropoff_datetime'],
                int(float(riga['passenger_count'])) if riga['passenger_count'] else None,
                float(riga['trip_distance']) if riga['trip_distance'] else None,
                float(riga['pickup_longitude']) if riga['pickup_longitude'] else None,
                float(riga['pickup_latitude']) if riga['pickup_latitude'] else None,
                float(riga['dropoff_longitude']) if riga['dropoff_longitude'] else None,
                float(riga['dropoff_latitude']) if riga['dropoff_latitude'] else None,
                int(float(riga['RatecodeID'])) if riga['RatecodeID'] else None,
                int(float(riga['payment_type'])) if riga['payment_type'] else None,
                float(riga['fare_amount']) if riga['fare_amount'] else None,
                float(riga['tip_amount']) if riga['tip_amount'] else None,
                float(riga['tolls_amount']) if riga['tolls_amount'] else None,
                float(riga['total_amount']) if riga['total_amount'] else None
            ))
            
            if len(lista_taxi) >= dimensione_blocco:
                svuota_e_invia()
                
        svuota_e_invia()
        
    cursor.close()
    conn.close()
    print("Inserimento Taxi completato.")

if __name__ == "__main__":
    print("================================")
    print("Inizio dell'inserimento dei dati")
    print("================================")
    tempo_inizio = timer()
    
    crea_db()
    
    try:
        print("Inserendo incidenti..")
        t_inc_inizio = timer()
        inserimento_incidenti(file_incidenti)
        t_inc_fine = timer()
        tempo_incidenti = t_inc_fine - t_inc_inizio
        print(f"-> Incidenti inseriti in: {tempo_incidenti:.2f} secondi.") 
        print("------------------------------")
        
        # 2. Inserimento Meteo
        print("Inserendo dati del meteo..")
        t_meteo_inizio = timer()
        inserimento_meteo(file_meteo)
        t_meteo_fine = timer()
        tempo_meteo = t_meteo_fine - t_meteo_inizio
        print(f"-> Meteo inserito in: {tempo_meteo:.2f} secondi.")
        print("------------------------------")
        
        # 3. Inserimento Traffico
        print("Inserendo dati del traffico..")
        t_traff_inizio = timer()
        inserimento_traffico(file_traffico)
        t_traff_fine = timer()
        tempo_traffico = t_traff_fine - t_traff_inizio
        print(f"-> Traffico inserito in: {tempo_traffico:.2f} secondi.")
        print("------------------------------")
        
        # 4. Inserimento Taxi
        print("Inserendo dati dei taxi..")
        t_taxi_inizio = timer()
        inserimento_taxi(file_taxi)
        t_taxi_fine = timer()
        tempo_taxi = t_taxi_fine - t_taxi_inizio
        print(f"-> Taxi inseriti in: {tempo_taxi:.2f} secondi.")
        print("------------------------------")
        
        tempo_fine = timer() 
        tempo_totale = tempo_fine - tempo_inizio 
        
        print(f"Tutti i dati inseriti correttamente in: {tempo_totale:.2f} Secondi.")
    
    except Exception as e:
        print(f"Errore al cercare di inserire i dati: {e}")
        

