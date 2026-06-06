import os
import re
import random
from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "fifa_sena_world_cup_2026"

# ==========================================
# CONEXIÓN DIRECTA A TU MONGODB ATLAS
# ==========================================
CADENA_CONEXION = "mongodb+srv://brian_dt:FJG4MLFMR0bo0up2@cluster0.ry2pwjd.mongodb.net/mundial2026_db?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = os.environ.get("MONGO_URI", CADENA_CONEXION)

def conectar_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    return client

# Fusión Académica y Deportiva: Cumple los requisitos del SENA y mantiene la inmersión del Mundial
PROGRAMAS_MUNDIAL = [
    {"nombre": "Colombia (ADSO)", "iso": "co", "color1": "#FCD116", "color2": "#003893"},
    {"nombre": "Argentina (Multimedia)", "iso": "ar", "color1": "#74ACDF", "color2": "#FFFFFF"},
    {"nombre": "Brasil (Automatización)", "iso": "br", "color1": "#FFDF00", "color2": "#009c3b"},
    {"nombre": "España (Ciberseguridad)", "iso": "es", "color1": "#C60B1E", "color2": "#FFC400"},
    {"nombre": "Francia (Gestión Administrativa)", "iso": "fr", "color1": "#002395", "color2": "#FFFFFF"},
    {"nombre": "México (Animación 3D)", "iso": "mx", "color1": "#006847", "color2": "#FFFFFF"},
    {"nombre": "Estados Unidos (Redes)", "iso": "us", "color1": "#002868", "color2": "#FFFFFF"},
    {"nombre": "Alemania (Mantenimiento)", "iso": "de", "color1": "#FFFFFF", "color2": "#000000"}
]

@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = None
    tipo_mensaje = "success"
    
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        
        # Población automática de la colección para asegurar que el dropdown nunca esté vacío
        if db['programas_formacion'].count_documents({}) == 0:
            db['programas_formacion'].insert_many(PROGRAMAS_MUNDIAL)
            
        programas_col = db['programas_formacion']
        dt_col = db['directores_tecnicos']
    except Exception as e:
        # Requisito SENA: Renderizado del pantallazo controlado ante errores de BD
        return render_template("error.html", titulo_error="Error de Conexión a MongoDB Atlas", error_mensaje=str(e))

    # PROCESAMIENTO Y VALIDACIÓN DE DATOS (Punto 1 y 2)
    if request.method == "POST":
        documento = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        programa = request.form.get("programa", "").strip()
        ficha = request.form.get("ficha", "").strip()

        patron_correo = r"^[\w\.-]+@[\w\.-]+\.\w+$"

        if not all([documento, nombre, correo, programa, ficha]):
            mensaje, tipo_mensaje = "⚠️ Todos los campos son obligatorios para la acreditación.", "danger"
        elif not documento.isdigit():
            mensaje, tipo_mensaje = "⚠️ El documento de identidad debe contener únicamente números.", "danger"
        elif not re.match(patron_correo, correo):
            mensaje, tipo_mensaje = "⚠️ El formato del correo electrónico ingresado no es válido.", "danger"
        else:
            try:
                if dt_col.find_one({"documento": documento}):
                    return redirect(url_for("jugar", documento=documento))
                else:
                    info_programa = programas_col.find_one({"nombre": programa})
                    nuevo_dt = {
                        "documento": documento, "nombre": nombre, "correo": correo, 
                        "equipo": programa, "iso": info_programa["iso"] if info_programa else "co",
                        "color1": info_programa["color1"] if info_programa else "#fff",
                        "color2": info_programa["color2"] if info_programa else "#000",
                        "ficha": ficha, "partidos_jugados": 0, "puntos": 0, "goles_favor": 0, "goles_contra": 0
                    }
                    dt_col.insert_one(nuevo_dt)
                    return redirect(url_for("jugar", documento=documento))
            except Exception as e:
                return render_template("error.html", titulo_error="Excepción en Operación de Escritura", error_mensaje=str(e))

    # CONSULTAR TODOS LOS REGISTROS DE LA BASE DE DATOS (Punto 3)
    try:
        lista_dts = list(dt_col.find().sort("puntos", -1))
        lista_programas = list(programas_col.find().sort("nombre", 1))
    except Exception as e:
        return render_template("error.html", titulo_error="Error al Consultar Colecciones", error_mensaje=str(e))

    return render_template("index.html", dts=lista_dts, programas=lista_programas, mensaje=mensaje, tipo_mensaje=tipo_mensaje)

@app.route("/jugar/<documento>")
def jugar(documento):
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        dt = db['directores_tecnicos'].find_one({"documento": documento})
        if not dt: return redirect(url_for("index"))
        
        todas_selecciones = list(db['programas_formacion'].find({}, {"_id": 0}))
        return render_template("game.html", dt=dt, todas_selecciones=todas_selecciones)
    except Exception as e:
        return render_template("error.html", titulo_error="Fallo al Inicializar Cancha Arcade", error_mensaje=str(e))

@app.route("/guardar_resultado", methods=["POST"])
def guardar_resultado():
    data = request.json
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        db['directores_tecnicos'].update_one(
            {"documento": data['documento']},
            {"$inc": {
                "partidos_jugados": int(data['partidos_jugados']), 
                "puntos": int(data['puntos_acumulados']), 
                "goles_favor": int(data['goles_favor']), 
                "goles_contra": int(data['goles_contra'])
            }}
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
