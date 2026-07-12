import threading
import requests
import logging
from typing import Dict, Any
from config.settings import settings

logger = logging.getLogger(__name__)

def trigger_webhook_async(endpoint: str, payload: Dict[str, Any]):
    if not settings.n8n_webhook_url:
        return
    
    def _send():
        url = f"{settings.n8n_webhook_url}/{endpoint}"
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            logger.info(f"Webhook triggered successfully: {url}")
        except requests.exceptions.ReadTimeout:
            pass # Ignore read timeouts since n8n still processes the request successfully
        except Exception as e:
            logger.error(f"Failed to trigger webhook {url}: {e}")

    thread = threading.Thread(target=_send)
    thread.start()

def trigger_task_webhook(task_name: str, deadline_date: str, deadline_time: str, email: str, description: str = ""):
    # Sends both formats so it works with ANY of the two n8n workflows!
    payload = {
        "taskName": task_name,
        "deadline": f"{deadline_date}T{deadline_time}+03:00",
        "email": email,
        "description": description,
        "entities": {
            "topic": task_name,
            "deadline_date": deadline_date,
            "deadline_time": deadline_time,
            "description": description
        }
    }
    trigger_webhook_async("add-task", payload)

def trigger_meeting_webhook(topic: str, deadline_date: str, deadline_time: str, email: str = "moakramzidan@gmail.com", description: str = ""):
    payload = {
        "taskName": topic,
        "deadline": f"{deadline_date}T{deadline_time}+03:00",
        "email": email,
        "description": description,
        "entities": {
            "topic": topic,
            "deadline_date": deadline_date,
            "deadline_time": deadline_time,
            "description": description
        }
    }
    trigger_webhook_async("add-task", payload)
