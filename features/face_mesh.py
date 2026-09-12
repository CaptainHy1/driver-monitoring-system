"""
Module trích xuất Facial Landmarks bằng MediaPipe Face Mesh.
Tính toán các chỉ số sinh trắc học:
- EAR (Eye Aspect Ratio): Mắt trái, mắt phải, trung bình
- MAR (Mouth Aspect Ratio): Độ mở miệng
- Head Pose 3D (Pitch, Yaw, Roll) sử dụng cv2.solvePnP
- Gaze Estimation (Độ lệch hướng nhìn của con ngươi)
- Face Bounding Box (ROI)
"""

import cv2
import numpy as np
import mediapipe as mp
import math

class FaceMeshDetector:
    def __init__(self, static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=static_image_mode,
            max_num_faces=max_num_faces,
            refine_landmarks=True,  # Bật iris landmarks (468-477)
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        # Định nghĩa các chỉ số Landmark mốc
        # Mắt trái (Left Eye)
        self.LEFT_EYE_PTS = {
            "corner_left": 33,
            "corner_right": 133,
            "top1": 160,
            "top2": 158,
            "bot1": 144,
            "bot2": 153,
            "iris": 468
        }

        # Mắt phải (Right Eye)
        self.RIGHT_EYE_PTS = {
            "corner_left": 362,
            "corner_right": 263,
            "top1": 385,
            "top2": 387,
            "bot1": 380,
            "bot2": 373,
            "iris": 473
        }

        # Miệng (Mouth / Lips)
        self.MOUTH_PTS = {
            "corner_left": 61,
            "corner_right": 291,
            "top1": 81,
            "top2": 13,
            "top3": 311,
            "bot1": 178,
            "bot2": 14,
            "bot3": 402
        }

        # Mô hình 3D khuôn mặt chuẩn (Anthropometric 3D Face Model) theo mm
        self.MODEL_POINTS_3D = np.array([
            (0.0, 0.0, 0.0),             # Chóp mũi (Nose tip - 4)
            (0.0, -330.0, -65.0),        # Cằm (Chin - 152)
            (-225.0, 170.0, -135.0),     # Khóe mắt trái ngoài (Left eye corner - 33)
            (225.0, 170.0, -135.0),      # Khóe mắt phải ngoài (Right eye corner - 263)
            (-150.0, -150.0, -125.0),    # Khóe miệng trái (Left mouth corner - 61)
            (150.0, -150.0, -125.0)      # Khóe miệng phải (Right mouth corner - 291)
        ], dtype=np.float64)

        # Các chỉ số Landmark tương ứng cho SolvePnP
        self.POSE_LANDMARK_IDS = [4, 152, 33, 263, 61, 291]

    def _euclidean_dist(self, p1, p2):
        """Tính khoảng cách Euclidean 2D"""
        return np.linalg.norm(np.array(p1) - np.array(p2))

    def calculate_ear(self, landmarks, eye_pts, img_w, img_h):
        """
        Tính Eye Aspect Ratio (EAR) theo công thức Soukupová & Čech:
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
        """
        try:
            p1 = (landmarks[eye_pts["corner_left"]].x * img_w, landmarks[eye_pts["corner_left"]].y * img_h)
            p4 = (landmarks[eye_pts["corner_right"]].x * img_w, landmarks[eye_pts["corner_right"]].y * img_h)
            p2 = (landmarks[eye_pts["top1"]].x * img_w, landmarks[eye_pts["top1"]].y * img_h)
            p6 = (landmarks[eye_pts["bot1"]].x * img_w, landmarks[eye_pts["bot1"]].y * img_h)
            p3 = (landmarks[eye_pts["top2"]].x * img_w, landmarks[eye_pts["top2"]].y * img_h)
            p5 = (landmarks[eye_pts["bot2"]].x * img_w, landmarks[eye_pts["bot2"]].y * img_h)

            vertical_1 = self._euclidean_dist(p2, p6)
            vertical_2 = self._euclidean_dist(p3, p5)
            horizontal = self._euclidean_dist(p1, p4)

            if horizontal < 1e-6:
                return 0.0

            ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
            return float(ear)
        except Exception:
            return 0.0

    def calculate_mar(self, landmarks, img_w, img_h):
        """
        Tính Mouth Aspect Ratio (MAR):
        MAR = (||top1 - bot1|| + ||top2 - bot2|| + ||top3 - bot3||) / (3 * ||left - right||)
        """
        try:
            pts = self.MOUTH_PTS
            p_left = (landmarks[pts["corner_left"]].x * img_w, landmarks[pts["corner_left"]].y * img_h)
            p_right = (landmarks[pts["corner_right"]].x * img_w, landmarks[pts["corner_right"]].y * img_h)

            p_t1 = (landmarks[pts["top1"]].x * img_w, landmarks[pts["top1"]].y * img_h)
            p_b1 = (landmarks[pts["bot1"]].x * img_w, landmarks[pts["bot1"]].y * img_h)

            p_t2 = (landmarks[pts["top2"]].x * img_w, landmarks[pts["top2"]].y * img_h)
            p_b2 = (landmarks[pts["bot2"]].x * img_w, landmarks[pts["bot2"]].y * img_h)

            p_t3 = (landmarks[pts["top3"]].x * img_w, landmarks[pts["top3"]].y * img_h)
            p_b3 = (landmarks[pts["bot3"]].x * img_w, landmarks[pts["bot3"]].y * img_h)

            v1 = self._euclidean_dist(p_t1, p_b1)
            v2 = self._euclidean_dist(p_t2, p_b2)
            v3 = self._euclidean_dist(p_t3, p_b3)
            h = self._euclidean_dist(p_left, p_right)

            if h < 1e-6:
                return 0.0

            mar = (v1 + v2 + v3) / (3.0 * h)
            return float(mar)
        except Exception:
            return 0.0

    def estimate_head_pose(self, landmarks, img_w, img_h):
        """
        Ước lượng góc nghiêng đầu (Pitch, Yaw, Roll) sử dụng Perspective-n-Point (cv2.solvePnP).
        Trả về: pitch, yaw, roll (tính theo độ - degrees)
        """
        try:
            image_points = []
            for idx in self.POSE_LANDMARK_IDS:
                lm = landmarks[idx]
                image_points.append([lm.x * img_w, lm.y * img_h])
            image_points = np.array(image_points, dtype=np.float64)

            # Giả định ma trận camera nội tại (Camera Matrix)
            focal_length = img_w
            center = (img_w / 2.0, img_h / 2.0)
            camera_matrix = np.array([
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1]
            ], dtype=np.float64)

            dist_coeffs = np.zeros((4, 1), dtype=np.float64)

            success, rot_vec, trans_vec = cv2.solvePnP(
                self.MODEL_POINTS_3D,
                image_points,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if not success:
                return 0.0, 0.0, 0.0, None, None

            rot_mat, _ = cv2.Rodrigues(rot_vec)

            # Trích xuất góc Euler từ ma trận quay
            # Góc pitch (gật gù), yaw (quay trái/phải), roll (nghiêng vai)
            sy = math.sqrt(rot_mat[0, 0] * rot_mat[0, 0] + rot_mat[1, 0] * rot_mat[1, 0])
            singular = sy < 1e-6

            if not singular:
                x = math.atan2(rot_mat[2, 1], rot_mat[2, 2])
                y = math.atan2(-rot_mat[2, 0], sy)
                z = math.atan2(rot_mat[1, 0], rot_mat[0, 0])
            else:
                x = math.atan2(-rot_mat[1, 2], rot_mat[1, 1])
                y = math.atan2(-rot_mat[2, 0], sy)
                z = 0

            pitch = math.degrees(x)
            yaw = math.degrees(y)
            roll = math.degrees(z)

            return pitch, yaw, roll, rot_vec, trans_vec
        except Exception:
            return 0.0, 0.0, 0.0, None, None

    def estimate_gaze(self, landmarks, img_w, img_h):
        """
        Ước lượng độ lệch hướng nhìn của con ngươi (Gaze Vector x, y trong khoảng [-1.0, 1.0])
        """
        try:
            if len(landmarks) <= 473:
                return 0.0, 0.0

            # Mắt trái
            l_corn_l = np.array([landmarks[33].x * img_w, landmarks[33].y * img_h])
            l_corn_r = np.array([landmarks[133].x * img_w, landmarks[133].y * img_h])
            l_iris = np.array([landmarks[468].x * img_w, landmarks[468].y * img_h])

            eye_center = (l_corn_l + l_corn_r) / 2.0
            eye_width = np.linalg.norm(l_corn_r - l_corn_l)

            if eye_width < 1e-6:
                return 0.0, 0.0

            gaze_x = (l_iris[0] - eye_center[0]) / (eye_width / 2.0)
            gaze_y = (l_iris[1] - eye_center[1]) / (eye_width / 4.0)

            # Giới hạn trong khoảng [-1.0, 1.0]
            gaze_x = float(np.clip(gaze_x, -1.0, 1.0))
            gaze_y = float(np.clip(gaze_y, -1.0, 1.0))

            return gaze_x, gaze_y
        except Exception:
            return 0.0, 0.0

    def process_frame(self, frame_bgr):
        """
        Xử lý frame hình ảnh, trả về thông tin sinh trắc học chi tiết.
        """
        h, w, _ = frame_bgr.shape
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(frame_rgb)

        if not results.multi_face_landmarks:
            return None

        landmarks = results.multi_face_landmarks[0].landmark

        # 1. Tính EAR
        ear_left = self.calculate_ear(landmarks, self.LEFT_EYE_PTS, w, h)
        ear_right = self.calculate_ear(landmarks, self.RIGHT_EYE_PTS, w, h)
        ear_avg = (ear_left + ear_right) / 2.0

        # 2. Tính MAR
        mar = self.calculate_mar(landmarks, w, h)

        # 3. Tính Head Pose
        pitch, yaw, roll, rot_vec, trans_vec = self.estimate_head_pose(landmarks, w, h)

        # 4. Tính Gaze
        gaze_x, gaze_y = self.estimate_gaze(landmarks, w, h)

        # 5. Xác định Bounding Box khuôn mặt
        xs = [lm.x * w for lm in landmarks]
        ys = [lm.y * h for lm in landmarks]
        x_min, x_max = int(max(0, min(xs))), int(min(w, max(xs)))
        y_min, y_max = int(max(0, min(ys))), int(min(h, max(ys)))
        face_bbox = (x_min, y_min, x_max - x_min, y_max - y_min)

        return {
            "detected": True,
            "ear_left": ear_left,
            "ear_right": ear_right,
            "ear_avg": ear_avg,
            "mar": mar,
            "pitch": pitch,
            "yaw": yaw,
            "roll": roll,
            "gaze_x": gaze_x,
            "gaze_y": gaze_y,
            "face_bbox": face_bbox,
            "landmarks": landmarks,
            "rot_vec": rot_vec,
            "trans_vec": trans_vec
        }
