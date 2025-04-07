import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
import numpy as np
import cv2
import matplotlib.pyplot as plt
import threading
import queue
from collections import deque
import socket
import time

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 8899
GAME_SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def draw_landmarks_on_image(rgb_image, detection_result):
    face_landmarks_list = detection_result.face_landmarks
    annotated_image = np.copy(rgb_image)

    # Loop through the detected faces to visualize.
    for idx in range(len(face_landmarks_list)):
        face_landmarks = face_landmarks_list[idx]

        # Draw the face landmarks.
        face_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
        face_landmarks_proto.landmark.extend([
            landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z)
            for landmark in face_landmarks
        ])

        solutions.drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks_proto,
            connections=mp.solutions.face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=mp.solutions.drawing_styles.get_default_face_mesh_tesselation_style(),
        )
        solutions.drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks_proto,
            connections=mp.solutions.face_mesh.FACEMESH_CONTOURS,
            landmark_drawing_spec=None,
            connection_drawing_spec=mp.solutions.drawing_styles.get_default_face_mesh_contours_style(),
        )
        solutions.drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks_proto,
            connections=mp.solutions.face_mesh.FACEMESH_IRISES,
            landmark_drawing_spec=None,
            connection_drawing_spec=mp.solutions.drawing_styles.get_default_face_mesh_iris_connections_style(),
        )

    return annotated_image


def plot_face_blendshapes_bar_graph(face_blendshapes):
    # Extract the face blendshapes category names and scores.
    face_blendshapes_names = [
        face_blendshapes_category.category_name
        for face_blendshapes_category in face_blendshapes
    ]
    face_blendshapes_scores = [
        face_blendshapes_category.score
        for face_blendshapes_category in face_blendshapes
    ]
    # The blendshapes are ordered in decreasing score value.
    face_blendshapes_ranks = range(len(face_blendshapes_names))

    fig, ax = plt.subplots(figsize=(12, 12))
    bar = ax.barh(
        face_blendshapes_ranks,
        face_blendshapes_scores,
        label=[str(x) for x in face_blendshapes_ranks],
    )
    ax.set_yticks(face_blendshapes_ranks, face_blendshapes_names)
    ax.invert_yaxis()

    # Label each bar with values
    for score, patch in zip(face_blendshapes_scores, bar.patches):
        plt.text(
            patch.get_x() + patch.get_width(), patch.get_y(), f"{score:.4f}", va="top"
        )

    ax.set_xlabel("Score")
    ax.set_title("Face Blendshapes")
    plt.tight_layout()
    plt.show()


# Add this function to calculate Euler angles from rotation matrix
def get_euler_angles(rotation_matrix):
    sy = np.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
    singular = sy < 1e-6

    if not singular:
        x = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
        y = np.arctan2(-rotation_matrix[2, 0], sy)
        z = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
    else:
        x = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
        y = np.arctan2(-rotation_matrix[2, 0], sy)
        z = 0

    return np.degrees(x), np.degrees(y), np.degrees(z)  # pitch, yaw, roll


def detect_head_facing_direction(image):
    # Create an FaceLandmarker object.
    base_options = python.BaseOptions(
        model_asset_path="face_landmarker_v2_with_blendshapes.task"
    )
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
        num_faces=1,
    )
    detector = vision.FaceLandmarker.create_from_options(options)

    # Load the input image.
    # image = mp.Image.create_from_file("down.jpg")

    # Detect face landmarks from the input image.
    detection_result = detector.detect(image)

    # New code to detect head direction
    if detection_result.facial_transformation_matrixes:
        # Extract rotation matrix from transformation matrix
        transformation_matrix = detection_result.facial_transformation_matrixes[0]
        rotation_matrix = transformation_matrix[:3, :3]

        pitch, yaw, roll = get_euler_angles(rotation_matrix)

        # Determine head direction
        directions = []
        if yaw < -15:
            directions.append("Right")
        elif yaw > 15:
            directions.append("Left")
        if pitch < -15:
            directions.append("Up")
        elif pitch > 15:
            directions.append("Down")

        # If no significant rotation, consider facing forward
        if not directions:
            directions.append("Forward")

        print("Head direction:", ", ".join(directions))
        print(f"Pitch: {pitch:.2f}°, Yaw: {yaw:.2f}°, Roll: {roll:.2f}°")

        result_queue.put(directions)
    else:
        result_queue.put(["Forward"])


# Worker function for the processing thread
def process_frames():
    while True:
        # time.sleep(0.1)
        try:
            frame = frame_queue.get_nowait()
        except queue.Empty:
            continue

        if frame is None:  # Exit signal
            break

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        detect_head_facing_direction(mp_image)


# # Process the detection result. In this case, visualize it.
# annotated_image = draw_landmarks_on_image(image.numpy_view(), detection_result)
# cv2.imshow("Head Pose Detection", cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
# cv2.waitKey(0)
# cv2.destroyAllWindows()

# plot_face_blendshapes_bar_graph(detection_result.face_blendshapes[0])


def connect_to_game():
    global GAME_SOCK
    try:
        GAME_SOCK.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("Game server not started.")
        exit(1)


def send_direction_to_game(direction: str):
    try:
        GAME_SOCK.sendall(f"{direction}\n".encode("utf-8"))
        print(f"Sent: {direction}")
    except Exception as e:
        connect_to_game()
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    connect_to_game()
    frame_queue = queue.Queue(maxsize=1)  # Only process latest frame
    result_queue = queue.Queue(maxsize=1)

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    # Start the processing thread
    processing_thread = threading.Thread(target=process_frames)
    processing_thread.start()

    while True:
        # Press 'q' to quit the video stream
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        # Capture frame-by-frame
        ret, frame = cap.read()
        if not ret:
            break

        try:
            directions = result_queue.get_nowait()
            for dir in directions:
                send_direction_to_game(dir)
        except queue.Empty:
            pass

        if not frame_queue.full():
            frame_queue.put(frame.copy())

        # Display the resulting frame
        cv2.imshow("Webcam Feed", cv2.flip(frame, 1))

    frame_queue.get_nowait()
    frame_queue.put(None)  # Signal thread to exit
    processing_thread.join()
    cap.release()
    cv2.destroyAllWindows()
