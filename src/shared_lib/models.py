import uuid

from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, INET, JSONB
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
        Index("idx_players_splashtag_gin", "splashtag"),
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
        Index(
            "idx_players_player_id_splashtag",
            "player_id",
            "splashtag",
        ),
        {"schema": "xscraper"},
    )


class PlayerLatest(Base):
    __tablename__ = "player_latest"

    player_id = Column(String, primary_key=True)
    mode = Column(
        ENUM(
            "Splat Zones",
            "Clam Blitz",
            "Rainmaker",
            "Tower Control",
            name="mode_name",
        ),
        primary_key=True,
    )
    timestamp = Column(DateTime(timezone=True))
    last_updated = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_player_latest_player_id_mode", "player_id", "mode"),
        {"schema": "xscraper"},
    )


class PlayerSeason(Base):
    __tablename__ = "player_season"

    player_id = Column(String, primary_key=True)
    region = Column(Boolean, nullable=False)
    season_number = Column(Integer, primary_key=True)

    __table_args__ = (
        Index("idx_player_season_player_id", "player_id"),
        Index("idx_player_season_season_number", "season_number"),
        Index(
            "idx_player_season_player_id_season_number",
            "player_id",
            "season_number",
        ),
        {"schema": "xscraper"},
    )


class SeasonResults(Base):
    __tablename__ = "season_results"

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
    season_number = Column(Integer)

    __table_args__ = (
        Index("idx_season_results_player_id", "player_id"),
        Index("idx_season_results_splashtag", "splashtag"),
        Index("idx_season_results_mode", "mode"),
        Index("idx_season_results_region", "region"),
        Index("idx_season_results_season_number", "season_number"),
        Index("idx_season_results_mode_season_number", "mode", "season_number"),
        Index(
            "idx_season_results_player_id_mode_season_number",
            "player_id",
            "mode",
            "season_number",
        ),
        {"schema": "xscraper"},
    )


class Aliases(Base):
    __tablename__ = "aliases"

    player_id = Column(String, primary_key=True)
    splashtag = Column(
        String,
        primary_key=True,
    )
    last_seen = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_aliases_player_id", "player_id"),
        Index("idx_aliases_splashtag", "splashtag"),
        {"schema": "xscraper"},
    )


class WeaponLeaderboard(Base):
    __tablename__ = "weapon_leaderboard"

    player_id = Column(String, primary_key=True, nullable=False)
    season_number = Column(Integer, primary_key=True, nullable=False)
    mode = Column(
        ENUM(
            "Splat Zones",
            "Clam Blitz",
            "Rainmaker",
            "Tower Control",
            name="mode_name",
        ),
        primary_key=True,
        nullable=False,
    )
    region = Column(Boolean, primary_key=True, nullable=False)
    weapon_id = Column(Integer, primary_key=True, nullable=False)
    max_x_power = Column(Float, nullable=False)
    games_played = Column(Integer, nullable=False)
    percent_games_played = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_weapon_leaderboard_player_id", "player_id"),
        Index("idx_weapon_leaderboard_season_number", "season_number"),
        Index("idx_weapon_leaderboard_mode", "mode"),
        Index("idx_weapon_leaderboard_region", "region"),
        Index("idx_weapon_leaderboard_weapon_id", "weapon_id"),
        {"schema": "xscraper"},
    )


class ModelInferenceLog(Base):
    __tablename__ = "model_inference_logs"
    __table_args__ = {"schema": "splatgpt"}

    id = Column(BigInteger, primary_key=True)
    request_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    timestamp = Column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    ip_address = Column(INET)
    user_agent = Column(Text)
    http_method = Column(String)
    endpoint = Column(String)
    client_id = Column(String)
    input_data = Column(JSONB)
    model_version = Column(String)
    processing_time_ms = Column(Integer)
    inference_time_ms = Column(Integer)
    status_code = Column(SmallInteger)
    output_data = Column(JSONB)
    error_message = Column(Text)
