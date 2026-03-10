import os

json_path = r"c:\Users\Admin\Desktop\proyecto deepzeek\deepseek-client_por glm\captures\ui_coordinates.json"

def find_token_in_binary(path):
    if not os.path.exists(path):
        return None
    
    # We are looking for something like "userToken":"{\"value\":\"YX...\"}"
    # In the file it looks like \"userToken\":\"{\\\"value\\\":\\\"YX
    target = b'\\"userToken\\":\\"{\\\\"value\\\\":\\\\"YX'
    
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        # Read from back in chunks
        chunk_size = 1024 * 1024 * 5 # 5MB
        for i in range(size - chunk_size, -chunk_size, -chunk_size):
            pos = max(0, i)
            f.seek(pos)
            chunk = f.read(chunk_size + 1000) # overlapped
            
            idx = chunk.rfind(target)
            if idx != -1:
                # Found it! Extract a good chunk
                return chunk[idx:idx+2000].decode("utf-8", errors="ignore")
    return None

snippet = find_token_in_binary(json_path)
if snippet:
    print("Found snippet:")
    print(snippet)
else:
    print("Not found")
