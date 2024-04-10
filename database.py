from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Base, Camera


engine = create_engine("sqlite:///db.sqlite", echo=True)


def db_init():
    Base.metadata.create_all(engine)


def get_all_cameras():
    with Session(engine) as session:
        return session.scalars(select(Camera)).all()


def get_unique_ping_periods():
    with Session(engine) as session:
        return session.scalars(select(Camera.ping_period)).unique().all()


def get_cameras_by_ping_period(ping_period):
    with Session(engine) as session:
        return session.scalars(
            select(Camera).where(Camera.ping_period == ping_period)
        ).all()
