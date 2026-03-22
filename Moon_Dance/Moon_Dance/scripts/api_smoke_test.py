import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_api import create_app, _ensure_ca_and_server_cert
from src.config import settings


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        cert_path, key_path, ca_cert_path = _ensure_ca_and_server_cert(tmp_dir, "localhost")
        assert os.path.exists(cert_path)
        assert os.path.exists(key_path)
        assert os.path.exists(ca_cert_path)

    app = create_app()
    client = app.test_client()

    login_resp = client.post(
        "/login",
        json={"app_id": settings.API_APP_ID, "app_secret": settings.API_APP_SECRET},
    )
    assert login_resp.status_code == 200, login_resp.data
    token = login_resp.get_json()["token"]

    req_id = str(uuid.uuid4())
    payload = {
        "request_id": req_id,
        "device_id": "device_001",
        "timestamp": 1700000000000,
        "sensors": {"left_force_n": 300.0, "right_force_n": 280.0},
        "analysis": {"deviation_ratio": 0.034},
    }
    headers = {"Authorization": f"Bearer {token}"}

    upload_resp = client.post("/api/v1/upload", json=payload, headers=headers)
    assert upload_resp.status_code == 201, upload_resp.data

    upload_resp2 = client.post("/api/v1/upload", json=payload, headers=headers)
    assert upload_resp2.status_code == 200, upload_resp2.data

    print("api_smoke_test_ok")


if __name__ == "__main__":
    main()
