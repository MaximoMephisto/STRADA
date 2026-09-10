from flask import Flask, render_template
# Crea un'istanza dell'app Flask
app = Flask(__name__)
# Definisci una route per la home page
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)