"""
Script para mitmproxy que extrae cookies y datos de sesión de DeepSeek.
Úsalo con: mitmproxy -s extract_data.py
"""

from mitmproxy import http
import json
import os
from datetime import datetime

class DeepSeekExtractor:
    def __init__(self):
        self.output_file = "deepseek_session.json"
        print(f"[*] DeepSeek Extractor cargado. Guardando en {self.output_file}")

    def response(self, flow: http.HTTPFlow):
        # Filtrar por el dominio de DeepSeek
        if "chat.deepseek.com" in flow.request.pretty_host:
            
            # Extraer cookies de la respuesta o petición
            cookies = flow.request.cookies
            session_id = cookies.get("ds_session_id")
            waf_token = cookies.get("aws-waf-token")
            
            if session_id or waf_token:
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "ds_session_id": session_id,
                    "aws_waf_token": waf_token,
                    "url": flow.request.pretty_url
                }
                
                # También podemos buscar en las cabeceras de respuesta si se establecen allí
                set_cookies = flow.response.headers.get_all("set-cookie")
                for sc in set_cookies:
                    if "ds_session_id=" in sc:
                        data["ds_session_id"] = sc.split("ds_session_id=")[1].split(";")[0]
                    if "aws-waf-token=" in sc:
                        data["aws_waf_token"] = sc.split("aws-waf-token=")[1].split(";")[0]

                # Guardar si tenemos datos nuevos
                if data.get("ds_session_id") or data.get("aws_waf_token"):
                    self.save_data(data)

            # Capturar HTML si es la página principal
            if flow.request.path == "/" or "/chat" in flow.request.path:
                if flow.response and "text/html" in flow.response.headers.get("content-type", ""):
                    filename = f"captures/page_{datetime.now().strftime('%H%M%S')}.html"
                    os.makedirs("captures", exist_ok=True)
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(flow.response.text)
                    print(f"[+] HTML guardado: {filename}")

            # Capturar API de Chat (JSON/SSE)
            if "/api/v0/chat" in flow.request.path:
                print(f"[*] Interceptado endpoint de chat: {flow.request.path}")
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "method": flow.request.method,
                    "url": flow.request.pretty_url,
                    "request_body": flow.request.text,
                    "response_summary": ""
                }
                
                if flow.response:
                    content_type = flow.response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        log_entry["response_summary"] = flow.response.text
                    elif "text/event-stream" in content_type:
                        log_entry["response_summary"] = "[STREAM EVENT DATA]"
                        # Guardar fragmento del stream para análisis de estructura
                        with open("captures/last_stream.txt", "w", encoding="utf-8") as f:
                            f.write(flow.response.text)
                
                with open("captures/chat_api_log.json", "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")

    def save_data(self, data):
        # Cargar datos existentes para no sobrescribir si no es necesario
        existing = {}
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, "r") as f:
                    existing = json.load(f)
            except:
                pass
        
        # Actualizar solo si hay cambios
        if data["ds_session_id"] != existing.get("ds_session_id") or \
           data["aws_waf_token"] != existing.get("aws_waf_token"):
            
            with open(self.output_file, "w") as f:
                json.dump(data, f, indent=4)
            print(f"[+] Datos de sesión actualizados: {data['ds_session_id'][:10]}...")
            
            # Opcional: Actualizar el archivo .env directamente
            self.update_env(data)

    def update_env(self, data):
        # Buscar el archivo .env en el directorio actual o padre
        env_path = ".env"
        if not os.path.exists(env_path):
            env_path = "../.env"
            
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
            
            new_lines = []
            updated_session = False
            updated_waf = False
            
            for line in lines:
                if line.startswith("DEEPSEEK_SESSION_ID="):
                    new_lines.append(f"DEEPSEEK_SESSION_ID={data['ds_session_id']}\n")
                    updated_session = True
                elif line.startswith("DEEPSEEK_WAF_TOKEN="):
                    new_lines.append(f"DEEPSEEK_WAF_TOKEN={data['aws_waf_token']}\n")
                    updated_waf = True
                else:
                    new_lines.append(line)
            
            # Añadir si no existían
            if not updated_session and data['ds_session_id']:
                new_lines.append(f"DEEPSEEK_SESSION_ID={data['ds_session_id']}\n")
            if not updated_waf and data['aws_waf_token']:
                new_lines.append(f"DEEPSEEK_WAF_TOKEN={data['aws_waf_token']}\n")
                
            with open(env_path, "w") as f:
                f.writelines(new_lines)
            print(f"[+] Archivo .env actualizado con éxito.")

addons = [DeepSeekExtractor()]
