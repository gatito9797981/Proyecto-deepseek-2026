import os
import json
import logging
from flask import Flask, jsonify, render_template, send_from_directory

# Configurar rutas bases
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_FILE = os.path.join(BASE_DIR, "metrics.json")
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "deepseek_client", "screenshots")

# Si el directorio de screenshots no existe en la config por defecto, fallback a la raiz
if not os.path.exists(SCREENSHOTS_DIR):
    SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")
    if not os.path.exists(SCREENSHOTS_DIR):
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

app = Flask(__name__)
# Para silenciar el logger hiper verboso de Flask a menos que sea error
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route("/")
def index():
    """Sirve el Single-Page App Dashboard (Frontend Tailwind)."""
    return render_template("index.html")

@app.route("/api/status")
def get_status():
    """Lee el metrics.json exportado en tiempo real por el DriverPool."""
    try:
        if os.path.exists(METRICS_FILE):
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify(data)
        else:
            return jsonify({
                "is_running": False,
                "message": "DriverPool desocupado o no iniciado. metrics.json vacío."
            }), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/screenshots")
def get_screenshots_list():
    """Retorna un listado de las últimas capturas de seguridad."""
    try:
        if not os.path.exists(SCREENSHOTS_DIR):
            return jsonify([])
            
        files = [f for f in os.listdir(SCREENSHOTS_DIR) if f.endswith('.png')]
        # Ordenar más recientes primero
        files.sort(key=lambda x: os.path.getmtime(os.path.join(SCREENSHOTS_DIR, x)), reverse=True)
        
        # Devolver solo las últimas 10 imágenes para no saturar el UI
        return jsonify(files[:10])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/screenshots/<filename>")
def serve_screenshot(filename):
    """Sirve la imagen binaria para el componente <img src=...> del frontend."""
    return send_from_directory(SCREENSHOTS_DIR, filename)

if __name__ == "__main__":
    print("==================================================")
    print("🚀 Iniciando DeepSeek Analytics Dashboard (Local)")
    print("📡 Abre en tu navegador: http://localhost:5000")
    print("==================================================")
    # Host='0.0.0.0' para poder verlo desde el celular si ambos están en la misma red WiFi
    app.run(host="0.0.0.0", port=5000, debug=False)
