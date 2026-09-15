from flask import Flask, render_template, request, redirect, url_for
from DDBB.connessione import connessione_al_db
import json
import plotly.express as px
import plotly.utils
import bcrypt


# Crea un'istanza dell'app Flask
app = Flask(__name__)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        passwd = request.form.get('passwd')
        
        conn = connessione_al_db()
        cursor = conn.cursor()
        try:
            # Cerchiamo l'hash della password per lo username inserito
            sql = "SELECT passwd FROM ADMIN.admins WHERE LOWER(TRIM(username)) = LOWER(:1)"
            cursor.execute(sql, (username,))
            row = cursor.fetchone()
            
            # Se row è None, significa che l'utente non esiste nel database
            if row is None:
                print("Utente non trovato.")
                # Mandiamo lo stesso errore generico per motivi di sicurezza
                return render_template('login.html', errore="Username o password errati.")
            
            # Recuperiamo l'hash (che nel DB è salvato come stringa VARCHAR2)
            hashed_password_db = row[0]
            
            # Convertiamo sia l'input in chiaro sia l'hash del DB in bytes
            password_bytes = passwd.encode('utf-8')
            hash_bytes = hashed_password_db.encode('utf-8')
            
            if bcrypt.checkpw(password_bytes, hash_bytes):
                return redirect(url_for('index'))
            else:
                print("Password errata.")
                return render_template('login.html', errore="Username o password errati.")
                
        except Exception as e:
            print(f"Errore durante il login: {e}")
            return "Errore interno del server", 500
        finally:
            cursor.close()
            conn.close()

    return render_template('login.html')

@app.route('/')
def index():
    with connessione_al_db() as connection:
        if connection is None:
            return "Errore di connessione al Database", 500
        
        with connection.cursor() as cursor:
            # STATISTICHE GENERALE #
            # Trova l'anno MINIMO registrato nella tabella incidenti
            cursor.execute('SELECT EXTRACT(YEAR FROM MIN(accident_date)) FROM incidenti')
            anno_corrente = cursor.fetchone()[0]
            
            # Query di esempio: estrae il numero totale di incidenti e l'ultimo aggiornamento
            cursor.execute("SELECT COUNT(*) FROM incidenti_veicoli")
            totale_incidenti = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM volume_traffico")
            totale_traffico = cursor.fetchone()[0]
            
            # Calcola la percentuale di incidenti che hanno causato almeno una vittima
            cursor.execute("""
                SELECT ROUND(
                    (SUM(CASE WHEN persons_killed > 0 THEN 1 ELSE 0 END) / COUNT(*)) * 100, 
                    2
                ) 
                FROM incidenti
            """)
            tasso_mortalita = cursor.fetchone()[0]
            tasso_mortalita_str = f"{tasso_mortalita}%".replace(".", ",") if tasso_mortalita is not None else "0,0%"
            
            # Incrocia le tabelle per trovare il fattore più comune escludendo i dati non definiti
            cursor.execute("""
            SELECT contributing_factor, COUNT(*)
            FROM incidenti_fattori
            WHERE UPPER(contributing_factor) NOT IN ('NON DEFINITO', 'UNSPECIFIED', 'UNKNOWN', 'UNKNOWN_VAL')
            GROUP BY contributing_factor
            ORDER BY COUNT(*) DESC
            """)
            res_causa = cursor.fetchone()
            causa_top = res_causa[0].title() if res_causa else "Non disponibile"
            incidenti_causa = f"{res_causa[1]:,}".replace(",", ".") if res_causa else "0"
            
            # Calcola quanti incidenti sono avvenuti nei giorni in cui c'era neve al suolo (> 0)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM incidenti i
                JOIN meteo m ON i.accident_date = m.data_meteo
                WHERE m.neve_suolo > 0
            """)
            res_meteo = cursor.fetchone()
            incidenti_con_neve = f"{res_meteo[0]:,}".replace(",", ".") if res_meteo else "0"
            
    return render_template(
        'index.html',
        anno=anno_corrente,
        numero_incidenti=f"{totale_incidenti:,}".replace(",", "."), 
        numero_traffico=f"{totale_traffico:,}".replace(",", "."),
        tasso_mortalita=tasso_mortalita_str,
        causa_top=causa_top,
        incidenti_causa=incidenti_causa,
        incidenti_con_neve=incidenti_con_neve
    )
    
if __name__ == '__main__':
    app.run(debug=True)
    