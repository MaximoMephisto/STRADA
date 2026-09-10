# P12345678910strada.
import os
import oracledb

def connesione_al_db():
    try:
        USER = "admin"
        PASSWORD = "P12345678910strada."
        DSN = "strada_high"
        WALLET_PASSWORD = "Maximo2010..."  # Sostituisci con la tua password del wallet
        # 1. Trova la cartella dove risiede questo file (DDBB)
        cartella_corrente = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Crea il percorso assoluto unendo DDBB con Wallet_STRADA
        WALLET_PATH = os.path.join(cartella_corrente, "Wallet_STRADA") 
        
        conn = oracledb.connect(
            user=USER,
            password=PASSWORD,
            dsn=DSN,
            config_dir=WALLET_PATH,
            wallet_location=WALLET_PATH,
            wallet_password=WALLET_PASSWORD
        )
        
        print("Connessione al database avvenuta con successo!")
        return conn
    except oracledb.Error as e:
        print("Errore durante la connessione al database:", e)
        return None

conessione = connesione_al_db()