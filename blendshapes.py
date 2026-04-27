
DESIRED_BLENDSHAPES = [
    "browInnerUp", "browDownLeft", "browDownRight", "browOuterUpLeft", "browOuterUpRight",
    "jawOpen", "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight",
    "eyeBlinkLeft", "eyeBlinkRight"
]

VTS_EYE_PARAMETERS = ["leftEyeX", "rightEyeX", "leftEyeY", "rightEyeY"]

DESIRED_PARAMETERS = [*DESIRED_BLENDSHAPES, *VTS_EYE_PARAMETERS]

PARAMETER_TOOLTIPS = {
    # eyebrows
    "browInnerUp": (
        "Raises the inner parts of both eyebrows. "
        "Higher values -> both eyebrows up, lower values -> allow other eyebrow parameters control."
    ),

    "browDownLeft": (
        "Right eyebrow lowered, used to help control furrowing. "
        "Higher values -> eyebrows furrowed."
    ),

    "browDownRight": (
        "Right eyebrow lowered, used to help control furrowing. "
        "Higher values -> eyebrows furrowed."
    ),

    "browOuterUpLeft": (
        "Left eyebrow outer edge raised. "
        "Higher values -> eyebrows up."
    ),

    "browOuterUpRight": (
        "Right eyebrow outer edge raised. "
        "Higher values -> eyebrows up."
    ),

    # mouth
    "jawOpen": (
        "How open the mouth/jaw is. "
        "lower values -> closed mouth, higher values -> open mouth (speaking / surprised)."
    ),

    "mouthSmileLeft": (
        "Left side of the mouth pulling upward into a smile. "
        "Higher values -> smile, both left and right are averaged to determine smile."
    ),

    "mouthSmileRight": (
        "Right side of the mouth pulling upward into a smile. "
        "Higher values -> smile, both left and right are averaged to determine smile."
    ),

    "mouthFrownLeft": (
        "Left side of mouth pulling downward (frown). "
        "Higher values -> frown, both left and right are averaged to determine frown."
    ),

    "mouthFrownRight": (
        "Right side of mouth pulling downward (frown). "
        "Higher values -> frown, both left and right are averaged to determine frown."
    ),

    # eyelids
    "eyeBlinkLeft": (
        "Left eyelid closing. "
        "Higher values -> closed, lower values -> open."
    ),

    "eyeBlinkRight": (
        "Right eyelid closing. "
        "Higher values -> closed, lower values -> open."
    ),

    # eyes
    "leftEyeX": (
        "Horizontal movement of left eye gaze. "
        "0 = neutral center, values shift left/right gaze direction."
    ),

    "rightEyeX": (
        "Horizontal movement of right eye gaze. "
        "0 = neutral center, values shift left/right gaze direction."
    ),

    "leftEyeY": (
        "Vertical movement of left eye gaze. "
        "0 = neutral center, values move up/down gaze direction."
    ),

    "rightEyeY": (
        "Vertical movement of right eye gaze. "
        "0 = neutral center, values move up/down gaze direction."
    ),
}



def processBlendshapes(blendshapes):
    # in the future it might be worth filtering out negligible values. Like less than 0.05 for example. Could save some
    # bandwidth, and it would be easy just to have the server assume any that don't show up are 0.
    return {
        c.category_name: c.score
        for c in blendshapes
        if c.category_name in DESIRED_BLENDSHAPES
    }
