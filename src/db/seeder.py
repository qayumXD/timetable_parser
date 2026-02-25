import json
from pathlib import Path

from .database import get_connection


def seed_locations(json_path: str = "data/room_locations.json"):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    with get_connection() as conn:
        for code, info in data.items():
            conn.execute(
                """
                UPDATE rooms SET
                    building = ?,
                    floor = ?,
                    description = ?,
                    landmark = ?
                WHERE code = ?
                """,
                (
                    info.get("building"),
                    info.get("floor"),
                    info.get("description"),
                    info.get("landmark"),
                    code,
                ),
            )
        conn.commit()
    print(f"Seeded location data for {len(data)} rooms.")
