import requests

url = "http://127.0.0.1:8000/api/chapters/run_sandbox/"
payload = {
    "code": """
gia_niem_yet = 5000000
ty_le_hao_hut = 0.02
hao_hut = gia_niem_yet * ty_le_hao_hut
result = gia_niem_yet - hao_hut
print(f"Hao hụt: {hao_hut}")
print(f"Thực nhận: {result}")
"""
}

response = requests.post(url, json=payload)
print(response.json())