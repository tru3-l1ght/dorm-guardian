import cv2

for index in range(6):
    camera = cv2.VideoCapture(index)

    if camera.isOpened():
        ret, frame = camera.read()

        if ret:
            print(f"Camera index {index}: WORKS, frame shape = {frame.shape}")
        else:
            print(f"Camera index {index}: opens but cannot read frame")

        camera.release()
    else:
        print(f"Camera index {index}: not available")