################################################################################
# This is not useful rn, use gen_unique_anims.py
############################################################################


import os
import json
import itertools

BASE_PATH = "Characters/Animations/RealFacialAnimations"

FOLDER_ORDER = [
    "Eyes",
    "LeftEyelid",
    "RightEyelid",
    "Brows",
    "Mouth"
]

def strip_ext(name):
    return os.path.splitext(name)[0]

def main():
    print("Input Root Folder and Press Enter")

    root = input()
    print("Input Output Path and Press Enter")
    output = input()
    print("Generating Animations Json")


    animations_by_folder = []

    for folder in FOLDER_ORDER:
        folder_path = os.path.join(root, folder)

        if not os.path.isdir(folder_path):
            print(f"Missing folder: {folder_path}")
            continue

        files = [
            f for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]

        if not files:
            print(f"No animations found in {folder}")
            continue

        animations_by_folder.append([
            {
                "folder": folder,
                "file": f
            }
            for f in sorted(files)  # also stable file order
        ])

    result = {}

    for combo in itertools.product(*animations_by_folder):
        key = "_".join(strip_ext(a["file"]) for a in combo)

        result[key] = {
            "Animations": [
                {
                    "Animation": f"{BASE_PATH}/{a['folder']}/{a['file']}",
                    "Looping": True
                }
                for a in combo
            ]
        }

    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Generated {len(result)} combinations into {output}")

if __name__ == "__main__":
    main()