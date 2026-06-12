import os
import re
import requests
import threading

def _send_message_task(number, text, instance_name):
    api_url = os.environ.get("WHATSAPP_API_URL", "").rstrip("/")
    api_key = os.environ.get("WHATSAPP_API_KEY", "")
    
    if not instance_name:
        print("Company has no WhatsApp instance configured. Skipping message.")
        return

    if not api_url or not api_key:
        print("Evolution API credentials not configured in .env")
        return

    # Limpa e formata o numero
    number = re.sub(r'\D', '', number)
    if not number.startswith("55") and len(number) <= 11:
        number = "55" + number
    
    url = f"{api_url}/message/sendText/{instance_name}"
    
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "number": number,
        "textMessage": {
            "text": text
        }
    }
    
    try:
        print("\n=== INICIANDO DISPARO WHATSAPP ===")
        print(f"Instância Remetente: {instance_name}")
        print(f"Número Destino: {number}")
        print(f"Mensagem: {text}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"Status Retornado: {response.status_code}")
        print(f"Resposta da Evolution API: {response.text}")
        print("==================================\n")
        
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Evolution API message to {number}: {e}")


def send_whatsapp_message(number, text, instance_name=None):
    if not number:
        return
    thread = threading.Thread(target=_send_message_task, args=(number, text, instance_name))
    thread.start()
