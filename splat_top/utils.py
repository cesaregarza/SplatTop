import datetime as dt


def get_seasons(now_date: dt.datetime) -> list[tuple[dt.datetime, str]]:
    # Earliest season is 2022-09-01
    first_season = dt.datetime(2022, 9, 1)
    seasons_dict = {
        3: "Fresh",
        6: "Sizzle",
        9: "Drizzle",
        12: "Chill",
    }
    # Generate all seasons from 2022-09-01 to now
    return [
        (dt.datetime(year, month, 1), f"{seasons_dict[month]} Season {year}")
        for year in range(2022, now_date.year + 1)
        for month in seasons_dict.keys()
        if dt.datetime(year, month, 1) >= first_season
        and (
            year < now_date.year
            or (year == now_date.year and month <= now_date.month)
        )
    ]
