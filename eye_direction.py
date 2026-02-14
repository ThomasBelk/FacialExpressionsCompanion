

left_eye_iris_center_id = 468
left_eye_left_id=33
left_eye_right_id=133
left_eye_top_id=159
left_eye_bottom_id=145

right_eye_iris_center_id=473
right_eye_left_id=362
right_eye_right_id=263
right_eye_top_id=386
right_eye_bottom_id=374

max_observed_y = 0.48
min_observed_y = 0.0

def eye_direction_from_landmarks(landmarks, iris_center_id, left_id, right_id, top_id, bottom_id, tracker):
    iris_x = landmarks[iris_center_id].x
    iris_y = landmarks[iris_center_id].y

    left_x = landmarks[left_id].x
    right_x = landmarks[right_id].x
    top_y = min(landmarks[top_id].y, landmarks[bottom_id].y)
    bottom_y = max(landmarks[top_id].y, landmarks[bottom_id].y)

    # raw fraction of iris position within the eye box
    x_raw = (iris_x - left_x) / (right_x - left_x)
    y_raw = (iris_y - top_y) / (bottom_y - top_y)

    x_raw = clamp01(x_raw)
    y_raw = clamp01(y_raw)

    x_cal, y_cal = tracker.update(x_raw, y_raw, landmarks, top_id, bottom_id)

    # Apply center correction after warm-up
    if not tracker.calibrating:
        x_cal = x_cal - (tracker.x_center - 0.5)
        y_cal = y_cal - (tracker.y_center - 0.5)
        x_cal = clamp01(x_cal)
        y_cal = clamp01(y_cal)

    # Convert to game coordinates (-1..1)
    x = 2 * x_cal - 1
    y = 2 * y_cal - 1



    return x, y

    x_norm = (iris_x - (left_x + right_x) / 2) / ((right_x - left_x) / 2)
    y_norm = (iris_y - (top_y + bottom_y) / 2) / ((bottom_y - top_y) / 2)

    return x_norm, y_norm

def eye_open(landmarks, top_id, bottom_id):
    return abs(landmarks[top_id].y - landmarks[bottom_id].y)

def clamp01(value):
    return max(0.0, min(1.0, value))


class AxisCalibrator:
    def __init__(self, adapt_rate=0.02):
        self.min = 1.0
        self.max = 0.0
        self.rate = adapt_rate

    def update(self, v):
        self.min += self.rate * (v - self.min) if v < self.min else 0
        self.max += self.rate * (v - self.max) if v > self.max else 0

    def remap(self, v):
        if self.max - self.min < 1e-4:
            return 0.5
        return (v - self.min) / (self.max - self.min)


class EyeTracker:
    def __init__(self, x_adapt=0.05, y_adapt=0.01, smooth_alpha=0.2, warmup_frames=90):
        # Raw observed extremes
        self.x_min = 1.0
        self.x_max = 0.0
        self.y_min = 1.0
        self.y_max = 0.0

        # Adapt rates
        self.x_rate = x_adapt
        self.y_rate = y_adapt

        # EMA smoothing
        self.smooth_alpha = smooth_alpha
        self.x_smooth = None
        self.y_smooth = None

        # Warm-up calibration
        self.warmup_frames = warmup_frames
        self.frame_count = 0
        self.calibrating = True

        self.x_center = 0.5
        self.y_center = 0.5

    @staticmethod
    def clamp01(v):
        return max(0.0, min(1.0, v))

    @staticmethod
    def eye_open(landmarks, top_id, bottom_id):
        return abs(landmarks[top_id].y - landmarks[bottom_id].y)

    def update(self, x_raw, y_raw, landmarks=None, top_id=None, bottom_id=None):
        """
        x_raw, y_raw: raw normalized iris fractions (0..1)
        landmarks + top/bottom IDs: used to blink-gate Y updates
        """

        # Clamp raw values
        x_raw = self.clamp01(x_raw)
        y_raw = self.clamp01(y_raw)

        # Warm-up / calibration
        if self.calibrating:
            self.x_min = min(self.x_min, x_raw)
            self.x_max = max(self.x_max, x_raw)

            if landmarks is None or self.eye_open(landmarks, top_id, bottom_id) > 0.01:
                self.y_min = min(self.y_min, y_raw)
                self.y_max = max(self.y_max, y_raw)

            self.frame_count += 1
            if self.frame_count >= self.warmup_frames:
                # self.x_center = (self.x_min + self.x_max) / 2
                # self.y_center = (self.y_min + self.y_max) / 2
                self.calibrating = False  # freeze min/max after warm-up

        # Remap to 0..1 using min/max
        def remap(v, vmin, vmax):
            if vmax - vmin < 1e-5:
                return 0.5
            return (v - vmin) / (vmax - vmin)

        x_cal = remap(x_raw, self.x_min, self.x_max)
        y_cal = remap(y_raw, self.y_min, self.y_max)

        # EMA smoothing
        if self.x_smooth is None:
            self.x_smooth = x_cal
            self.y_smooth = y_cal
        else:
            self.x_smooth = self.smooth_alpha * x_cal + (1 - self.smooth_alpha) * self.x_smooth
            self.y_smooth = self.smooth_alpha * y_cal + (1 - self.smooth_alpha) * self.y_smooth

        # Clamp final values
        x_final = self.clamp01(self.x_smooth)
        y_final = self.clamp01(self.y_smooth)

        return x_final, y_final

    def as_game_coords(self):
        """
        Convert 0..1 -> -1..1 for game use
        """
        return 2 * self.x_smooth - 1, 2 * self.y_smooth - 1