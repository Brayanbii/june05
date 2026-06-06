import os
import re
import random
from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError

app = Flask(__name__)
app.secret_key = "fifa_world_cup_2026_master_key"

# ==========================================
# CONEXIÓN A MONGODB ATLAS
# ==========================================
CADENA_CONEXION = "mongodb+srv://brian_dt:FJG4MLFMR0bo0up2@cluster0.ry2pwjd.mongodb.net/mundial2026_db?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = os.environ.get("MONGO_URI", CADENA_CONEXION)

def conectar_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    return client

# Base de datos de equipos reales con su Poder (ELO) para cálculos matemáticos
EQUIPOS_REALES = [
    {"nombre": "Argentina", "iso": "ar", "poder": 95}, {"nombre": "Francia", "iso": "fr", "poder": 94},
    {"nombre": "Brasil", "iso": "br", "poder": 93}, {"nombre": "Inglaterra", "iso": "gb-eng", "poder": 92},
    {"nombre": "España", "iso": "es", "poder": 90}, {"nombre": "Portugal", "iso": "pt", "poder": 89},
    {"nombre": "Alemania", "iso": "de", "poder": 88}, {"nombre": "Italia", "iso": "it", "poder": 87},
    {"nombre": "Países Bajos", "iso": "nl", "poder": 86}, {"nombre": "Croacia", "iso": "hr", "poder": 85},
    {"nombre": "Colombia", "iso": "co", "poder": 84}, {"nombre": "Uruguay", "iso": "uy", "poder": 84},
    {"nombre": "Marruecos", "iso": "ma", "poder": 83}, {"nombre": "Bélgica", "iso": "be", "poder": 82},
    {"nombre": "Estados Unidos", "iso": "us", "poder": 80}, {"nombre": "México", "iso": "mx", "poder": 79},
    {"nombre": "Japón", "iso": "jp", "poder": 79}, {"nombre": "Senegal", "iso": "sn", "poder": 78},
    {"nombre": "Suiza", "iso": "ch", "poder": 78}, {"nombre": "Dinamarca", "iso": "dk", "poder": 77},
    {"nombre": "Ecuador", "iso": "ec", "poder": 77}, {"nombre": "Corea del Sur", "iso": "kr", "poder": 76},
    {"nombre": "Canadá", "iso": "ca", "poder": 75}, {"nombre": "Serbia", "iso": "rs", "poder": 75},
    {"nombre": "Polonia", "iso": "pl", "poder": 74}, {"nombre": "Chile", "iso": "cl", "poder": 74},
    {"nombre": "Nigeria", "iso": "ng", "poder": 73}, {"nombre": "Gales", "iso": "gb-wls", "poder": 72},
    {"nombre": "Perú", "iso": "pe", "poder": 72}, {"nombre": "Egipto", "iso": "eg", "poder": 71},
    {"nombre": "Argelia", "iso": "dz", "poder": 70}, {"nombre": "Costa Rica", "iso": "cr", "poder": 68}
]

def inicializar_torneo(db):
    """Inyecta los equipos a la BD la primera vez"""
    if db['selecciones'].count_documents({}) == 0:
        db['selecciones'].insert_many(EQUIPOS_REALES)

@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = None
    tipo_mensaje = "success"
    
    # 4. CONTROL DE EXCEPCIONES
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        inicializar_torneo(db)
        selecciones_col = db['selecciones']
        dt_col = db['directores_tecnicos']
    except Exception as e:
        return render_template("error.html", titulo_error="Error de Conexión a BD", error_mensaje=str(e))

    # 1. y 2. REGISTRO Y VALIDACIÓN (REQUISITO DE LA TAREA)
    if request.method == "POST":
        documento = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        equipo = request.form.get("equipo", "").strip()
        ficha = request.form.get("ficha", "").strip()

        if not all([documento, nombre, correo, equipo, ficha]):
            mensaje = "⚠️ Todos los campos son obligatorios."
            tipo_mensaje = "danger"
        elif not documento.isdigit():
            mensaje = "⚠️ El documento debe contener solo números."
            tipo_mensaje = "danger"
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            mensaje = "⚠️ Formato de correo inválido."
            tipo_mensaje = "danger"
        else:
            if dt_col.find_one({"documento": documento}):
                mensaje = "⚠️ Este documento ya está registrado como Mánager."
                tipo_mensaje = "danger"
            else:
                info_seleccion = selecciones_col.find_one({"nombre": equipo})
                nuevo_dt = {
                    "documento": documento, "nombre": nombre, "correo": correo, 
                    "equipo": equipo, "iso": info_seleccion["iso"] if info_seleccion else "co", 
                    "ficha": ficha, "poder": info_seleccion["poder"] if info_seleccion else 70
                }
                dt_col.insert_one(nuevo_dt)
                mensaje = f"✅ ¡Mánager {nombre} registrado exitosamente con {equipo}!"
                tipo_mensaje = "success"

    # 3. CONSULTA GENERAL
    try:
        lista_dts = list(dt_col.find().sort("_id", -1))
        lista_paises = list(selecciones_col.find().sort("nombre", 1))
    except Exception as e:
        return render_template("error.html", titulo_error="Error de Consulta", error_mensaje=str(e))

    return render_template("index.html", dts=lista_dts, selecciones=lista_paises, mensaje=mensaje, tipo_mensaje=tipo_mensaje)

# ==========================================
# MOTOR IA DE SIMULACIÓN DEL TORNEO
# ==========================================
def simular_partido(equipo1, equipo2):
    ventaja = (equipo1["poder"] - equipo2["poder"]) / 12.0
    goles1 = max(0, int(random.gauss(1.5 + ventaja, 1.2)))
    goles2 = max(0, int(random.gauss(1.5 - ventaja, 1.2)))
    
    if goles1 == goles2:
        if random.choice([True, False]): goles1 += 1
        else: goles2 += 1

    return {"equipo1": equipo1, "equipo2": equipo2, "goles1": goles1, "goles2": goles2, "ganador": equipo1 if goles1 > goles2 else equipo2}

@app.route("/api/simular_torneo")
def api_simular_torneo():
    equipos = EQUIPOS_REALES.copy()
    random.shuffle(equipos)
    
    fases = {"octavos": [], "cuartos": [], "semifinal": [], "final": [], "campeon": None}
    
    # Octavos
    avanzan_cuartos = []
    for i in range(0, 16, 2):
        p = simular_partido(equipos[i], equipos[i+1])
        fases["octavos"].append(p)
        avanzan_cuartos.append(p["ganador"])
        
    # Cuartos
    avanzan_semi = []
    for i in range(0, 8, 2):
        p = simular_partido(avanzan_cuartos[i], avanzan_cuartos[i+1])
        fases["cuartos"].append(p)
        avanzan_semi.append(p["ganador"])
        
    # Semis
    avanzan_final = []
    for i in range(0, 4, 2):
        p = simular_partido(avanzan_semi[i], avanzan_semi[i+1])
        fases["semifinal"].append(p)
        avanzan_final.append(p["ganador"])
        
    # Final
    final = simular_partido(avanzan_final[0], avanzan_final[1])
    fases["final"].append(final)
    fases["campeon"] = final["ganador"]
    
    return jsonify(fases)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
