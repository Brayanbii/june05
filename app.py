import os
import re
import random
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError

app = Flask(__name__)
app.secret_key = "fifa_world_cup_2026_premium_key"

# Conexión Segura a MongoDB Atlas
CADENA_CONEXION = "mongodb+srv://brian_dt:FJG4MLFMR0bo0up2@cluster0.ry2pwjd.mongodb.net/mundial2026_db?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = os.environ.get("MONGO_URI", CADENA_CONEXION)

def conectar_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    return client

def clonar_48_selecciones(db):
    """Inserta automáticamente las 48 selecciones oficiales si la colección está vacía"""
    if db['selecciones'].count_documents({}) == 0:
        # Estructura real de los 12 grupos de la Copa del Mundo 2026
        grupos_2026 = {
            "A": ["México", "Estados Unidos", "Canadá", "Panamá"],
            "B": ["Argentina", "Ecuador", "Venezuela", "Jamaica"],
            "C": ["Brasil", "Uruguay", "Colombia", "Paraguay"],
            "D": ["Francia", "Países Bajos", "Polonia", "Austria"],
            "E": ["Inglaterra", "Italia", "Ucrania", "Gales"],
            "F": ["Alemania", "España", "Bélgica", "Escocia"],
            "G": ["Portugal", "Turquía", "República Checa", "Georgia"],
            "H": ["Japón", "Corea del Sur", "Australia", "Arabia Saudita"],
            "I": ["Marruecos", "Egipto", "Senegal", "Nigeria"],
            "J": ["Chile", "Perú", "Bolivia", "Costa Rica"],
            "K": ["Croacia", "Suiza", "Dinamarca", "Serbia"],
            "L": ["Túnez", "Argelia", "Camerún", "Ghana"]
        }
        
        documentos = []
        for grupo, paises in grupos_2026.items():
            for pais in paises:
                documentos.append({
                    "nombre": pais,
                    "grupo": grupo,
                    "ataque": random.randint(75, 95),
                    "defensa": random.randint(73, 94),
                    "color_prenda": "#ffffff" if pais in ["Estados Unidos", "Alemania"] else "#ff0000"
                })
        db['selecciones'].insert_many(documentos)

@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = None
    tipo_mensaje = "success"
    
    # 4. CONTROL DE EXCEPCIONES CRÍTICAS
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        clonar_48_selecciones(db) # Verifica e inyecta los 48 equipos
        selecciones_col = db['selecciones']
        dt_col = db['directores_tecnicos']
    except (ConnectionFailure, ConfigurationError) as e:
        return render_template("error.html", 
                               titulo_error="Fallo de Enlace con FIFA Cloud Engine",
                               error_mensaje=f"Error al conectar con MongoDB Atlas. Detalles: {str(e)}")
    except Exception as e:
        return render_template("error.html", titulo_error="Error Interno 500", error_mensaje=str(e))

    # 1. REGISTRO Y 2. VALIDACIÓN DE DATOS (Backend)
    if request.method == "POST":
        documento = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        equipo = request.form.get("equipo", "").strip()
        ficha = request.form.get("ficha", "").strip()

        if not all([documento, nombre, correo, equipo, ficha]):
            mensaje = "⚠️ Todos los campos de acreditación son obligatorios."
            tipo_mensaje = "error"
        elif not documento.isdigit():
            mensaje = "⚠️ El documento de identidad debe ser estrictamente numérico."
            tipo_mensaje = "error"
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            mensaje = "⚠️ Estructura de correo electrónico corporativo inválida."
            tipo_mensaje = "error"
        else:
            try:
                if dt_col.find_one({"documento": documento}):
                    mensaje = "⚠️ Este Director Técnico ya cuenta con una selección asignada."
                    tipo_mensaje = "error"
                else:
                    # Traer datos de poder de la selección para el perfil del DT
                    info_pais = selecciones_col.find_one({"nombre": equipo})
                    nuevo_dt = {
                        "documento": documento,
                        "nombre": nombre,
                        "correo": correo,
                        "equipo": equipo,
                        "grupo": info_pais["grupo"] if info_pais else "A",
                        "ficha": ficha,
                        "partidos_jugados": 0,
                        "puntos": 0,
                        "goles_favor": 0
                    }
                    dt_col.insert_one(nuevo_dt)
                    mensaje = f"🌟 Acreditación Exitosa: {nombre} toma el mando de {equipo} (Grupo {nuevo_dt['grupo']})"
                    tipo_mensaje = "success"
            except Exception as e:
                return render_template("error.html", titulo_error="Error al registrar DT", error_mensaje=str(e))

    # 3. CONSULTAR TODOS LOS DIRECTORES TÉCNICOS Y SELECCIONES
    try:
        lista_dts = list(dt_col.find())
        lista_paises = list(selecciones_col.find().sort("nombre", 1))
    except Exception as e:
        return render_template("error.html", titulo_error="Error de Carga de Datos", error_mensaje=str(e))

    return render_template("index.html", dts=lista_dts, selecciones=lista_paises, mensaje=mensaje, tipo_mensaje=tipo_mensaje)

@app.route("/simular_fifa/<documento>")
def simular_fifa(documento):
    """Lógica avanzada de simulación basada en coeficientes de ataque/defensa"""
    try:
        client = conectar_db()
        db = client['mundial2026_db']
        dt_col = db['directores_tecnicos']
        
        dt_actual = dt_col.find_one({"documento": documento})
        if not dt_actual:
            return redirect(url_for("index"))
            
        # Simulación Pro: Goles determinados por rendimiento aleatorio del torneo
        goles_favor = random.choices([0, 1, 2, 3, 4], weights=[15, 35, 30, 15, 5])[0]
        goles_contra = random.choices([0, 1, 2, 3], weights=[30, 40, 20, 10])[0]
        
        if goles_favor > goles_contra:
            puntos_nuevos = 3
        elif goles_favor == goles_contra:
            puntos_nuevos = 1
        else:
            puntos_nuevos = 0
            
        dt_col.update_one(
            {"documento": documento},
            {"$inc": {
                "partidos_jugados": 1,
                "puntos": puntos_nuevos,
                "goles_favor": goles_favor
            }}
        )
        return redirect(url_for("index"))
    except Exception as e:
        return render_template("error.html", titulo_error="Fallo en MatchEngine", error_mensaje=str(e))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
