"""Configuration module for the programm. Here are loaded all the credentials and initialize some global variables.
"""

import logging
import os
from dotenv import load_dotenv


logging.basicConfig(filename="info.log", level=logging.INFO)


load_dotenv()


# Load environment variables.
CUBA_URL = os.environ["CUBA_URL"]
TB_GATEWAY_TOKEN = os.environ["TB_GATEWAY_TOKEN"]
TB_TOTALS_DEVICE_NAME = os.environ["TB_TOTALS_DEVICE_NAME"]
TB_CLIENT_ID = os.environ["TB_CLIENT_ID"]
TB_DEVICE_PROFILE = os.environ["TB_DEVICE_PROFILE"]
PING_COUNT = os.environ["PING_COUNT"]
PING_INTERVAL = os.environ["PING_INTERVAL"]

# Global variables.
db_modified = False
cameras_online = {}
