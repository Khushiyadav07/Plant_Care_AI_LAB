# Plant Care AI — Flask + SQLite

A responsive plant-care web application with account registration, private scan history, a garden dashboard, leaf-colour stress mapping, a health indicator, and a TensorFlow image-classification pipeline.

> **Important AI note:** this ZIP does not include a trained model or a labelled training dataset. The website runs without model files and will clearly tell you that disease classification is not enabled yet. To enable real disease predictions, train a model from labelled leaf images using the instructions below. It never fabricates a disease result.

## Included features

- Register/login with hashed passwords and user-specific scan history
- SQLite database created and migrated automatically
- Upload PNG, JPG/JPEG, or WEBP leaf images (maximum 8 MB)
- TensorFlow/Keras model loading with cached inference
- Model confidence, care suggestions, and a 7-day action plan
- Browser-side leaf colour stress map (a visual clue, **not** a disease diagnosis)
- Living Garden page with plant records, health trends, and badges
- Responsive interface and input validation
- Tests for home page, registration, scan flow, and garden dashboard

## Windows setup (recommended: Python 3.11, 64-bit)

1. Install **Python 3.11 (64-bit)** from python.org. During installation, tick **Add Python to PATH**.
2. Extract the ZIP to a normal folder, for example `C:\Plant_Care_AI_Lab`. Avoid running it directly inside the ZIP.
3. Open that folder in File Explorer. Click the address bar, type `cmd`, and press Enter.
4. Create and activate a virtual environment:

   ```bat
   py -3.11 -m venv .venv
   .venv\Scripts\activate
   python -m pip install --upgrade pip
   ```

5. Install packages:

   ```bat
   pip install -r requirements.txt
   ```

   TensorFlow is a large dependency; installation can take several minutes. If `py -3.11` is not found, install Python 3.11 64-bit and reopen Command Prompt.

6. Start the app:

   ```bat
   python run.py
   ```

7. Open **http://127.0.0.1:5000** in Chrome or Edge. Register a new account, then use **Scan**.
8. Stop the server with `Ctrl+C` in the Command Prompt.

### If you get `No module named flask` or `No module named tensorflow`

Make sure the terminal shows `(.venv)` at the beginning of the prompt. If it does not, run `.venv\Scripts\activate`, then run `pip install -r requirements.txt` again.

### If port 5000 is already in use

In Command Prompt, run:

```bat
set PORT=5001
python run.py
```

Then open `http://127.0.0.1:5001`.

## Enable actual AI disease predictions

The model must be trained on a labelled image dataset. A suitable dataset has one subfolder per class, with leaf photos inside each folder. For example:

```text
dataset/
  APPLE___Early_blight/
    image001.jpg
    image002.jpg
  Bell_pepper___healthy/
    image003.jpg
  Potato___Late_blight/
    image004.jpg
  Potato___healthy/
    image005.jpg
```

Use a legitimate, labelled dataset such as PlantVillage or another appropriately licensed dataset. Make sure every class has enough images for a training/validation split and that class labels are correct. Do not use a folder of unlabeled mixed images.

With the virtual environment activated and the terminal at the project root, run:

```bat
python train_model.py --data dataset --epochs 8 --batch-size 16
```

The default training uses MobileNetV2 transfer learning and downloads ImageNet weights on the first run, so internet access is required for that initial download. To train without downloading those weights (usually much less accurate unless you have a large dataset), use:

```bat
python train_model.py --data dataset --epochs 12 --batch-size 16 --weights none
```

Optional fine-tuning:

```bat
python train_model.py --data dataset --epochs 8 --batch-size 16 --fine-tune
```

The script saves these files in `models/`:

- `plant_disease_model.keras` — trained model
- `class_names.json` — class names in the model's output order
- `model_info.json` — model metadata
- `training_log.csv` — epoch metrics

Restart the web app after training and the Detect page should show that the disease model is available. Keep the model and `class_names.json` from the same training run. Training accuracy alone does not establish real-world accuracy; evaluate with a separate test set of photos taken in real conditions before presenting predictions as reliable.

## Run tests

Install dependencies, activate `.venv`, then run:

```bat
python -m unittest discover -s tests -v
```

## Project structure

```text
app/
  __init__.py       Flask app factory and configuration
  auth.py           Registration, login, logout
  db.py             SQLite schema, migrations, connection lifecycle
  main.py           Dashboard, detection, garden, history, result routes
  templates/        Jinja pages
  static/           CSS and JavaScript
models/             Trained model files (created by train_model.py)
instance/           SQLite database (created automatically)
uploads/            Private uploaded images
train_model.py      Model training script
run.py              Development server entry point
requirements.txt    Python dependencies
```

## Troubleshooting the common import error

If you see an import traceback, copy the **last 10–20 lines** from the terminal. The first line often only says where the app started; the last line usually names the missing module or exact failing import.

## Responsible use

Predictions are advisory and may be wrong for unfamiliar plant species, poor lighting, backgrounds unlike the training set, or diseases absent from the dataset. A photo alone is not a laboratory diagnosis. Confirm serious plant-health issues with a local agricultural expert and use only locally approved treatments.
