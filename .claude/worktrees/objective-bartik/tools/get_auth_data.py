import json
import os
import re

json_path = r"c:\Users\Admin\Desktop\proyecto deepzeek\deepseek-client_por glm\captures\ui_coordinates.json"

def get_last_auth(path):
    if not os.path.exists(path):
        return None
    
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        # Read the last 5MB (it's a huge file)
        chunk_size = min(size, 5 * 1024 * 1024)
        f.seek(-chunk_size, 2)
        tail = f.read().decode("utf-8", errors="ignore")
        
        # Find all records with userToken
        records = []
        # Match using regex for more flexibility
        matches = re.finditer(r'\{"url":.*?"localStorage":\{.*?"userToken":"(.*?)"\}', tail)
        for match in matches:
            try:
                # Find the surrounding { ... }
                start = tail.rfind('{"url"', 0, match.start())
                level = 0
                end = -1
                for i in range(start, len(tail)):
                    if tail[i] == '{': level += 1
                    elif tail[i] == '}': 
                        level -= 1
                        if level == 0:
                            end = i + 1
                            break
                if end != -1:
                    records.append(json.loads(tail[start:end]))
            except:
                continue
        
        # Return the last one with non-null userToken
        for record in reversed(records):
            token_data = record.get("storage", {}).get("localStorage", {}).get("userToken")
            if token_data:
                try:
                    # userToken is often stored as JSON string in localStorage
                    if isinstance(token_data, str) and token_data.startswith('{'):
                         val = json.loads(token_data).get("value")
                         if val: return record
                    elif isinstance(token_data, dict) and token_data.get("value"):
                         return record
                except:
                    pass
    return None

auth_record = get_last_auth(json_path)
if auth_record:
    ls = auth_record.get("storage", {}).get("localStorage", {})
    cookies = auth_record.get("storage", {}).get("cookies", "")
    
    # Extract userToken value
    ut_raw = ls.get("userToken", "{}")
    user_token = "Not found"
    try:
        if isinstance(ut_raw, str):
            user_token = json.loads(ut_raw).get("value", "Not found")
        else:
            user_token = ut_raw.get("value", "Not found")
    except:
        pass

    print(json.dumps({
        "userToken": user_token,
        "cookies": cookies,
        "timestamp": auth_record.get("timestamp")
    }, indent=2))
else:
    print("Could not find any entry with userToken")
