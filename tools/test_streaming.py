import sys
import os
# Añadir el directorio raíz al path para encontrar deepseek_client
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from deepseek_client.client import DeepSeekClient
from deepseek_client.config import Config

def main():
    config = Config()
    config.headless = True 
    client = DeepSeekClient(config_obj=config, auto_login=True)
    
    print("\n[+] DeepSeek Listo. Probando Motor Hibrido (Pensamiento + Respuesta)...")
    
    try:
        client.new_conversation()
        client.toggle_deepthink(True)
        print("\n=== PREGUNTA ===")
        print("Explica brevemente la teoria de cuerdas. Piensa en voz alta antes.")
        print("\n=== RESPUESTA (STREAMING) ===")
        
        # Consumir el generador en vivo
        for chunk in client.ask_stream("Explica brevemente la teoria de cuerdas. Usa DeepThink antes."):
            sys.stdout.write(chunk)
            sys.stdout.flush()
            
        print("\n\n[✓] Prueba finalizada exitosamente.")
        
    except Exception as e:
        print(f"\n[!] Error durante la prueba: {e}")
    finally:
        client.driver.quit()

if __name__ == "__main__":
    main()
