import os
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DE CONEXIÓN CON MONGO ATLAS
# ==========================================
# Integrada tu clave real y corregida directamente aquí
MONGO_URI = os.environ.get(
    "MONGO_URI", 
    "mongodb+srv://brian_dt:Sena2026Pro@cluster0.ry2pwjd.mongodb.net/sena_core_db?retryWrites=true&w=majority"
)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client['sena_core_db']
    collection = db['estudiantes']
    # Comprobación física de estado de la red con Atlas
    client.admin.command('ping')
    db_connected = True
    db_error_msg = None
    print(">>> [SENA ENGINE] Conexión 100% exitosa a MongoDB Atlas.")
except Exception as e:
    db_connected = False
    collection = None
    db_error_msg = str(e)
    print(f">>> [SENA ENGINE] Error crítico capturado en conexión: {e}")

# Estructura exacta para el bucle {% for prog in programas %} -> {{ prog.nombre }} de tu index.html
PROGRAMAS_SENA = [
    {"nombre": "Análisis y Desarrollo de Software (ADSO)"},
    {"nombre": "Gestión de Redes de Datos"},
    {"nombre": "Animación Digital"},
    {"nombre": "Desarrollo Multimedia y Web"},
    {"nombre": "Sistemas y Programación"}
]

# Helper para extraer y estructurar los registros mapeados con las variables de tu tabla
def obtener_estudiantes_mapeados():
    if collection is None:
        return []
    estudiantes_cursor = collection.find()
    lista = []
    for est in estudiantes_cursor:
        lista.append({
            "documento": est.get("documento"),
            "nombre": est.get("nombre"),
            "correo": est.get("correo"),
            "equipo": est.get("equipo"),  # Mapeado a {{ dt.equipo }}
            "ficha": est.get("ficha"),
            "iso": est.get("iso", "co"),   # Bandera por defecto
            "puntos": est.get("puntos", 120),
            "partidos_jugados": est.get("partidos_jugados", 0),
            "goles_favor": est.get("goles_favor", 0)
        })
    return lista

# ==========================================
# LÓGICA CENTRAL DE REGISTRO (MIDDLEWARE)
# ==========================================
def ejecutar_registro_aprendiz():
    try:
        # 1. Recuperar datos del formulario
        documento = request.form.get('documento', '').strip()
        nombre = request.form.get('nombre', '').strip()
        correo = request.form.get('correo', '').strip()
        programa = request.form.get('programa', '').strip()
        ficha = request.form.get('ficha', '').strip()

        # 2. Validar los datos registrados por el usuario (Requerimiento SENA)
        if not all([documento, nombre, correo, programa, ficha]):
            return render_template('index.html', dts=obtener_estudiantes_mapeados(), programas=PROGRAMAS_SENA, mensaje="Error: Todos los campos son obligatorios.", tipo_mensaje="danger")

        if not documento.isdigit():
            return render_template('index.html', dts=obtener_estudiantes_mapeados(), programas=PROGRAMAS_SENA, mensaje="Error: El documento debe contener solo números.", tipo_mensaje="danger")

        if not ficha.isdigit():
            return render_template('index.html', dts=obtener_estudiantes_mapeados(), programas=PROGRAMAS_SENA, mensaje="Error: La ficha debe ser un número entero válido.", tipo_mensaje="danger")

        if "@" not in correo or "." not in correo:
            return render_template('index.html', dts=obtener_estudiantes_mapeados(), programas=PROGRAMAS_SENA, mensaje="Error: Estructura de correo electrónico inválida.", tipo_mensaje="danger")

        # Documento JSON listo para guardar en la colección de Mongo Atlas
        nuevo_estudiante = {
            "documento": documento,
            "nombre": nombre,
            "correo": correo,
            "equipo": programa,  
            "ficha": ficha,
            "iso": "co",         
            "puntos": 120,       # Puntos de torneo iniciales para tu diseño arcade
            "partidos_jugados": 0,
            "goles_favor": 0
        }

        collection.insert_one(nuevo_estudiante)
        return redirect(url_for('success'))

    except Exception as e:
        # 4. Controlar excepciones inesperadas empleando Try – Except
        return render_template(
            'error.html', 
            titulo_error="Excepción en Proceso de Registro", 
            error_mensaje=f"Error de base de datos interceptado por Try-Except:\n\n{str(e)}"
        )

# ==========================================
# ENRUTAMIENTO CONTROLADO
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def index():
    # Validación previa de conexión segura
    if not db_connected or collection is None:
        return render_template(
            'error.html', 
            titulo_error="Fallo Crítico de Autenticación o Red en Mongo Atlas", 
            error_mensaje=f"El servidor Flask no pudo establecer comunicación con el clúster remoto. Detalles del error técnico:\n\n{db_error_msg}\n\nCONSEJO: Verifica que tu IP actual o la de Render esté permitida en la sección 'Network Access' de MongoDB Atlas."
        )

    if request.method == 'POST':
        return ejecutar_registro_aprendiz()

    # 3. Consultar todos los estudiantes registrados (Método GET)
    try:
        dts_actuales = obtener_estudiantes_mapeados()
        return render_template('index.html', dts=dts_actuales, programas=PROGRAMAS_SENA)
    except PyMongoError as e:
        return render_template(
            'error.html', 
            titulo_error="Error de Lectura de Datos", 
            error_mensaje=f"Ocurrió un error al intentar consultar los registros en la nube de Atlas: {str(e)}"
        )

# ESCUDO CONTRA 404: Si el formulario o el usuario cae en /registrar por GET o POST, se procesa sin caerse
@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        return ejecutar_registro_aprendiz()
    return redirect(url_for('index'))


@app.route('/success')
def success():
    return render_template('success.html')


@app.route('/error')
def error():
    return render_template('error.html')


if __name__ == '__main__':
    app.run(debug=True)
