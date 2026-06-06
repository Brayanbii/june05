import os
import re
from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "sena_adso_student_key"

# ==========================================
# CONEXIÓN A MONGODB ATLAS (Clave Inyectada Directamente)
# ==========================================
CADENA_CONEXION = "mongodb+srv://brian_dt:FJG4MLFMR0bo0up2@cluster0.ry2pwjd.mongodb.net/sena_db?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = os.environ.get("MONGO_URI", CADENA_CONEXION)

def conectar_db():
    # Tiempo límite de selección de servidor configurado a 3 segundos para reaccionar ante fallos inmediatamente
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    return client

# Programas de formación académica del SENA con configuraciones cromáticas para la interfaz
PROGRAMAS_SENA = [
    {"nombre": "Análisis y Desarrollo de Software (ADSO)", "iso": "co", "color1": "#39A900", "color2": "#FFFFFF"}, # Verde Institucional
    {"nombre": "Diseño e Integración Multimedia", "iso": "es", "color1": "#002395", "color2": "#FFFFFF"},
    {"nombre": "Automatización Industrial", "iso": "br", "color1": "#FFDF00", "color2": "#009c3b"},
    {"nombre": "Gestión Administrativa", "iso": "fr", "color1": "#C60B1E", "color2": "#FFC400"},
    {"nombre": "Ciberseguridad y Redes", "iso": "mx", "color1": "#006847", "color2": "#FFFFFF"},
    {"nombre": "Animación Digital 3D", "iso": "us", "color1": "#FFFFFF", "color2": "#002868"}
]

@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = None
    tipo_mensaje = "success"
    
    # Control de Excepciones para Conexión de Base de Datos (Punto 4)
    try:
        client = conectar_db()
        db = client['sena_db']
        if db['programas'].count_documents({}) == 0:
            db['programas'].insert_many(PROGRAMAS_SENA)
        programas_col = db['programas']
        estudiantes_col = db['estudiantes']
    except Exception as e:
        # En caso de fallo de servidor o conexión, se intercepta de forma segura
        return render_template("error.html", titulo_error="Error de Conexión a MongoDB Atlas", error_mensaje=str(e))

    # PROCESAR Y VALIDAR FORMULARIO (Punto 1 y 2)
    if request.method == "POST":
        documento = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        programa = request.form.get("programa", "").strip()
        ficha = request.form.get("ficha", "").strip()

        # Patrón RegEx para verificar sintaxis de correo electrónico válida
        patron_correo = r"^[\w\.-]+@[\w\.-]+\.\w+$"

        # Validaciones de Datos solicitadas en el Punto 2
        if not all([documento, nombre, correo, programa, ficha]):
            mensaje, tipo_mensaje = "⚠️ Todos los campos son estrictamente obligatorios.", "danger"
        elif not documento.isdigit():
            mensaje, tipo_mensaje = "⚠️ El documento de identidad debe contener exclusivamente valores numéricos.", "danger"
        elif not re.match(patron_correo, correo):
            mensaje, tipo_mensaje = "⚠️ El formato del correo electrónico ingresado no es válido.", "danger"
        else:
            try:
                # Comprobar si el aprendiz ya está registrado en la base de datos distribuida
                if estudiantes_col.find_one({"documento": documento}):
                    return redirect(url_for("jugar", documento=documento))
                else:
                    info_programa = programas_col.find_one({"nombre": programa})
                    nuevo_estudiante = {
                        "documento": documento, 
                        "nombre": nombre, 
                        "correo": correo, 
                        "programa": programa, 
                        "iso": info_programa["iso"] if info_programa else "co",
                        "color1": info_programa["color1"] if info_programa else "#39A900",
                        "color2": info_programa["color2"] if info_programa else "#FFFFFF",
                        "ficha": ficha, 
                        "partidos_jugados": 0, 
                        "puntos": 0, 
                        "goles_favor": 0, 
                        "goles_contra": 0
                    }
                    estudiantes_col.insert_one(nuevo_estudiante)
                    return redirect(url_for("jugar", documento=documento))
            except Exception as e:
                return render_template("error.html", titulo_error="Error al Escribir en Base de Datos", error_mensaje=str(e))

    # CONSULTAR TODOS LOS ESTUDIANTES REGISTRADOS (Punto 3)
    try:
        lista_estudiantes = list(estudiantes_col.find().sort("puntos", -1))
        lista_programas = list(programas_col.find().sort("nombre", 1))
    except Exception as e:
        return render_template("error.html", titulo_error="Error al Recuperar Documentos", error_mensaje=str(e))

    return render_template("index.html", estudiantes=lista_estudiantes, programas=lista_programas, mensaje=mensaje, tipo_mensaje=tipo_mensaje)

@app.route("/jugar/<documento>")
def jugar(documento):
    """Carga la simulación interactiva con los datos persistidos del aprendiz"""
    try:
        client = conectar_db()
        db = client['sena_db']
        estudiante = db['estudiantes'].find_one({"documento": documento})
        if not estudiante: 
            return redirect(url_for("index"))
        
        # Selección aleatoria de un programa rival para interactuar en el canvas 2D
        rival = db['programas'].aggregate([{"$match": {"nombre": {"$ne": estudiante["programa"]}}}, {"$sample": {"size": 1}}]).next()
        
        return render_template("game.html", estudiante=estudiante, rival=rival)
    except Exception as e:
        return render_template("error.html", titulo_error="Fallo al Inicializar la Simulación", error_mensaje=str(e))

@app.route("/guardar_resultado", methods=["POST"])
def guardar_resultado():
    """Actualiza las métricas de desempeño lúdico del estudiante"""
    data = request.json
    try:
        client = conectar_db()
        db = client['sena_db']
        puntos = 3 if data['goles_l'] > data['goles_v'] else (1 if data['goles_l'] == data['goles_v'] else 0)
        
        db['estudiantes'].update_one(
            {"documento": data['documento']},
            {"$inc": {"partidos_jugados": 1, "puntos": puntos, "goles_favor": data['goles_l'], "goles_contra": data['goles_v']}}
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
