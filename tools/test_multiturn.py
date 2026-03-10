import json
import time
import sys
import os

# Añadir el directorio raíz al path para encontrar deepseek_client
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from deepseek_client.client import DeepSeekClient


def main():
    print("Iniciando prueba automática de multi-turno...")
    client = DeepSeekClient()
    
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_path = os.path.join(base_dir, 'test_prompts.json')
    
    with open(prompts_path, 'r', encoding='utf-8') as f:
        prompts = json.load(f)
        
    for i, p in enumerate(prompts):
        prompt = p['prompt']
        print(f"\n--- PROMPT {i+1} ---")
        print(f"User: {prompt}")
        print("Esperando respuesta...")
        
        try:
            full_ans = ""
            for chunk in client.ask(prompt):
                full_ans += chunk
                print(chunk, end="", flush=True)
            print(f"\n[OK] Respuesta {i+1} completada. (Longitud: {len(full_ans)})")
            
            # Guardamos la respuesta en un log para revisar
            with open('test_results.log', 'a', encoding='utf-8') as flog:
                flog.write(f"PROMPT {i+1}: {prompt}\n")
                flog.write(f"RESPUESTA {i+1}:\n{full_ans}\n")
                flog.write("-" * 50 + "\n")
                
        except Exception as e:
            print(f"\n[ERROR] Falló prompt {i+1}: {e}")
            
        time.sleep(2) # Pausa entre turnos
        
if __name__ == "__main__":
    main()
