"""Download OpenCV YuNet + SFace ONNX models used for face verification."""

from pathlib import Path
from urllib.request import urlretrieve

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
FILES = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ),
    "face_recognition_sface_2021dec.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ),
}


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = MODELS_DIR / name
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"Already present: {dest}")
            continue
        print(f"Downloading {name} ...")
        urlretrieve(url, dest)
        print(f"Saved {dest} ({dest.stat().st_size} bytes)")
    print("Face models are ready.")


if __name__ == "__main__":
    main()
