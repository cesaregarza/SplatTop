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
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Schedule(Base):
    __tablename__ = "schedules"

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
            name="start_time_end_time_unique",
        ),
    )


class Player(Base):
    __tablename__ = "players"

    player_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    name_id = Column(String, nullable=False)
    splashtag = Column(
        String,
        unique=True,
        nullable=False,
    )
    rank = Column(Integer, nullable=False)
    x_power = Column(Float, nullable=False)
    weapon_id = Column(Integer, nullable=False)
    nameplate_id = Column(Integer, nullable=False)
    byname = Column(String)
    text_color = Column(String)
    badge_left_id = Column(Integer)
    badge_center_id = Column(Integer)
    badge_right_id = Column(Integer)
    timestamp = Column(DateTime(timezone=True), primary_key=True)
    mode = Column(
        ENUM(
            "Splat Zones",
            "Clam Blitz",
            "Rainmaker",
            "Tower Control",
            name="mode_name",
        )
    )
    region = Column(Boolean, nullable=False)
    rotation_start = Column(DateTime(timezone=True))
    season_number = Column(Integer)
    updated = Column(Boolean)

    __table_args__ = (
        Index("idx_players_splashtag", "splashtag"),
        Index("idx_players_timestamp", "timestamp"),
        Index("idx_players_mode", "mode"),
        Index("idx_players_region", "region"),
        Index("idx_players_rotation_start", "rotation_start"),
        Index("idx_players_season_number", "season_number"),
        Index(
            "idx_players_mode_timestamp_season_number",
            "mode",
            "timestamp",
            "season_number",
        ),
        {"schema": "xscraper"},
    )
