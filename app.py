import re
from flask import Flask, request, jsonify
import logging
from function_pdf_parser.__init__ import parse_pdf_from_bytes
from function_zip_parser.__init__ import parse_pdfs_from_zip
import json

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)

@app.route('/pdf_parser', methods=['POST'])
def pdf_parser_endpoint():
    logging.info('接收到PDF解析请求。')
    try:
        pdf_data = request.get_data()
        if not pdf_data:
            return jsonify({"error": "请在请求体中发送PDF二进制数据。"}), 400

        pdf_name = None

        # 尝试从 X-File-Name 头获取
        x_file_name = request.headers.get('X-File-Name')
        if x_file_name:
            pdf_name = x_file_name
            logging.info(f"从 X-File-Name 头获取到文件名: {pdf_name}")
        
        # 如果没有从 X-File-Name 头获取到，尝试从 Content-Disposition 头获取
        if not pdf_name:
            content_disposition = request.headers.get('Content-Disposition')
            if content_disposition:
                filename_match = re.search(r'filename="([^"]+)"', content_disposition)
                if filename_match:
                    pdf_name = filename_match.group(1)
                    logging.info(f"从 Content-Disposition 头获取到文件名: {pdf_name}")
        
        # 如果仍然没有文件名，尝试从查询参数中获取
        if not pdf_name:
            query_filename = request.args.get('filename')
            if query_filename:
                pdf_name = query_filename
                logging.info(f"从查询参数获取到文件名: {pdf_name}")

        if not pdf_name:
            pdf_name = 'unknown_pdf.pdf'
            logging.warning("未能在请求中找到文件名，使用默认值: unknown_pdf.pdf")
        
        result = parse_pdf_from_bytes(pdf_data, pdf_name)
        return jsonify(result), 200
    except ValueError as ve:
        logging.error(f"请求数据错误: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logging.error(f"处理PDF解析请求时发生错误: {e}")
        return jsonify({"error": f"处理请求时发生错误: {str(e)}"}), 500

@app.route('/zip_parser', methods=['POST'])
def zip_parser_endpoint():
    logging.info('接收到ZIP解析请求。')
    try:
        zip_data = request.get_data()
        if not zip_data:
            return jsonify({"error": "请在请求体中发送ZIP二进制数据。"}), 400

        results = parse_pdfs_from_zip(zip_data)
        
        if not results:
            return jsonify({"message": "ZIP文件中未找到可解析的PDF文件。"}), 200 # 或者400，取决于业务需求

        return jsonify(results), 200
    except ValueError as ve:
        logging.error(f"请求数据错误: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logging.error(f"处理ZIP解析请求时发生错误: {e}")
        return jsonify({"error": f"处理请求时发生错误: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8080)
