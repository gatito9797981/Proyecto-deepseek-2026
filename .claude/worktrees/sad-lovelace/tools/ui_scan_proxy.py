"""
DeepSeek Unified Capture Proxy.
Intercepts UI reports, authentication data, and Chat API interactions.
"""
import json
import os
import re
from datetime import datetime
from mitmproxy import http

class UnifiedDeepSeekInterceptor:
    def __init__(self):
        self.output_dir = "captures"
        self.session_file = "deepseek_session.json"
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"[*] DeepSeek Unified Interceptor Activo.")

    def request(self, flow: http.HTTPFlow):
        # 1. Capturar Reportes del UI Scanner (JS)
        if "/__ui_scan_report" in flow.request.path:
            self._handle_ui_report(flow)

    def response(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host
        if "chat.deepseek.com" not in host:
            return

        # 2. Extraer Datos de Sesión (Cookies/Tokens)
        self._extract_session_data(flow)

        # 3. Interceptar API de Chat
        if "/api/v0/chat" in flow.request.path:
            self._log_chat_api(flow)

    def _handle_ui_report(self, flow):
        try:
            data = json.loads(flow.request.text)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Guardar JSON de elementos
            json_path = os.path.join(self.output_dir, f"ui_map_{ts}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            
            # Guardar Snapshot HTML
            if "html_snapshot" in data:
                html_path = os.path.join(self.output_dir, f"dom_snap_{ts}.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(data["html_snapshot"])
                print(f"[+] UI Map & DOM Snapshot guardados.")

            flow.response = http.Response.make(200, b'{"status": "ok"}', {"Content-Type": "application/json"})
        except Exception as e:
            print(f"[!] Error en reporte UI: {e}")

    def _extract_session_data(self, flow):
        # Buscar en cookies y headers
        session_id = flow.request.cookies.get("ds_session_id")
        
        # Si hay session_id, guardar/actualizar
        if session_id:
            data = {
                "timestamp": datetime.now().isoformat(),
                "ds_session_id": session_id,
                "user_agent": flow.request.headers.get("user-agent", "")
            }
            with open(self.session_file, "w") as f:
                json.dump(data, f, indent=4)
            # print(f"[+] Sesión interceptada: {session_id[:12]}...")

    def _log_chat_api(self, flow):
        entry = {
            "ts": datetime.now().isoformat(),
            "url": flow.request.path,
            "req": flow.request.text[:1000],
            "resp_type": flow.response.headers.get("content-type", "")
        }
        log_path = os.path.join(self.output_dir, "chat_api_stream.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

addons = [UnifiedDeepSeekInterceptor()]
