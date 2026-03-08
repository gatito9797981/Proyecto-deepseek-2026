import os

path = r"c:\Users\Admin\Desktop\proyecto deepzeek\deepseek-client_por glm\captures\ui_coordinates.json"

def deep_extract():
    # Target near the previously found position
    with open(path, "rb") as f:
        f.seek(449000)
        chunk = f.read(10000).decode("utf-8", errors="ignore")
        
        print("--- RAW CONTENT AROUND AUTH ---")
        # Look for the start of the "storage" object
        start_idx = chunk.find('"storage":{')
        if start_idx != -1:
            # Try to find the end of this specific JSON object
            level = 0
            end_idx = -1
            # Simple brace counting
            for i in range(start_idx, len(chunk)):
                if chunk[i] == '{': level += 1
                elif chunk[i] == '}': 
                    level -= 1
                    if level == 0:
                        end_idx = i + 1
                        break
            
            if end_idx != -1:
                storage_raw = chunk[start_idx:end_idx]
                print(storage_raw)
            else:
                print(chunk[start_idx:start_idx+2000])
        else:
            print("Storage block not found in this chunk.")

deep_extract()
