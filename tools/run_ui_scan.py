"""
DeepSeek UI Scanner Runner.
Launches the driver and injects ui_scanner.js.
"""
import time
import os
from deepseek_client.driver import AntiDetectionDriver
from deepseek_client.config import Config

def run_scanner():
    config = Config()
    config.headless = False # Necesario para ver el escaneo
    config.proxy = "127.0.0.1:8080" # Conectar al mitmproxy
    
    print("[*] Iniciando Escáner de Interfaz...")
    print("[*] Asegúrate de tener el proxy corriendo: mitmdump -s tools/ui_scan_proxy.py")
    
    # Cargar script JS
    js_path = os.path.join("deepseek_client", "resources", "ui_scanner.js")
    with open(js_path, "r", encoding="utf-8") as f:
        scanner_js = f.read()

    try:
        with AntiDetectionDriver(config_obj=config) as driver:
            driver.get("https://chat.deepseek.com")
            print("[+] Página cargada. Inyectando escáner...")
            
            # Inyectar escáner
            driver.execute_script(scanner_js)
            
            print("[!] Escáner activo. Revisando la UI cada 10 segundos.")
            print("[!] Los resultados se guardarán en la carpeta 'captures'.")
            print("[!] Presiona Ctrl+C para terminar.")
            
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n[*] Escaneo finalizado.")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    run_scanner()
