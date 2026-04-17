import orjson


def players_to_columnar(players: list[dict]) -> dict[str, list]:
    out: dict[str, list] = {}
    for player in players:
        for key, value in player.items():
            out.setdefault(key, []).append(value)
    return out


def serialize_leaderboard_payload(players: list[dict]) -> bytes:
    return orjson.dumps({"players": players_to_columnar(players)})
