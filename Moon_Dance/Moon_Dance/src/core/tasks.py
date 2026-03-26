from __future__ import annotations
import os
from celery import Celery
from datetime import datetime
from typing import Any, Dict
from src.config.settings import REDIS_URL, DATA_LOG_FILE, BASE_PATH

celery = Celery("moondance", broker=REDIS_URL, backend=REDIS_URL)

@celery.task(name="moondance.save_data")
def save_data(payload: Dict[str, Any]) -> bool:
    os.makedirs(os.path.dirname(DATA_LOG_FILE), exist_ok=True)
    line = f"{datetime.utcnow().isoformat()}Z\t{payload}\n"
    with open(DATA_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    return True
