import csv
file = "Dati_puliti/Taxi_2016-01_pulito.csv"
with open(file, mode='r', encoding='utf-8') as f:
    lettore = csv.DictReader(f)
    
    # QUESTO TI SALVA: ti stampa sul terminale i nomi veri delle colonne del tuo file!
    print(f"Le colonne reali del tuo CSV sono: {lettore.fieldnames}")
    
