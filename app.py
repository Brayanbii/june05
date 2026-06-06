import os
import re
import random
from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "sena_adso_arcade_cup"

# ==========================================
# CONEXIÓN A MONGODB ATLAS (REQUISITO CONTROL EXCEPCIONES)
# ==========================================
CADENA_CONEXION = "mongodb+srv://brian_dt:FJG4MLFMR0bo0up2@cluster0.ry2pwjd.mongodb.net/mundial2026_db?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = os.environ.get("MONGO_URI", CADENA_CONEXION)

def conectar_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    return client

# Programas de formación académica con configuraciones visuales heredadas para el simulador 2D
PROGRAMAS_REALES = [
    {"nombre": "Análisis y Desarrollo de Software (ADSO)", "iso": "co", "color1": "#39A900", "color2": "#FFFFFF"}, # Colores Institucionales SENA
    {"nombre": "Diseño e Integración Multimedia", "iso": "es", "color1": "#C60B1E", "color2": "#FFC400"},
    {"nombre": "Gestión Administrativa", "iso": "fr", "color1": "#002395", "color2": "#FFFFFF"},
    {"nombre": "Automatización Industrial", "iso": "br", "color1": "#FFDF00", "color2": "#009c3b"},
    {"nombre": "Ciberseguridad y Redes", "iso": "us", "color1": "#002868", "color2": "#FFFFFF"},
    {"nombre": "Animación 3D y Videojuegos", "iso": "ar", "color1": "#74ACDF", "color2": "#FFFFFF"}
]

@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = None
    tipo_mensaje = "success"
    
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        
        # Inicializar colección de programas si se encuentra vacía
        if db['programas'].count_documents({}) == 0:
            db['programas'].insert_many(PROGRAMAS_REALES)
            
        programas_col = db['programas']
        estudiantes_col = db['estudiantes']
    except Exception as e:
        # Requisito SENA: Captura segura y renderizado del pantallazo de error de servidor/BD
        return render_template("error.html", titulo_error="Error Crítico de Conexión a MongoDB Atlas", error_mensaje=str(e))

    # PROCESAR FORMULARIO CON VALIDACIONES ROBUSTAS (Punto 1 y 2 del taller)
    if request.method == "POST":
        documento = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        programa = request.form.get("programa", "").strip()
        ficha = request.form.get("ficha", "").strip()

        # Expresión regular estándar para validación sintáctica de emails
        patron_correo = r"^[\w\.-]+@[\w\.-]+\.\w+$"

        if not all([documento, nombre, correo, programa, ficha]):
            mensaje, tipo_mensaje = "⚠️ Todos los campos son estrictamente obligatorios.", "danger"
        elif not documento.isdigit():
            mensaje, tipo_mensaje = "⚠️ El documento de identidad debe constar únicamente de caracteres numéricos.", "danger"
        elif not re.match(patron_correo, correo):
            mensaje, tipo_mensaje = "⚠️ El correo electrónico ingresado no posee un formato sintáctico válido.", "danger"
        else:
            try:
                if estudiantes_col.find_one({"documento": documento}):
                    # Si el aprendiz ya existe, redirige directamente a su entorno interactivo
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
                        "color2": info_programa["color2"] if info_programa else "#ffffff",
                        "ficha": ficha, 
                        "partidos_jugados": 0, 
                        "puntos": 0, 
                        "goles_favor": 0, 
                        "goles_contra": 0
                    }
                    estudiantes_col.insert_one(nuevo_estudiante)
                    return redirect(url_for("jugar", documento=documento))
            except Exception as e:
                return render_template("error.html", titulo_error="Excepción en Operación de Persistencia", error_mensaje=str(e))

    # CONSULTAR TODOS LOS ESTUDIANTES REGISTRADOS (Punto 3 del taller)
    try:
        lista_estudiantes = list(estudiantes_col.find().sort("puntos", -1))
        lista_programas = list(programas_col.find().sort("nombre", 1))
    except Exception as e:
        return render_template("error.html", titulo_error="Error en Consulta de Documentos", error_mensaje=str(e))

    return render_template("index.html", estudiantes=lista_estudiantes, programas=lista_programas, mensaje=mensaje, tipo_mensaje=tipo_mensaje)

@app.route("/jugar/<documento>")
def jugar(documento):
    """Carga la arena interactiva utilizando los datos del estudiante matriculado"""
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        estudiante = db['estudiantes'].find_one({"documento": documento})
        if not estudiante: 
            return redirect(url_for("index"))
        
        # Seleccionar una facultad rival aleatoria de la base de datos
        rival = db['programas'].aggregate([{"$match": {"nombre": {"$ne": estudiante["programa"]}}}, {"$sample": {"size": 1}}]).next()
        
        return render_template("game.html", estudiante=estudiante, rival=rival)
    except Exception as e:
        return render_template("error.html", titulo_error="Fallo al Inicializar Entorno Lúdico", error_mensaje=str(e))

@app.route("/guardar_resultado", methods=["POST"])
def guardar_resultado():
    """Actualiza las métricas de desempeño del estudiante tras interactuar con la simulación 2D"""
    data = request.json
    try:
        client = conectar_db()
        db = client['mundial2026_db']
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
