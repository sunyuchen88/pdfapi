# main_app.py
#
# 这是一个基于 Flask 框架构建的 PDF 和 ZIP 文件处理服务。
# 它提供了三个主要的 API 端点：
# 1. `/pdf_parser`: 用于解析单个 PDF 文件的内容。
# 2. `/zip_parser`: 用于解析 ZIP 文件中包含的多个 PDF 文件。
# 3. `/pdf_to_png`: 用于将 PDF 文件转换为 PNG 图像。
#
# 服务使用 PyMuPDF (fitz) 进行 PDF 处理，并集成了自定义的 PDF 和 ZIP 解析函数。
#
# 扩展功能：现在所有文件处理端点都支持通过 POST 请求体直接传入二进制数据，
# 或通过 JSON 请求体传入文件链接 (URL) 来获取文件。

import re
from flask import Flask, request, jsonify, url_for
import logging
import base64
import fitz  # PyMuPDF 库，用于 PDF 处理
from function_pdf_parser.__init__ import parse_pdf_from_bytes # 导入 PDF 解析函数
from function_zip_parser.__init__ import parse_pdfs_from_zip # 导入 ZIP 中 PDF 解析函数
import json
import io # 用于处理二进制数据流
import requests # 导入 requests 库用于从 URL 下载文件
import os
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/png_output'

# 配置日志
# 设置日志级别为 INFO，以便记录信息、警告和错误。
logging.basicConfig(level=logging.INFO)

def _get_file_data_from_request(file_type: str):
    """
    辅助函数：从 Flask 请求中获取文件数据和文件名。
    支持三种方式：
    1. 从 multipart/form-data 表单中获取文件。
    2. 从 JSON 请求体中获取 'url' 参数，然后下载文件。
    3. 直接从请求体获取二进制数据。
    """
    logging.info(f"开始获取文件数据，Content-Type: {request.content_type}")

    # 方式一：检查 multipart/form-data 文件上传
    if request.content_type and 'multipart/form-data' in request.content_type:
        logging.info("检测到 multipart/form-data 请求。")
        if request.files:
            file_key = next(iter(request.files))
            uploaded_file = request.files[file_key]
            if uploaded_file and uploaded_file.filename:
                file_name = uploaded_file.filename
                file_data = uploaded_file.read()
                logging.info(f"从 multipart/form-data 获取到文件: {file_name}")
                return file_data, file_name
        raise ValueError("multipart/form-data 请求中未找到文件。")

    # 方式二：尝试从 JSON 请求体中获取 'url'
    elif request.is_json:
        logging.info("检测到 JSON 请求。")
        json_data = request.get_json()
        if json_data and 'url' in json_data:
            file_url = json_data['url']
            file_name = json_data.get('filename')
            logging.info(f"从 URL 下载 {file_type} 文件: {file_url}")
            try:
                response = requests.get(file_url, stream=True)
                response.raise_for_status()
                file_data = response.content
                if not file_name:
                    file_name = file_url.split('/')[-1].split('?')[0]
                logging.info(f"成功下载文件: {file_name or 'unknown'}")
                return file_data, file_name or f"downloaded_{file_type}.{file_type}"
            except requests.exceptions.RequestException as req_err:
                raise ValueError(f"从 URL 下载 {file_type} 文件失败: {req_err}")
        else:
            raise ValueError("JSON 请求体中未找到 'url' 键。")

    # 方式三：假设请求体是原始二进制数据
    else:
        logging.info("未检测到 form-data 或标准 JSON，作为原始二进制数据处理。")
        file_data = request.get_data()
        if not file_data:
            raise ValueError("请求体为空，且不是有效的 form-data 或 JSON 请求。")
        
        file_name = None
        x_file_name = request.headers.get('X-File-Name')
        if x_file_name:
            file_name = x_file_name
        elif request.headers.get('Content-Disposition'):
            content_disposition = request.headers.get('Content-Disposition')
            filename_match = re.search(r'filename="([^"]+)"', content_disposition)
            if filename_match:
                file_name = filename_match.group(1)
        
        if not file_name:
            file_name = request.args.get('filename')

        if not file_name:
            file_name = f'unknown_{file_type}.{file_type}'
        
        logging.info(f"从原始请求体获取到数据，文件名为: {file_name}")
        return file_data, file_name

@app.route('/')
def hello_index():
    """
    根路径路由，用于简单的服务健康检查或欢迎信息。
    """
    return 'Hello World!'

@app.route('/pdf_parser', methods=['POST'])
def pdf_parser_endpoint():
    """
    PDF 解析端点。
    接收 PDF 文件的二进制数据，或 PDF 文件链接，并尝试解析其内容。
    """
    logging.info('接收到PDF解析请求。')
    try:
        pdf_data, pdf_name = _get_file_data_from_request('pdf')
        
        # 调用外部函数解析 PDF 数据
        result = parse_pdf_from_bytes(pdf_data, pdf_name)
        return jsonify(result), 200
    except ValueError as ve:
        # 处理数据相关的错误
        logging.error(f"请求数据错误: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        # 捕获其他所有异常并记录
        logging.error(f"处理PDF解析请求时发生错误: {e}")
        return jsonify({"error": f"处理请求时发生错误: {str(e)}"}), 500

@app.route('/zip_parser', methods=['POST'])
def zip_parser_endpoint():
    """
    ZIP 文件解析端点。
    接收 ZIP 文件的二进制数据，或 ZIP 文件链接，并尝试解析其中包含的所有 PDF 文件。
    """
    logging.info('接收到ZIP解析请求。')
    try:
        zip_data, _ = _get_file_data_from_request('zip') # ZIP 文件名通常不重要，因为内部有多个PDF
        
        # 调用外部函数解析 ZIP 文件中的 PDF
        results = parse_pdfs_from_zip(zip_data)
        
        if not results:
            # 如果 ZIP 文件中没有找到可解析的 PDF 文件。
            return jsonify({"message": "ZIP文件中未找到可解析的PDF文件。"}), 200

        return jsonify(results), 200
    except ValueError as ve:
        # 处理数据相关的错误
        logging.error(f"请求数据错误: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        # 捕获其他所有异常并记录
        logging.error(f"处理ZIP解析请求时发生错误: {e}")
        return jsonify({"error": f"处理请求时发生错误: {str(e)}"}), 500

@app.route('/pdf_to_png', methods=['POST'])
def pdf_to_png_endpoint():
    """
    PDF 转 PNG 端点。
    接收 PDF 文件的二进制数据，或 PDF 文件链接，将其每一页转换为 PNG 图像，并返回图片的 URL。
    """
    logging.info('接收到PDF转PNG请求。')
    try:
        pdf_data, pdf_name = _get_file_data_from_request('pdf')

        if not pdf_data:
            logging.error("未能获取到 PDF 数据。")
            return jsonify({"error": "未能获取到 PDF 数据。"}), 400
        
        logging.info(f"成功获取到 PDF 数据，大小: {len(pdf_data)} 字节，文件名: {pdf_name}")

        pdf_file = io.BytesIO(pdf_data)
        doc = fitz.open(stream=pdf_file, filetype="pdf")
        
        image_urls = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            
            # 生成唯一的文件名
            image_filename = f"{uuid.uuid4().hex}.png"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            
            # 保存图片
            pix.save(image_path)
            
            # 生成图片的 URL
            image_url = url_for('static', filename=f'png_output/{image_filename}', _external=True)
            image_urls.append(image_url)
            
        doc.close()

        if not image_urls:
            return jsonify({"message": "PDF文件中未生成任何PNG图片。"}), 200

        return jsonify({"image_urls": image_urls}), 200
    except Exception as e:
        logging.error(f"处理PDF转PNG请求时发生错误: {e}")
        return jsonify({"error": f"处理请求时发生错误: {str(e)}"}), 500

from cleanup_scheduler import start_scheduler

if __name__ == '__main__':
    # 启动清理调度器
    start_scheduler()
    # 当直接运行此脚本时，启动 Flask 开发服务器。
    # 在生产环境中，应使用 Gunicorn 或其他 WSGI 服务器来运行应用。
    app.run(host='0.0.0.0', debug=True, port=8080)
