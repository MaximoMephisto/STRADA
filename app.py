from flask import Flask, render_template, request, redirect, url_for, session
from DDBB.connessione import connessione_al_db
import json
import plotly.express as px
import plotly.utils
import bcrypt

# Crea un'istanza dell'app Flask
app = Flask(__name__)

# Crea una chiave per criptare i cookie
app.secret_key = 'admin_strada_cookies_crip'

@app.route('/logout')
def logout():
    session.clear() 
    print("Sessione chiusa con successo. Utente disconnesso.")
    
    # Reindirizza l'utente alla schermata di login
    return redirect(url_for('login'))

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
                session['superadmin'] = username
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

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'superadmin' not in session:
        print("Accesso negato: Utente non loggato.")
        return render_template('login.html', errore="Devi prima effettuare il login.")
    
    admin = session['superadmin']
    
    with connessione_al_db() as connection:
        if connection is None:
            return "Errore di connessione al Database", 500
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT tutti_permessi FROM ADMIN.admins WHERE username = :1", (admin,))
            row_permessi = cursor.fetchone()
            # Se l'utente esiste (e deve esistere), prendiamo il numero, altrimenti impostiamo 0
            permessi_admin = row_permessi[0] if row_permessi else 0
            
            lista_admins = []
            if permessi_admin == 1:
                # Estraiamo l'ID, lo Username e il ruolo (convertito in testo comprensibile)
                cursor.execute("""
                    SELECT id_admin, username, 
                           CASE WHEN tutti_permessi = 1 THEN 'Super Admin' ELSE 'Limitato' END 
                    FROM ADMIN.admins
                    ORDER BY username ASC
                """)
                lista_admins = cursor.fetchall() # Salva tutte le righe estratte
            
            if request.method == 'POST':
                username = request.form.get('username').strip()
                passwd = request.form.get('passwd')
                # Recuperiamo la select del booleano (sarà "1" o "0") e la convertiamo in int
                tutti_permessi = int(request.form.get('tutti_permessi') or 0)
                
                try:
                    # Criptiamo la password con bcrypt
                    salt = bcrypt.gensalt()
                    hashed_password = bcrypt.hashpw(passwd.encode('utf-8'), salt).decode('utf-8')
                    
                    # Query di inserimento inserendo ADMIN.admins
                    sql_insert = """
                        INSERT INTO ADMIN.admins (username, passwd, tutti_permessi) 
                        VALUES (:1, :2, :3)
                    """
                    cursor.execute(sql_insert, (username, hashed_password, tutti_permessi))
                    
                    # Forziamo il commit sulla connessione attiva
                    connection.commit()
                    print(f"Nuovo admin '{username}' registrato con successo!")
                    
                    # Puoi passare un messaggio di successo all'HTML se lo desideri
                    messaggio_successo = f"Amministratore {username} creato con successo."
                    
                    
                except Exception as e:
                    print(f"Errore durante l'inserimento del nuovo admin: {e}")
                    connection.rollback()
                    return f"Errore interno durante il salvataggio: {e}", 500
            
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
            
            # Top 3 dei quartieri (Borough) più pericolosi
            cursor.execute("""
                SELECT borough, COUNT(*), SUM(persons_injured), SUM(persons_killed)
                FROM ADMIN.incidenti
                WHERE borough IS NOT NULL
                GROUP BY borough
                ORDER BY COUNT(*) DESC
                FETCH FIRST 3 ROWS ONLY
            """)
            top_boroughs = cursor.fetchall() # Restituisce una lista di 3 tuple
            
    return render_template(
        'index.html',
        username = admin,
        permessi = permessi_admin,
        lista_admins=lista_admins,
        anno=anno_corrente,
        numero_incidenti=f"{totale_incidenti:,}".replace(",", "."), 
        numero_traffico=f"{totale_traffico:,}".replace(",", "."),
        tasso_mortalita=tasso_mortalita_str,
        causa_top=causa_top,
        incidenti_causa=incidenti_causa,
        incidenti_con_neve=incidenti_con_neve,
        top_boroughs=top_boroughs,
        successo=locals().get('messaggio_successo', None)
    )
    
if __name__ == '__main__':
    app.run(debug=True)
    