import os
import re
import requests
import threading

def _send_message_task(number, text, instance_name):
    api_url = os.environ.get("EVOLUTION_API_URL", "").rstrip("/")
    instance = instance_name or os.environ.get("EVOLUTION_INSTANCE_NAME", "")
    api_key = os.environ.get("EVOLUTION_API_KEY", "")
    
    if not api_url or not instance or not api_key:
        print("Evolution API credentials not configured in .env")
        return

    # Limpa e formata o numero
    number = re.sub(r'\D', '', number)
    if not number.startswith("55") and len(number) <= 11:
        number = "55" + number
    
    url = f"{api_url}/message/sendText/{instance}"
    
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "number": number,
        "text": text
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"Message sent via Evolution API to {number}")
    except Exception as e:
        print(f"Failed to send Evolution API message to {number}: {e}")

def send_whatsapp_message(number, text, instance_name=None):
    if not number:
        return
    thread = threading.Thread(target=_send_message_task, args=(number, text, instance_name))
    thread.start()
