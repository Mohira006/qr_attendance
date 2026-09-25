import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import BadRequestError

PHOTOS_DIR = "photos"
LETTERS_DIR = "letters"
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
ALLOWED_LETTER_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_CHUNK_SIZE = 64 * 1024


def storage_root() -> Path:
    return Path(get_settings().STORAGE_PATH)


def ensure_directories() -> None:
    (storage_root() / PHOTOS_DIR).mkdir(parents=True, exist_ok=True)
    (storage_root() / LETTERS_DIR).mkdir(parents=True, exist_ok=True)


def resolve(relative_path: str) -> Path:
    """Resolve a stored relative path, refusing anything that escapes the storage root."""
    root = storage_root().resolve()
    candidate = (root / relative_path).resolve()
    if root not in candidate.parents:
        raise BadRequestError("Invalid file path", code="invalid_path")
    return candidate


async def save_profile_photo(employee_code: str, upload: UploadFile) -> str:
    """Store the upload and return the relative path to persist on the employee."""
    extension = ALLOWED_CONTENT_TYPES.get((upload.content_type or "").lower())
    if extension is None:
        raise BadRequestError("Only JPEG, PNG and WebP images are accepted", code="unsupported_media_type")

    max_bytes = get_settings().MAX_PHOTO_SIZE_BYTES
    ensure_directories()
    relative_path = f"{PHOTOS_DIR}/{employee_code.lower()}-{uuid.uuid4().hex}{extension}"
    destination = storage_root() / relative_path

    written = 0
    try:
        with destination.open("wb") as target:
            while chunk := await upload.read(_CHUNK_SIZE):
                written += len(chunk)
                if written > max_bytes:
                    raise BadRequestError(
                        f"Photo exceeds the maximum size of {max_bytes // 1024} KB", code="file_too_large"
                    )
                target.write(chunk)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    if written == 0:
        destination.unlink(missing_ok=True)
        raise BadRequestError("Uploaded file is empty", code="empty_file")
    return relative_path


async def save_letter_attachment(letter_id: int, employee_code: str, upload: UploadFile) -> str:
    """Store an employee's uploaded explanation document (PDF or image) and return
    the relative path to persist on the letter."""
    extension = ALLOWED_LETTER_CONTENT_TYPES.get((upload.content_type or "").lower())
    if extension is None:
        raise BadRequestError("Only PDF, JPEG, PNG and WebP files are accepted", code="unsupported_media_type")

    max_bytes = get_settings().MAX_LETTER_ATTACHMENT_SIZE_BYTES
    ensure_directories()
    relative_path = f"{LETTERS_DIR}/{employee_code.lower()}-{letter_id}-{uuid.uuid4().hex}{extension}"
    destination = storage_root() / relative_path

    written = 0
    try:
        with destination.open("wb") as target:
            while chunk := await upload.read(_CHUNK_SIZE):
                written += len(chunk)
                if written > max_bytes:
                    raise BadRequestError(
                        f"File exceeds the maximum size of {max_bytes // (1024 * 1024)} MB", code="file_too_large"
                    )
                target.write(chunk)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    if written == 0:
        destination.unlink(missing_ok=True)
        raise BadRequestError("Uploaded file is empty", code="empty_file")
    return relative_path


def delete_file(relative_path: str | None) -> None:
    if not relative_path:
        return
    try:
        resolve(relative_path).unlink(missing_ok=True)
    except BadRequestError:
        pass
