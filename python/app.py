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
from concurrent.futures import ThreadPoolExecutor # 新增：引入线程池

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # lab401/
HTML_DIR = os.path.join(BASE_DIR, 'html')
HTML_FILES_DIR = os.path.join(HTML_DIR, 'html_files')
CSS_DIR = os.path.join(HTML_DIR, 'css_files')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
RESULT_DIR = os.path.join(BASE_DIR, 'result')
PROCESSORS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processors')

# 确保目录存在
for dir_path in [UPLOAD_DIR, RESULT_DIR]:
    os.makedirs(dir_path, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# ============ 并发调度核心 ============
task_lock = threading.Lock()
TASK_REGISTRY: Dict[str, dict] = {}  # task_id -> {"status", "result", "error", "filename", "created_at"}

# 线程池：max_workers 根据服务器 CPU/GPU 能力调整，建议 2~4
PROCESSOR_EXECUTOR = ThreadPoolExecutor(max_workers=4)

# 用于记录最新任务的ID，供 /latest_image 使用
LATEST_TASK_LOCK = threading.Lock()
LATEST_TASK_ID = None

# 处理器相关
PROCESSORS: Dict[str, Dict] = {}


def allowed_file(filename: str) -> bool:
    """检查文件是否为允许的类型"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload_file():
    global LATEST_TASK_ID  
    """处理文件上传"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '请求中未包含文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # 生成唯一 task_id 和文件名
            task_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            unique_id = task_id[:8]
            filename = secure_filename(file.filename)
            name, ext = os.path.splitext(filename)
            new_filename = f"{timestamp}_{unique_id}_{name}{ext}"
            
            file_path = os.path.join(UPLOAD_DIR, new_filename)
            file.save(file_path)
            
            # 注册任务状态
            with task_lock:
                TASK_REGISTRY[task_id] = {
                    "status": "pending",
                    "result": None,
                    "error": None,
                    "filename": new_filename,
                    "created_at": time.time()
                }

            # 在这里更新最新任务ID，确保最后上传的才是最新的
            with LATEST_TASK_LOCK:
                LATEST_TASK_ID = task_id


            # 上传即提交到线程池并发处理，不再排队
            PROCESSOR_EXECUTOR.submit(_process_single_image, task_id, file_path, new_filename)
            
            return jsonify({
                'success': True,
                'message': '文件上传成功，已提交处理',
                'task_id': task_id,          # 新增：返回任务ID供轮询
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


def _process_single_image(task_id: str, src_path: str, filename: str) -> None:
    """在独立线程中处理单张图片"""
    base, _ = os.path.splitext(filename)
    result_name = f"{base}_result.txt"
    result_path = os.path.join(RESULT_DIR, result_name)

    with task_lock:
        TASK_REGISTRY[task_id]["status"] = "processing"

    try:
        algo_path = os.path.join(BASE_DIR, 'model', 'LeNet', 'predict.py')
        
        # 使用 sys.executable 动态获取当前 Python 解释器，不再硬编码 Windows 路径
        LENET_PYTHON = sys.executable 
        
        algo_dir = os.path.dirname(algo_path)

        if not os.path.exists(algo_path):
            with task_lock:
                TASK_REGISTRY[task_id]["status"] = "error"
                TASK_REGISTRY[task_id]["error"] = f"算法脚本不存在: {algo_path}"
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
            app.logger.error(f"算法执行失败: {result.stderr}")
            return

        # 检查结果文件是否完整
        if os.path.exists(result_path):
            with open(result_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if content.strip():
                with task_lock:
                    TASK_REGISTRY[task_id]["status"] = "done"
                    TASK_REGISTRY[task_id]["result"] = content
            else:
                with task_lock:
                    TASK_REGISTRY[task_id]["status"] = "error"
                    TASK_REGISTRY[task_id]["error"] = "结果文件为空"
        else:
            with task_lock:
                TASK_REGISTRY[task_id]["status"] = "error"
                TASK_REGISTRY[task_id]["error"] = "结果文件未生成"

    except subprocess.TimeoutExpired:
        with task_lock:
            TASK_REGISTRY[task_id]["status"] = "error"
            TASK_REGISTRY[task_id]["error"] = "算法执行超时(60s)"
        app.logger.error(f"算法执行超时: {filename}")
    except Exception as e:
        with task_lock:
            TASK_REGISTRY[task_id]["status"] = "error"
            TASK_REGISTRY[task_id]["error"] = str(e)
        app.logger.error(f"处理文件 {filename} 时出错: {str(e)}")


def load_processors() -> None:
    """加载所有处理器插件"""
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


# 路由：HTML和静态资源
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


# API路由
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
        'success': True,
        'ready': True,
        'task_id': task_id,
        'filename': task["filename"],
        'updated_at': task.get("created_at", 0)
    })


@app.route('/result', methods=['GET'])
def get_result():
    """获取处理结果"""
    task_id = request.args.get('task_id')
    filename = request.args.get('filename')

    if task_id:
        with task_lock:
            task = TASK_REGISTRY.get(task_id)
        if not task:
            return jsonify({'success': False, 'message': '任务不存在'}), 404
        if task["status"] in ("pending", "processing"):
            return jsonify({'success': True, 'ready': False})
        if task["status"] == "done":
            return jsonify({
                'success': True,
                'ready': True,
                'content': task["result"],
                'filename': task["filename"]
            })
        if task["status"] == "error":
            # 返回 200 + ready:True，让前端正常接收错误信息并停止轮询
            return jsonify({
                'success': False,
                'ready': True,  # 标记流程已结束，停止轮询
                'message': task["error"]
            }), 200

    # 兼容旧版：通过文件名查找对应任务
    if filename:
        with task_lock:
            for tid, t in TASK_REGISTRY.items():
                if t.get("filename") == filename:
                    if t["status"] == "done":
                        return jsonify({
                            'success': True,
                            'ready': True,
                            'content': t["result"],
                            'filename': t["filename"]
                        })
                    elif t["status"] in ("pending", "processing"):
                        return jsonify({'success': True, 'ready': False})
                    else:
                        return jsonify({'success': False, 'message': t.get("error", "处理失败")}), 500

        # 兜底：registry 里没找到，检查文件系统
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
                    'success': True,
                    'ready': True,
                    'filename': result_name,
                    'content': content
                })
            else:
                return jsonify({'success': True, 'ready': False})
        except Exception as e:
            return jsonify({'success': False, 'message': f'读取结果失败: {str(e)}'}), 500

    return jsonify({'success': False, 'message': '缺少参数 task_id 或 filename'}), 400


@app.route('/processors', methods=['GET'])
def list_processors():
    """列出所有可用的处理器"""
    return jsonify({
        'success': True,
        'processors': [
            {
                'id': p['id'],
                'label': p.get('label', p['id']),
                'description': p.get('description', '')
            } for p in PROCESSORS.values()
        ]
    })


@app.route('/process', methods=['POST'])
def process_image():
    """使用指定处理器处理图片"""
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
            # 确保图片在处理前被正确加载
            img.load()
            processed = PROCESSORS[proc_id]['process'](img, params)

        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'png'
        out_name = f"{proc_id}_{filename}"
        out_path = os.path.join(UPLOAD_DIR, out_name)
        processed.save(out_path)

        return jsonify({
            'success': True,
            'message': '图片处理成功',
            'url': f"/uploads/{out_name}",
            'filename': out_name
        })
    except Exception as e:
        app.logger.error(f"图片处理失败: {str(e)}")
        return jsonify({'success': False, 'message': f'处理图片时出错: {str(e)}'})


@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """下载文件"""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'message': '文件不存在'}), 404
    return send_file(file_path, as_attachment=True)

def cleanup_tasks():
    """定期清理过期的 TASK_REGISTRY 条目，防止内存泄漏"""
    global LATEST_TASK_ID
    
    while True:
        time.sleep(300)  # 每5分钟清理一次
        now = time.time()
        
        # 第1步：收集过期任务的 key
        with task_lock:
            expired_keys = [
                k for k, v in TASK_REGISTRY.items()
                if v["status"] in ("done", "error") and (now - v.get("created_at", now)) > 600
            ]
        
        if not expired_keys:
            continue
        
        # 第2步：如果最新任务已过期，清空 LATEST_TASK_ID
        with LATEST_TASK_LOCK:
            if LATEST_TASK_ID in expired_keys:
                LATEST_TASK_ID = None
        
        # 第3步：删除过期任务
        with task_lock:
            for k in expired_keys:
                TASK_REGISTRY.pop(k, None)
                
        app.logger.info(f"已清理 {len(expired_keys)} 个过期任务")


if __name__ == '__main__':
    # 初始化
    load_processors()
    
    # 启动后台清理线程
    threading.Thread(target=cleanup_tasks, daemon=True).start()
    
    # 开启多线程模式，关闭 debug 避免重载器冲突
    app.run(host='0.0.0.0', port=5401, threaded=True, debug=False)