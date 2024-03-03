from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Schedule(Base):
    __tablename__ = "x_schedule"

    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime(timezone=True), index=True)
    end_time = Column(DateTime(timezone=True), index=True)
    splatfest = Column(Boolean)
    mode = Column(String)
    stage_1_id = Column(Integer)
    stage_1_name = Column(String)
    stage_2_id = Column(Integer)
    stage_2_name = Column(String)

    __table_args__ = (
        UniqueConstraint(
            "start_time",
            "end_time",
            name="start_time_end_time_unique_x",
        )
    )


class Player(Base):
    __tablename__ = "players"

    primary_key = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(String, index=True)
    name = Column(String)
    name_id = Column(String)
    rank = Column(Integer)
    x_power = Column(Float, index=True)
    weapon = Column(String, index=True)
    weapon_id = Column(String, index=True)
    weapon_sub = Column(String, index=True)
    weapon_sub_id = Column(String, index=True)
    weapon_special = Column(String, index=True)
    weapon_special_id = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), index=True)
    mode = Column(String, index=True)
    region = Column(String, index=True)
    rotation_start = Column(DateTime(timezone=True), index=True)
    search_text = Column(String)
    season_number = Column(Integer)

    __table_args__ = (
        UniqueConstraint(
            "timestamp",
            "id",
            "mode",
            name="timestamp_id_mode_unique",
        ),
        Index(
            "idx_search_text_trgm",
            search_text,
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        )
    )

    name_name_id_idx = Index("name_name_id_idx", name, name_id)
    snapshot_idx = Index("snapshot_idx", timestamp, region, mode)
