# Perche CSV e non Pandas?
# Pandas a differenza di CSV nativo di Python, Pandas carica tutto il file nella memoria RAM,
# mentre CSV legge il file riga per riga, occupando pochissimi Megabyte di RAM independentemente dalle dimensioni del file
import csv
from tqdm import tqdm
from connessione import connessione_al_db
from timeit import default_timer as timer
from crea_DB import crea_db
import bcrypt

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
    id_incidenti_visti = set()  # Controllo degli ID unici
    
    def svuota_e_invia():
        if not lista_incidenti:
            return True
        
        try:
            cursor.executemany(query_incidenti, lista_incidenti)
            if lista_fattori: 
                cursor.executemany(query_fattori, lista_fattori)
            if lista_veicoli: 
                cursor.executemany(query_veicoli, lista_veicoli)
            conn.commit()
            return True
        except Exception as e:
            print(f"\n[ERRORE CRITICO] Errore durante l'inserimento degli incidenti: {e}")
            conn.rollback()
            return False
        finally:
            lista_incidenti.clear()
            lista_fattori.clear()
            lista_veicoli.clear()
        
    with open(file, mode='r', encoding='utf-8') as f:
        lettore = csv.DictReader(f)
        
        for riga in lettore:
            id_inc = int(riga['COLLISION_ID'])

            if id_inc in id_incidenti_visti:
                continue
            id_incidenti_visti.add(id_inc)

            lista_incidenti.append((
                id_inc, 
                riga.get('ACCIDENT DATE'), 
                riga.get('ACCIDENT TIME'), 
                riga.get('BOROUGH'), 
                riga.get('ZIP CODE'),
                float(riga['LATITUDE']) if riga.get('LATITUDE') and riga['LATITUDE'].strip() else None,
                float(riga['LONGITUDE']) if riga.get('LONGITUDE') and riga['LONGITUDE'].strip() else None,
                riga.get('ON STREET NAME'), 
                riga.get('CROSS STREET NAME'), 
                riga.get('OFF STREET NAME'),
                int(riga['NUMBER OF PERSONS INJURED']) if riga.get('NUMBER OF PERSONS INJURED') and riga['NUMBER OF PERSONS INJURED'].strip() else 0, 
                int(riga['NUMBER OF PERSONS KILLED']) if riga.get('NUMBER OF PERSONS KILLED') and riga['NUMBER OF PERSONS KILLED'].strip() else 0,
                int(riga['NUMBER OF PEDESTRIANS INJURED']) if riga.get('NUMBER OF PEDESTRIANS INJURED') and riga['NUMBER OF PEDESTRIANS INJURED'].strip() else 0, 
                int(riga['NUMBER OF PEDESTRIANS KILLED']) if riga.get('NUMBER OF PEDESTRIANS KILLED') and riga['NUMBER OF PEDESTRIANS KILLED'].strip() else 0,
                int(riga['NUMBER OF CYCLIST INJURED']) if riga.get('NUMBER OF CYCLIST INJURED') and riga['NUMBER OF CYCLIST INJURED'].strip() else 0, 
                int(riga['NUMBER OF CYCLIST KILLED']) if riga.get('NUMBER OF CYCLIST KILLED') and riga['NUMBER OF CYCLIST KILLED'].strip() else 0,
                int(riga['NUMBER OF MOTORIST INJURED']) if riga.get('NUMBER OF MOTORIST INJURED') and riga['NUMBER OF MOTORIST INJURED'].strip() else 0, 
                int(riga['NUMBER OF MOTORIST KILLED']) if riga.get('NUMBER OF MOTORIST KILLED') and riga['NUMBER OF MOTORIST KILLED'].strip() else 0
            ))

            for i in range(1, 6):
                campo_fattore = f'CONTRIBUTING FACTOR VEHICLE {i}'
                if riga.get(campo_fattore) and riga[campo_fattore].strip():
                    lista_fattori.append((id_inc, riga[campo_fattore].strip()))

            for i in range(1, 6):
                campo_veicolo = f'VEHICLE TYPE CODE {i}'
                if riga.get(campo_veicolo) and riga[campo_veicolo].strip():
                    lista_veicoli.append((id_inc, riga[campo_veicolo].strip()))
            
            if len(lista_incidenti) >= dimensione_blocco:
                if not svuota_e_invia():
                    print("Processo interrotto per errore.")
                    cursor.close()
                    conn.close()
                    return
        
        svuota_e_invia()
    
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
        if not lista_meteo: return True
        try:
            cursor.executemany(query_meteo, lista_meteo)
            conn.commit()
            return True
        except Exception as e:
            print(f"\n[ERRORE CRITICO] Errore durante l'inserimento dei dati meteo: {e}")
            conn.rollback()
            return False
        finally:
            lista_meteo.clear()

    with open(file, mode='r', encoding='utf-8') as f:
        lettore = csv.DictReader(f)
        for riga in lettore:
            lista_meteo.append((
                float(riga['PRCP']) if riga.get('PRCP') and riga['PRCP'].strip() else None,
                riga['DATE'],
                float(riga['SNOW']) if riga.get('SNOW') and riga['SNOW'].strip() else None,
                float(riga['SNWD']) if riga.get('SNWD') and riga['SNWD'].strip() else None,
                float(riga['TMIN']) if riga.get('TMIN') and riga['TMIN'].strip() else None,
                float(riga['TMAX']) if riga.get('TMAX') and riga['TMAX'].strip() else None
            ))
            
            if len(lista_meteo) >= dimensione_blocco:
                if not svuota_e_invia():
                    print("Processo interrotto per errore.")
                    cursor.close()
                    conn.close()
                    return
                
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
    
    # Sincronizzato con la nuova tabella volume_traffico (id_incidente al primo posto)
    query_traffico = """
        INSERT INTO volume_traffico (
            id_incidente, request_id, boro, anno, mese, giorno, ora, minuto, volume, segment_id, street, from_st, to_st, direction
        ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14)
    """
    
    lista_traffico = []
    
    def svuota_e_invia():
        if not lista_traffico: return True
        try:
            cursor.executemany(query_traffico, lista_traffico)
            conn.commit()
            return True
        except Exception as e:
            print(f"\n[ERRORE CRITICO] Errore durante l'inserimento del traffico: {e}")
            conn.rollback()
            return False 
        finally:
            lista_traffico.clear()

    with open(file, mode='r', encoding='utf-8') as f:
        lettore = csv.DictReader(f)
        for riga in tqdm(lettore, desc="Caricamento Traffico"):
            lista_traffico.append((
                None,  # id_incidente impostato come None iniziale
                int(riga['RequestID']) if riga.get('RequestID') and riga['RequestID'].strip() else None,
                riga.get('Boro'),
                int(riga['Yr']) if riga.get('Yr') and riga['Yr'].strip() else None,
                int(riga['M']) if riga.get('M') and riga['M'].strip() else None,
                int(riga['D']) if riga.get('D') and riga['D'].strip() else None,
                int(riga['HH']) if riga.get('HH') and riga['HH'].strip() else None,
                int(riga['MM']) if riga.get('MM') and riga['MM'].strip() else None,
                int(riga['Vol']) if riga.get('Vol') and riga['Vol'].strip() else None,
                int(riga['SegmentID']) if riga.get('SegmentID') and riga['SegmentID'].strip() else None,
                riga.get('street'),
                riga.get('fromSt'),
                riga['toSt'][:100] if riga.get('toSt') else None,
                riga.get('Direction')
            ))
            
            if len(lista_traffico) >= dimensione_blocco:
                if not svuota_e_invia():
                    print("Processo interrotto per errore.")
                    cursor.close()
                    conn.close()
                    return
                
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
    
    # Sincronizzato con la nuova tabella taxi (id_incidente al primo posto)
    query_taxi = """
        INSERT INTO taxi (
            id_incidente, vendor_id, pickup_datetime, dropoff_datetime, passenger_count, trip_distance,
            pickup_longitude, pickup_latitude, dropoff_longitude, dropoff_latitude,
            ratecode_id, payment_type, fare_amount, tip_amount, tolls_amount, total_amount
        ) VALUES (:1, :2, TO_TIMESTAMP(:3, 'YYYY-MM-DD HH24:MI:SS'), TO_TIMESTAMP(:4, 'YYYY-MM-DD HH24:MI:SS'), :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15, :16)
    """
    
    lista_taxi = []
    
    def svuota_e_invia():
        if not lista_taxi: return True
        try:
            cursor.executemany(query_taxi, lista_taxi)
            conn.commit()
            return True
        except Exception as e:
            print(f"\n[ERRORE CRITICO] Errore durante l'inserimento dei taxi: {e}")
            conn.rollback()
            return False
        finally:
            lista_taxi.clear()

    with open(file, mode='r', encoding='utf-8') as f:
        lettore = csv.DictReader(f)
        for riga in lettore:
            lista_taxi.append((
                None,  # id_incidente impostato come None iniziale
                int(float(riga['VendorID'])) if riga.get('VendorID') and riga['VendorID'].strip() else None,
                riga.get('tpep_pickup_datetime'),
                riga.get('tpep_dropoff_datetime'),
                int(float(riga['passenger_count'])) if riga.get('passenger_count') and riga['passenger_count'].strip() else None,
                float(riga['trip_distance']) if riga.get('trip_distance') and riga['trip_distance'].strip() else None,
                float(riga['pickup_longitude']) if riga.get('pickup_longitude') and riga['pickup_longitude'].strip() else None,
                float(riga['pickup_latitude']) if riga.get('pickup_latitude') and riga['pickup_latitude'].strip() else None,
                float(riga['dropoff_longitude']) if riga.get('dropoff_longitude') and riga['dropoff_longitude'].strip() else None,
                float(riga['dropoff_latitude']) if riga.get('dropoff_latitude') and riga['dropoff_latitude'].strip() else None,
                int(float(riga['RatecodeID'])) if riga.get('RatecodeID') and riga['RatecodeID'].strip() else None,
                int(float(riga['payment_type'])) if riga.get('payment_type') and riga['payment_type'].strip() else None,
                float(riga['fare_amount']) if riga.get('fare_amount') and riga['fare_amount'].strip() else None,
                float(riga['tip_amount']) if riga.get('tip_amount') and riga['tip_amount'].strip() else None,
                float(riga['tolls_amount']) if riga.get('tolls_amount') and riga['tolls_amount'].strip() else None,
                float(riga['total_amount']) if riga.get('total_amount') and riga['total_amount'].strip() else None
            ))
            
            if len(lista_taxi) >= dimensione_blocco:
                if not svuota_e_invia():
                    print("Processo interrotto per errore.")
                    cursor.close()
                    conn.close()
                    return
                
        svuota_e_invia()
        
    cursor.close()
    conn.close()
    print("Inserimento Taxi completato.")


def inserimento_admin():
    conn = connessione_al_db()
    if conn is None:
        print("Connessione al database fallita.")
        return
    
    cursor = conn.cursor() 
    USERNAME_ADMIN = "superadmin"
    PASSWORD_CHIARO = "1234" 
    TUTTI_PERMESSI = True 
    
    try:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(PASSWORD_CHIARO.encode('utf-8'), salt).decode('utf-8')
        
        permesso_int = 1 if TUTTI_PERMESSI else 0
        
        sql = """
            INSERT INTO admins (username, passwd, tutti_permessi) 
            VALUES (:1, :2, :3)
        """
        
        print(f"Inserimento dell'utente '{USERNAME_ADMIN}' nel database Oracle...")
        cursor.execute(sql, (USERNAME_ADMIN, hashed_password, permesso_int))
        conn.commit()
        print(f"Username: {USERNAME_ADMIN}")
        print(f"Password originale: {PASSWORD_CHIARO}")
        print(f"Hash salvato: {hashed_password[:20]}...")
        print("="*45)
    except Exception as e:
        print(f"\n[!] Errore imprevisto durante il lancio: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    
    
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
        
        print("Inserendo dati del meteo..")
        t_meteo_inizio = timer()
        inserimento_meteo(file_meteo)
        t_meteo_fine = timer()
        tempo_meteo = t_meteo_fine - t_meteo_inizio
        print(f"-> Meteo inserito in: {tempo_meteo:.2f} secondi.")
        print("------------------------------")
        
        print("Inserendo dati del traffico..")
        t_traff_inizio = timer()
        inserimento_traffico(file_traffico)
        t_traff_fine = timer()
        tempo_traffico = t_traff_fine - t_traff_inizio
        print(f"-> Traffico inserito in: {tempo_traffico:.2f} secondi.")
        print("------------------------------")
        
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