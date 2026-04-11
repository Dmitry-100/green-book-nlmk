import io

import pytest
from PIL import Image

from app.services import media


class FakeS3Client:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.get_calls = 0
        self.put_calls: list[dict] = []

    def get_object(self, **kwargs):
        self.get_calls += 1
        return {"Body": io.BytesIO(self.payload), **kwargs}

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        self.payload = kwargs["Body"]


def _build_image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (1200, 800)) -> bytes:
    image = Image.new("RGB", size, color=(12, 130, 220))
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, quality=95)
    return buffer.getvalue()


def test_optimize_image_object_rewrites_jpeg(monkeypatch):
    client = FakeS3Client(_build_image_bytes("JPEG"))
    monkeypatch.setattr(media, "get_s3_client", lambda: client)

    processed = media.optimize_image_object("observations/demo.jpg", "image/jpeg")

    assert len(client.put_calls) == 1
    assert client.get_calls == 1
    assert processed is not None
    put_call = client.put_calls[0]
    assert put_call["Key"] == "observations/demo.jpg"
    assert put_call["ContentType"] == "image/jpeg"
    assert isinstance(put_call["Body"], bytes)

    with Image.open(io.BytesIO(put_call["Body"])) as processed:
        assert processed.format == "JPEG"
        assert processed.size == (1200, 800)


def test_optimize_image_object_rejects_invalid_payload(monkeypatch):
    client = FakeS3Client(b"not-an-image")
    monkeypatch.setattr(media, "get_s3_client", lambda: client)

    with pytest.raises(ValueError, match="not a valid image"):
        media.optimize_image_object("observations/broken.jpg", "image/jpeg")


def test_optimize_image_object_skips_non_image_types(monkeypatch):
    client = FakeS3Client(b"text")
    monkeypatch.setattr(media, "get_s3_client", lambda: client)

    result = media.optimize_image_object("observations/text.txt", "text/plain")

    assert result is None
    assert client.get_calls == 0
    assert client.put_calls == []


def test_optimize_image_object_resizes_by_dimension_limit(monkeypatch):
    client = FakeS3Client(_build_image_bytes("JPEG", size=(3200, 1600)))
    monkeypatch.setattr(media, "get_s3_client", lambda: client)
    monkeypatch.setattr(media.settings, "media_max_image_dimension", 1000)

    media.optimize_image_object("observations/large.jpg", "image/jpeg")

    with Image.open(io.BytesIO(client.put_calls[0]["Body"])) as processed:
        assert processed.size == (1000, 500)


def test_optimize_image_object_rejects_excessive_pixel_budget(monkeypatch):
    client = FakeS3Client(_build_image_bytes("JPEG", size=(1800, 1200)))
    monkeypatch.setattr(media, "get_s3_client", lambda: client)
    monkeypatch.setattr(media.settings, "media_max_image_pixels", 1_000_000)

    with pytest.raises(ValueError, match="pixel budget"):
        media.optimize_image_object("observations/too-large.jpg", "image/jpeg")


def test_create_thumbnail_from_image_uses_processed_payload_without_refetch(monkeypatch):
    client = FakeS3Client(_build_image_bytes("JPEG", size=(1200, 800)))
    monkeypatch.setattr(media, "get_s3_client", lambda: client)

    processed = media.optimize_image_object("observations/processed.jpg", "image/jpeg")
    assert processed is not None
    before_get_calls = client.get_calls

    thumb_key = media.create_thumbnail_from_image("observations/processed.jpg", processed)
    processed.close()

    assert thumb_key == "thumbnails/processed.jpg"
    assert client.get_calls == before_get_calls
    assert len(client.put_calls) == 2
    with Image.open(io.BytesIO(client.put_calls[1]["Body"])) as thumb:
        assert max(thumb.size) <= media.settings.media_thumbnail_size
