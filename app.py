import os
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DEL MOTOR MONGO ATLAS REAL
# ==========================================
# Se añade serverSelectionTimeoutMS=3000 para que si falla la red o las IPs de Atlas,
# el bloque Try-Except responda en 3 segundos en lugar de congelar el servidor.
MONGO_URI = "mongodb+srv://brian_dt:5evUgWVBdUqylln6@cluster0.ry2pwjd.mongodb.net/?appName=Cluster0"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client['sena_core_db']
    collection = db['estudiantes']
    # Comando de verificación inmediata para validar el puente físico con Atlas
    client.admin.command('ping')
    db_connected = True
    db_error_msg = None
    print(">>> [SENA ENGINE] Conexión 100% exitosa a MongoDB Atlas.")
except Exception as e:
    db_connected = False
    collection = None
    db_error_msg = str(e)
    print(f">>> [SENA ENGINE] Error crítico capturado en conexión: {e}")

# Listado oficial de programas para el componente select del formulario
PROGRAMAS_SENA = [
    "Análisis y Desarrollo de Software (ADSO)",
    "Gestión de Redes de Datos",
    "Animación Digital",
    "Desarrollo Multimedia y Web",
    "Sistemas y Programación"
]

# ==========================================
# REGLAS DE ENRUTAMIENTO Y LOGICA (TRY - EXCEPT)
# ==========================================

@app.route('/')
def index():
    # 4. Control de excepciones previo: Si el clúster falla o no conecta, se aborta y se muestra la pantalla de error
    if not db_connected or collection is None:
        return render_template(
            'error.html', 
            titulo_error="Fallo Crítico de Autenticación o Red en Mongo Atlas", 
            error_mensaje=f"El servidor Flask no pudo establecer comunicación con el clúster remoto. Detalles del error técnico:\n\n{db_error_msg}\n\nCONSEJO: Asegúrate de habilitar el acceso a cualquier IP (0.0.0.0/0) en la sección 'Network Access' de tu consola de MongoDB Atlas."
        )
    
    try:
        # 3. Consultar todos los estudiantes registrados en tiempo real
        estudiantes_cursor = collection.find()
        lista_estudiantes = list(estudiantes_cursor)
        return render_template('index.html', estudiantes=lista_estudiantes, programas=PROGRAMAS_SENA)
        
    except PyMongoError as e:
        # 4. Captura de errores inesperados durante operaciones de lectura
        return render_template(
            'error.html', 
            titulo_error="Error de Lectura de Cursor en MongoDB Atlas", 
            error_mensaje=f"Excepción de base de datos en tiempo de ejecución: {str(e)}"
        )


@app.route('/registrar', methods=['POST'])
def registrar():
    if not db_connected or collection is None:
        return redirect(url_for('index'))
        
    try:
        # 1. Recepción y limpieza de las variables del formulario
        documento = request.form.get('documento', '').strip()
        nombre = request.form.get('nombre', '').strip()
        correo = request.form.get('correo', '').strip()
        programa = request.form.get('programa', '').strip()
        ficha = request.form.get('ficha', '').strip()
        
        # 2. Módulo de validación estricta de datos de usuario en Servidor
        if not all([documento, nombre, correo, programa, ficha]):
            return render_template(
                'index.html', 
                estudiantes=list(collection.find()), 
                programas=PROGRAMAS_SENA,
                mensaje_alerta="Error: Todos los campos solicitados en el formulario son obligatorios.",
                tipo_alerta="danger"
            )
            
        if not documento.isdigit():
            return render_template(
                'index.html', 
                estudiantes=list(collection.find()), 
                programas=PROGRAMAS_SENA,
                mensaje_alerta="Error: El Documento de Identidad debe ser únicamente numérico.",
                tipo_alerta="danger"
            )
            
        if not ficha.isdigit():
            return render_template(
                'index.html', 
                estudiantes=list(collection.find()), 
                programas=PROGRAMAS_SENA,
                mensaje_alerta="Error: El número de Ficha Académica debe contener solo números enteros.",
                tipo_alerta="danger"
            )
            
        if "@" not in correo or "." not in correo:
            return render_template(
                'index.html', 
                estudiantes=list(collection.find()), 
                programas=PROGRAMAS_SENA,
                mensaje_alerta="Error: El correo electrónico provisto no tiene una estructura formal válida.",
                tipo_alerta="danger"
            )

        # Inicialización de métricas avanzadas (Motor Pro) para el estudiante
        nuevo_estudiante = {
            "documento": documento,
            "nombre": nombre,
            "correo": correo,
            "programa": programa,
            "ficha": ficha,
            "horas_practica": 0,       # Comienza su ruta formativa con 0 horas
            "competencias_ok": 0,      # Inicia sin competencias validadas
            "score_rendimiento": 100   # XP base asignado por el motor central
        }
        
        # Escritura del documento BSON directamente en la nube de Atlas
        collection.insert_one(nuevo_estudiante)
        return redirect(url_for('success'))
        
    except Exception as e:
        # 4. Controlar excepciones inesperadas mediante Try - Except
        return render_template(
            'error.html', 
            titulo_error="Excepción en Proceso de Escritura/Inserción", 
            error_mensaje=f"Fallo crítico interceptado por el middleware de seguridad de Flask:\n\n{str(e)}"
        )


@app.route('/success')
def success():
    return render_template('success.html')


if __name__ == '__main__':
    app.run(debug=True)
