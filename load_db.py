import csv
from models import Camera
from database import engine
from sqlalchemy.orm import Session
import json
from database import create_camera


# with open("list.csv", "r") as cameras_list:
#     with Session(engine) as session:
#         reader = csv.reader(cameras_list)
#         for row in reader:
#             if row[2] != "UUID":
#                 session.add(Camera(name=row[0], id=row[2], ip=row[4]))
#                 print(f"Title: {row[0]}; UUID: {row[2]}; IP: {row[4]}")
#         session.commit()


with open("data.json") as f:
    data = json.load(f)

    for item in data:
        try:
            create_camera(**item)
        except Exception as e:
            print(e)
