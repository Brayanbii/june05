import os
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DE CONEXIÓN CON MONGO ATLAS
# ==========================================
# Usa tu nueva cadena pulida con la contraseña Sena2026Pro
MONGO_URI = os.environ.get(
    "MONGO_URI", 
    "mongodb+srv://brian_dt:Sena2026Pro@cluster0.ry2pwjd.mongodb.net/sena_core_db?retryWrites=true&w=majority"
)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client['sena_core_db']
    collection = db['estudiantes']
    # Comprobación de estado física
    client.admin.command('ping')
    db_connected = True
    db_error_msg = None
    print(">>> [SENA ENGINE] Conexión 100% exitosa a MongoDB Atlas.")
except Exception as e:
    db_connected = False
    collection = None
    db_error_msg = str(e)
    print(f">>> [SENA ENGINE] Error crítico capturado en conexión: {e}")

# Mapeado exacto para el bucle {% for prog in programas %} -> {{ prog.nombre }} de tu HTML
PROGRAMAS_SENA = [
    {"nombre": "Análisis y Desarrollo de Software (ADSO)"},
    {"nombre": "Gestión de Redes de Datos"},
    {"nombre": "Animación Digital"},
    {"nombre": "Desarrollo Multimedia y Web"},
    {"nombre": "Sistemas y Programación"}
]

# Helper para extraer y estructurar los registros como los pide tu plantilla index.html
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
            "iso": est.get("iso", "co"),   # Bandera por defecto (co)
            "puntos": est.get("puntos", 100),
            "partidos_jugados": est.get("partidos_jugados", 0),
            "goles_favor": est.get("goles_favor", 0)
        })
    return lista


# ==========================================
# CONTROLADOR PRINCIPAL (MÉTODOS GET Y POST)
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def index():
    # 4. Control de excepciones previo: Si la DB falla, salta a la terminal-log de error.html
    if not db_connected or collection is None:
        return render_template(
            'error.html', 
            titulo_error="Fallo Crítico de Autenticación o Red en Mongo Atlas", 
            error_mensaje=f"El servidor Flask no pudo establecer comunicación con el clúster remoto. Detalles del error técnico:\n\n{db_error_msg}\n\nCONSEJO: Asegúrate de habilitar el acceso a cualquier IP (0.0.0.0/0) en la sección 'Network Access' de tu consola de MongoDB Atlas."
        )

    if request.method == 'POST':
        try:
            # 1. Recuperar datos del formulario
            documento = request.form.get('documento', '').strip()
            nombre = request.form.get('nombre', '').strip()
            correo = request.form.get('correo', '').strip()
            programa = request.form.get('programa', '').strip()
            ficha = request.form.get('ficha', '').strip()

            # 2. Validar los datos registrados por el usuario
            if not all([documento, nombre, correo, programa, ficha]):
                return render_template('index.html', dts=obtener_estudiantes_mapeados(), programas=PROGRAMAS_SENA, mensaje="Error: Todos los campos son obligatorios.", tipo_mensaje="danger")

            if not documento.isdigit():
                return render_template('index.html', dts=obtener_estudiantes_mapeados(), programas=PROGRAMAS_SENA, mensaje="Error: El documento debe contener solo números.", tipo_mensaje="danger")

            if not ficha.isdigit():
                return render_template('index.html', dts=obtener_estudiantes_mapeados(), programas=PROGRAMAS_SENA, mensaje="Error: La ficha debe ser un número entero válido.", tipo_mensaje="danger")

            if "@" not in correo or "." not in correo:
                return render_template('index.html', dts=obtener_estudiantes_mapeados(), programas=PROGRAMAS_SENA, mensaje="Error: Estructura de correo electrónico inválida.", tipo_mensaje="danger")

            # JSON adaptado a los campos Arcade de tu tabla actual
            nuevo_estudiante = {
                "documento": documento,
                "nombre": nombre,
                "correo": correo,
                "equipo": programa,  
                "ficha": ficha,
                "iso": "co",         
                "puntos": 120,       # Puntos iniciales para la clasificación
                "partidos_jugados": 0,
                "goles_favor": 0
            }

            # Guardar en Mongo Atlas
            collection.insert_one(nuevo_estudiante)
            return redirect(url_for('success'))

        except Exception as e:
            return render_template(
                'error.html', 
                titulo_error="Excepción en Proceso de Registro", 
                error_mensaje=f"Error técnico interceptado en caliente por Try-Except:\n\n{str(e)}"
            )

    # Si entra por GET: 3. Consultar y mostrar todos los estudiantes registrados
    try:
        dts_actuales = obtener_estudiantes_mapeados()
        return render_template('index.html', dts=dts_actuales, programas=PROGRAMAS_SENA)
    except PyMongoError as e:
        return render_template(
            'error.html', 
            titulo_error="Error de Lectura de Datos", 
            error_mensaje=f"Ocurrió un error al intentar consultar los registros en la nube de Atlas: {str(e)}"
        )


@app.route('/success')
def success():
    return render_template('success.html')


@app.route('/error')
def error():
    return render_template('error.html')


if __name__ == '__main__':
    app.run(debug=True)
