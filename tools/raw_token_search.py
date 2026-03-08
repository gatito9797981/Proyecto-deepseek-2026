import os

path = r"c:\Users\Admin\Desktop\proyecto deepzeek\deepseek-client_por glm\captures\ui_coordinates.json"

def raw_search():
    target = b"YXDSX"
    with open(path, "rb") as f:
        # File is big, read in chunks
        chunk_size = 5 * 1024 * 1024
        while True:
            chunk = f.read(chunk_size)
            if not chunk: break
            
            idx = chunk.find(target)
            if idx != -1:
                print(f"Found target at raw position {f.tell() - len(chunk) + idx}")
                # Print 500 bytes around it
                snippet = chunk[max(0, idx-100) : min(len(chunk), idx+400)]
                print(snippet.decode("utf-8", errors="ignore"))
                return
    print("Target byte sequence not found")

raw_search()
