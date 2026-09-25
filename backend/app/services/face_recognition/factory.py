from app.core.config import get_settings
from app.services.face_recognition.base import FaceRecognitionProvider
from app.services.face_recognition.http_provider import HttpProvider
from app.services.face_recognition.simulator import SimulatorProvider


def get_provider() -> FaceRecognitionProvider:
    settings = get_settings()
    if settings.FACE_RECOGNITION_PROVIDER == "http":
        return HttpProvider(settings.FACE_RECOGNITION_URL, settings.FACE_RECOGNITION_API_KEY)
    return SimulatorProvider()
