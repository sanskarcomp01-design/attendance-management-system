import struct
from pathlib import Path

import cv2
import numpy as np
from flask import current_app

YUNET_NAME = "face_detection_yunet_2023mar.onnx"
SFACE_NAME = "face_recognition_sface_2021dec.onnx"
MIN_HEAD_TURN = 0.12
MAX_NEUTRAL_OFFSET = 0.22

_detector = None
_recognizer = None


class FaceServiceError(Exception):
    pass


def model_paths():
    folder = Path(current_app.config["MODEL_FOLDER"])
    return folder / YUNET_NAME, folder / SFACE_NAME


def models_ready() -> bool:
    yunet, sface = model_paths()
    return yunet.exists() and sface.exists()


def _load_models():
    global _detector, _recognizer
    if _detector is not None and _recognizer is not None:
        return
    yunet, sface = model_paths()
    if not yunet.exists() or not sface.exists():
        raise FaceServiceError(
            "Face models are missing. From the backend folder run: python scripts/download_models.py"
        )
    _detector = cv2.FaceDetectorYN.create(str(yunet), "", (320, 320), 0.9, 0.3, 5000)
    _recognizer = cv2.FaceRecognizerSF.create(str(sface), "")


def decode_image(image_bytes: bytes):
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise FaceServiceError("Could not read the photo. Use a clear JPEG or PNG selfie.")
    return image


def detect_best_face(image):
    _load_models()
    h, w = image.shape[:2]
    _detector.setInputSize((w, h))
    _retval, faces = _detector.detect(image)
    if faces is None or len(faces) == 0:
        raise FaceServiceError("No face found. Face the camera with good lighting and try again.")
    if len(faces) > 1:
        raise FaceServiceError("More than one face was found. Only the student should be in the frame.")
    return faces[0]


def extract_embedding(image_bytes: bytes) -> np.ndarray:
    image = decode_image(image_bytes)
    face = detect_best_face(image)
    aligned = _recognizer.alignCrop(image, face)
    feature = _recognizer.feature(aligned)
    vector = np.asarray(feature, dtype=np.float32).flatten()
    return vector


def embedding_to_bytes(vector: np.ndarray) -> bytes:
    values = vector.astype(np.float32).tolist()
    return struct.pack(f"I{len(values)}f", len(values), *values)


def bytes_to_embedding(blob: bytes) -> np.ndarray:
    (count,) = struct.unpack_from("I", blob, 0)
    values = struct.unpack_from(f"{count}f", blob, 4)
    return np.asarray(values, dtype=np.float32)


def compare(probe: np.ndarray, enrolled: np.ndarray) -> float:
    _load_models()
    score = float(_recognizer.match(probe, enrolled, cv2.FaceRecognizerSF_FR_COSINE))
    return score


def verify_face(image_bytes: bytes, enrolled_blob: bytes) -> tuple[bool, float]:
    probe = extract_embedding(image_bytes)
    enrolled = bytes_to_embedding(enrolled_blob)
    score = compare(probe, enrolled)
    threshold = float(current_app.config["FACE_MATCH_THRESHOLD"])
    return score >= threshold, score


def _face_pose(image_bytes: bytes):
    image = decode_image(image_bytes)
    face = detect_best_face(image)
    right_eye = face[4:6]
    left_eye = face[6:8]
    nose = face[8:10]
    eye_distance = float(np.linalg.norm(right_eye - left_eye))
    if eye_distance == 0:
        raise FaceServiceError("Could not verify head movement. Face the camera and try again.")
    eye_midpoint_x = float((right_eye[0] + left_eye[0]) / 2)
    horizontal_offset = float((nose[0] - eye_midpoint_x) / eye_distance)
    return image, face, horizontal_offset


def verify_face_liveness(
    neutral_image: bytes,
    turned_image: bytes,
    expected_direction: str,
    enrolled_blob: bytes,
) -> tuple[bool, float, bool]:
    neutral, neutral_face, neutral_pose = _face_pose(neutral_image)
    turned, turned_face, turned_pose = _face_pose(turned_image)
    enrolled = bytes_to_embedding(enrolled_blob)
    neutral_probe = np.asarray(
        _recognizer.feature(_recognizer.alignCrop(neutral, neutral_face)),
        dtype=np.float32,
    ).flatten()
    turned_probe = np.asarray(
        _recognizer.feature(_recognizer.alignCrop(turned, turned_face)),
        dtype=np.float32,
    ).flatten()
    neutral_score = compare(neutral_probe, enrolled)
    turned_score = compare(turned_probe, enrolled)
    score = min(neutral_score, turned_score)
    threshold = float(current_app.config["FACE_MATCH_THRESHOLD"])

    movement = turned_pose - neutral_pose
    moved_as_requested = movement <= -MIN_HEAD_TURN if expected_direction == "left" else movement >= MIN_HEAD_TURN
    live = abs(neutral_pose) <= MAX_NEUTRAL_OFFSET and moved_as_requested
    return score >= threshold, score, live
