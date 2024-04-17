from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from models import Base, Camera
from sqlite3 import IntegrityError
import logging


engine = create_engine("sqlite:///db.sqlite")

session = Session(engine, expire_on_commit=True, autoflush=False)


def db_init():
    Base.metadata.create_all(engine)


def get_all_cameras():
    return session.scalars(select(Camera)).all()


def get_unique_ping_periods():
    return session.scalars(select(Camera.ping_period)).unique().all()


def get_cameras_by_ping_period(ping_period):
    return session.scalars(
        select(Camera).where(Camera.ping_period == ping_period)
    ).all()


def get_modified_cameras():
    return session.scalars(select(Camera).where(Camera.status == 1)).all()


def flush_cameras_changes(cameras):
    if cameras:
        session.add_all(cameras)
        session.commit()


def update_ping_period(camera_name, new_ping_period):
    camera = session.scalar(select(Camera).where(Camera.name == camera_name))
    camera.prev_ping_period = camera.ping_period
    camera.ping_period = new_ping_period
    camera.status = 1

    session.add(camera)
    session.commit()


def create_camera(**kwargs):
    try:
        camera = Camera(**kwargs)
        session.add(camera)
        session.commit()
        return camera
    except IntegrityError:
        session.rollback()


def get_camera_by_id(name):
    try:
        return session.scalar(select(Camera).where(Camera.name == name))
    except Exception as e:
        logging.exception(f"Error while fetching camera: {e}")


def delete_camera(camera):
    try:
        session.delete(camera)
        session.commit()
    except Exception as e:
        logging.exception(f"Error while deleting camera: {e}")


# def get():
#     return session.scalars(
#         select(Camera).where(
#             Camera.id.in_(
#                 (
#                     "005003-04_P",
#                     "005005-04_P",
#                     "005006-05_P",
#                     "005007-04_P",
#                     "005010-03_P",
#                     "005012-05_P",
#                     "005014-07_P",
#                 )
#             )
#         )
#     ).all()


def update_ping_period_dev():

    session.execute(
        update(Camera)
        .values({"ping_period": 60, "status": 0})
        .where(
            Camera.id
            # Camera.id.in_(
            #     (
            #         "005003-04_P",
            #         "005005-04_P",
            #         "005006-05_P",
            #         "005007-04_P",
            #         "005010-03_P",
            #         "005012-05_P",
            #         "005014-07_P",
            #     )
            # )
        )
    )

    # session.commit(
    #     session.query(
    #         update(Camera)
    #         .where(
    #             Camera.id.in_(
    #                 (
    #                     "005003-04_P",
    #                     "005005-04_P",
    #                     "005006-05_P",
    #                     "005007-04_P",
    #                     "005010-03_P",
    #                     "005012-05_P",
    #                     "005014-07_P",
    #                 )
    #             )
    #         )
    #         .values(ping_period=30)
    #         .returning(Camera.ping_period)
    #     )
    # )
    session.commit()
