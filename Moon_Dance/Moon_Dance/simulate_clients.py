import argparse
import os
import subprocess
import sys
import time
import textwrap

def run_command(cmd, cwd=None):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, text=True)
    if result.returncode != 0:
        print(f"Command failed with code {result.returncode}: {cmd}")
        sys.exit(result.returncode)

def generate_client_files():
    client_dir = "simulate_client"
    os.makedirs(client_dir, exist_ok=True)
    
    # Write client.py
    client_code = """\
import os
import time
import random
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEVICE_ID = os.environ.get("DEVICE_ID", f"device_{random.randint(100, 999)}")
API_URL = os.environ.get("API_URL", "https://www.myhjmycjh.tech:3006/api/v2/ingest")
TOKEN = os.environ.get("TOKEN", "change_me_token")
INTERVAL = int(os.environ.get("INTERVAL", "5"))

def send_data():
    print(f"[{DEVICE_ID}] Starting simulated client, targeting {API_URL}")
    while True:
        try:
            f_left = random.uniform(10.0, 50.0)
            f_right = random.uniform(10.0, 50.0)
            ratio = abs(f_left - f_right) / (f_left + f_right) if (f_left + f_right) > 0 else 0
            
            payload = {
                "device_id": DEVICE_ID,
                "timestamp": int(time.time() * 1000),
                "sensors": {
                    "left_force_n": round(f_left, 1),
                    "right_force_n": round(f_right, 1),
                    "total_force_n": round(f_left + f_right, 1)
                },
                "analysis": {
                    "deviation_ratio": round(ratio, 4)
                }
            }
            
            headers = {
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json"
            }
            
            # verify=False is used because we might be using a self-signed cert for the domain locally
            response = requests.post(API_URL, json=payload, headers=headers, verify=False, timeout=5)
            print(f"[{DEVICE_ID}] Sent data: {payload['sensors']} - Status: {response.status_code}")
        except Exception as e:
            print(f"[{DEVICE_ID}] Error sending data: {e}")
        
        time.sleep(INTERVAL)

if __name__ == "__main__":
    send_data()
"""
    with open(os.path.join(client_dir, "client.py"), "w", encoding="utf-8") as f:
        f.write(client_code)
        
    # Write Dockerfile
    dockerfile_code = """\
FROM python:3.9-slim
WORKDIR /app
RUN pip install requests urllib3
COPY client.py /app/client.py
CMD ["python", "client.py"]
"""
    with open(os.path.join(client_dir, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write(dockerfile_code)
        
    return client_dir

def deploy_flask_cloud():
    print("Deploying Flask cloud framework via Docker Compose...")
    # Using docker-compose.yml and docker-compose-nginx.yml
    run_command("docker-compose -f docker-compose.yml -f docker-compose-nginx.yml up -d --build")
    print("Flask cloud framework deployed successfully.")
    
def deploy_simulated_clients(n, client_dir, args):
    print(f"Building simulated client image...")
    run_command(f"docker build -t moondance-client {client_dir}")
    
    print(f"Deploying {n} simulated clients...")
    # First, stop any existing clients
    stop_cmd = "docker ps -a -q --filter ancestor=moondance-client"
    existing_clients = subprocess.check_output(stop_cmd, shell=True, text=True).strip().split()
    if existing_clients:
        print("Stopping existing simulated clients...")
        run_command(f"docker rm -f {' '.join(existing_clients)}")
        
    for i in range(1, n + 1):
        device_id = f"sim_device_{i:03d}"
        print(f"Starting client {device_id}...")
        # Since the domain might not resolve to the local server if run externally,
        # but the instructions say "确保模拟客户端和模拟云之间通过http协议输送数据，我的域名是www.myhjmycjh.tech"
        # We can pass an extra host mapping to ensure the container resolves the domain to the host IP.
        # But if the user really wants to use the domain and the server has it configured, it might just work.
        # Let's add an option to pass the host IP if needed, or let Docker resolve it naturally.
        # Actually, since Nginx runs in the same machine, we can just use the public IP or use host.docker.internal
        # But to be safe with the domain name, we can add --add-host www.myhjmycjh.tech:host-gateway
        
        # Determine the target API URL based on arguments
        target_api_url = args.api_url if args.api_url else "https://www.myhjmycjh.tech:3006/api/v2/ingest"
        
        # If running locally to hit a remote server, we might not need the host-gateway hack
        # unless the remote server also relies on it, but usually, we just hit the public IP/domain.
        # However, if testing locally (cloud and clients on same machine), host-gateway is useful.
        host_mapping = "--add-host www.myhjmycjh.tech:host-gateway " if not args.remote else ""

        cmd = (
            f"docker run -d --name {device_id} "
            f"{host_mapping}"
            f"-e DEVICE_ID={device_id} "
            f"-e API_URL={target_api_url} "
            f"moondance-client"
        )
        run_command(cmd)
        
    print(f"Successfully deployed {n} simulated clients.")
    print("You can view client logs using: docker logs -f sim_device_001")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy MoonDance simulated clients and cloud framework.")
    parser.add_argument("-n", "--number", type=int, default=3, help="Number of simulated clients to deploy")
    parser.add_argument("--skip-cloud", action="store_true", help="Skip deploying the Flask cloud framework")
    parser.add_argument("--remote", action="store_true", help="Set this if you are running this script locally to connect to a remote cloud server")
    parser.add_argument("--api-url", type=str, help="Custom API URL to hit (e.g., https://124.220.79.133:3006/api/v2/ingest)")
    args = parser.parse_args()
    
    if not args.skip_cloud and not args.remote:
        deploy_flask_cloud()
    else:
        print("Skipping Flask cloud framework deployment (running remote mode or skipped explicitly).")
        
    client_dir = generate_client_files()
    deploy_simulated_clients(args.number, client_dir, args)
