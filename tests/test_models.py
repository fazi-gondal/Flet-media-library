import pytest
from flet.controls.control_event import get_event_field_type

from flet_media_library.exceptions import (
    InvalidArgumentError,
    UnsupportedError,
    error_from_exception,
)
from flet_media_library.media_library import MediaLibrary
from flet_media_library.models import (
    MediaChangeEvent,
    parse_asset_page,
    parse_media_asset,
    parse_permission_status,
)


# ───────────────────────────── model parsing ─────────────────────────────────


def test_parse_media_asset_full():
    asset = parse_media_asset(
        {
            "id": "123",
            "display_name": "cat.jpg",
            "mime_type": "image/jpeg",
            "media_type": "image",
            "size": 1024,
            "width": 800,
            "height": 600,
            "duration_ms": 0,
            "date_added": 1700000000,
            "date_modified": 1700000001,
            "orientation": 90,
            "album_name": "Camera",
            "relative_path": "Pictures/Camera/",
        }
    )
    assert asset.id == "123"
    assert asset.display_name == "cat.jpg"
    assert asset.size == 1024
    assert asset.orientation == 90
    assert asset.album_name == "Camera"


def test_parse_media_asset_missing_fields_default_to_empty():
    asset = parse_media_asset({"id": "x"})
    assert asset.display_name == ""
    assert asset.size == 0
    assert asset.media_type == ""


def test_parse_asset_page():
    page = parse_asset_page(
        {
            "items": [{"id": "1"}, {"id": "2"}],
            "total": 10,
            "offset": 20,
            "limit": 2,
            "has_more": True,
        }
    )
    assert len(page.items) == 2
    assert page.total == 10
    assert page.offset == 20
    assert page.has_more is True


def test_parse_permission_status():
    status = parse_permission_status(
        {
            "permissions": {"image": "granted", "video": "denied"},
            "can_request": True,
        }
    )
    assert status["image"] == "granted"
    assert status["video"] == "denied"
    assert status["audio"] == "unknown"
    assert not status.all_granted
    assert status.can_request


def test_permission_status_all_granted():
    status = parse_permission_status(
        {
            "permissions": {"image": "granted", "video": "limited"},
            "can_request": False,
        }
    )
    assert not status.all_granted
    assert status.any_limited is True


def test_media_change_event_is_flet_event():
    media = MediaLibrary()
    event = MediaChangeEvent(
        name="change",
        control=media,
        change_type="added",
        asset_id="123",
        media_type="image",
        timestamp=1700000000000,
    )
    assert event.name == "change"
    assert event.control is media
    assert event.change_type == "added"
    assert event.asset_id == "123"


def test_media_library_change_event_type_is_resolvable():
    assert get_event_field_type(MediaLibrary(), "on_change") is MediaChangeEvent


# ───────────────────────────── argument validation ───────────────────────────


@pytest.mark.asyncio
async def test_get_assets_rejects_bad_media_type():
    media = MediaLibrary()
    with pytest.raises(InvalidArgumentError):
        await media.get_assets(media_type="pdf")


@pytest.mark.asyncio
async def test_get_assets_rejects_bad_sort_field():
    media = MediaLibrary()
    with pytest.raises(InvalidArgumentError):
        await media.get_assets(sort_by="unicorn")


@pytest.mark.asyncio
async def test_get_assets_rejects_bad_sort_order():
    media = MediaLibrary()
    with pytest.raises(InvalidArgumentError):
        await media.get_assets(sort_order="up")


@pytest.mark.asyncio
async def test_get_assets_rejects_bad_limit():
    media = MediaLibrary()
    with pytest.raises(InvalidArgumentError):
        await media.get_assets(limit=0)
    with pytest.raises(InvalidArgumentError):
        await media.get_assets(limit=501)


@pytest.mark.asyncio
async def test_get_assets_rejects_negative_offset():
    media = MediaLibrary()
    with pytest.raises(InvalidArgumentError):
        await media.get_assets(offset=-1)


@pytest.mark.asyncio
async def test_delete_assets_requires_non_empty_list():
    media = MediaLibrary()
    with pytest.raises(InvalidArgumentError):
        await media.delete_assets([])


@pytest.mark.asyncio
async def test_rename_asset_rejects_empty_name():
    media = MediaLibrary()
    with pytest.raises(InvalidArgumentError):
        await media.rename_asset("1", "   ")


@pytest.mark.asyncio
async def test_rename_asset_rejects_empty_id():
    media = MediaLibrary()
    with pytest.raises(InvalidArgumentError):
        await media.rename_asset("", "name.jpg")


@pytest.mark.asyncio
async def test_move_asset_rejects_empty_path():
    media = MediaLibrary()
    with pytest.raises(InvalidArgumentError):
        await media.move_asset("1", "")


@pytest.mark.asyncio
async def test_save_image_rejects_empty_path():
    media = MediaLibrary()
    with pytest.raises(InvalidArgumentError):
        await media.save_image("")


@pytest.mark.asyncio
async def test_save_image_rejects_missing_local_file(tmp_path):
    media = MediaLibrary()
    missing = tmp_path / "nope.jpg"
    # Parent exists locally; file does not → should raise.
    with pytest.raises(InvalidArgumentError):
        await media.save_image(str(missing))


# ───────────────────────────── error conversion ──────────────────────────────


def test_error_from_exception_maps_known_codes():
    err = error_from_exception(Exception("unsupported: no MIME column"))
    assert isinstance(err, UnsupportedError)
    assert str(err) == "no MIME column"


def test_error_from_exception_falls_back_to_base():
    err = error_from_exception(Exception("something exploded"))
    assert type(err).__name__ == "MediaLibraryError"
