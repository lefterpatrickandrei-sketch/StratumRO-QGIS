import os
import requests

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}",
    "Accept": "application/json",
}

payload = {
    "messages": [
        {"role": "user", "content": "Reply with exactly: KIMI K3 WORKS"}
    ],
    "model": "moonshotai/kimi-k3",
    "max_tokens": 64,
    "temperature": 0,
    "stream": False,
}

response = requests.post(invoke_url, headers=headers, json=payload)
print("Status:", response.status_code)
print("Response:", response.text[:500])