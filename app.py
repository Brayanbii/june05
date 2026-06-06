import os
import re
import random
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError

app = Flask(__name__)
app.secret_key = "fifa_world_cup_2026_ultra_premium_key"

CADENA_CONEXION_REAL = "mongodb+srv://brian_dt:FJG4MLFMR0bo0up2@cluster0.ry2pwjd.mongodb.net/mundial2026_db?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = os.environ.get("MONGO_URI", CADENA_CONEXION_REAL)

def conectar_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    return client

def inicializar_torneo_48(db):
    if db['selecciones'].count_documents({}) == 0:
        grupos = {
            "A": [("México", "#006847"), ("Estados Unidos", "#002868"), ("Canadá", "#FF0000"), ("Panamá", "#DA121A")],
            "B": [("Argentina", "#74ACDF"), ("Ecuador", "#FFDD00"), ("Venezuela", "#7B142C"), ("Jamaica", "#009B3A")],
            "C": [("Brasil", "#FFDF00"), ("Uruguay", "#00A6EF"), ("Colombia", "#FCD116"), ("Paraguay", "#D5141A")],
            "D": [("Francia", "#002395"), ("Países Bajos", "#21468B"), ("Polonia", "#DC143C"), ("Austria", "#ED2939")],
            "E": [("Inglaterra", "#FFFFFF"), ("Italia", "#0066BC"), ("Ucrania", "#FFD700"), ("Gales", "#CE1126")],
            "F": [("Alemania", "#000000"), ("España", "#C60B1E"), ("Bélgica", "#E30A17"), ("Escocia", "#002B62")],
            "G": [("Portugal", "#FF0000"), ("Turquía", "#E30A17"), ("Rep. Checa", "#11457E"), ("Georgia", "#FF0000")],
            "H": [("Japón", "#000080"), ("Corea del Sur", "#CD113B"), ("Australia", "#00008B"), ("Arabia Saudita", "#006C35")],
            "I": [("Marruecos", "#C1272D"), ("Egipto", "#CE1126"), ("Senegal", "#00853F"), ("Nigeria", "#008751")],
            "J": [("Chile", "#0039A6"), ("Perú", "#D91414"), ("Bolivia", "#007A33"), ("Costa Rica", "#11457E")],
            "K": [("Croacia", "#FF0000"), ("Suiza", "#D5141A"), ("Dinamarca", "#C1042F"), ("Serbia", "#C6363C")],
            "L": [("Túnez", "#E30A17"), ("Argelia", "#006633"), ("Camerún", "#007A5E"), ("Ghana", "#006B3F")]
        }
        documentos = []
        for grupo_id, paises in grupos.items():
            for nombre_pais, color in paises:
                documentos.append({"nombre": nombre_pais, "grupo": grupo_id, "ataque": random.randint(78, 96), "defensa": random.randint(75, 95), "color_kit": color})
        db['selecciones'].insert_many(documentos)

@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = None
    tipo_mensaje = "success"
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        inicializar_torneo_48(db)
        selecciones_col = db['selecciones']
        dt_col = db['directores_tecnicos']
    except Exception as e:
        return render_template("error.html", titulo_error="Error de Conexión", error_mensaje=str(e))

    if request.method == "POST":
        documento = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        equipo = request.form.get("equipo", "").strip()
        ficha = request.form.get("ficha", "").strip()

        if not all([documento, nombre, correo, equipo, ficha]):
            mensaje, tipo_mensaje = "❌ Faltan campos.", "danger"
        elif not documento.isdigit():
            mensaje, tipo_mensaje = "❌ Documento inválido.", "danger"
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            mensaje, tipo_mensaje = "❌ Correo inválido.", "danger"
        else:
            if dt_col.find_one({"documento": documento}):
                # Si el DT ya existe, simplemente lo redirigimos a jugar el partido
                return redirect(url_for("preparar_partido", documento=documento))
            else:
                info_seleccion = selecciones_col.find_one({"nombre": equipo})
                nuevo_dt = {
                    "documento": documento, "nombre": nombre, "correo": correo, "equipo": equipo,
                    "grupo": info_seleccion.get("grupo", "A") if info_seleccion else "A",
                    "color_kit": info_seleccion.get("color_kit", "#ffffff") if info_seleccion else "#ffffff",
                    "ficha": ficha, "partidos_jugados": 0, "puntos": 0, "goles_favor": 0, "goles_contra": 0
                }
                dt_col.insert_one(nuevo_dt)
                # Tras un registro exitoso, lanzarlo directamente a la arena de juego
                return redirect(url_for("preparar_partido", documento=documento))

    lista_dts = list(dt_col.find().sort("puntos", -1))
    lista_paises = list(selecciones_col.find().sort("nombre", 1))
    return render_template("index.html", dts=lista_dts, selecciones=lista_paises, mensaje=mensaje, tipo_mensaje=tipo_mensaje)

@app.route("/partido/<documento>")
def preparar_partido(documento):
    """Carga la arena HTML5 Canvas pasándole los datos de los equipos"""
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        dt = db['directores_tecnicos'].find_one({"documento": documento})
        if not dt: return redirect(url_for("index"))
            
        rival = db['selecciones'].find_one({"nombre": {"$ne": dt["equipo"]}})
        
        datos_partido = {
            "documento": dt["documento"],
            "local": dt["equipo"],
            "color_local": dt.get("color_kit", "#ffffff"),
            "visitante": rival["nombre"],
            "color_visitante": rival.get("color_kit", "#ff0000"),
            "manager": dt["nombre"]
        }
        return render_template("match.html", partido=datos_partido)
    except Exception as e:
        return render_template("error.html", titulo_error="Error de Carga", error_mensaje=str(e))

@app.route("/guardar_resultado/<documento>/<int:goles_l>/<int:goles_v>")
def guardar_resultado(documento, goles_l, goles_v):
    """Endpoint llamado por el motor JS al pitar el final del partido"""
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        
        puntos = 3 if goles_l > goles_v else (1 if goles_l == goles_v else 0)
        
        db['directores_tecnicos'].update_one(
            {"documento": documento},
            {"$inc": {"partidos_jugados": 1, "puntos": puntos, "goles_favor": goles_l, "goles_contra": goles_v}}
        )
        return redirect(url_for("index"))
    except Exception as e:
        return render_template("error.html", titulo_error="Error guardando estadísticas", error_mensaje=str(e))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
