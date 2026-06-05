from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import re

app = Flask(__name__)
app.secret_key = "clave-secreta-mundial-nokia"

# ==========================================
# CONFIGURACIÓN DE MONGODB ATLAS
# ==========================================
# REEMPLAZA <usuario>, <contraseña> y cluster0.xxxx con tu cadena de conexión real de Atlas
MONGO_URI = "mongodb+srv://<usuario>:<contraseña>@cluster0.xxxx.mongodb.net/?retryWrites=true&w=majority"

def obtener_conexion_db():
    """Intenta conectar a MongoDB Atlas aplicando un timeout rápido de 3 segundos"""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    # Forzamos un ping directo para validar si la base de datos responde
    client.admin.command('ping')
    return client

@app.route("/", methods=["GET", "POST"])
def index():
    mensaje = None
    tipo_mensaje = "success"
    
    # 4. CONTROL DE EXCEPCIONES (Verificación de Conexión a Base de Datos)
    try:
        client = obtener_conexion_db()
        db = client['mundial2026_db']
        jugadores_col = db['jugadores']
    except (ConnectionFailure, ConfigurationError) as e:
        # Si falla MongoDB Atlas, se captura la excepción y se le muestra este error detallado al usuario
        return render_template("error.html", 
                               titulo_error="Fallo de Conexión con Base de Datos",
                               error_mensaje=f"No se pudo establecer el enlace con MongoDB Atlas. Detalles: {str(e)}")
    except Exception as e:
        # Captura cualquier otro error imprevisto del servidor
        return render_template("error.html", 
                               titulo_error="Error Inesperado del Servidor",
                               error_mensaje=f"Ocurrió un problema crítico interno: {str(e)}")

    # 1. REGISTRAR PARTICIPANTES (Procesamiento del Formulario)
    if request.method == "POST":
        documento = request.form.get("documento", "").strip()
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        equipo = request.form.get("equipo", "").strip() # Equivale a Programa de Formación
        ficha = request.form.get("ficha", "").strip()   # Ficha académica del torneo

        # 2. VALIDACIÓN DE DATOS (Backend)
        if not documento or not nombre or not correo or not equipo or not ficha:
            mensaje = "❌ Todos los campos son totalmente obligatorios."
            tipo_mensaje = "danger"
        elif not documento.isdigit():
            mensaje = "❌ El Documento debe contener únicamente valores numéricos."
            tipo_mensaje = "danger"
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            mensaje = "❌ El formato del Correo Electrónico no es válido."
            tipo_mensaje = "danger"
        else:
            try:
                # Comprobar si el documento único ya existe registrado en la colección
                if jugadores_col.find_one({"documento": documento}):
                    mensaje = "❌ Este documento ya se encuentra inscrito en el torneo."
                    tipo_mensaje = "danger"
                else:
                    # Estructura del documento JSON a guardar
                    nuevo_jugador = {
                        "documento": documento,
                        "nombre": nombre,
                        "correo": correo,
                        "equipo": equipo,
                        "ficha": ficha,
                        "puntos": 0,
                        "goles_favor": 0
                    }
                    jugadores_col.insert_one(nuevo_jugador)
                    mensaje = f"⚽ ¡{nombre} ({equipo}) ha sido registrado con éxito en la Ficha {ficha}!"
                    tipo_mensaje = "success"
            except Exception as e:
                return render_template("error.html", 
                                       titulo_error="Error al Guardar Datos",
                                       error_mensaje=f"No se pudo insertar el documento en la colección: {str(e)}")

    # 3. CONSULTAR TODOS LOS REGISTROS
    try:
        lista_jugadores = list(jugadores_col.find())
    except Exception as e:
        return render_template("error.html", 
                               titulo_error="Error de Consulta",
                               error_mensaje=f"No se pudieron cargar los datos de la colección: {str(e)}")

    return render_template("index.html", jugadores=lista_jugadores, mensaje=mensaje, tipo_mensaje=tipo_mensaje)


@app.route("/simular/<documento>")
def simular_partido(documento):
    """Ruta del juego interactivo para añadir dinamismo sumando goles y puntos al jugador"""
    try:
        client = obtener_conexion_db()
        db = client['mundial2026_db']
        jugadores_col = db['jugadores']
        
        import random
        goles = random.randint(0, 4)
        puntos_ganados = 3 if goles > 1 else (1 if goles == 1 else 0)
        
        # Modificación incremental directa en la base de datos
        jugadores_col.update_one(
            {"documento": documento},
            {"$inc": {"puntos": puntos_ganados, "goles_favor": goles}}
        )
        return redirect(url_for("index"))
    except Exception as e:
        return render_template("error.html", titulo_error="Error de Simulación", error_mensaje=str(e))

if __name__ == "__main__":
    app.run(debug=True)
