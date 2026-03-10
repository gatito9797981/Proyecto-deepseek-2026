import json
import base64
import time
import threading
import logging
from typing import Optional, Dict, Any, Callable

class TokenManager:
    """
    Servicio en segundo plano para monitorizar la caducidad del token de sesión de DeepSeek.
    """
    def __init__(
        self, 
        driver, 
        logger: logging.Logger, 
        alert_callback: Optional[Callable[[str], None]] = None
    ):
        self.driver = driver
        self.logger = logger
        self.alert_callback = alert_callback
        
        self._is_running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Configuraciones de tiempo (en segundos)
        self.check_interval = 60         # Revisar cada 60s
        self.refresh_threshold = 300     # Intentar refrescar si quedan < 5 min
        self.critical_threshold = 120    # Alerta crítica si quedan < 2 min
        
    def start_monitoring(self):
        """Inicia el hilo demonio de monitorización."""
        if self._is_running:
            return
            
        self._is_running = True
        self._monitor_thread = threading.Thread(
            target=self._watchdog_loop,
            daemon=True,
            name="TokenWatchdog"
        )
        self._monitor_thread.start()
        self.logger.info("Servicio de monitorización de Tokens iniciado.")
        
    def stop_monitoring(self):
        """Detiene la monitorización."""
        self._is_running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            # No forzamos join para no bloquear el apagado rápido
            pass
            
    def _watchdog_loop(self):
        """Bucle principal del hilo de monitorización."""
        while self._is_running:
            try:
                self._check_and_refresh()
            except Exception as e:
                self.logger.debug(f"Error silencioso en Token Watchdog: {e}")
            
            # Dormir cortado para permitir cierres rápidos
            for _ in range(self.check_interval):
                if not self._is_running:
                    break
                time.sleep(1)
                
    def _check_and_refresh(self):
        """Extrae el token, verifica expiración e intenta acciones correctivas."""
        if not self.driver:
            return
            
        token = self.extract_token()
        if not token:
            return
            
        payload = self.decode_jwt(token)
        if not payload or 'exp' not in payload:
            return
            
        exp_time = payload['exp']
        current_time = time.time()
        time_left = exp_time - current_time
        
        if time_left <= 0:
            self._trigger_alert("La sesión ha caducado. Por favor, recargue el entorno.")
            return
            
        # Si estamos dentro del umbral de advertencia pero aún no es crítico, intentamos refrescar pasivamente
        if time_left < self.refresh_threshold:
            self.logger.info(f"Token expira en {time_left:.0f}s. Intentando auto-refresco pasivo...")
            success = self._attempt_passive_refresh()
            
            if success:
                # Verificamos si realmente se renovó
                time.sleep(2)
                new_token = self.extract_token()
                if new_token and new_token != token:
                    new_payload = self.decode_jwt(new_token)
                    if new_payload and 'exp' in new_payload:
                        new_left = new_payload['exp'] - time.time()
                        self.logger.info(f"Auto-refresco EXITOSO. Nuevo tiempo restante: {new_left:.0f}s")
                        return
            
            # Si el refresco falló o no dio nuevo token, verificamos alerta crítica
            if time_left < self.critical_threshold:
                self.logger.warning(f"Expiración crítica inminente en {time_left:.0f}s")
                self._trigger_alert(f"[CRÍTICO] Sesión expira en {int(time_left)} segundos. Recarga la página o guarda tu trabajo.")
                self.inject_ui_warning(f"⚠️ Sesión expira en {int(time_left)}s")
                
    def extract_token(self) -> Optional[str]:
        """Extrae el token directamente del LocalStorage o Cookies mediante JS."""
        # DeepSeek almacena comúnmente en storage
        script = """
        // Intentar varias llaves comunes donde podría estar el JWT
        let token = localStorage.getItem('userToken') || 
                    localStorage.getItem('token') || 
                    sessionStorage.getItem('userToken');
        if (token) {
            // A veces lo guardan estructurado en JSON
            try {
                let parsed = JSON.parse(token);
                if (parsed.token) return parsed.token;
                if (parsed.value) return parsed.value;
            } catch(e) {}
            return token;
        }
        
        // Buscar en cookies si no está en storage
        let match = document.cookie.match(new RegExp('(^| )token=([^;]+)'));
        if (match) return match[2];
        return null;
        """
        try:
            return self.driver.execute_script(script)
        except Exception:
            return None
            
    def decode_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Aplica padding a base64 y decodifica el cuerpo del JWT (sin validar firma)."""
        try:
            # Eliminar comillas extras si las hay de un parseo crudo JSON
            token = token.strip('"')
            parts = token.split('.')
            if len(parts) != 3:
                return None
                
            payload_b64 = parts[1]
            # Reparar padding del base64
            padding = len(payload_b64) % 4
            if padding:
                payload_b64 += '=' * (4 - padding)
                
            # DeepSeek usa URL_SAFE
            decoded_bytes = base64.urlsafe_b64decode(payload_b64)
            return json.loads(decoded_bytes.decode('utf-8'))
        except Exception as e:
            self.logger.debug(f"Error decodificando JWT: {e}")
            return None
            
    def _attempt_passive_refresh(self) -> bool:
        """
        Ejecuta un fetch JS indetectable contra un endpoint inofensivo
        para forzar a los interceptores web del sitio a pedir/renovar token.
        """
        script = """
        return (async function() {
            try {
                // Hacemos ping al usuario actual que usa la autenticación implícita
                let res = await fetch('/api/v0/users/current', {
                    method: 'GET',
                    headers: {'Accept': 'application/json'}
                });
                return res.ok;
            } catch (e) {
                return false;
            }
        })();
        """
        try:
            return self.driver.execute_script(script)
        except Exception:
            return False
            
    def _trigger_alert(self, message: str):
        """Dispara callback a la Interfaz de Línea de Comandos CLI."""
        if self.alert_callback:
            try:
                self.alert_callback(message)
            except Exception:
                pass
                
    def inject_ui_warning(self, message: str):
        """Inyecta un Snackbar rojo visual en la página."""
        script = f"""
        if (!document.getElementById('deepseek-token-alert')) {{
            let div = document.createElement('div');
            div.id = 'deepseek-token-alert';
            div.style.position = 'fixed';
            div.style.top = '10px';
            div.style.left = '50%';
            div.style.transform = 'translateX(-50%)';
            div.style.backgroundColor = 'rgba(220, 38, 38, 0.9)';
            div.style.color = 'white';
            div.style.padding = '12px 24px';
            div.style.borderRadius = '8px';
            div.style.zIndex = '999999';
            div.style.fontWeight = 'bold';
            div.style.pointerEvents = 'none';
            div.style.boxShadow = '0 4px 6px rgba(0,0,0,0.3)';
            div.innerText = '{message}';
            document.body.appendChild(div);
            
            // Destruir alerta despues de unos segundos
            setTimeout(() => {{
                if(div.parentNode) div.parentNode.removeChild(div);
            }}, 15000);
        }}
        """
        try:
            self.driver.execute_script(script)
        except Exception:
            pass
