from src.db.database import get_connection


def resolve_room(room_code: str) -> dict:
    """
    Returns human-readable location info for a room code.
    Returns a dict with all location fields, or minimal info if not seeded yet.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM rooms WHERE code = ?",
            (room_code,),
        ).fetchone()

    if not row:
        return {"code": room_code, "description": "Location not found"}

    location = dict(row)

    parts = []
    if location.get("building"):
        parts.append(location["building"])
    if location.get("floor") is not None:
        floor_label = {1: "Ground floor", 2: "2nd floor", 3: "3rd floor"}.get(
            location["floor"], f"Floor {location['floor']}"
        )
        parts.append(floor_label)
    if location.get("description"):
        parts.append(location["description"])
    if location.get("landmark"):
        parts.append(f"Landmark: {location['landmark']}")

    location["human_readable"] = " - ".join(parts) if parts else room_code
    return location
