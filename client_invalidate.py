import requests
BASE_URL = "http://localhost:8000"
session_id = 1  # укажите ID сессии для инвалидизации
resp = requests.post(f"{BASE_URL}/session/invalidate", params={"session_id": session_id})
print(resp.json())
