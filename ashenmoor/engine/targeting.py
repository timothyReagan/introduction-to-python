"""
ashenmoor.engine.targeting
──────────────────────────
Keyword-based targeting system.

Any command that needs to resolve a player's target string into a live
object, mob, or character calls find_target().

Target string format
────────────────────
  "marker"      first thing in the room whose keywords include "marker"
  "2.marker"    second such thing
  "1.marker"    same as "marker" — explicit index 1
  "guardian"    first mob/character whose name or keywords match "guardian"

Search order within the room (consistent, predictable)
───────────────────────────────────────────────────────
  1. Mobs        (room.mobs list, in order)
  2. Characters  (players currently in the room, from locations dict)
  3. Objects     (room.objects list, in order)

This order means combat targets (mobs, players) are always found before
items on the ground, which matches player expectations.

A mob or object matches if *keyword* appears in its .key_words tuple.
A character matches if *keyword* appears anywhere in their .name (case-insensitive).

Returns
───────
  The matched instance (Mob, Character, Object/Item/Weapon) or None.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..world.room     import Room
    from ..core.character import Character


def parse_target(s: str) -> tuple[int, str]:
    """
    Split a target string into (index, keyword).

    "marker"    -> (1, "marker")
    "2.marker"  -> (2, "marker")
    "1.guardian"-> (1, "guardian")

    Index is 1-based (1 = first match).
    """
    s = s.strip().lower()
    if "." in s:
        prefix, _, keyword = s.partition(".")
        if prefix.isdigit():
            idx = int(prefix)
            return (max(1, idx), keyword.strip())
    return (1, s)


def find_target(
    target_str:  str,
    room:        "Room",
    locations:   dict[str, int]         | None = None,
    characters:  dict[str, "Character"] | None = None,
) -> object | None:
    """
    Resolve a target string to a live instance in the room.

    Parameters
    ----------
    target_str  : str
        Raw target word from player input, e.g. "marker", "2.student", "guardian".
    room        : Room
        The room to search.
    locations   : dict[str, int] | None
        character_name -> room_number.  Required to find player characters.
    characters  : dict[str, Character] | None
        character_name -> Character.  Required to find player characters.

    Returns
    -------
    The matched object / mob / character instance, or None if not found.

    Examples
    --------
        target = find_target("marker",    room, locations, characters)
        target = find_target("2.marker",  room, locations, characters)
        target = find_target("guardian",  room, locations, characters)
        target = find_target("moted",     room, locations, characters)
    """
    idx, keyword = parse_target(target_str)
    matches = 0

    # ── 1. Mobs ───────────────────────────────────────────────────────────────
    for mob in room.mobs:
        if _mob_matches(mob, keyword):
            matches += 1
            if matches == idx:
                return mob

    # ── 2. Characters (players in this room) ──────────────────────────────────
    if locations is not None and characters is not None:
        for name, room_id in locations.items():
            if room_id == room.number and name in characters:
                char = characters[name]
                if _char_matches(char, keyword):
                    matches += 1
                    if matches == idx:
                        return char

    # ── 3. Objects ────────────────────────────────────────────────────────────
    for obj in room.objects:
        if _obj_matches(obj, keyword):
            matches += 1
            if matches == idx:
                return obj

    return None


def find_all_targets(
    keyword:    str,
    room:       "Room",
    locations:  dict[str, int]         | None = None,
    characters: dict[str, "Character"] | None = None,
) -> list:
    """
    Return every instance in the room that matches *keyword*.

    Useful for AoE commands, inventory listing, or disambiguation messages
    ("There are 3 markers here — did you mean 1.marker or 2.marker?").
    """
    _, kw = parse_target(keyword)
    results = []

    for mob in room.mobs:
        if _mob_matches(mob, kw):
            results.append(mob)

    if locations is not None and characters is not None:
        for name, room_id in locations.items():
            if room_id == room.number and name in characters:
                char = characters[name]
                if _char_matches(char, kw):
                    results.append(char)

    for obj in room.objects:
        if _obj_matches(obj, kw):
            results.append(obj)

    return results


def target_name(instance) -> str:
    """
    Return the display name of a target for use in messages.

    Works for Mob, Character, Object/Item/Weapon — anything with a .name.
    """
    return getattr(instance, "name", str(instance))


# ── Internal matchers ─────────────────────────────────────────────────────────

def _mob_matches(mob, keyword: str) -> bool:
    """Mob matches if keyword is in key_words or appears in name."""
    if hasattr(mob, "key_words"):
        if keyword in (k.lower() for k in mob.key_words):
            return True
    return keyword in mob.name.lower()


def _char_matches(char, keyword: str) -> bool:
    """Character matches if keyword appears anywhere in their name."""
    return keyword in char.name.lower()


def _obj_matches(obj, keyword: str) -> bool:
    """Object matches if keyword is in key_words or appears in name."""
    if hasattr(obj, "key_words"):
        if keyword in (k.lower() for k in obj.key_words):
            return True
    return keyword in obj.name.lower()
