import sys
import subprocess
import time
import urllib.request
from dotenv import load_dotenv

load_dotenv()

p = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8003"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
time.sleep(3)


def fetch(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            print(response.status, response.read().decode())
    except urllib.error.HTTPError as e:
        print(e.code, e.read().decode())
    except Exception as e:
        print(e)


print("Testing /api/v1/hardware/")
fetch("http://127.0.0.1:8003/api/v1/hardware/")

print("Testing /api/v1/virtual-machines/")
fetch("http://127.0.0.1:8003/api/v1/virtual-machines/")

print("Testing /api/v1/runbooks/")
fetch("http://127.0.0.1:8003/api/v1/runbooks/")

p.terminate()
p.wait()
print("--- UVICORN LOGS ---")
print(p.stdout.read())
