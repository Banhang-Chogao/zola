import pytest
from fastapi import HTTPException

from services.vipzone.cms_repo import _normalize_editorial_slots, _slot_slug_list


def test_editorial_slots_normalize_versioned_schema():
    slots = _normalize_editorial_slots({
        "lead_story": "real-post",
        "featured": "other-post",
        "secondary": ["secondary-one", "secondary-two"],
        "sidebar_featured": None,
    })
    assert slots["version"] == 1
    assert slots["allow_duplicates"] is False
    assert _slot_slug_list(slots) == [
        "real-post", "other-post", "secondary-one", "secondary-two",
    ]


@pytest.mark.parametrize("payload", [
    {"lead_story": "../escape"},
    {"secondary": "not-a-list"},
    {"secondary": ["one", "two", "three", "four", "five"]},
])
def test_editorial_slots_reject_invalid_shapes(payload):
    with pytest.raises(HTTPException):
        _normalize_editorial_slots(payload)
