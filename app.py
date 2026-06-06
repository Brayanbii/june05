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

# Equipos con sus colores oficiales para renderizar los uniformes en el juego 2D
EQUIPOS_REALES = [
    {"nombre": "Argentina", "iso": "ar", "color1": "#74ACDF", "color2": "#FFFFFF"},
    {"nombre": "Francia", "iso": "fr", "color1": "#002395", "color2": "#FFFFFF"},
    {"nombre": "Brasil", "iso": "br", "color1": "#FFDF00", "color2": "#009c3b"},
    {"nombre": "Colombia", "iso": "co", "color1": "#FCD116", "color2": "#003893"},
    {"nombre": "España", "iso": "es", "color1": "#C60B1E", "color2": "#FFC400"},
    {"nombre": "Inglaterra", "iso": "gb-eng", "color1": "#FFFFFF", "color2": "#CF081F"},
    {"nombre": "México", "iso": "mx", "color1": "#006847", "color2": "#FFFFFF"},
    {"nombre": "Estados Unidos", "iso": "us", "color1": "#FFFFFF", "color2": "#002868"}
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

    # PROCESAR FORMULARIO (REQUISITO SENA)
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
                # Si ya existe, lo mandamos directo a jugar
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
    """Carga la arena de juego interactiva HTML5"""
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        dt = db['directores_tecnicos'].find_one({"documento": documento})
        if not dt: return redirect(url_for("index"))
        
        # Elegir un rival aleatorio que no sea el mismo
        rival = db['selecciones'].aggregate([{"$match": {"nombre": {"$ne": dt["equipo"]}}}, {"$sample": {"size": 1}}]).next()
        
        return render_template("game.html", dt=dt, rival=rival)
    except Exception as e:
        return render_template("error.html", titulo_error="Fallo al cargar el juego", error_mensaje=str(e))

@app.route("/guardar_resultado", methods=["POST"])
def guardar_resultado():
    """Recibe los goles desde el juego en JavaScript y actualiza la BD"""
    data = request.json
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        puntos = 3 if data['goles_l'] > data['goles_v'] else (1 if data['goles_l'] == data['goles_v'] else 0)
        
        db['directores_tecnicos'].update_one(
            {"documento": data['documento']},
            {"$inc": {"partidos_jugados": 1, "puntos": puntos, "goles_favor": data['goles_l'], "goles_contra": data['goles_v']}}
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
