# backend/ml_models/model_manager.py
# Saves and loads trained ML models to/from disk using joblib
# Avoids retraining on every request

import os
import json
import joblib

from datetime import datetime, timezone


MODELS_DIR = os.path.join(
    os.path.dirname(__file__),
    '..',
    'saved_models'
)


# ============================================================
# DIRECTORY
# ============================================================

def _ensure_dir():
    """Create saved_models directory if it doesn't exist."""
    os.makedirs(
        MODELS_DIR,
        exist_ok=True
    )


# ============================================================
# PATH HELPERS
# ============================================================

def _model_path(user_id, model_name):
    return os.path.join(
        MODELS_DIR,
        f"user_{user_id}_{model_name}.joblib"
    )


def _meta_path(user_id, model_name):
    return os.path.join(
        MODELS_DIR,
        f"user_{user_id}_{model_name}_meta.json"
    )


# ============================================================
# SAVE MODEL
# ============================================================

def save_model(
    user_id,
    model_name,
    model_object,
    metadata=None
):
    """
    Save a trained model to disk.

    Also saves metadata such as:
    - user id
    - model name
    - training timestamp
    - model version
    """

    _ensure_dir()

    try:

        # Save model
        joblib.dump(
            model_object,
            _model_path(
                user_id,
                model_name
            )
        )


        # Use timezone-aware UTC timestamp.
        # datetime.utcnow() is deprecated.
        meta = {
            'user_id': user_id,
            'model_name': model_name,
            'trained_at': (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            'model_version': '1.0'
        }


        if metadata:
            meta.update(
                metadata
            )


        with open(
            _meta_path(
                user_id,
                model_name
            ),
            'w',
            encoding='utf-8'
        ) as f:

            json.dump(
                meta,
                f,
                indent=2,
                default=str
            )


        return True


    except Exception as e:

        print(
            f"[ModelManager] "
            f"Save failed for {model_name}: {e}"
        )

        return False


# ============================================================
# LOAD MODEL
# ============================================================

def load_model(
    user_id,
    model_name
):
    """
    Load a trained model from disk.

    Returns:
        (model_object, metadata)

    Returns:
        (None, None)
    if model does not exist or loading fails.
    """

    path = _model_path(
        user_id,
        model_name
    )


    if not os.path.exists(
        path
    ):
        return None, None


    try:

        model = joblib.load(
            path
        )


        meta = {}

        meta_path = _meta_path(
            user_id,
            model_name
        )


        if os.path.exists(
            meta_path
        ):

            with open(
                meta_path,
                encoding='utf-8'
            ) as f:

                meta = json.load(
                    f
                )


        return model, meta


    except Exception as e:

        print(
            f"[ModelManager] "
            f"Load failed for {model_name}: {e}"
        )

        return None, None


# ============================================================
# MODEL FRESHNESS
# ============================================================

def is_model_fresh(
    user_id,
    model_name,
    max_age_hours=24
):
    """
    Check if a saved model is recent enough to use.

    Returns True when the model was trained within
    max_age_hours.
    """

    _, meta = load_model(
        user_id,
        model_name
    )


    if not meta or 'trained_at' not in meta:
        return False


    try:

        trained_at = datetime.fromisoformat(
            meta['trained_at']
        )


        # Compatibility with older metadata files
        # that may contain a naive timestamp.
        if trained_at.tzinfo is None:

            trained_at = trained_at.replace(
                tzinfo=timezone.utc
            )


        now_utc = datetime.now(
            timezone.utc
        )


        age_hours = (
            now_utc - trained_at
        ).total_seconds() / 3600


        return (
            age_hours < max_age_hours
        )


    except Exception:

        return False


# ============================================================
# DELETE USER MODELS
# ============================================================

def delete_user_models(
    user_id
):
    """
    Delete all saved models belonging to a user.
    Used when an account is deleted.
    """

    _ensure_dir()

    deleted = 0


    for filename in os.listdir(
        MODELS_DIR
    ):

        if filename.startswith(
            f"user_{user_id}_"
        ):

            path = os.path.join(
                MODELS_DIR,
                filename
            )


            try:

                if os.path.isfile(
                    path
                ):

                    os.remove(
                        path
                    )

                    deleted += 1

            except OSError as e:

                print(
                    f"[ModelManager] "
                    f"Delete failed for {filename}: {e}"
                )


    return deleted


# ============================================================
# LIST USER MODELS
# ============================================================

def list_user_models(
    user_id
):
    """List all saved models for a user."""

    _ensure_dir()

    models = []


    for filename in os.listdir(
        MODELS_DIR
    ):

        if (
            filename.startswith(
                f"user_{user_id}_"
            )
            and filename.endswith(
                '_meta.json'
            )
        ):

            path = os.path.join(
                MODELS_DIR,
                filename
            )


            try:

                with open(
                    path,
                    encoding='utf-8'
                ) as mf:

                    meta = json.load(
                        mf
                    )


                models.append(
                    meta
                )


            except (
                OSError,
                ValueError,
                TypeError
            ):

                # Ignore malformed metadata files
                # and continue listing other models.
                pass


    return models