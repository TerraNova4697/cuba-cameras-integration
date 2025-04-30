# Install current project as daemon service.

python3 -m venv .venv &&
sudo .venv/bin/pip install -r requirements.txt
sudo cp cuba-cameras-integration.service /etc/systemd/system/cuba-cameras-integration.service
sudo systemctl daemon-reload
