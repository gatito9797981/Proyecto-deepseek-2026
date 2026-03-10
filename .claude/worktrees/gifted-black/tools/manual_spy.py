"""
Manual Spy Script for DeepSeek
Launches a browser with Spy Mode enabled and takes periodic captures.
"""

import time
import os
from deepseek_client.driver import AntiDetectionDriver
from deepseek_client.config import Config
from deepseek_client.profiles import PROFILES
import logging

def run_spy_session():
    # Configuración básica
    config = Config()
    config.headless = False  # Necesitamos ver la interacción
    
    # Usar un perfil específico o aleatorio
    profile_name = "linux_dev" 
    profile = PROFILES.get(profile_name)
    
    print(f"[*] Iniciando Sesión de Observación con perfil: {profile_name}")
    print("[*] Asegúrate de tener mitmproxy corriendo si quieres captura de red: mitmproxy -s extract_data.py")
    
    # Crear carpeta de capturas
    os.makedirs("captures", exist_ok=True)
    
    try:
        with AntiDetectionDriver(profile=profile, config_obj=config) as driver:
            # Ir a DeepSeek
            print("[*] Navegando a DeepSeek...")
            driver.get("https://chat.deepseek.com")
            
            # Esperar a que el usuario interactúe
            print("\n[!] MODO ESPÍA ACTIVO")
            print("[!] Puedes iniciar sesión y chatear normalmente.")
            print("[!] El script inyectará el monitor de UI y tomará capturas cada 30 segundos.")
            print("[!] Presiona Ctrl+C en esta terminal para detener.\n")
            
            count = 0
            while True:
                count += 1
                # Tomar captura de pantalla
                driver.take_observation_screenshot(name=f"spy_{count}")
                
                # Guardar HTML para análisis de estructura
                html_path = f"captures/page_{count}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                
                # Inyectar/Re-inyectar spy_mode.js
                driver.enable_spy_mode()
                    
                # Leer logs de la consola (donde spy_mode.js reporta datos)
                try:
                    logs = driver.get_log('browser')
                    for entry in logs:
                        if "DEEPSEEK_SPY_DATA:" in entry['message']:
                            # Extraer solo el JSON del mensaje de log
                            data_str = entry['message'].split("DEEPSEEK_SPY_DATA:")[1]
                            # Limpiar posibles comillas de escape de la consola
                            if data_str.startswith('"') and data_str.endswith('"'):
                                data_str = data_str[1:-1].replace('\\"', '"')
                                
                            with open("captures/ui_coordinates.json", "a", encoding="utf-8") as f:
                                f.write(data_str + "\n")
                except Exception as log_err:
                    pass # Algunos drivers pueden fallar aquí temporalmente
                
                if count % 10 == 0:
                    print(f"[*] Capturadas {count} ráfagas de datos (IMG + HTML + UI). Sigue observando...")
                
                time.sleep(1) # Intervalo de 1 segundo

    except KeyboardInterrupt:
        print("\n[*] Sesión finalizada por el usuario.")
    except Exception as e:
        print(f"\n[!] Error durante la sesión: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_spy_session()
