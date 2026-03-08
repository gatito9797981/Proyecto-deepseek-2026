import json
import os

path = r"c:\Users\Admin\Desktop\proyecto deepzeek\deepseek-client_por glm\captures\ui_coordinates.json"

def extract_from_middle():
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i > 10000: break
            if "Thought for 13 seconds" in line:
                try:
                    data = json.loads(line)
                    # The line itself is the recorded object
                    storage = data.get("storage", {})
                    ls = storage.get("localStorage", {})
                    cookies = storage.get("cookies", "")
                    
                    ut_raw = ls.get("userToken", "{}")
                    user_token = "Not found"
                    if isinstance(ut_raw, str):
                        try:
                            user_token = json.loads(ut_raw).get("value")
                        except: pass
                    elif isinstance(ut_raw, dict):
                        user_token = ut_raw.get("value")
                    
                    print(json.dumps({
                        "userToken": user_token,
                        "cookies": cookies,
                        "line": i
                    }, indent=2))
                    return
                except:
                    pass

extract_from_middle()
