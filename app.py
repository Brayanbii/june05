import os
import re
import random
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError

app = Flask(__name__)
app.secret_key = "fifa_world_cup_2026_ultra_premium_key"

# ==========================================
# CONEXIÓN INTEGRADA A TU MONGODB ATLAS
# ==========================================
CADENA_CONEXION = "mongodb+srv://brian_dt:FJG4MLFMR0bo0up2@cluster0.ry2pwjd.mongodb.net/mundial2026_db?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = os.environ.get("MONGO_URI", CADENA_CONEXION)

def conectar_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    return client

def inicializar_torneo_48(db):
    """Inyecta las 48 selecciones con sus grupos oficiales si la colección está vacía"""
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
                documentos.append({
                    "nombre": nombre_pais,
                    "grupo": grupo_id,
                    "ataque": random.randint(78, 96),
                    "defensa": random.randint(75, 95),
                    "color_kit": color
                })
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
    except (ConnectionFailure, ConfigurationError) as e:
        return render_template("error.html", 
                               titulo_error="Fallo Crítico de Conexión Base de Datos",
                               error_mensaje=f"No se pudo establecer el enlace con tu clúster de MongoDB Atlas. Detalles: {str(e)}")
    except Exception as e:
        return render_template("error.html", titulo_error="Error Interno del Servidor", error_mensaje=str(e))

    if request.method == "POST":
        documento = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        equipo = request.form.get("equipo", "").strip()
        ficha = request.form.get("ficha", "").strip()

        if not all([documento, nombre, correo, equipo, ficha]):
            mensaje = "❌ Todos los campos de acreditación son obligatorios."
            tipo_mensaje = "danger"
        elif not documento.isdigit():
            mensaje = "❌ El campo Documento de Identidad debe tener únicamente números."
            tipo_mensaje = "danger"
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            mensaje = "❌ El correo electrónico ingresado no tiene un formato válido."
            tipo_mensaje = "danger"
        else:
            try:
                if dt_col.find_one({"documento": documento}):
                    mensaje = "❌ Este documento ya se encuentra registrado con una selección."
                    tipo_mensaje = "danger"
                else:
                    info_seleccion = selecciones_col.find_one({"nombre": equipo})
                    
                    # Uso Seguro de .get() para evitar fallos con datos antiguos
                    grupo_detectado = "A"
                    color_detectado = "#ffffff"
                    if info_seleccion:
                        grupo_detectado = info_seleccion.get("grupo", "A")
                        color_detectado = info_seleccion.get("color_kit", info_seleccion.get("color_prenda", "#ffffff"))

                    nuevo_dt = {
                        "documento": documento,
                        "nombre": nombre,
                        "correo": correo,
                        "equipo": equipo,
                        "grupo": grupo_detectado,
                        "color_kit": color_detectado,
                        "ficha": ficha,
                        "partidos_jugados": 0,
                        "puntos": 0,
                        "goles_favor": 0,
                        "goles_contra": 0
                    }
                    dt_col.insert_one(nuevo_dt)
                    mensaje = f"🏆 ¡Manager {nombre} acreditado exitosamente para dirigir a {equipo}!"
                    tipo_mensaje = "success"
            except Exception as e:
                return render_template("error.html", titulo_error="Error al Insertar Registro", error_mensaje=str(e))

    try:
        lista_dts = list(dt_col.find().sort("puntos", -1))
        lista_paises = list(selecciones_col.find().sort("nombre", 1))
    except Exception as e:
        return render_template("error.html", titulo_error="Error de Consulta de Datos", error_mensaje=str(e))

    return render_template("index.html", dts=lista_dts, selecciones=lista_paises, mensaje=mensaje, tipo_mensaje=tipo_mensaje)


@app.route("/partido/<documento>")
def preparar_partido(documento):
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        dt = db['directores_tecnicos'].find_one({"documento": documento})
        
        if not dt:
            return redirect(url_for("index"))
            
        rival = db['selecciones'].find_one({"nombre": {"$ne": dt["equipo"]}})
        
        goles_local = 0
        goles_visitante = 0
        eventos = []
        
        comentarios_posibles = [
            "¡Remate potente desde fuera del área!",
            "¡Cabezazo letal tras un tiro de esquina impecable!",
            "¡Error defensivo garrafal aprovechado por el delantero!",
            "¡Penalti cobrado con frialdad absoluta a las redes!",
            "¡Jugada colectiva de fantasía que termina en anotación!"
        ]

        for minuto in range(1, 91, random.randint(5, 15)):
            accion = random.choices(["gol_local", "gol_visitante", "falta", "nada"], weights=[12, 10, 20, 58])[0]
            if accion == "gol_local":
                goles_local += 1
                eventos.append(f"⏱️ Min {minuto}': ¡GOL DE {dt['equipo'].upper()}! {random.choice(comentarios_posibles)}")
            elif accion == "gol_visitante":
                goles_visitante += 1
                eventos.append(f"⏱️ Min {minuto}': ¡GOL DE {rival['nombre'].upper()}! {random.choice(comentarios_posibles)}")
            elif accion == "falta":
                eventos.append(f"⏱️ Min {minuto}': Tarjeta amarilla por juego peligroso en la mitad del campo.")

        if goles_local > goles_visitante:
            puntos_ganados = 3
            resultado_texto = "VICTORIA 🟢"
        elif goles_local == goles_visitante:
            puntos_ganados = 1
            resultado_texto = "EMPATE 🟡"
        else:
            puntos_ganados = 0
            resultado_texto = "DERROTA 🔴"

        db['directores_tecnicos'].update_one(
            {"documento": documento},
            {"$inc": {
                "partidos_jugados": 1,
                "puntos": puntos_ganados,
                "goles_favor": goles_local,
                "goles_contra": goles_visitante
            }}
        )

        datos_partido = {
            "local": dt["equipo"],
            "color_local": dt.get("color_kit", "#ffffff"),
            "visitante": rival["nombre"],
            "color_visitante": rival.get("color_kit", "#ffffff"),
            "goles_l": goles_local,
            "goles_v": goles_visitante,
            "eventos": eventos,
            "resultado": resultado_texto,
            "manager": dt["nombre"]
        }

        return render_template("match.html", partido=datos_partido)
    except Exception as e:
        return render_template("error.html", titulo_error="Fallo Crítico en MatchEngine v2026", error_mensaje=str(e))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
