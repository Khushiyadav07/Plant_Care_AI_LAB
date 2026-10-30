import os
import csv
import io
import json
import uuid
import numpy as np
from functools import wraps
from PIL import Image, UnidentifiedImageError
from flask import current_app
from flask import (Blueprint, flash, redirect, render_template, request, session, url_for, send_from_directory, abort, make_response)
from werkzeug.utils import secure_filename
from .db import get_db

ALLOWED = {"png", "jpg", "jpeg", "webp"}

def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED

def unique_name(name):
    return f"{uuid.uuid4().hex}_{secure_filename(name)}"

bp = Blueprint("main", __name__)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

CARE_ADVICE = {
    "healthy": "The model classifies this leaf as healthy. Keep a consistent watering routine, provide suitable sunlight, and inspect leaves regularly.",
    "early blight": "Remove affected leaves, avoid overhead watering, improve airflow, and rotate crops. Confirm the diagnosis before applying any treatment.",
    "late blight": "Separate affected plants where practical, avoid wetting foliage, remove severely affected material safely, and seek local agricultural guidance promptly.",
    "powdery mildew": "Improve airflow and spacing, remove heavily affected leaves, and avoid excessive nitrogen. Use only locally approved treatments if needed.",
    "leaf mold": "Improve ventilation, avoid overhead irrigation, and remove infected plant debris. Check crop-specific guidance before treatment.",
    "bacterial": "Avoid handling wet plants, disinfect tools, remove badly affected material, and avoid overhead watering. A photo alone cannot confirm bacterial disease.",
    "mosaic virus": "Remove severely affected plants where advised, control insect vectors, clean tools, and use certified disease-free seed or planting material.",
}

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped

def advice_for(label):
    lower = label.lower()
    for key, advice in CARE_ADVICE.items():
        if key in lower:
            return advice
    return "This is an AI-assisted result, not a laboratory diagnosis. Inspect the plant, avoid spreading possible infection, and consult a local agricultural expert before applying chemicals."

PLANS = {
    "healthy": ("Keep your watering rhythm and rotate the pot or bed for even light.", "Check leaf undersides for pests and eggs.", "Re-scan to confirm health holds steady."),
    "early blight": ("Remove spotted leaves and bag them (don't compost).", "Water only at the base and mulch to stop soil splash.", "Re-scan. If spots keep spreading, ask a local expert about approved treatments."),
    "late blight": ("Isolate the plant and remove badly affected foliage safely.", "Keep foliage dry and improve airflow.", "Re-scan and seek local agricultural guidance promptly if it spreads."),
    "powdery mildew": ("Prune crowded growth and remove heavily coated leaves.", "Water the soil, not the leaves, early in the day.", "Re-scan; use only locally approved treatments if needed."),
    "leaf mold": ("Open up ventilation and remove infected debris.", "Stop overhead watering and lower humidity.", "Re-scan and compare the stress map."),
    "bacterial": ("Disinfect tools and avoid touching wet plants.", "Remove badly affected material and keep leaves dry.", "Re-scan; photo alone can't confirm bacterial disease, so consult an expert."),
    "mosaic virus": ("Remove severely affected plants if advised and clean tools.", "Control aphids and other insect vectors.", "Use certified disease-free planting material next season."),
}
DEFAULT_PLAN = ("Isolate the plant and photograph it daily.", "Remove badly affected leaves and sanitise tools.", "Re-scan. If it worsens, consult a local agricultural expert.")
_MODEL = {}

def plan_for(label):
    lower = label.lower()
    steps = next((v for k, v in PLANS.items() if k in lower), DEFAULT_PLAN)
    return list(zip(("Today", "Day 3", "Day 7"), steps))

def health_score(green, yellow, brown, confidence, label, have_vitals):
    score = 100 - 1.2 * yellow - 2.2 * brown if have_vitals else 100
    if confidence > 0 and "healthy" not in label.lower():
        score -= 30 * confidence
    return int(max(1, min(100, round(score))))

def _pct(name):
    try:
        return max(0.0, min(100.0, round(float(request.form.get(name, "")), 1)))
    except (TypeError, ValueError):
        return None

def _plant_names():
    rows = get_db().execute("SELECT DISTINCT plant_name FROM predictions WHERE user_id=? ORDER BY plant_name", (session["user_id"],)).fetchall()
    return [r["plant_name"] for r in rows]

def _model_ready():
    return os.path.exists(current_app.config["MODEL_PATH"]) and os.path.exists(current_app.config["CLASS_NAMES_PATH"])

def predict_image(path):
    model_path = current_app.config["MODEL_PATH"]
    names_path = current_app.config["CLASS_NAMES_PATH"]
    if not (os.path.exists(model_path) and os.path.exists(names_path)):
        return None, None, "The website is running, but no trained AI model is installed yet. Follow the README instructions to train a model; no fake prediction has been generated."
    try:
        import tensorflow as tf
        model = _MODEL.get(model_path)
        if model is None:
            model = tf.keras.models.load_model(model_path)
            _MODEL[model_path] = model
        with open(names_path, "r", encoding="utf-8") as f:
            class_names = json.load(f)
        if not isinstance(class_names, list) or not class_names:
            raise ValueError("class_names.json must contain a non-empty JSON list")
        with Image.open(path) as source:
            image = source.convert("RGB").resize((224, 224))
            # train_model.py uses a Rescaling layer inside the saved model, so
            # inference passes the original 0-255 RGB pixel values.
            array = np.asarray(image, dtype=np.float32)
        probabilities = np.asarray(model.predict(np.expand_dims(array, 0), verbose=0)[0])
        if probabilities.ndim != 1 or len(probabilities) != len(class_names):
            raise ValueError("The model output size does not match class_names.json")
        idx = int(np.argmax(probabilities))
        return str(class_names[idx]), float(probabilities[idx]), None
    except Exception as exc:
        current_app.logger.exception("Model prediction failed")
        return None, None, "The model could not process this image. Check that the model and class_names.json were created together by train_model.py. See the terminal log for technical details."

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM predictions WHERE user_id=?", (session["user_id"],)).fetchone()["n"]
    recent = db.execute("SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC LIMIT 5", (session["user_id"],)).fetchall()
    avg = db.execute("SELECT AVG(health) AS a FROM predictions WHERE user_id=? AND health>0", (session["user_id"],)).fetchone()["a"]
    return render_template("dashboard.html", total=total, recent=recent, avg=round(avg) if avg else None)

@bp.route("/detect", methods=["GET", "POST"])
@login_required
def detect():
    ctx = dict(model_error=None, model_ready=_model_ready(), plants=_plant_names())
    if request.method == "POST":
        uploaded = request.files.get("leaf_image")
        if not uploaded or not uploaded.filename:
            flash("Choose a leaf image first.", "error")
            return redirect(url_for("main.detect"))
        original = secure_filename(uploaded.filename)
        ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
        if ext not in ALLOWED_EXTENSIONS:
            flash("Use a PNG, JPG, JPEG, or WEBP image.", "error")
            return redirect(url_for("main.detect"))
        filename = uuid.uuid4().hex + "." + ext
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        try:
            uploaded.save(path)
            with Image.open(path) as img:
                img.verify()
        except (UnidentifiedImageError, OSError):
            if os.path.exists(path):
                os.remove(path)
            flash("That file is not a valid image. Please try another photo.", "error")
            return redirect(url_for("main.detect"))

        label, confidence, error = predict_image(path)
        green, yellow, brown = _pct("green"), _pct("yellow"), _pct("brown")
        have_vitals = None not in (green, yellow, brown)
        if error and not have_vitals:
            os.remove(path)
            return render_template("detect.html", **{**ctx, "model_error": error})
        if not have_vitals:
            green = yellow = brown = 0.0
        if error:  # no disease model: honest vitals-only scan, nothing is faked
            label, confidence = "Vitals scan", 0.0
            advice = ("This is a colour-vitals scan, not a disease diagnosis. Yellowing often points to water, light or nutrient stress; "
                      "brown patches can mean sunburn, drought or infection. Install a trained model to get disease names.")
        else:
            advice = advice_for(label)
        health = health_score(green, yellow, brown, confidence, label, have_vitals)
        plant = request.form.get("plant_name", "").strip()[:40] or "My plant"
        db = get_db()
        cur = db.execute(
            "INSERT INTO predictions(user_id, image_filename, predicted_class, confidence, advice, plant_name, green, yellow, brown, health) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (session["user_id"], filename, label, confidence, advice, plant, green, yellow, brown, health)
        )
        db.commit()
        return redirect(url_for("main.result", prediction_id=cur.lastrowid))
    return render_template("detect.html", **ctx)

@bp.route("/garden")
@login_required
def garden():
    rows = [r for r in get_db().execute("SELECT * FROM predictions WHERE user_id=? ORDER BY id", (session["user_id"],)).fetchall() if r["health"] > 0]
    groups = {}
    for r in rows:
        groups.setdefault(r["plant_name"], []).append(r)
    plants = []
    for name, items in groups.items():
        hs = [i["health"] for i in items][-12:]
        n = len(hs)
        pts = " ".join(f"{i * 100 / (n - 1):.1f},{30 - hs[i] * 0.28:.1f}" for i in range(n)) if n > 1 else ""
        plants.append(dict(name=name, scans=len(items), latest=items[-1], health=hs[-1], pts=pts, delta=hs[-1] - hs[0] if n > 1 else 0))
    plants.sort(key=lambda p: -p["latest"]["id"])
    best = max((r["health"] for r in rows), default=0)
    badges = [("🌱", "First Sprout", "Run your first scan", len(rows) >= 1), ("🔬", "Plant Detective", "Run 5 scans", len(rows) >= 5),
              ("🌟", "Thriving", "Log a 90+ health score", best >= 90), ("🏡", "Garden Keeper", "Track 3 different plants", len(groups) >= 3)]
    avg = round(sum(r["health"] for r in rows) / len(rows)) if rows else 0
    return render_template("garden.html", plants=plants, badges=badges, avg=avg, total=len(rows))

@bp.route("/result/<int:prediction_id>")
@login_required
def result(prediction_id):
    item = get_db().execute(
        "SELECT * FROM predictions WHERE id=? AND user_id=?",
        (prediction_id, session["user_id"])
    ).fetchone()
    if item is None:
        abort(404)
    label = item["predicted_class"].replace("___", " — ").replace("_", " ")
    key = "healthy" if item["confidence"] <= 0 and item["health"] >= 80 else item["predicted_class"]
    return render_template("result.html", item=item, label=label, plan=plan_for(key))

@bp.route("/history")
@login_required
def history():
    rows = get_db().execute(
        "SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    return render_template("history.html", rows=rows)

@bp.route("/history/export")
@login_required
def export_history():
    rows = get_db().execute(
        "SELECT plant_name, predicted_class, confidence, health, green, yellow, brown, advice, created_at "
        "FROM predictions WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["Plant", "Prediction", "Model confidence (%)", "Health score", "Green (%)",
                     "Yellow (%)", "Brown (%)", "Care advice", "Created at"])
    for row in rows:
        writer.writerow([row["plant_name"], row["predicted_class"], round(row["confidence"] * 100, 1),
                         row["health"], row["green"], row["yellow"], row["brown"], row["advice"], row["created_at"]])
    response = make_response("\ufeff" + stream.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=plant-care-history.csv"
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    # Only allow the current user's images to be served.
    row = get_db().execute(
        "SELECT id FROM predictions WHERE user_id=? AND image_filename=?",
        (session["user_id"], filename)
    ).fetchone()
    if row is None:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
from flask import Blueprint, jsonify, request

@bp.route('/api/generate-plan', methods=['POST'])
def generate_weekly_plan():
    data = request.get_json() or {}
    plant_name = data.get('plant_name', 'Houseplant')
    condition = data.get('condition', 'Healthy')

    # Example template schedule (or call Gemini/OpenAI API here)
    schedule = {
        "Monday": [f"Check {plant_name} soil moisture (water if top 2 inches are dry)"],
        "Tuesday": ["Mist leaves for humidity"],
        "Wednesday": ["Rotate pot 90° for even sun exposure"],
        "Thursday": ["Check undersides of leaves for pests"],
        "Friday": ["Light watering if required"],
        "Saturday": ["Wipe down leaves with a damp cloth"],
        "Sunday": [f"Inspect condition ({condition}) & record growth"]
    }
    return jsonify({"plant": plant_name, "schedule": schedule})