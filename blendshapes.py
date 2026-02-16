
DESIRED_BLENDSHAPES = [
    "browInnerUp", "browDownLeft", "browDownRight", "browOuterUpLeft", "browOuterUpRight",
    "jawOpen", "mouthLeft", "mouthRight", "mouthFrownLeft", "mouthFrownRight",
    "eyeBlinkLeft", "eyeBlinkRight"
]



def processBlendshapes(blendshapes):
    # in the future it might be worth filtering out negligible values. Like less than 0.05 for example. Could save some
    # bandwidth, and it would be easy just to have the server assume any that don't show up are 0.
    return {
        c.category_name: c.score
        for c in blendshapes
        if c.category_name in DESIRED_BLENDSHAPES
    }
