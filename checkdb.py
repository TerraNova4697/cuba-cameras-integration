import csv
from database import engine
from sqlalchemy.orm import Session
from database import db_init, get_camera_by_name, get_all_cameras, create_camera  # noqa
import json


db_init()

cameras = get_all_cameras()
print(len(cameras))


with open("list.csv", "r") as cameras_list:
    with Session(engine) as session:
        reader = csv.reader(cameras_list)
        lack_rows = []
        for row in reader:
            if row[2] != "UUID":
                camera = get_camera_by_name(row[0])
                if not camera:
                    print(row[0], row[2], row[4])
                    lack_rows.append(
                        {"name": row[0], "id": row[2], "ip": row[5], "ping_period": 60}
                    )
        with open("data.json", "w") as f:
            json.dump(lack_rows, f, ensure_ascii=False, indent=2)
        print(len(lack_rows))


# with open("data.json") as f:
#     data = json.load(f)

#     for item in data:
#         create_camera(**item)
