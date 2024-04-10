import asyncio
import logging
import subprocess
from time import time

from tb_gateway_mqtt import TBGatewayMqttClient

import config
from database import (
    get_all_cameras,
    db_init,
    get_unique_ping_periods,
    get_cameras_by_ping_period,
)


db_init()
logging.basicConfig(filename="info.log", level=logging.INFO)

cameras_map = {}


def handle_rpc(gateway, request_body):
    logging.info(f"RPC: {request_body}")
    # TODO: write RPC that would update ping_period of cameras


async def connect_devices(
    gateway: TBGatewayMqttClient, devices: list, device_type: str = "default"
):
    for device in devices:
        gateway.gw_connect_device(device.name, device_type)
        await asyncio.sleep(0.0001)

    logging.info(f"{len(devices)} devices successfully connected")


async def ping_camera(gateway, device):
    connection_status = 0
    try:
        # Ping device
        # process = await asyncio.create_subprocess_exec(
        #     "ping",
        #     "-c",
        #     PING_COUNT,
        #     "-i",
        #     PING_INTERVAL,
        #     device.ip,
        #     stdout=subprocess.DEVNULL,
        #     stderr=subprocess.DEVNULL,
        # )
        # await process.communicate()
        # connection_status = 1 if process.returncode == 0 else 0

        # telemetry = {"online": connection_status}
        # gateway.gw_send_telemetry(device.name, telemetry)

        # TODO: update camera values in BD

        # global devices_connections_changed
        # devices_connections_changed += 1
        await asyncio.sleep(1)

    except Exception as e:
        error_msg = "Error in getting device {} ({}) connection: {}"
        error_msg.format(device.name, device.ip, e)
        logging.error(error_msg)

    # return connection_status
    return 1


async def ping_cameras_list(gateway, period, devices):
    while True:
        time_start = time()
        tasks = []
        for device in devices:
            tasks.append(ping_camera(gateway, device))

        results = await asyncio.gather(*tasks)

        print(results)
        time_end = time()
        time_to_wait = period - (time_end - time_start)
        logging.info(f"Coroutine finished in {time_end-time_start} sec.")
        if time_to_wait > 0:
            await asyncio.sleep(time_to_wait)


async def main():
    # Initialize gateway
    gateway = TBGatewayMqttClient(config.CUBA_URL, 1883, config.TB_GATEWAY_TOKEN)

    gateway.connect()
    gateway.gw_set_server_side_rpc_request_handler(handle_rpc)

    logging.info(f"Gateway connected on {config.CUBA_URL}")

    cameras = get_all_cameras()
    print(cameras)

    # Connect devices
    # await connect_devices(gateway, cameras, device_type=TB_DEVICE_PROFILE)

    # TODO: map cameras acc. to its ping time as key and id:camera list as value.
    periods = get_unique_ping_periods()
    for period in periods:
        cameras = get_cameras_by_ping_period(period)
        cameras_map[period] = {camera.id: camera for camera in cameras}

    # TODO: for every key:item run coroutine
    period_tasks = []
    for key, item in cameras_map.items():
        period_tasks.append(
            ping_cameras_list(gateway=gateway, period=key, devices=item.values())
        )
    await asyncio.gather(*period_tasks)

    # TODO: run a coroutine that will check if there were changes in DB via RPC


#     # Ping devices and send data to platform
#     while True:
#         curr_datetime = datetime.now()
#         curr_datetime -= timedelta(
#             seconds=curr_datetime.second, microseconds=curr_datetime.microsecond
#         )

#         if last_datetime == curr_datetime:
#             await asyncio.sleep(3)
#             continue

#         last_datetime = curr_datetime

#         # Initialize counter
#         global devices_connections_changed
#         devices_connections_changed = 0

#         loop_st = time()
#         try:
#             # Create tasks
#             tasks = []
#             for device in CAMERAS:
#                 tasks.append(
#                     send_device_connection_status(
#                         gateway, device["deviceName"], device["IP"], curr_datetime
#                     )
#                 )

#             # Waiting for tasks execution
#             results = await asyncio.gather(*tasks)

#             # Count active devices
#             total_devices = len(results)
#             active_devices = sum(results)
#             inactive_devices = total_devices - active_devices

#             totals_telemetry = {
#                 "total devices": total_devices,
#                 "active devices": active_devices,
#                 "inactive devices": inactive_devices,
#             }
#             # Send totals to platform
#             gateway.gw_send_telemetry(config.TB_TOTALS_DEVICE_NAME, totals_telemetry)
#         except Exception as e:
#             logging.critical(f"Error in main loop: {e}")

#         loop_et = time()
#         loop_exec_t = loop_et - loop_st
#         logging.info(f"Loop execution time: {loop_exec_t} seconds")
#         logging.info(f"Devices connections changed: {devices_connections_changed}")
#         await asyncio.sleep(4)

#     # Disconnect devices
#     await disconnect_devices(gateway, config.CAMERAS)
#     logging.info("Devices disconnected")

#     # Disconnect gateway
#     gateway.disconnect()
#     logging.info("Gateway disconnected")


if __name__ == "__main__":
    asyncio.run(main())
