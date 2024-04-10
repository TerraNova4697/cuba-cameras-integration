# import json noqa
import logging
import os
from dotenv import load_dotenv


logging.basicConfig(filename="info.log", level=logging.INFO)

# # Load config.json
# with open("./configs/config.json", "r") as config:
#     CONFIGS = json.load(config)

# CUBA_URL = CONFIGS["CUBA_URL"]
# TB_GATEWAY_TOKEN = CONFIGS["TB_GATEWAY_TOKEN"]
# TB_TOTALS_DEVICE_NAME = CONFIGS["TB_TOTALS_DEVICE_NAME"]
# TB_CLIENT_ID = CONFIGS["TB_CLIENT_ID"]
# TB_DEVICE_PROFILE = CONFIGS["TB_DEVICE_PROFILE"]

# PING_COUNT = CONFIGS["PING_COUNT"]
# PING_INTERVAL = CONFIGS["PING_INTERVAL"]

# # Load cameras.json
# with open("./configs/cameras.json", "r") as cameras_config:
#     CAMERAS = json.load(cameras_config)

# DEVICES_COUNT = len(CAMERAS)

# logging.info(f"Импортировано камер: {DEVICES_COUNT}")


load_dotenv()


CUBA_URL = os.environ["CUBA_URL"]
TB_GATEWAY_TOKEN = os.environ["TB_GATEWAY_TOKEN"]
TB_TOTALS_DEVICE_NAME = os.environ["TB_TOTALS_DEVICE_NAME"]
TB_CLIENT_ID = os.environ["TB_CLIENT_ID"]
TB_DEVICE_PROFILE = os.environ["TB_DEVICE_PROFILE"]
PING_COUNT = os.environ["PING_COUNT"]
PING_INTERVAL = os.environ["PING_INTERVAL"]
