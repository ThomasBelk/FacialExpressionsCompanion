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
    try:
        print("Input Root Folder and Press Enter")
        root = input().strip()

        print("Input Output Index JSON Path and Press Enter")
        output = input().strip()

        print("Generating Animations Json")

        generated_dir = os.path.join(root, "Generated")
        os.makedirs(generated_dir, exist_ok=True)

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
                for f in sorted(files)
            ])

        result = {}

        for combo in itertools.product(*animations_by_folder):
            key = "_".join(strip_ext(a["file"]) for a in combo)
            out_anim_path = os.path.join(generated_dir, f"{key}.blockyanim")

            combined_node_animations = {}

            # 🔹 Load base animation (first in combo)
            base = combo[0]
            base_path = os.path.join(root, base["folder"], base["file"])

            with open(base_path, "r", encoding="utf-8") as f:
                combined_anim = json.load(f)

            # Remove base nodeAnimations — we will rebuild it
            combined_anim["nodeAnimations"] = {}

            # 🔹 Merge nodeAnimations from all animations in combo
            for a in combo:
                src_path = os.path.join(root, a["folder"], a["file"])

                with open(src_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                node_anims = data.get("nodeAnimations", {})

                for node, anim in node_anims.items():
                    combined_anim["nodeAnimations"][node] = anim

            # 🔹 Write combined .blockyanim
            with open(out_anim_path, "w", encoding="utf-8") as f:
                json.dump(combined_anim, f, indent=2)

            # 🔹 Index entry
            result[key] = {
                "Animations": [
                    {
                        "Animation": f"{BASE_PATH}/Generated/{key}.blockyanim"
                    }
                ]
            }

        with open(output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        print(f"Generated {len(result)} combinations into {output}")

    except Exception as e:
        print("Error:", e)
        print("Restarting Program. Press CTRL+C to stop")
        main()

if __name__ == "__main__":
    main()
