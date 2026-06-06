from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient  # Basado en tus requirements.txt

app = Flask(__name__)

# Ejemplo de conexión (ajusta con tu configuración)
# client = MongoClient("tu_uri_de_mongodb")
# db = client['tu_base_de_datos']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    # 1. Aquí procesas los datos del formulario (request.form)
    # 2. Guardas en MongoDB usando pymongo
    
    # 3. En lugar de renderizar el juego, rediriges a la pantalla de éxito
    return redirect(url_for('success'))

@app.route('/success')
def success():
    # Renderiza la nueva plantilla limpia y minimalista
    return render_template('success.html')

@app.route('/error')
def error():
    return render_template('error.html')

if __name__ == '__main__':
    app.run(debug=True)
