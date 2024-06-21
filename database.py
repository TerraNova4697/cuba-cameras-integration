"""
Here is implemented database connection and all the DML interaction with Database.
"""

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from models import Base, Camera
from sqlite3 import IntegrityError
from typing import Sequence
import logging


engine = create_engine("sqlite:///db.sqlite")

session = Session(engine, expire_on_commit=True, autoflush=False)


def db_init():
    Base.metadata.create_all(engine)


def get_all_cameras() -> Sequence:
    """Get all cameras in DB.

    Returns:
        Sequence: List of cameras.
    """
    with Session(engine, expire_on_commit=False) as session:
        return session.scalars(select(Camera)).all()


def get_unique_ping_periods() -> Sequence:
    """Get unique values of Camera.ping_period.

    Returns:
        Sequence: List of Camera.ping_period.
    """
    with Session(engine, expire_on_commit=False) as session:
        return session.scalars(select(Camera.ping_period)).unique().all()


def get_cameras_by_ping_period(ping_period: int) -> Sequence:
    """Get list of cameras with given ping_period.

    Args:
        ping_period (int): ping period of camera.

    Returns:
        Sequence: List of Cameras.
    """
    with Session(engine, expire_on_commit=False) as session:
        return session.scalars(
            select(Camera).where(Camera.ping_period == ping_period)
        ).all()


def get_modified_cameras() -> Sequence:
    """Get all recently modified cameras (Camera is modified if Camera.status == 1).

    Returns:
        Sequence: List of Cameras.
    """
    with Session(engine, expire_on_commit=False) as session:
        return session.scalars(select(Camera).where(Camera.status == 1)).all()


def flush_cameras_changes(cameras: list[Camera]) -> None:
    """Sets Camera.status = 0 for all given cameras.

    Args:
        cameras (list[Camera]): List of Cameras.
    """
    if cameras:
        with Session(engine, expire_on_commit=False) as session:
            session.add_all(cameras)
            session.commit()


def update_ping_period(camera_name: str, new_ping_period: int) -> bool:
    """Set Camera.ping_period for given camera on a given ping period.

    Args:
        camera_name (str): Camera.name
        new_ping_period (int): New ping period to be set.add

    Returns:
        bool: returns True if update was successful. False otherwise.
    """
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


def create_camera(**kwargs) -> Camera | None:
    """Creates new camera. Returns new Camera from DB if cuccessful, None otherwise.

    Returns:
        Camera: Newly created camera.
    """
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


def get_camera_by_name(name: str) -> Camera | None:
    """
    Fetch camera with given name if exists. Return None otherwise.

    Args:
        name (str): Camera.name.

    Returns:
        Camera | None: Either newly created Camera or None object.
    """
    try:
        with Session(engine, expire_on_commit=False) as session:
            return session.scalar(select(Camera).where(Camera.name == name))
    except Exception as e:
        logging.exception(f"Error while fetching camera: {e}")


def get_camera_by_id(id: str) -> Camera | None:
    """
    Fetch camera with given id if exists. Return None otherwise.

    Args:
        id (str): Camera.id.

    Returns:
        Camera | None: Either newly created Camera or None object.
    """
    try:
        with Session(engine, expire_on_commit=False) as session:
            return session.scalar(select(Camera).where(Camera.id == id))
    except Exception as e:
        logging.exception(f"Error while fetching camera: {e}")


def update_camera(camera: Camera) -> bool:
    """Update given camera.

    Args:
        camera (Camera): Camera object.

    Returns:
        bool: Returns True if successful. False otherwise.
    """
    try:
        with Session(engine, expire_on_commit=False) as session:
            session.add(camera)
            session.commit()
            return True
    except Exception as e:
        logging.exception(f"Error while updating camera: {e}")
        return False


def delete_camera(camera: Camera) -> bool:
    """Delete given camera.

    Args:
        camera (Camera): Camera object

    Returns:
        bool: Returns True if successful. False otherwise.
    """
    try:
        with Session(engine, expire_on_commit=False) as session:
            session.delete(camera)
            session.commit()
            return True
    except Exception as e:
        logging.exception(f"Error while deleting camera: {e}")
        return False


def update_ping_period_dev() -> None:
    """Set Camera.ping_period for cameras.
    Development use only.
    """
    with Session(engine, expire_on_commit=False) as session:
        session.execute(
            update(Camera).values({"ping_period": 60, "status": 0}).where(Camera.id)
        )
        session.commit()
