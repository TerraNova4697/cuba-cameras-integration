import csv
from models import Camera
from database import engine
from sqlalchemy.orm import Session


with open("list.csv", "r") as cameras_list:
    with Session(engine) as session:
        reader = csv.reader(cameras_list)
        for row in reader:
            if row[2] != "UUID":
                session.add(Camera(name=row[0], id=row[2], ip=row[4]))
                print(f"Title: {row[0]}; UUID: {row[2]}; IP: {row[4]}")
        session.commit()
