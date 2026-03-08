import os

path = r"c:\Users\Admin\Desktop\proyecto deepzeek\deepseek-client_por glm\captures\ui_coordinates.json"

def deep_extract_escaped():
    # Posición encontrada anteriormente
    target_pos = 449793
    with open(path, "rb") as f:
        # Read a good chunk around the position
        f.seek(max(0, target_pos - 10000))
        chunk = f.read(20000)
        # We need to handle the bytes and then decode safely
        text = chunk.decode("utf-8", errors="ignore")
        
        # Look for "cookies" within the escaped text
        # It looks like \"cookies\":\"....\"
        print("--- SEARCHING FOR COOKIES ---")
        import re
        # Search for any cookie string that might contain ds_session_id
        matches = re.findall(r'\\"cookies\\":\\"([^\\"]+)\\"', text)
        for m in matches:
            if "ds_session_id" in m or "smidV2" in m:
                print(f"FOUND COOKIE STRING: {m}")
        
        # Look for userToken again just to be sure we have the full context
        token_matches = re.findall(r'\\"userToken\\":\\"{\\\\"value\\\\":\\\\"([^\\"]+)\\\\"', text)
        for tm in token_matches:
            print(f"FOUND USER TOKEN: {tm}")

deep_extract_escaped()
