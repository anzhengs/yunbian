# python/app.py
from flask import Flask, request, jsonify, send_from_directory, send_file
import os
import io
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import importlib
import pkgutil
import threading
import time
import sys
import subprocess
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_DIR = os.path.join(BASE_DIR, 'html')
HTML_FILES_DIR = os.path.join(HTML_DIR, 'html_files')
CSS_DIR = os.path.join(HTML_DIR, 'css_files')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
RESULT_DIR = os.path.join(BASE_DIR, 'result')
PROCESSORS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processors')

for dir_path in [UPLOAD_DIR, RESULT_DIR]:
    os.makedirs(dir_path, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# ============ 任务注册表（保留，兼容历史查询） ============
task_lock = threading.Lock()
TASK_REGISTRY: Dict[str, dict] = {}

# ============ 设备名称配置 ============
# ★ 在此自定义每个设备的显示名称，未配置的默认显示为"设备 X"
DEVICE_NAMES = {
    1: "192.168.40.101",
    2: "192.168.40.102", 
    3: "192.168.40.103",
    4: "192.168.40.104",
    5: "192.168.40.105",
    6: "192.168.40.106",
    7: "192.168.40.107",
    8: "192.168.40.108",
    9: "192.168.40.109",
    10: "192.168.40.110",
}

# ============ 设备注册表（新增，10个固定槽位） ============
DEVICE_LOCK = threading.Lock()
DEVICE_REGISTRY: Dict[int, dict] = {
    i: {
        "device_id": i,
        "display_name": DEVICE_NAMES.get(i, f"设备 {i}"),  # ★ 新增：优先使用映射表名称
        "status": "idle",       # idle | pending | processing | done | error
        "task_id": None,
        "result": None,
        "image_url": None,
        "filename": None,
        "error": None,
        "last_seen": None,
        "connected": False,
    }
    for i in range(1, 11)       # 设备 1~10
}

PROCESSOR_EXECUTOR = ThreadPoolExecutor(max_workers=4)

LATEST_TASK_LOCK = threading.Lock()
LATEST_TASK_ID = None

PROCESSORS: Dict[str, Dict] = {}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload_file():
    global LATEST_TASK_ID

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '请求中未包含文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    # ★ 读取固定设备ID（必传，1~10）
    device_id = request.form.get('device_id', type=int)
    if device_id is None or device_id < 1 or device_id > 10:
        return jsonify({'success': False, 'message': 'device_id 必须为 1~10 的整数'}), 400

    if file and allowed_file(file.filename):
        try:
            task_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            unique_id = task_id[:8]
            filename = secure_filename(file.filename)
            name, ext = os.path.splitext(filename)
            # ★ 文件名含 device_id，便于溯源
            new_filename = f"{timestamp}_dev{device_id}_{unique_id}{ext}"

            file_path = os.path.join(UPLOAD_DIR, new_filename)
            file.save(file_path)

            # 注册到任务表
            with task_lock:
                TASK_REGISTRY[task_id] = {
                    "status": "pending",
                    "result": None,
                    "error": None,
                    "filename": new_filename,
                    "created_at": time.time(),
                    "device_id": device_id,
                }

            with LATEST_TASK_LOCK:
                LATEST_TASK_ID = task_id

            # ★ 更新设备注册表为"排队中"
            with DEVICE_LOCK:
                DEVICE_REGISTRY[device_id] = {
                    "device_id": device_id,
                    "status": "pending",
                    "task_id": task_id,
                    "result": None,
                    "image_url": f"/uploads/{new_filename}",
                    "filename": new_filename,
                    "error": None,
                    "last_seen": time.time(),
                    "connected": True,
                }

            # ★ 传入 device_id
            PROCESSOR_EXECUTOR.submit(_process_single_image, task_id, file_path, new_filename, device_id)

            return jsonify({
                'success': True,
                'message': '文件上传成功，已提交处理',
                'task_id': task_id,
                'device_id': device_id,
                'filename': new_filename,
                'url': f"/uploads/{new_filename}"
            })
        except Exception as e:
            app.logger.error(f"文件上传失败: {str(e)}")
            return jsonify({'success': False, 'message': f'上传失败：{str(e)}'}), 500

    return jsonify({
        'success': False,
        'message': f'不支持的文件格式，允许的格式：{ALLOWED_EXTENSIONS}'
    }), 400


def _process_single_image(task_id: str, src_path: str, filename: str, device_id: int) -> None:
    """在独立线程中处理单张图片，同步更新 TASK_REGISTRY 和 DEVICE_REGISTRY"""
    base, _ = os.path.splitext(filename)
    result_name = f"{base}_result.txt"
    result_path = os.path.join(RESULT_DIR, result_name)

    # 更新为"处理中"
    with task_lock:
        TASK_REGISTRY[task_id]["status"] = "processing"
    with DEVICE_LOCK:
        DEVICE_REGISTRY[device_id]["status"] = "processing"
        DEVICE_REGISTRY[device_id]["last_seen"] = time.time()

    try:
        algo_path = os.path.join(BASE_DIR, 'model', 'LeNet', 'predict.py')
        LENET_PYTHON = sys.executable
        algo_dir = os.path.dirname(algo_path)

        if not os.path.exists(algo_path):
            with task_lock:
                TASK_REGISTRY[task_id]["status"] = "error"
                TASK_REGISTRY[task_id]["error"] = f"算法脚本不存在: {algo_path}"
            with DEVICE_LOCK:
                DEVICE_REGISTRY[device_id]["status"] = "error"
                DEVICE_REGISTRY[device_id]["error"] = "算法脚本不存在"
            return

        cmd = [
            LENET_PYTHON, "predict.py",
            '--input', os.path.abspath(src_path),
            '--output', os.path.abspath(result_path)
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=60, cwd=algo_dir, encoding='utf-8'
        )

        if result.returncode != 0:
            with task_lock:
                TASK_REGISTRY[task_id]["status"] = "error"
                TASK_REGISTRY[task_id]["error"] = result.stderr
            with DEVICE_LOCK:
                DEVICE_REGISTRY[device_id]["status"] = "error"
                DEVICE_REGISTRY[device_id]["error"] = result.stderr[:200]
            app.logger.error(f"算法执行失败: {result.stderr}")
            return

        if os.path.exists(result_path):
            with open(result_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if content.strip():
                with task_lock:
                    TASK_REGISTRY[task_id]["status"] = "done"
                    TASK_REGISTRY[task_id]["result"] = content
                with DEVICE_LOCK:
                    DEVICE_REGISTRY[device_id]["status"] = "done"
                    DEVICE_REGISTRY[device_id]["result"] = content
                    DEVICE_REGISTRY[device_id]["last_seen"] = time.time()
            else:
                with task_lock:
                    TASK_REGISTRY[task_id]["status"] = "error"
                    TASK_REGISTRY[task_id]["error"] = "结果文件为空"
                with DEVICE_LOCK:
                    DEVICE_REGISTRY[device_id]["status"] = "error"
                    DEVICE_REGISTRY[device_id]["error"] = "结果文件为空"
        else:
            with task_lock:
                TASK_REGISTRY[task_id]["status"] = "error"
                TASK_REGISTRY[task_id]["error"] = "结果文件未生成"
            with DEVICE_LOCK:
                DEVICE_REGISTRY[device_id]["status"] = "error"
                DEVICE_REGISTRY[device_id]["error"] = "结果文件未生成"

    except subprocess.TimeoutExpired:
        with task_lock:
            TASK_REGISTRY[task_id]["status"] = "error"
            TASK_REGISTRY[task_id]["error"] = "算法执行超时(60s)"
        with DEVICE_LOCK:
            DEVICE_REGISTRY[device_id]["status"] = "error"
            DEVICE_REGISTRY[device_id]["error"] = "算法执行超时"
        app.logger.error(f"算法执行超时: {filename}")
    except Exception as e:
        with task_lock:
            TASK_REGISTRY[task_id]["status"] = "error"
            TASK_REGISTRY[task_id]["error"] = str(e)
        with DEVICE_LOCK:
            DEVICE_REGISTRY[device_id]["status"] = "error"
            DEVICE_REGISTRY[device_id]["error"] = str(e)[:200]
        app.logger.error(f"处理文件 {filename} 时出错: {str(e)}")


def load_processors() -> None:
    global PROCESSORS
    PROCESSORS.clear()
    if not os.path.isdir(PROCESSORS_DIR):
        app.logger.warning(f"处理器目录不存在: {PROCESSORS_DIR}")
        return
    for finder, name, ispkg in pkgutil.iter_modules([PROCESSORS_DIR]):
        try:
            module = importlib.import_module(f'processors.{name}')
            meta = getattr(module, 'PROCESSOR', None)
            if meta and all(k in meta for k in ('id', 'label', 'process')):
                PROCESSORS[meta['id']] = meta
                app.logger.info(f"加载处理器成功: {meta['id']}")
            else:
                app.logger.warning(f"处理器 {name} 缺少必要属性")
        except Exception as e:
            app.logger.error(f"加载处理器 {name} 失败: {e}")


# ========== 静态资源路由 ==========

@app.route('/')
def index():
    return send_from_directory(HTML_FILES_DIR, 'index.html')

@app.route('/css_files/<path:path>')
def serve_css(path):
    return send_from_directory(CSS_DIR, path)

@app.route('/uploads/<path:path>')
def serve_uploads(path):
    return send_from_directory(UPLOAD_DIR, path)

@app.route('/assets/<path:path>')
def serve_assets(path):
    workspace_root = os.path.dirname(os.path.dirname(BASE_DIR))
    assets_dir = os.path.join(workspace_root, 'html', 'assets')
    return send_from_directory(assets_dir, path)


# ========== API 路由 ==========

@app.route('/devices', methods=['GET'])
def get_devices():
    """★ 新增：返回10个设备的最新状态，供看板轮询"""
    with DEVICE_LOCK:
        devices = []
        for i in range(1, 11):
            d = DEVICE_REGISTRY[i].copy()
            if d["last_seen"]:
                d["last_seen_fmt"] = datetime.fromtimestamp(d["last_seen"]).strftime('%H:%M:%S')
            else:
                d["last_seen_fmt"] = "--:--:--"
            devices.append(d)
    return jsonify({"success": True, "devices": devices})


@app.route('/latest_image', methods=['GET'])
def latest_image():
    with LATEST_TASK_LOCK:
        task_id = LATEST_TASK_ID
    if not task_id:
        return jsonify({'success': True, 'ready': False})
    with task_lock:
        task = TASK_REGISTRY.get(task_id)
    if not task:
        return jsonify({'success': True, 'ready': False})
    return jsonify({
        'success': True, 'ready': True,
        'task_id': task_id, 'filename': task["filename"],
        'updated_at': task.get("created_at", 0)
    })


@app.route('/result', methods=['GET'])
def get_result():
    """获取处理结果 —— 支持 task_id / filename / device_id 三种查询方式"""
    task_id = request.args.get('task_id')
    filename = request.args.get('filename')
    device_id_str = request.args.get('device_id')

    # ★ 新增：支持 device_id 查询（边缘端轮询首选）
    if device_id_str:
        try:
            device_id = int(device_id_str)
        except ValueError:
            return jsonify({'success': False, 'message': 'device_id 格式错误'}), 400
        with DEVICE_LOCK:
            dev = DEVICE_REGISTRY.get(device_id)
        if not dev:
            return jsonify({'success': False, 'message': '设备不存在'}), 404
        if dev["status"] in ("idle", "pending", "processing"):
            return jsonify({'success': True, 'ready': False})
        if dev["status"] == "done":
            return jsonify({
                'success': True, 'ready': True,
                'content': dev["result"], 'device_id': device_id
            })
        if dev["status"] == "error":
            return jsonify({
                'success': False, 'ready': True,
                'message': dev.get("error", "处理失败")
            }), 200

    # 原有 task_id 查询（兼容）
    if task_id:
        with task_lock:
            task = TASK_REGISTRY.get(task_id)
        if not task:
            return jsonify({'success': False, 'message': '任务不存在'}), 404
        if task["status"] in ("pending", "processing"):
            return jsonify({'success': True, 'ready': False})
        if task["status"] == "done":
            return jsonify({
                'success': True, 'ready': True,
                'content': task["result"], 'filename': task["filename"]
            })
        if task["status"] == "error":
            return jsonify({
                'success': False, 'ready': True,
                'message': task["error"]
            }), 200

    # 原有 filename 查询（兼容）
    if filename:
        with task_lock:
            for tid, t in TASK_REGISTRY.items():
                if t.get("filename") == filename:
                    if t["status"] == "done":
                        return jsonify({
                            'success': True, 'ready': True,
                            'content': t["result"], 'filename': t["filename"]
                        })
                    elif t["status"] in ("pending", "processing"):
                        return jsonify({'success': True, 'ready': False})
                    else:
                        return jsonify({'success': False, 'message': t.get("error", "处理失败")}), 500

        base, _ = os.path.splitext(filename)
        result_name = f"{base}_result.txt"
        result_path = os.path.join(RESULT_DIR, result_name)
        if not os.path.exists(result_path):
            return jsonify({'success': True, 'ready': False})
        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if content.strip():
                return jsonify({
                    'success': True, 'ready': True,
                    'filename': result_name, 'content': content
                })
            else:
                return jsonify({'success': True, 'ready': False})
        except Exception as e:
            return jsonify({'success': False, 'message': f'读取结果失败: {str(e)}'}), 500

    return jsonify({'success': False, 'message': '缺少参数 task_id、filename 或 device_id'}), 400


@app.route('/processors', methods=['GET'])
def list_processors():
    return jsonify({
        'success': True,
        'processors': [
            {'id': p['id'], 'label': p.get('label', p['id']), 'description': p.get('description', '')}
            for p in PROCESSORS.values()
        ]
    })


@app.route('/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务的状态列表（保留，供历史查看）"""
    with task_lock:
        tasks_data = []
        for tid, info in TASK_REGISTRY.items():
            device_name = f"Device-{info.get('device_id', '?')}"
            fn = info.get("filename", "")
            tasks_data.append({
                "task_id": tid[:8],
                "full_task_id": tid,
                "device_id": info.get("device_id"),
                "device_name": device_name,
                "status": info.get("status"),
                "image_url": f"/uploads/{fn}",
                "result_preview": (info.get("result") or "")[:80],
                "timestamp": info.get("created_at", 0)
            })
    tasks_data.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify(tasks_data[:30])


@app.route('/process', methods=['POST'])
def process_image():
    data = request.get_json(silent=True) or {}
    filename = data.get('filename')
    proc_id = data.get('processor_id')
    params = data.get('params') or {}
    if not filename or not proc_id:
        return jsonify({'success': False, 'message': '缺少必要参数 filename 或 processor_id'})
    if proc_id not in PROCESSORS:
        return jsonify({'success': False, 'message': f'未找到处理器: {proc_id}'})
    src_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(src_path):
        return jsonify({'success': False, 'message': '图片不存在'})
    try:
        with Image.open(src_path) as img:
            img.load()
            processed = PROCESSORS[proc_id]['process'](img, params)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'png'
        out_name = f"{proc_id}_{filename}"
        out_path = os.path.join(UPLOAD_DIR, out_name)
        processed.save(out_path)
        return jsonify({
            'success': True, 'message': '图片处理成功',
            'url': f"/uploads/{out_name}", 'filename': out_name
        })
    except Exception as e:
        app.logger.error(f"图片处理失败: {str(e)}")
        return jsonify({'success': False, 'message': f'处理图片时出错: {str(e)}'})


@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'message': '文件不存在'}), 404
    return send_file(file_path, as_attachment=True)


def cleanup_tasks():
    """定期清理过期的 TASK_REGISTRY 条目；DEVICE_REGISTRY 不清理（设备槽位始终保留）"""
    global LATEST_TASK_ID
    while True:
        time.sleep(300)
        now = time.time()
        with task_lock:
            expired_keys = [
                k for k, v in TASK_REGISTRY.items()
                if v["status"] in ("done", "error") and (now - v.get("created_at", now)) > 600
            ]
        if not expired_keys:
            continue
        with LATEST_TASK_LOCK:
            if LATEST_TASK_ID in expired_keys:
                LATEST_TASK_ID = None
        with task_lock:
            for k in expired_keys:
                TASK_REGISTRY.pop(k, None)
        # ★ 可选：同时清理磁盘上的过期上传图片和结果文件
        for k in expired_keys:
            with task_lock:
                info = TASK_REGISTRY.get(k)  # 已删除则跳过
            # 如需清理磁盘文件，可在此处添加 os.remove 逻辑
        app.logger.info(f"已清理 {len(expired_keys)} 个过期任务")

    # ★ 可选：检测设备离线（超过N秒未上报视为断连）
    # with DEVICE_LOCK:
    #     for dev_id, dev in DEVICE_REGISTRY.items():
    #         if dev["connected"] and dev["last_seen"] and (now - dev["last_seen"]) > 120:
    #             DEVICE_REGISTRY[dev_id]["status"] = "offline"


if __name__ == '__main__':
    load_processors()
    threading.Thread(target=cleanup_tasks, daemon=True).start()
    app.run(host='0.0.0.0', port=5401, threaded=True, debug=False)