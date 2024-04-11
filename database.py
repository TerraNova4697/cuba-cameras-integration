from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from models import Base, Camera


engine = create_engine("sqlite:///db.sqlite", echo=True)

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


def update_ping_period():

    session.execute(
        update(Camera)
        .values({"ping_period": 30, "status": 1})
        .where(
            Camera.id.in_(
                (
                    "005003-04_P",
                    "005005-04_P",
                    "005006-05_P",
                    "005007-04_P",
                    "005010-03_P",
                    "005012-05_P",
                    "005014-07_P",
                )
            )
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
