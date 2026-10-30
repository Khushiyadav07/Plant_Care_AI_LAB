import os
import numpy as np
from PIL import Image

classes = {
    "Healthy_Leaf": (45, 160, 60),        # Rich green
    "Yellow_Chlorosis": (210, 195, 50),   # Yellowed leaf
    "Early_Blight_Spot": (120, 85, 45),   # Brown lesions
    "Bacterial_Leaf_Spot": (90, 110, 50)  # Spotted dark green/brown
}

base_dir = "sample_dataset"
for cls_name, (r, g, b) in classes.items():
    folder = os.path.join(base_dir, cls_name)
    os.makedirs(folder, exist_ok=True)
    for i in range(25):  # 25 images per class
        noise = np.random.randint(-25, 25, (224, 224, 3))
        img_array = np.clip(np.array([r, g, b]) + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(img_array)
        img.save(os.path.join(folder, f"img_{i}.jpg"))

print("Sample dataset created in ./sample_dataset!")