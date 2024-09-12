from tb_rest_client.rest_client_pe import RestClientPE, DeviceId, EdgeId, EntityId

from database import (
    get_all_cameras,
    get_camera_by_name,
    create_camera,
    delete_camera,
    db_init,
)
import time

cameras = {

}

db_init()

for camera in cameras:
    create_camera(id=camera, name=f"Школьная камера {camera}", ip=camera)
