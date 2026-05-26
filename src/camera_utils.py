import cv2


def scan_cameras(max_index: int = 8) -> list[tuple[int, str]]:
    """Return available cameras as (index, label) pairs."""
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            label = f"Camera {i}" + (" (default)" if i == 0 else "")
            found.append((i, label))
            cap.release()
    return found
