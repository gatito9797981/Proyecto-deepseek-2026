import os

path = r"c:\Users\Admin\Desktop\proyecto deepzeek\deepseek-client_por glm\captures\ui_coordinates.json"

def final_extract():
    target = b"YXDSXEOCIWVcvSzQiKbSVjxPqG"
    with open(path, "rb") as f:
        f.seek(440000) # Start near the found position
        chunk = f.read(20000)
        
        idx = chunk.find(target)
        if idx != -1:
            # Re-read to be sure we have the context
            # We want to extract the whole "storage" object if possible
            # But regex is easier for the two specific keys
            text = chunk.decode("utf-8", errors="ignore")
            
            import re
            ut_match = re.search(r'\\"userToken\\":\\"{\\\\"value\\\\":\\\\"([^\\"]+)\\\\"', text)
            cookie_match = re.search(r'\\"cookies\\":\\"([^\\"]+)\\"', text)
            
            res = {}
            if ut_match: res["userToken"] = ut_match.group(1)
            if cookie_match: res["cookies"] = cookie_match.group(1)
            
            print("EXTRACTED_DATA_START")
            import json
            print(json.dumps(res, indent=2))
            print("EXTRACTED_DATA_END")

final_extract()
