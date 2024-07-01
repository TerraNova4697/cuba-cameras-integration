"""
This module is the entry point of the programm. It checks which camera from the given list is online.
"""

import asyncio
import logging
from time import time
from datetime import datetime, timedelta

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
    update_camera,
)


db_init()
cameras_map = {}
coroutines_map = {}


def handle_rpc(gateway: TBGatewayMqttClient, request_body: dict) -> None:
    """Callback for handling all RPC's from platform.

    Args:
        gateway (TBGatewayMqttClient): Gateway to send RPC replies to.
        request_body (dict): Request body.
    """

    logging.info(f"RPC: {request_body}")

    # Parse data from the RPC message
    data = request_body["data"]
    method = data["method"]
    device = request_body["device"]
    request_id = str(data["id"])

    # Handle RPC according to method name
    if method == "update_ping_period":
        try:

            # Get new ping period and update device
            ping_period = data["params"]["seconds"]
            res = update_ping_period(device, ping_period)

            # If successfully updated, update db status and send RPC reply "successful"
            if res:
                config.db_modified = True
                gateway.gw_send_rpc_reply(device, request_id, True)
                logging.info("RPC acknowledged.")
            # Else send RPC reply "unsuccessful"
            else:
                gateway.gw_send_rpc_reply(device, request_id, False)
        except Exception as e:
            logging.exception(f"Error while executing 'update_ping_period': {e}")

    if method == "add_device":
        try:

            # Create new device
            camera = create_camera(**data["params"])
            if camera:
                logging.info(
                    f"new camera in {__file__}: {camera.name}, {camera.ping_period}"
                )

                # Put new camera in the pool with it's ping period. If there is no such, create.
                if cameras_map.get(camera.ping_period):
                    cameras_map[camera.ping_period][camera.id] = camera
                else:
                    cameras_map[camera.ping_period] = {}
                    cameras_map[camera.ping_period][camera.id] = camera

                # Send RPC reply "successful"
                gateway.gw_send_rpc_reply(device, request_id, True)
            else:
                # Send RPC reply "unsuccessful"
                gateway.gw_send_rpc_reply(device, request_id, False)

        except Exception as e:
            logging.exception(f"Error while executing 'add_device': {e}")

    if method == "delete_device":
        try:
            # Get camera from DB
            camera = get_camera_by_name(data["params"]["name"])

            # If there is such, delete it from cameras pool and DB
            if camera:
                try:
                    del cameras_map[camera.ping_period][camera.id]
                except AttributeError:
                    pass

                res = delete_camera(camera)

                # If camera deleted, send RPC reply "successful"
                if not res:
                    gateway.gw_send_rpc_reply(device, request_id, False)
                    return

            # If camera not found, send RPC reply "unsuccessful"
            gateway.gw_send_rpc_reply(device, request_id, True)
        except Exception as e:
            logging.exception(f"Error while executing 'delete_device': {e}")

    if method == "update_device":
        try:

            # Get camera from DB
            camera = get_camera_by_name(data["params"]["name"])
            if camera:

                # Delete old camera from corresponding cameras pool
                try:
                    del cameras_map[camera.ping_period][camera.id]
                except AttributeError:
                    pass

                # Update camera parameters and save to DB
                camera.id = data["params"]["id"]
                camera.ip = data["params"]["ip"]
                camera.name = data["params"]["newName"]
                res = update_camera(camera)

                # If successful, put camera in corresponding cameras pool and send RPC reply "successful".
                # Otherwise "unsuccessful"
                if res:
                    cameras_map[camera.ping_period][camera.id] = camera
                    gateway.gw_send_rpc_reply(device, request_id, True)
                else:
                    gateway.gw_send_rpc_reply(device, request_id, False)

            # If camera not found in DB, send RPC reply "unsuccessful"
            else:
                gateway.gw_send_rpc_reply(device, request_id, False)

        except Exception as e:
            logging.exception(f"Error while executing 'update_device': {e}")


async def connect_devices(
    gateway: TBGatewayMqttClient, devices: list, device_type: str = "default"
) -> None:
    """Connect given devices to platform.

    Args:
        gateway (TBGatewayMqttClient): Gateway.
        devices (list): List of devices.
        device_type (str, optional): Type of device. Defaults to "default".
    """
    gateway.gw_connect_device("CAMERAS_TOTALS", "default")
    await asyncio.sleep(0.0001)
    for device in devices:
        gateway.gw_connect_device(device.name, device_type)
        await asyncio.sleep(0.0001)

    logging.info(f"{len(devices)} devices successfully connected")


async def disconnect_devices(gateway: TBGatewayMqttClient, devices: list) -> None:
    """Disconnect given devices from platform.

    Args:
        gateway (TBGatewayMqttClient): Gateway.
        devices (list): List of devices.
    """
    gateway.gw_disconnect_device("CAMERAS_TOTALS")
    await asyncio.sleep(0.0001)
    for device in devices:
        gateway.gw_disconnect_device(device.name)
        await asyncio.sleep(0.0001)


async def ping_camera(
    gateway: TBGatewayMqttClient, name: str, ip: str, ts: int
) -> tuple:
    """Ping device, send telemetry and save data.

    Args:
        gateway (TBGatewayMqttClient): Gateway to send data to.
        name (str): Device name.
        ip (str): Device IP.
        ts (int): Timestamp when operation was executed. Sent to platform as timeseries timestamp.

    Returns:
        tuple: Cameras current connection status and it's IP.
    """

    connection_status = 0
    try:
        # Ping device
        creating_process = datetime.now()
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
        new_time = datetime.now()
        if (new_time - creating_process) > timedelta(seconds=30):
            logging.info(
                f"Creating process took {datetime.now() - creating_process} sec"
            )
        await process.communicate()
        connection_status = 1 if process.returncode == 0 else 0

        # Form telemetry with timestamp
        telemetry = {"online": connection_status}
        ts = datetime.timestamp(ts) * 1000
        data = [{"ts": ts, "values": telemetry}]

        # Send telemetry
        gateway.gw_send_telemetry(name, data)

        # TODO: update camera values in BD

        # global devices_connections_changed
        # devices_connections_changed += 1

    except asyncio.exceptions.TimeoutError as e:
        logging.exception(f"Timeout while ping {e}")
    except Exception as e:
        error_msg = f"Error in getting device {name} ({ip}) connection: {e}"
        logging.error(error_msg)

    # Return cameras current connection status and it's IP.
    return connection_status, ip


async def ping_cameras_list(gateway: TBGatewayMqttClient, period: int) -> None:
    """This coroutine creates tasks for each device and waits for tasks to complete.
       Then sleeps for cetain amount of time.
       Works in loop.

    Args:
        gateway (TBGatewayMqttClient): Gateway.
        period (int): Ping period.
    """
    ts = datetime.now()

    while True:
        # All telemetry will be sent with same timestamp, which is created at this point.
        time_start = time()

        # Get cameras with given ping period from cameras pool.
        devices = cameras_map.get(period, {}).values()

        # If there is no devices with given ping period, suspend.
        if len(devices) == 0:
            await asyncio.sleep(period)

        # Create task of camera ping for every device.
        creating_coros = datetime.now()
        tasks = []
        for device in devices:
            tasks.append(ping_camera(gateway, device.name, device.ip, ts))
        logging.info(f"Creating coros took {datetime.now() - creating_coros} sec")

        # Wait for every task to be completed.
        gatehring_tasks = datetime.now()
        finished = await asyncio.gather(*tasks)
        logging.info(f"implementing coros took {datetime.now() - gatehring_tasks} sec")

        # Update amount of cameras online and collect camera's statuses in list.
        updating = datetime.now()
        results = []
        for task in finished:
            status, ip = task[0], task[1]
            config.cameras_online[ip] = status
            results.append(status)
        logging.info(f"Updating took {datetime.now() - updating} sec")

        # Calculate time to wait till next iteration and suspend coroutine.
        # If time to wait is less than 0, restart iteration immediately.
        time_end = time()
        time_to_wait = period - (time_end - time_start)
        logging.info(
            f"With period {period} ({len(devices)} items). Coroutine finished in {time_end-time_start} sec. \
            Next iteration in {time_to_wait} sec."
        )
        ts += timedelta(seconds=period)
        if time_to_wait > 0 and ts > datetime.now():
            await asyncio.sleep(time_to_wait)


async def check_db(gateway: TBGatewayMqttClient) -> None:
    """Check if there are modified data in cameras table. This coroutine will take them and add to common pool.

    Args:
        gateway (TBGatewayMqttClient): Gateway.
    """
    # Update cameras pinging strategy if there are changes in DB.
    while True:
        # logging.info(cameras_map)
        logging.info(coroutines_map)

        # Check if there are changes in DB. Suspend otherwise.
        if config.db_modified:

            # Get all newly modified cameras from DB.
            modified_cameras = get_modified_cameras()
            logging.info(
                f"Updating camera pool with: {len(modified_cameras)} new items"
            )

            # Delete every modified camera from corresponding cameras pool if ping period was modified.
            # Put camera in it's cameras pool if it exists.
            # If not, create the pool and put camera in it.
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

            # Flush cameras modified status after we implemented all the logic.
            flush_cameras_changes(modified_cameras)
            config.db_modified = False

            # Make sure every camera pool gets handled in it's asyncronous task.
            # If there is no task for some camera pool, create and run it.
            for key in cameras_map.keys():
                if not coroutines_map.get(key):
                    coro = ping_cameras_list(gateway, key)
                    asyncio.create_task(coro)
                    coroutines_map[key] = coro

        logging.info("DB has been checked. Next iteration in 60 sec.")
        await asyncio.sleep(60)


async def report_total_cameras_online(gateway: TBGatewayMqttClient) -> None:
    """Send data of how many cameras are currently online and offline.

    Args:
        gateway (TBGatewayMqttClient): Gateway.
    """

    # Should be started with suspention.
    await asyncio.sleep(120)
    while True:

        # Calculate online, offline and total count of cameras.
        total = len(config.cameras_online)
        online = sum(config.cameras_online.values())
        offline = total - online

        # Send data on platform.
        gateway.gw_send_telemetry(
            config.TB_TOTALS_DEVICE_NAME,
            {
                "total devices": total,
                "active devices": online,
                "inactive devices": offline,
            },
        )

        # Suspend iteration.
        await asyncio.sleep(60)


async def main() -> None:
    """Programm main entry."""
    try:
        # Initialize and connect gateway.
        gateway = TBGatewayMqttClient(
            config.CUBA_URL,
            1883,
            config.TB_GATEWAY_TOKEN,
            client_id=config.TB_CLIENT_ID,
        )
        gateway.connect()

        # Add callback to handle RPC's from platform.
        gateway.gw_set_server_side_rpc_request_handler(handle_rpc)

        logging.info(f"Gateway connected on {config.CUBA_URL}")

        # Get all cameras from DB. Map their current status.
        cameras = get_all_cameras()
        for camera in cameras:
            config.cameras_online[camera.ip] = 0

        # Connect devices
        await connect_devices(gateway, cameras, device_type=config.TB_DEVICE_PROFILE)

        # Map cameras acc. to its ping time as key and id:camera list as value.
        periods = get_unique_ping_periods()
        for period in periods:
            cameras = get_cameras_by_ping_period(period)
            cameras_map[period] = {camera.id: camera for camera in cameras}

        for key in cameras_map.keys():
            logging.info(f"With period {key}: {len(cameras_map[key])} items.")

        # For every key:item initialize coroutine. Map them by ping period.
        for key, item in cameras_map.items():
            coroutine = ping_cameras_list(gateway=gateway, period=key)
            coroutines_map[key] = coroutine

        # Run all coroutines.
        # TODO: run a coroutine that will check if there were changes in DB via RPC
        await asyncio.gather(
            # Coroutines list, that pings cameras.
            *coroutines_map.values(),
            # Coroutine, that checks if DB was modified and applies needed logic if necessary.
            check_db(gateway),
            # Coroutine that sends telemetry of devices count online, devices count offline, devices count total.
            # report_total_cameras_online(gateway),
        )

    except Exception as e:
        logging.exception(e)
    finally:
        await disconnect_devices(gateway, cameras)


if __name__ == "__main__":
    asyncio.run(main())
