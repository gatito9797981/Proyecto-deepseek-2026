
import os
import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from deepseek_client.client import DeepSeekClient
from dotenv import load_dotenv

def test_advanced_features():
    load_dotenv()
    print("[*] Iniciando Test de Funciones Avanzadas (Adjuntos, Historial, Nuevo Chat)...")
    
    test_dir = os.path.abspath("captures/advanced_tests")
    os.makedirs(test_dir, exist_ok=True)
    
    client = DeepSeekClient(headless=False, auto_login=True)
    driver = client.driver.driver
    
    results = {"timestamp": time.time(), "tests": []}
    
    def log_test(name, status, error=None):
        print(f"[{'X' if error else 'V'}] {name} - Status: {status}")
        results["tests"].append({"name": name, "status": status, "error": error})

    try:
        print("[*] Esperando carga de UI...")
        time.sleep(6)
        
        # --- TEST 1: BOTON ADJUNTAR Y CIERRE DEL POPUP ---
        print("\n[*] TEST 1: Manejo del Popup de Adjuntos")
        attach_btn = driver.find_element(By.CSS_SELECTOR, "div.f02f0e25[role='button']")
        
        # Clic para abrir
        driver.execute_script("arguments[0].click();", attach_btn)
        time.sleep(2)
        driver.save_screenshot(os.path.join(test_dir, "1_attach_popup_open.png"))
        
        # Cerrar explícitamente con ESCAPE (Lo que soluciona el bloqueo)
        print("[*] Cerrando popup con ESCAPE...")
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(1)
        driver.save_screenshot(os.path.join(test_dir, "1_attach_popup_closed.png"))
        log_test("Manejo Popup Adjuntar", "success")
        
        # --- TEST 2: HISTORIAL (SELECCIONAR CONVERSACION PREVIA) ---
        print("\n[*] TEST 2: Historial (Navegación)")
        # Asegurar que el sidebar esté abierto. Si no hay items, intentamos hacer clic al botón de menú
        history_items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/a/chat/s/']") 
        if not history_items:
            print("[*] Sidebar parece cerrado, abriendo...")
            menu_btn = driver.find_element(By.CSS_SELECTOR, "div._4f3769f")
            driver.execute_script("arguments[0].click();", menu_btn)
            time.sleep(2)
            history_items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/a/chat/s/']")
        
        if history_items:
            target_href = history_items[0].get_attribute("href")
            print(f"[*] Seleccionando historial: {target_href}")
            driver.execute_script("arguments[0].click();", history_items[0])
            time.sleep(4) # Esperar a que cargue
            driver.save_screenshot(os.path.join(test_dir, "2_history_loaded.png"))
            log_test("Seleccion de Historial", "success")
        else:
            print("[!] No se encontró historial para seleccionar.")
            log_test("Seleccion de Historial", "skipped", "No hay items en historial")

        # --- TEST 3: NUEVO CHAT ---
        print("\n[*] TEST 3: Nuevo Chat")
        # El botón de nuevo chat
        new_chat_btn = None
        try:
            # Seleccionar por SVG/clase que tiene el New Chat (normalmente en la parte superior izquierda del sidebar)
            new_chat_btn = driver.find_element(By.CSS_SELECTOR, "div._5a8ac7a")
        except:
            # Fallback por texto si la clase cambió
            for el in driver.find_elements(By.CSS_SELECTOR, "[role='button'], div"):
                if "new chat" in (el.text or "").lower() or "nuevo chat" in (el.text or "").lower():
                    new_chat_btn = el
                    break

        if new_chat_btn:
            driver.execute_script("arguments[0].click();", new_chat_btn)
            print("[*] Clic en Nuevo Chat, esperando transición...")
            time.sleep(3)
            driver.save_screenshot(os.path.join(test_dir, "3_new_chat_loaded.png"))
            log_test("Nuevo Chat", "success")
        else:
            log_test("Nuevo Chat", "failed", "Boton no encontrado")

        # Guardar reporte
        report_path = os.path.join(test_dir, "advanced_tests_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        print(f"\n[+] Pruebas avanzadas completadas exitosamente. Reporte en: {report_path}")

    except Exception as e:
        print(f"[!] Fallo crítico en el test: {e}")
        log_test("Test general", "failed", str(e))
    finally:
        client.close()

if __name__ == "__main__":
    test_advanced_features()
