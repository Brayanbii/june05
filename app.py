import os
import re
import random
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError

app = Flask(__name__)
app.secret_key = "clave-secreta-mundial-nokia"

# ==========================================
# TU CONFIGURACIÓN DE MONGODB ATLAS
# ==========================================
# Usamos os.environ para que funcione en Render de forma segura. 
# Si estás en tu PC local, usará por defecto tu enlace que me pasaste.
CADENA_CONEXION_REAL = "mongodb+srv://brian_dt:FJG4MLFMR0bo0up2@cluster0.ry2pwjd.mongodb.net/mundial2026_db?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = os.environ.get("MONGO_URI", CADENA_CONEXION_REAL)

def obtener_conexion_db():
    """Intenta conectar a tu base de datos mundial2026_db aplicando un timeout de 3 segundos"""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    # Hacemos un ping de control para verificar si hay conexión real
    client.admin.command('ping')
    return client

@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = None
    tipo_mensaje = "success"
    
    # 4. CONTROL DE EXCEPCIONES (Manejo de errores si se cae la base de datos o el servidor)
    try:
        client = obtener_conexion_db()
        db = client['mundial2026_db']
        jugadores_col = db['jugadores']
    except (ConnectionFailure, ConfigurationError) as e:
        # Si falla tu conexión a Atlas, se muestra la pantalla de error exigida por el taller
        return render_template("error.html", 
                               titulo_error="Error de Conexión a MongoDB Atlas",
                               error_mensaje=f"No se pudo establecer enlace con tu base de datos en la nube. Detalles técnicos: {str(e)}")
    except Exception as e:
        # Captura cualquier otro error inesperado
        return render_template("error.html", 
                               titulo_error="Fallo General Interno",
                               error_mensaje=str(e))

    # 1. REGISTRAR ESTUDIANTES / DIRECTORES TÉCNICOS (Mundial 2026)
    if request.method == "POST":
        documento = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        equipo = request.form.get("equipo", "").strip()  # Programa de Formación (Selección)
        ficha = request.form.get("ficha", "").strip()    # Ficha del SENA

        # 2. VALIDACIÓN DE DATOS REQUERIDA
        if not documento or not nombre or not correo or not equipo or not ficha:
            mensaje = "❌ Todos los campos son totalmente obligatorios."
            tipo_mensaje = "danger"
        elif not documento.isdigit():
            mensaje = "❌ El campo Documento debe contener únicamente números."
            tipo_mensaje = "danger"
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            mensaje = "❌ El formato de Correo Electrónico no es válido."
            tipo_mensaje = "danger"
        else:
            try:
                # Validar que no se repita el mismo documento
                if jugadores_col.find_one({"documento": documento}):
                    mensaje = "❌ Este número de documento ya está inscrito en el torneo."
                    tipo_mensaje = "danger"
                else:
                    # Estructura del documento a guardar
                    nuevo_registro = {
                        "documento": documento,
                        "nombre": nombre,
                        "correo": correo,
                        "equipo": equipo,
                        "ficha": ficha,
                        "puntos": 0,
                        "goles_favor": 0
                    }
                    jugadores_col.insert_one(nuevo_registro)
                    mensaje = f"⚽ ¡{nombre} ({equipo}) registrado con éxito en la Ficha {ficha}!"
                    tipo_mensaje = "success"
            except Exception as e:
                return render_template("error.html", titulo_error="Error de Inserción", error_mensaje=str(e))

    # 3. CONSULTAR TODOS LOS REGISTROS GUARDADOS
    try:
        lista_jugadores = list(jugadores_col.find())
    except Exception as e:
        return render_template("error.html", titulo_error="Error de Consulta", error_mensaje=str(e))

    return render_template("index.html", jugadores=lista_jugadores, mensaje=mensaje, tipo_mensaje=tipo_mensaje)


@app.route("/simular/<documento>")
def simular_partido(documento):
    """Ruta del minijuego para simular un partido retro sumando goles aleatorios directamente a Atlas"""
    try:
        client = obtener_conexion_db()
        db = client['mundial2026_db']
        jugadores_col = db['jugadores']
        
        goles = random.randint(0, 4)
        puntos_ganados = 3 if goles > 1 else (1 if goles == 1 else 0)
        
        # Modificación incremental directa en MongoDB
        jugadores_col.update_one(
            {"documento": documento},
            {"$inc": {"puntos": puntos_ganados, "goles_favor": goles}}
        )
        return redirect(url_for("index"))
    except Exception as e:
        return render_template("error.html", titulo_error="Error en Simulación", error_mensaje=str(e))

if __name__ == "__main__":
    # Render asigna puertos de forma dinámica mediante variables de entorno
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=True)
