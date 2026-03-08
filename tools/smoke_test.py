from deepseek_client.client import DeepSeekClient
import os
from dotenv import load_dotenv

def smoke_test():
    load_dotenv()
    print("Iniciando Smoke Test...")
    try:
        # Forzar headless para la prueba si no se especifica
        client = DeepSeekClient(headless=True, auto_login=True)
        
        print(f"URL Actual: {client.driver.driver.current_url}")
        
        if "sign_in" in client.driver.driver.current_url:
            print("ERROR: El bypass de login falló. Seguimos en la página de sign_in.")
        else:
            print("ÉXITO: Bypass de login confirmado.")
            
            try:
                chat_input = client._wait_for_chat_input(timeout=10)
                print("ÉXITO: Input de chat detectado.")
            except Exception as e:
                print(f"ADVERTENCIA: No se detectó el input de chat tras el bypass: {e}")
                client.driver.save_screenshot("captures/failure_smoke_test.png")
    
    except Exception as e:
        print(f"FALLO CRÍTICO: {e}")
    finally:
        if 'client' in locals():
            client.driver.quit()

if __name__ == "__main__":
    smoke_test()
