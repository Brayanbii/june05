import os
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DE CONEXIÓN CON MONGO ATLAS
# ==========================================
MONGO_URI = os.environ.get(
    "MONGO_URI", 
    "mongodb+srv://brian_dt:Sena2026Pro@cluster0.ry2pwjd.mongodb.net/sena_core_db?retryWrites=true&w=majority"
)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client['sena_core_db']
    collection = db['estudiantes']
    # Verificación física de conexión
    client.admin.command('ping')
    db_connected = True
    db_error_msg = None
    print(">>> [SENA ENGINE] Conexión exitosa a MongoDB Atlas.")
except Exception as e:
    db_connected = False
    collection = None
    db_error_msg = str(e)
    print(f">>> [SENA ENGINE] Error de conexión: {e}")

# Listado de programas para el select del formulario
PROGRAMAS_SENA = [
    "Análisis y Desarrollo de Software (ADSO)",
    "Gestión de Redes de Datos",
    "Animación Digital",
    "Desarrollo Multimedia y Web",
    "Sistemas y Programación"
]

# ==========================================
# ENRUTAMIENTO Y LÓGICA CENTRAL
# ==========================================

@app.route('/', methods=['GET', 'POST'])
@app.route('/registrar', methods=['GET', 'POST'])
def index():
    # 4. Control de excepciones: Si la base de datos no responde, muestra el error estilizado
    if not db_connected or collection is None:
        return render_template(
            'error.html', 
            titulo_error="Fallo de Conexión con Mongo Atlas", 
            error_mensaje=f"Detalles técnicos del fallo:\n\n{db_error_msg}\n\nCONSEJO: Verifica el 'Network Access' en MongoDB Atlas para permitir conexiones desde cualquier IP (0.0.0.0/0)."
        )

    # 1. Procesar el registro cuando el usuario envía el formulario (POST)
    if request.method == 'POST':
        try:
            documento = request.form.get('documento', '').strip()
            nombre = request.form.get('nombre', '').strip()
            correo = request.form.get('correo', '').strip()
            programa = request.form.get('programa', '').strip()
            ficha = request.form.get('ficha', '').strip()

            # 2. Validar los datos del usuario en el Servidor
            if not all([documento, nombre, correo, programa, ficha]):
                return render_template('index.html', estudiantes=list(collection.find()), programas=PROGRAMAS_SENA, mensaje="Error: Todos los campos son obligatorios.", tipo_mensaje="danger")

            if not documento.isdigit() or not ficha.isdigit():
                return render_template('index.html', estudiantes=list(collection.find()), programas=PROGRAMAS_SENA, mensaje="Error: El documento y la ficha deben ser numéricos.", tipo_mensaje="danger")

            if "@" not in correo or "." not in correo:
                return render_template('index.html', estudiantes=list(collection.find()), programas=PROGRAMAS_SENA, mensaje="Error: Estructura de correo inválida.", tipo_mensaje="danger")

            # Estructura del documento para MongoDB con métricas iniciales simuladas
            nuevo_estudiante = {
                "documento": documento,
                "nombre": nombre,
                "correo": correo,
                "programa": programa,
                "ficha": ficha,
                "horas_practica": 40,       # Horas iniciales de formación
                "competencias_ok": 2,      # Competencias aprobadas por defecto
                "score_rendimiento": 100   # XP Académico inicial
            }

            # Guardar en Mongo Atlas
            collection.insert_one(nuevo_estudiante)
            return redirect(url_for('success'))

        except Exception as e:
            return render_template(
                'error.html', 
                titulo_error="Excepción en Proceso de Registro", 
                error_mensaje=str(e)
            )

    # 3. Consultar todos los estudiantes registrados (GET)
    try:
        lista_estudiantes = list(collection.find())
        return render_template('index.html', estudiantes=lista_estudiantes, programas=PROGRAMAS_SENA)
    except PyMongoError as e:
        return render_template(
            'error.html', 
            titulo_error="Error de Consulta de Datos", 
            error_mensaje=str(e)
        )


@app.route('/success')
def success():
    return render_template('success.html')


@app.route('/error')
def error():
    return render_template('error.html')


if __name__ == '__main__':
    app.run(debug=True)
