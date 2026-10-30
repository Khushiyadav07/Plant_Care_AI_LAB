import os
from flask import Flask, flash, redirect, url_for
from .db import init_app as init_db

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.environ.get("PLANTCARE_SECRET_KEY", "dev-only-change-this-key-before-deployment"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("PLANTCARE_HTTPS", "0") == "1",
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        UPLOAD_FOLDER=os.path.join(app.root_path, "..", "uploads"),
        MODEL_PATH=os.path.join(app.root_path, "..", "models", "plant_disease_model.keras"),
        CLASS_NAMES_PATH=os.path.join(app.root_path, "..", "models", "class_names.json"),
    )
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "models"), exist_ok=True)
    init_db(app)

    from .auth import bp as auth_bp
    from .main import bp as main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.errorhandler(413)
    def too_large(_error):
        flash("Image is too large. Please upload an image smaller than 8 MB.", "error")
        return redirect(url_for("main.detect"))

    return app
