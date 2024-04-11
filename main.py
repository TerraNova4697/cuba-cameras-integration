import asyncio
import logging
from time import time

from tb_gateway_mqtt import TBGatewayMqttClient

# from reference import send_device_connection_status
import config

from database import (
    get_all_cameras,
    db_init,
    get_unique_ping_periods,
    get_cameras_by_ping_period,
    get_modified_cameras,
    flush_cameras_changes,
    update_ping_period,
)


# log_fh = logging.FileHandler("info.log")
logging.basicConfig(
    format="%(asctime)s - %(lineno)s - %(levelname)s - %(message)s",
    filename="info.log",
    level=logging.INFO,
)


db_init()


cameras_map = {}
new_cameras = False


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


async def ping_camera(gateway, name, ip):
    """Ping device, send telemetry and save data.

    Args:
        gateway (TBGatewayMqttClient): Gateway to send data to.
        name (str): Name of the device.
        ip (str): IP of the address.

    Returns:
        _type_: _description_
    """
    connection_status = 0
    try:
        # Ping device
        process = await asyncio.create_subprocess_exec(
            "ping",
            "-c",
            config.PING_COUNT,
            "-i",
            config.PING_INTERVAL,
            ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.communicate()
        connection_status = 1 if process.returncode == 0 else 0

        # telemetry = {"online": connection_status}
        # gateway.gw_send_telemetry(device.name, telemetry)

        # TODO: update camera values in BD

        # global devices_connections_changed
        # devices_connections_changed += 1

    except asyncio.exceptions.TimeoutError as e:
        logging.exception(f"Timeout while ping {e}")
    except Exception as e:
        error_msg = f"Error in getting device {name} ({ip}) connection: {e}"
        logging.error(error_msg)

    # return connection_status
    return connection_status


async def ping_cameras_list(gateway, period, devices):
    """This coroutine creates tasks for each device and waits fot tasks to complete.
       Then sleeps for cetain amount of time.
       Works in loop.

    Args:
        gateway (TBGatewayMqttClient): Gateway to send data to.
        period (int): How often will cameras be pinged.
        devices (list): List of devices.
    """
    while True:
        time_start = time()

        tasks = []
        for device in devices:
            tasks.append(
                asyncio.create_task(ping_camera(gateway, device.name, device.ip))
            )

        results = []
        for task in tasks:
            await task
            results.append(task.result())

        print(results)
        time_end = time()
        time_to_wait = period - (time_end - time_start)
        logging.info(
            f"With period {period} ({len(devices)} items). Coroutine finished in {time_end-time_start} sec. \
            Next iteration in {time_to_wait} sec."
        )
        if time_to_wait > 0:
            await asyncio.sleep(time_to_wait)


async def update_ping():
    await asyncio.sleep(30)
    update_ping_period()
    config.db_modified = True


async def check_db():
    """Check if there are modified data in cameras table this coroutine will take them and add to common pool."""
    # Update cameras pinging strategy if there are changes in DB
    while True:

        if config.db_modified:
            modified_cameras = get_modified_cameras()
            logging.info(
                f"Updating camera pool with: {len(modified_cameras)} new items"
            )
            for camera in modified_cameras:
                try:
                    del cameras_map[camera.prev_ping_period][camera.id]
                except Exception:
                    pass
                if cameras_map.get(camera.ping_period):
                    cameras_map[camera.ping_period][camera.id] = camera
                else:
                    cameras_map[camera.ping_period] = {}
                    cameras_map[camera.ping_period][camera.id] = camera
                camera.status = 0
            flush_cameras_changes(modified_cameras)
            config.db_modified = False

        logging.info("DB has been checked. Next iteration in 60 sec.")
        await asyncio.sleep(60)


async def main():
    # Initialize gateway
    gateway = TBGatewayMqttClient(
        config.CUBA_URL, 1883, config.TB_GATEWAY_TOKEN, client_id=config.TB_CLIENT_ID
    )
    gateway.connect()
    gateway.gw_set_server_side_rpc_request_handler(handle_rpc)

    logging.info(f"Gateway connected on {config.CUBA_URL}")

    cameras = get_all_cameras()

    # Connect devices
    # await connect_devices(gateway, cameras, device_type=TB_DEVICE_PROFILE)

    # TODO: map cameras acc. to its ping time as key and id:camera list as value.
    periods = get_unique_ping_periods()
    for period in periods:
        cameras = get_cameras_by_ping_period(period)
        cameras_map[period] = {camera.id: camera for camera in cameras}

    for key in cameras_map.keys():
        logging.info(f"With period {key}: {len(cameras_map[key])} items.")

    # TODO: for every key:item run coroutine
    period_tasks = []
    for key, item in cameras_map.items():
        period_tasks.append(
            ping_cameras_list(gateway=gateway, period=key, devices=item.values())
        )

    asyncio.create_task(update_ping())
    results = await asyncio.gather(*period_tasks, check_db())
    print(results)
    # print(
    #     f"{time() - start}",
    #     f"online {sum(results)}",
    #     f"offline {len(results) - sum(results)}",
    # )

    # TODO: run a coroutine that will check if there were changes in DB via RPC


if __name__ == "__main__":
    asyncio.run(main())
