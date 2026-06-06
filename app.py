import os
import random
from flask import Flask, render_template, jsonify
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "world_cup_2026_pro_bracket"

# Equipos con su código ISO para llamar a la API de banderas reales y su Poder Real (Estadística IA)
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

def simular_partido(equipo1, equipo2):
    """Simula un partido ponderando el poder de cada equipo. Goles más realistas."""
    # Se genera una ventaja matemática basada en la diferencia de ELO/Poder
    ventaja = (equipo1["poder"] - equipo2["poder"]) / 10.0
    
    # Base aleatoria de goles usando distribución de Poisson simplificada
    goles1 = max(0, int(random.gauss(1.5 + ventaja, 1.2)))
    goles2 = max(0, int(random.gauss(1.5 - ventaja, 1.2)))
    
    # En fase eliminatoria no hay empates (se simulan penales si igualan)
    if goles1 == goles2:
        if random.choice([True, False]):
            goles1 += 1  # Gana en penales o prórroga
        else:
            goles2 += 1

    ganador = equipo1 if goles1 > goles2 else equipo2
    
    return {
        "equipo1": equipo1, "equipo2": equipo2,
        "goles1": goles1, "goles2": goles2,
        "ganador": ganador
    }

def generar_bracket():
    """Genera las fases desde Dieciseisavos hasta la Final"""
    equipos = EQUIPOS_REALES.copy()
    random.shuffle(equipos) # Sorteo aleatorio de llaves iniciales
    
    fases = {"dieciseisavos": [], "octavos": [], "cuartos": [], "semifinal": [], "final": [], "campeon": None}
    
    # 1. Dieciseisavos (32 equipos -> 16 partidos)
    avanzan_a_octavos = []
    for i in range(0, 32, 2):
        partido = simular_partido(equipos[i], equipos[i+1])
        fases["dieciseisavos"].append(partido)
        avanzan_a_octavos.append(partido["ganador"])
        
    # 2. Octavos (16 equipos -> 8 partidos)
    avanzan_a_cuartos = []
    for i in range(0, 16, 2):
        partido = simular_partido(avanzan_a_octavos[i], avanzan_a_octavos[i+1])
        fases["octavos"].append(partido)
        avanzan_a_cuartos.append(partido["ganador"])
        
    # 3. Cuartos (8 equipos -> 4 partidos)
    avanzan_a_semi = []
    for i in range(0, 8, 2):
        partido = simular_partido(avanzan_a_cuartos[i], avanzan_a_cuartos[i+1])
        fases["cuartos"].append(partido)
        avanzan_a_semi.append(partido["ganador"])
        
    # 4. Semifinal (4 equipos -> 2 partidos)
    avanzan_a_final = []
    for i in range(0, 4, 2):
        partido = simular_partido(avanzan_a_semi[i], avanzan_a_semi[i+1])
        fases["semifinal"].append(partido)
        avanzan_a_final.append(partido["ganador"])
        
    # 5. Final
    final = simular_partido(avanzan_a_final[0], avanzan_a_final[1])
    fases["final"].append(final)
    fases["campeon"] = final["ganador"]
    
    return fases

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/simular_torneo")
def api_simular_torneo():
    """Endpoint que devuelve el JSON del torneo completo al frontend"""
    bracket_data = generar_bracket()
    return jsonify(bracket_data)

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=True)
