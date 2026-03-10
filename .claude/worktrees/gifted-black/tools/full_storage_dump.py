import os
import json

path = r"c:\Users\Admin\Desktop\proyecto deepzeek\deepseek-client_por glm\captures\ui_coordinates.json"

def full_storage_dump():
    target_pos = 449793
    with open(path, "rb") as f:
        f.seek(max(0, target_pos - 15000))
        chunk = f.read(30000).decode("utf-8", errors="ignore")
        
        # Look for the storage object
        # It's escaped: \"storage\":{...}
        import re
        match = re.search(r'\\"storage\\":\\({.*?\\})', chunk)
        if match:
            # The capture has extra escapes. Let's try to unescape just enough
            escaped_json = match.group(1)
            # Unescape \" to " and \\ to \
            unescaped = escaped_json.replace('\\"', '"').replace('\\\\', '\\')
            try:
                # Still might have issues if there are more escapes
                print("--- STORAGE DUMP ---")
                print(unescaped[:2000]) # Print first part to see structure
                
                # Try to parse keys
                keys = re.findall(r'"([^"]+)":', unescaped)
                print("\nDETECTED KEYS:")
                print(list(set(keys))[:50])
            except:
                print("Could not parse storage JSON nicely.")
                print(unescaped[:1000])
        else:
            print("Storage block not found with strict regex.")
            # Fallback to broad search
            print("Broad snippet:")
            print(chunk[10000:12000])

full_storage_dump()
