
import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from deepseek_client.client import DeepSeekClient
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def real_flow_battle_test():
    load_dotenv()
    print("[*] Iniciando Test de Combate de Flujo Real...")
    
    battle_dir = os.path.abspath("captures/battle_tests")
    os.makedirs(battle_dir, exist_ok=True)
    
    client = DeepSeekClient(headless=False, auto_login=True)
    driver = client.driver.driver
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "scenarios": []
    }

    def handle_blocking_attachments():
        """Detecta si el panel de adjuntos está abierto y trata de salir."""
        try:
            # Si el input de archivo está presente o hay un diálogo visible
            # Buscaremos un botón de 'cerrar' o simplemente pulsaremos ESC
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(1)
        except:
            pass

    def run_scenario(name, deepthink=False, search=False, prompt="Hola, dime el clima en Marte"):
        print(f"\n[*] Escenario: {name}")
        scenario_entry = {"name": name, "prompt": prompt, "status": "pending"}
        
        try:
            # 1. Configurar Modos
            client.toggle_deepthink(deepthink)
            client.toggle_search(search)
            time.sleep(1)
            
            # 2. Captura de Panel Pre-Envío
            driver.save_screenshot(os.path.join(battle_dir, f"{name.lower()}_configured.png"))
            
            # 3. Enviar Prompt
            print(f"[*] Enviando prompt...")
            # Usaremos el client.ask para probar la lógica interna que el usuario critica
            response = client.ask(prompt, continue_conversation=True)
            
            # 4. Verificar si hubo confusión de botones (Mirando si el input de archivo se activó)
            # Nota: detectamos si el input de archivo tiene foco o si hay un modal.
            
            scenario_entry["response_preview"] = response.content[:100]
            scenario_entry["status"] = "success"
            print(f"[+] Éxito: Respuesta recibida.")
            
            # Captura de Respuesta
            driver.save_screenshot(os.path.join(battle_dir, f"{name.lower()}_response.png"))
            
        except Exception as e:
            print(f"[!] Fallo en {name}: {e}")
            scenario_entry["status"] = "failed"
            scenario_entry["error"] = str(e)
            driver.save_screenshot(os.path.join(battle_dir, f"{name.lower()}_error.png"))
            handle_blocking_attachments()
            
        results["scenarios"].append(scenario_entry)

    try:
        print("[*] Estabilizando interfaz...")
        time.sleep(5)
        
        # Test 1: Flujo Normal (Sin modos)
        run_scenario("Normal_Flow", deepthink=False, search=False, prompt="¿Qué hora es en Tokio?")
        
        # Test 2: DeepThink Activo
        run_scenario("DeepThink_Only", deepthink=True, search=False, prompt="Explica la relatividad en 1 frase.")
        
        # Test 3: Search Activo
        run_scenario("Search_Only", deepthink=False, search=True, prompt="Noticias de hoy sobre IA.")
        
        # Test 4: Ambos Activos
        run_scenario("Full_Throttle", deepthink=True, search=True, prompt="¿Cuál es el mejor lenguaje para IA en 2025?")

        # Guardar reporte
        with open(os.path.join(battle_dir, "battle_report.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
            
        print(f"\n[+] Test de combate finalizado. Resultados en {battle_dir}")

    except Exception as e:
        print(f"[!] Error sistémico: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    real_flow_battle_test()
