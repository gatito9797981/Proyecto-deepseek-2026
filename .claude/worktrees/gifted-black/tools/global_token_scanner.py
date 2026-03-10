import json
import re

path = r"c:\Users\Admin\Desktop\proyecto deepzeek\deepseek-client_por glm\captures\ui_coordinates.json"

def extract_valid_token():
    # Use a regex to find all userToken values
    # Pattern: \"userToken\":\"{\\\"value\\\":\\\"(YX.*?)\\\"
    # Or more general: \"userToken\":\"{\\\"value\\\":\\\"([^"]+)\\\"
    
    pattern = re.compile(r'\\"userToken\\":\\"{\\\\"value\\\\":\\\\"([^\\"]+)\\\\"')
    last_token = None
    
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        # Read in large chunks
        chunk_size = 10 * 1024 * 1024 # 10MB
        while True:
            chunk = f.read(chunk_size)
            if not chunk: break
            
            matches = pattern.findall(chunk)
            if matches:
                last_token = matches[-1]
            
            # Move back slightly to avoid splitting a match
            if len(chunk) == chunk_size:
                f.seek(f.tell() - 1000)

    if last_token:
        # Now find cookies near the end of the file too
        # Looking for \"cookies\":\"(.*?)\"
        cookie_pattern = re.compile(r'\\"cookies\\":\\"([^\\"]+)\\"')
        last_cookies = None
        
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 10 * 1014 * 1024)) # Last 10MB
            tail = f.read()
            c_matches = cookie_pattern.findall(tail)
            if c_matches:
                last_cookies = c_matches[-1]
        
        print(json.dumps({
            "userToken": last_token,
            "cookies": last_cookies
        }, indent=2))
    else:
        print("No valid userToken found in the entire file")

extract_valid_token()
