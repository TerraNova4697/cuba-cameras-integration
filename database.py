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
    with Session(engine, expire_on_commit=False) as session:
        return session.scalars(select(Camera)).all()


def get_unique_ping_periods():
    with Session(engine, expire_on_commit=False) as session:
        return session.scalars(select(Camera.ping_period)).unique().all()


def get_cameras_by_ping_period(ping_period):
    with Session(engine, expire_on_commit=False) as session:
        return session.scalars(
            select(Camera).where(Camera.ping_period == ping_period)
        ).all()


def get_modified_cameras():
    with Session(engine, expire_on_commit=False) as session:
        return session.scalars(select(Camera).where(Camera.status == 1)).all()


def flush_cameras_changes(cameras):
    if cameras:
        with Session(engine, expire_on_commit=False) as session:
            session.add_all(cameras)
            session.commit()


def update_ping_period(camera_name, new_ping_period):
    try:
        with Session(engine, expire_on_commit=False) as session:
            camera = session.scalar(select(Camera).where(Camera.name == camera_name))
            camera.prev_ping_period = camera.ping_period
            camera.ping_period = new_ping_period
            camera.status = 1

            session.add(camera)
            session.commit()
            return True
    except Exception as e:
        logging.exception(f"Error while updating camera: {e}")
        return False


def create_camera(**kwargs):
    try:
        with Session(engine, expire_on_commit=False) as session:
            camera = Camera(**kwargs)
            session.add(camera)
            session.commit()
            logging.info(
                f"new camera in {__file__}: {camera.name}, {camera.ping_period}"
            )
            return camera
    except IntegrityError as e:
        logging.exception(f"Error while fetching camera: {e}")


def get_camera_by_name(name):
    try:
        with Session(engine, expire_on_commit=False) as session:
            return session.scalar(select(Camera).where(Camera.name == name))
    except Exception as e:
        logging.exception(f"Error while fetching camera: {e}")


def update_camera(camera):
    try:
        with Session(engine, expire_on_commit=False) as session:
            session.add(camera)
            session.commit()
            return True
    except Exception as e:
        logging.exception(f"Error while updating camera: {e}")
        return False


def delete_camera(camera):
    try:
        with Session(engine, expire_on_commit=False) as session:
            session.delete(camera)
            session.commit()
            return True
    except Exception as e:
        logging.exception(f"Error while deleting camera: {e}")
        return False


def update_ping_period_dev():
    with Session(engine, expire_on_commit=False) as session:
        session.execute(
            update(Camera).values({"ping_period": 60, "status": 0}).where(Camera.id)
        )
        session.commit()
