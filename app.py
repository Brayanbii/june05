import os  # <--- IMPORTANTE: Agrega esto al inicio de tu archivo
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import re

app = Flask(__name__)
app.secret_key = "clave-secreta-mundial-nokia"

# ==========================================
# CONFIGURACIÓN DE MONGODB ATLAS (SEGURO)
# ==========================================
# Render inyectará automáticamente la URL real aquí. 
# Si estás en local y no la encuentra, usará la de prueba que pongas a la derecha.
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://tu_usuario:tu_contraseña@cluster.xxxx.mongodb.net/?retryWrites=true&w=majority")

def obtener_conexion_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    return client

# ... (Todo el resto de tus rutas de juego, formularios y consultas quedan exactamente IGUAL) ...

if __name__ == "__main__":
    # Render asigna un puerto aleatorio mediante una variable de entorno llamada PORT.
    # Si no existe (estás en tu PC local), usará el puerto 5000 por defecto.
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=True)
