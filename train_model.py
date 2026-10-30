"""Train a plant-leaf classifier and save a model compatible with the Flask app.

Expected layout: dataset/<class-name>/<image files>.
For best results, use a labelled PlantVillage-style dataset and keep a separate
real-world test set to evaluate performance before relying on predictions.
"""
import argparse
import json
import os
from pathlib import Path

import tensorflow as tf

IMAGE_SIZE = (224, 224)


def main():
    parser = argparse.ArgumentParser(description="Train a transfer-learning plant disease classifier.")
    parser.add_argument("--data", required=True, help="Dataset folder with one subfolder per class")
    parser.add_argument("--epochs", type=int, default=8, help="Training epochs for the classification head")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--weights", choices=("imagenet", "none"), default="imagenet",
                        help="Use ImageNet-pretrained MobileNetV2 weights (downloads once) or train from scratch")
    parser.add_argument("--fine-tune", action="store_true", help="Unfreeze the top MobileNetV2 layers for a short fine-tuning stage")
    parser.add_argument("--output", default="models", help="Folder in which to save the model and class names")
    args = parser.parse_args()

    data_dir = Path(args.data)
    if not data_dir.is_dir():
        raise SystemExit(f"Dataset folder not found: {data_dir.resolve()}")
    class_dirs = sorted(p for p in data_dir.iterdir() if p.is_dir())
    if len(class_dirs) < 2:
        raise SystemExit("Dataset must contain at least two class subfolders.")
    if args.epochs < 1 or args.batch_size < 1:
        raise SystemExit("--epochs and --batch-size must be positive integers.")

    common = dict(directory=str(data_dir), validation_split=0.2, seed=42,
                  image_size=IMAGE_SIZE, batch_size=args.batch_size, label_mode="int")
    train_ds = tf.keras.utils.image_dataset_from_directory(subset="training", **common)
    val_ds = tf.keras.utils.image_dataset_from_directory(subset="validation", **common)
    class_names = train_ds.class_names
    if len(class_names) < 2:
        raise SystemExit("At least two classes are required for classification.")

    autotune = tf.data.AUTOTUNE
    # Avoid caching the entire dataset in RAM; PlantVillage-sized datasets can be large.
    train_ds = train_ds.shuffle(1000).prefetch(autotune)
    val_ds = val_ds.prefetch(autotune)

    weights = "imagenet" if args.weights == "imagenet" else None
    try:
        backbone = tf.keras.applications.MobileNetV2(
            input_shape=(*IMAGE_SIZE, 3), include_top=False, weights=weights
        )
    except Exception as exc:
        raise SystemExit(
            "Could not load MobileNetV2 weights. Check internet access for the first ImageNet-weight download, "
            "or retry with --weights none. Original error: " + str(exc)
        )
    backbone.trainable = False

    inputs = tf.keras.Input(shape=(*IMAGE_SIZE, 3), name="leaf_rgb_0_255")
    augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.06),
        tf.keras.layers.RandomZoom(0.08),
    ], name="training_augmentation")
    x = augmentation(inputs)
    x = tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1, name="mobilenet_preprocessing")(x)
    x = backbone(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(len(class_names), activation="softmax", name="class_probabilities")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
                  loss="sparse_categorical_crossentropy", metrics=["accuracy"])

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "plant_disease_model.keras"
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True),
        tf.keras.callbacks.ModelCheckpoint(str(model_path), monitor="val_accuracy", save_best_only=True),
        tf.keras.callbacks.CSVLogger(str(output_dir / "training_log.csv")),
    ]
    model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=callbacks)

    if args.fine_tune:
        backbone.trainable = True
        # Fine-tune only the last 30 layers; keep batch-normalization layers frozen.
        for layer in backbone.layers[:-30]:
            layer.trainable = False
        for layer in backbone.layers:
            if isinstance(layer, tf.keras.layers.BatchNormalization):
                layer.trainable = False
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
                      loss="sparse_categorical_crossentropy", metrics=["accuracy"])
        model.fit(train_ds, validation_data=val_ds, epochs=max(2, min(5, args.epochs)), callbacks=callbacks)

    model.save(model_path)
    with (output_dir / "class_names.json").open("w", encoding="utf-8") as f:
        json.dump(class_names, f, ensure_ascii=False, indent=2)
    with (output_dir / "model_info.json").open("w", encoding="utf-8") as f:
        json.dump({"architecture": "MobileNetV2 transfer learning", "image_size": list(IMAGE_SIZE),
                   "classes": class_names, "validation_note": "Evaluate on a separate real-world test set before deployment."},
                  f, ensure_ascii=False, indent=2)
    print(f"Saved model: {model_path.resolve()}")
    print(f"Saved class names: {(output_dir / 'class_names.json').resolve()}")


if __name__ == "__main__":
    main()
