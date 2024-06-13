# Install current project as daemon service.

sudo apt update
sudo apt install -y python3 python3-pip python3-dev
sudo pip3 install -r requirements.txt
sudo mv /cuba/cuba-cameras-integration/cuba-cameras-integration.service /lib/systemd/system/cuba-cameras-integration.service
sudo systemctl daemon-reload