from flask import Blueprint, request, jsonify, session, Response
from models import db, FaceDataset
from services.camera import VideoCamera
import os, shutil
import json
import cv2
import numpy as np
from config import Config
from services.embedding_helper import EmbeddingModel
from services.face_preprocessing import detect_and_align_face

cam = VideoCamera()
dataset_bp = Blueprint("dataset", __name__)


def login_required(f):
    import functools
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper


def _normalize_embedding(embedding):
    embedding = np.asarray(embedding, dtype=np.float32)
    return embedding / (np.linalg.norm(embedding) + 1e-8)


def _extract_training_embedding(face_model, img):
    if img is None:
        return None

    face_img = img
    if img.shape[:2] != (112, 112):
        aligned = detect_and_align_face(img, score_threshold=0.75, output_size=(112, 112))
        if aligned is not None:
            face_img = aligned

    emb = face_model.extract_embedding(face_img)
    if emb is None:
        return None
    return _normalize_embedding(emb)


def _build_embedding_template(embeddings):
    embeddings = np.asarray(embeddings, dtype=np.float32)
    embeddings = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
    all_embeddings = embeddings

    centroid = _normalize_embedding(np.mean(embeddings, axis=0))
    sims = embeddings @ centroid

    if len(embeddings) >= 5:
        cutoff = max(0.30, float(np.percentile(sims, 20)))
        keep_mask = sims >= cutoff
        if np.count_nonzero(keep_mask) >= 3:
            embeddings = embeddings[keep_mask]
            sims = sims[keep_mask]
            centroid = _normalize_embedding(np.mean(embeddings, axis=0))
            sims = embeddings @ centroid

    sample_sims = all_embeddings @ centroid
    order = np.argsort(sample_sims)[::-1]
    max_samples = min(Config.FACE_TEMPLATE_MAX_SAMPLES, len(order))
    selected = all_embeddings[order[:max_samples]]

    return {
        "version": 2,
        "count": int(len(all_embeddings)),
        "centroid_count": int(len(embeddings)),
        "centroid": centroid.tolist(),
        "samples": selected.tolist(),
        "quality": {
            "min_similarity": float(np.min(sims)),
            "mean_similarity": float(np.mean(sims)),
            "max_similarity": float(np.max(sims)),
        },
    }


# ── Lấy danh sách dataset ──────────────────────────────────────────────────
@dataset_bp.route("/", methods=["GET"])
@login_required
def get_datasets():
    datasets = FaceDataset.query.filter_by(user_id=session["user_id"]).all()
    return jsonify([{
        "id":          d.id,
        "name":        d.name,
        "photo_count": d.photo_count,
        "created_at":  d.created_at.isoformat(),
    } for d in datasets])


# ── Thêm dataset ───────────────────────────────────────────────────────────
@dataset_bp.route("/", methods=["POST"])
@login_required
def add_dataset():
    name = (request.json or {}).get("name", "").strip()
    if not name:
        return jsonify({"error": "Tên không được để trống"}), 400
    if FaceDataset.query.filter_by(name=name).first():
        return jsonify({"error": "Tên đã tồn tại"}), 400
    ds = FaceDataset(user_id=session["user_id"], name=name)
    db.session.add(ds)
    db.session.commit()
    os.makedirs(f"captured_faces/{name}", exist_ok=True)
    return jsonify({"status": "ok", "id": ds.id, "name": ds.name})


# ── Đổi tên dataset ────────────────────────────────────────────────────────
@dataset_bp.route("/<int:ds_id>", methods=["PUT"])
@login_required
def rename_dataset(ds_id):
    ds = FaceDataset.query.filter_by(id=ds_id, user_id=session["user_id"]).first_or_404()
    new_name = (request.json or {}).get("name", "").strip()
    if not new_name:
        return jsonify({"error": "Tên không hợp lệ"}), 400
    if FaceDataset.query.filter_by(name=new_name).first():
        return jsonify({"error": "Tên đã tồn tại"}), 400
    old_path = f"captured_faces/{ds.name}"
    new_path = f"captured_faces/{new_name}"
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
    ds.name = new_name
    db.session.commit()
    return jsonify({"status": "ok"})


# ── Xoá dataset ────────────────────────────────────────────────────────────
@dataset_bp.route("/<int:ds_id>", methods=["DELETE"])
@login_required
def delete_dataset(ds_id):
    ds = FaceDataset.query.filter_by(id=ds_id, user_id=session["user_id"]).first_or_404()
    # Nếu đang capture dataset này thì dừng lại
    if cam.current_user == ds.name:
        cam.is_capturing = False
        cam.current_user = ""
    path = f"captured_faces/{ds.name}"
    if os.path.exists(path):
        shutil.rmtree(path)
    db.session.delete(ds)
    db.session.commit()
    return jsonify({"status": "ok"})


# ── Start capture ──────────────────────────────────────────────────────────
@dataset_bp.route("/capture/start", methods=["POST"])
@login_required
def capture_start():
    name = (request.json or {}).get("name", "").strip()
    if not name:
        return jsonify({"error": "Thiếu tên"}), 400
    # Kiểm tra dataset thuộc user hiện tại
    ds = FaceDataset.query.filter_by(name=name, user_id=session["user_id"]).first()
    if not ds:
        return jsonify({"error": "Dataset không tồn tại"}), 404
    cam.current_user = name
    cam.is_capturing = True
    return jsonify({"status": "ok"})


# ── Stop capture & Trích xuất Embedding ────────────────────────────────────
@dataset_bp.route("/capture/stop", methods=["POST"])
@login_required
def capture_stop():
    user_name = cam.current_user
    cam.is_capturing = False
    cam.current_user = ""
    
    # Nếu đang có người được chụp, tiến hành trích xuất đặc trưng ngay
    if user_name:
        ds = FaceDataset.query.filter_by(name=user_name, user_id=session["user_id"]).first()
        if ds:
            face_model = EmbeddingModel.get_instance()
            path = f"captured_faces/{ds.name}"
            embeddings = []
            
            # Quét ảnh vừa chụp
            if os.path.exists(path):
                for fname in os.listdir(path):
                    if fname.endswith(".jpg"):
                        fpath = os.path.join(path, fname)
                        img = cv2.imread(fpath)
                        emb = _extract_training_embedding(face_model, img)
                        if emb is not None:
                            embeddings.append(emb)
            
            if embeddings:
                ds.embedding = json.dumps(_build_embedding_template(embeddings))
                db.session.commit()
                print(f"[INFO] Đã lưu embedding cho {ds.name} thành công!")

    return jsonify({"status": "ok"})


# ── Trạng thái capture (để frontend polling) ───────────────────────────────
@dataset_bp.route("/capture/status", methods=["GET"])
@login_required
def capture_status():
    return jsonify({
        "is_capturing": cam.is_capturing,
        "current_user": cam.current_user,
    })


# ── Video stream ───────────────────────────────────────────────────────────
@dataset_bp.route("/stream")
@login_required
def stream():
    def gen():
        cam.active_viewers += 1
        try:
            while True:
                frame = cam.get_frame()
                if frame:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + frame
                        + b"\r\n"
                    )
        except GeneratorExit:
            # Client đã ngắt kết nối — không làm gì thêm
            pass
        finally:
            cam.active_viewers -= 1
            if cam.active_viewers <= 0:
                cam.release_camera()

    return Response(
        gen(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            # Ngăn browser cache stream
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma":        "no-cache",
        },
    )
