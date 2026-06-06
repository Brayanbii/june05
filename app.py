import os
import re
import random
from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "fifa_world_cup_2026_arcade"

# ==========================================
# CONEXIÓN A MONGODB ATLAS
# ==========================================
CADENA_CONEXION = "mongodb+srv://brian_dt:FJG4MLFMR0bo0up2@cluster0.ry2pwjd.mongodb.net/mundial2026_db?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = os.environ.get("MONGO_URI", CADENA_CONEXION)

def conectar_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    return client

# Ampliación de escuadras oficiales para la simulación del cuadro del Mundial 2026
EQUIPOS_REALES = [
    {"nombre": "Argentina", "iso": "ar", "color1": "#74ACDF", "color2": "#FFFFFF"},
    {"nombre": "Francia", "iso": "fr", "color1": "#002395", "color2": "#FFFFFF"},
    {"nombre": "Brasil", "iso": "br", "color1": "#FFDF00", "color2": "#009c3b"},
    {"nombre": "Colombia", "iso": "co", "color1": "#FCD116", "color2": "#003893"},
    {"nombre": "España", "iso": "es", "color1": "#C60B1E", "color2": "#FFC400"},
    {"nombre": "Inglaterra", "iso": "gb-eng", "color1": "#FFFFFF", "color2": "#CF081F"},
    {"nombre": "México", "iso": "mx", "color1": "#006847", "color2": "#FFFFFF"},
    {"nombre": "Estados Unidos", "iso": "us", "color1": "#002868", "color2": "#FFFFFF"},
    {"nombre": "Alemania", "iso": "de", "color1": "#FFFFFF", "color2": "#000000"},
    {"nombre": "Italia", "iso": "it", "color1": "#004FA3", "color2": "#FFFFFF"},
    {"nombre": "Portugal", "iso": "pt", "color1": "#E42522", "color2": "#126B33"},
    {"nombre": "Japón", "iso": "jp", "color1": "#000080", "color2": "#FFFFFF"}
]

@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = None
    tipo_mensaje = "success"
    
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        if db['selecciones'].count_documents({}) == 0:
            db['selecciones'].insert_many(EQUIPOS_REALES)
        selecciones_col = db['selecciones']
        dt_col = db['directores_tecnicos']
    except Exception as e:
        return render_template("error.html", titulo_error="Error de Conexión a BD", error_mensaje=str(e))

    if request.method == "POST":
        documento = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        equipo = request.form.get("equipo", "").strip()
        ficha = request.form.get("ficha", "").strip()

        if not all([documento, nombre, correo, equipo, ficha]):
            mensaje, tipo_mensaje = "⚠️ Todos los campos son obligatorios.", "danger"
        elif not documento.isdigit():
            mensaje, tipo_mensaje = "⚠️ El documento debe ser numérico.", "danger"
        else:
            if dt_col.find_one({"documento": documento}):
                return redirect(url_for("jugar", documento=documento))
            else:
                info_seleccion = selecciones_col.find_one({"nombre": equipo})
                nuevo_dt = {
                    "documento": documento, "nombre": nombre, "correo": correo, 
                    "equipo": equipo, "iso": info_seleccion["iso"] if info_seleccion else "co",
                    "color1": info_seleccion["color1"] if info_seleccion else "#fff",
                    "color2": info_seleccion["color2"] if info_seleccion else "#000",
                    "ficha": ficha, "partidos_jugados": 0, "puntos": 0, "goles_favor": 0, "goles_contra": 0
                }
                dt_col.insert_one(nuevo_dt)
                return redirect(url_for("jugar", documento=documento))

    try:
        lista_dts = list(dt_col.find().sort("puntos", -1))
        lista_paises = list(selecciones_col.find().sort("nombre", 1))
    except Exception as e:
        return render_template("error.html", titulo_error="Error", error_mensaje=str(e))

    return render_template("index.html", dts=lista_dts, selecciones=lista_paises, mensaje=mensaje, tipo_mensaje=tipo_mensaje)

@app.route("/jugar/<documento>")
def jugar(documento):
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        dt = db['directores_tecnicos'].find_one({"documento": documento})
        if not dt: return redirect(url_for("index"))
        
        # Enviamos toda la lista de selecciones disponibles al cliente para armar el fixture del campeonato
        todas_selecciones = list(db['selecciones'].find({}, {"_id": 0}))
        
        return render_template("game.html", dt=dt, todas_selecciones=todas_selecciones)
    except Exception as e:
        return render_template("error.html", titulo_error="Fallo al cargar el juego", error_mensaje=str(e))

@app.route("/guardar_resultado", methods=["POST"])
def guardar_resultado():
    data = request.json
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        
        # El backend procesa el acumulado de todo el campeonato jugado en la sesión
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
