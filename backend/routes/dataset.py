from flask import Blueprint, request, jsonify, session, Response
from models import db, FaceDataset
from services.camera import VideoCamera
import os, shutil

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


# ── Stop capture ───────────────────────────────────────────────────────────
@dataset_bp.route("/capture/stop", methods=["POST"])
@login_required
def capture_stop():
    cam.is_capturing = False
    cam.current_user = ""
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

    return Response(
        gen(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            # Ngăn browser cache stream
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma":        "no-cache",
        },
    )