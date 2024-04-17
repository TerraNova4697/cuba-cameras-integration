import asyncio
import logging
from time import time
from datetime import datetime

from tb_gateway_mqtt import TBGatewayMqttClient

import config

from database import (
    get_all_cameras,
    db_init,
    get_unique_ping_periods,
    get_cameras_by_ping_period,
    get_modified_cameras,
    flush_cameras_changes,
    update_ping_period,
    create_camera,
    get_camera_by_name,
    delete_camera,
)


db_init()
cameras_map = {}
coroutines_map = {}


def handle_rpc(gateway: TBGatewayMqttClient, request_body):
    logging.info(f"RPC: {request_body}")

    data = request_body["data"]
    method = data["method"]

    if method == "update_ping_period":
        device = request_body["device"]
        ping_period = data["params"]["seconds"]
        update_ping_period(device, ping_period)
        config.db_modified = True
        gateway.send_rpc_reply(str(data["id"]), True)
        logging.info("RPC acknowledged.")

    if method == "add_device":
        try:
            camera = create_camera(**data["params"])
            if cameras_map.get(camera.ping_period):
                cameras_map[camera.ping_period][camera.id] = camera
            else:
                cameras_map[camera.ping_period] = {}
                cameras_map[camera.ping_period][camera.id] = camera

        except Exception as e:
            logging.exception(f"Error while executing 'add_device': {e}")

    if method == "delete_device":
        try:
            camera = get_camera_by_name(data["params"]["name"])
            try:
                del cameras_map[camera.ping_period][camera.id]
            except AttributeError:
                pass

            delete_camera(data["params"]["id"])
        except Exception as e:
            logging.exception(f"Error while executing 'delete_device': {e}")


async def connect_devices(
    gateway: TBGatewayMqttClient, devices: list, device_type: str = "default"
):
    gateway.gw_connect_device("CAMERAS_TOTALS", "default")
    await asyncio.sleep(0.0001)
    for device in devices:
        gateway.gw_connect_device(device.name, device_type)
        await asyncio.sleep(0.0001)

    logging.info(f"{len(devices)} devices successfully connected")


async def disconnect_devices(gateway: TBGatewayMqttClient, devices: list):
    gateway.gw_disconnect_device("CAMERAS_TOTALS")
    await asyncio.sleep(0.0001)
    for device in devices:
        gateway.gw_disconnect_device(device["deviceName"])
        await asyncio.sleep(0.0001)


async def ping_camera(gateway, name, ip, ts):
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

        telemetry = {"online": connection_status}
        ts = datetime.timestamp(ts) * 1000
        data = [{"ts": ts, "values": telemetry}]

        gateway.gw_send_telemetry(name, data)

        # TODO: update camera values in BD

        # global devices_connections_changed
        # devices_connections_changed += 1

    except asyncio.exceptions.TimeoutError as e:
        logging.exception(f"Timeout while ping {e}")
    except Exception as e:
        error_msg = f"Error in getting device {name} ({ip}) connection: {e}"
        logging.error(error_msg)

    # return connection_status
    return connection_status, ip


async def ping_cameras_list(gateway, period):
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
        ts = datetime.now()

        devices = cameras_map.get(period, {}).values()

        if len(devices) == 0:
            await asyncio.sleep(period)

        tasks = []
        for device in devices:
            tasks.append(ping_camera(gateway, device.name, device.ip, ts))

        finished = await asyncio.gather(*tasks)

        results = []
        for task in finished:
            status, ip = task[0], task[1]
            config.cameras_online[ip] = status
            results.append(status)

        # print(results)
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


async def check_db(gateway):
    """Check if there are modified data in cameras table this coroutine will take them and add to common pool."""
    # Update cameras pinging strategy if there are changes in DB
    while True:
        # logging.info(cameras_map)
        logging.info(coroutines_map)

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

            for key in cameras_map.keys():
                if not coroutines_map.get(key):
                    coro = ping_cameras_list(gateway, key)
                    asyncio.create_task(coro)
                    coroutines_map[key] = coro

        logging.info("DB has been checked. Next iteration in 60 sec.")
        await asyncio.sleep(60)


async def report_total_cameras_online(gateway):
    await asyncio.sleep(120)
    while True:
        total = len(config.cameras_online)
        online = sum(config.cameras_online.values())
        offline = total - online

        gateway.gw_send_telemetry(
            config.TB_TOTALS_DEVICE_NAME,
            {
                "total devices": total,
                "active devices": online,
                "inactive devices": offline,
            },
        )

        await asyncio.sleep(60)


async def main():
    try:
        # Initialize gateway
        gateway = TBGatewayMqttClient(
            config.CUBA_URL,
            1883,
            config.TB_GATEWAY_TOKEN,
            client_id=config.TB_CLIENT_ID,
        )
        gateway.connect()
        gateway.gw_set_server_side_rpc_request_handler(handle_rpc)

        logging.info(f"Gateway connected on {config.CUBA_URL}")

        cameras = get_all_cameras()
        for camera in cameras:
            config.cameras_online[camera.ip] = 0

        # Connect devices
        await connect_devices(gateway, cameras, device_type=config.TB_DEVICE_PROFILE)

        # TODO: map cameras acc. to its ping time as key and id:camera list as value.
        periods = get_unique_ping_periods()
        for period in periods:
            cameras = get_cameras_by_ping_period(period)
            cameras_map[period] = {camera.id: camera for camera in cameras}

        for key in cameras_map.keys():
            logging.info(f"With period {key}: {len(cameras_map[key])} items.")

        # TODO: for every key:item run coroutine
        # period_tasks = []
        for key, item in cameras_map.items():
            coroutine = ping_cameras_list(gateway=gateway, period=key)
            # period_tasks.append(coroutine)
            coroutines_map[key] = coroutine

        # asyncio.create_task(update_ping())  # TODO: delete line.
        # TODO: run a coroutine that will check if there were changes in DB via RPC
        await asyncio.gather(
            *coroutines_map.values(),
            check_db(gateway),
            report_total_cameras_online(gateway),
        )

    except Exception as e:
        logging.exception(e)
    finally:
        await disconnect_devices(gateway, cameras)


if __name__ == "__main__":
    asyncio.run(main())
