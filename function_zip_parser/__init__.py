# function_zip_parser/__init__.py
#
# 该模块提供了从 ZIP 文件的二进制数据中提取 PDF 文件，并对每个 PDF 文件进行解析的功能。
# 它依赖于 `zipfile` 库来处理 ZIP 归档，并复用了 `function_pdf_parser` 模块中的 PDF 解析逻辑。

import logging
import io
import json
import zipfile
from function_pdf_parser.__init__ import parse_pdf_from_bytes # 导入PDF解析函数

# 配置日志
logging.basicConfig(level=logging.INFO)

def parse_pdfs_from_zip(zip_data: bytes):
    """
    解析 ZIP 二进制数据，提取其中所有以 .pdf 结尾的文件，并对每个 PDF 文件进行内容解析。

    Args:
        zip_data (bytes): ZIP 文件的二进制内容。

    Returns:
        list[dict]: 包含每个成功解析的 PDF 文件的 'pdfname' 和 'content' 的字典列表。
                    如果 ZIP 文件中没有找到可解析的 PDF，则返回空列表。
                    如果某个 PDF 解析失败，其内容将包含错误信息。

    Raises:
        ValueError: 如果 zip_data 为空或不是有效的 ZIP 文件。
    """
    logging.info('开始解析ZIP文件。')

    if not zip_data:
        raise ValueError("ZIP二进制数据不能为空。")

    # 使用 io.BytesIO 将二进制数据转换为文件对象，以便 zipfile 模块可以读取
    zip_file_obj = io.BytesIO(zip_data)
    
    parsed_pdfs = []

    try:
        # 以读取模式打开 ZIP 文件
        with zipfile.ZipFile(zip_file_obj, 'r') as zf:
            # 遍历 ZIP 文件中的所有文件和目录名
            for name in zf.namelist():
                # 只处理以 .pdf (不区分大小写) 结尾的文件
                if name.lower().endswith('.pdf'):
                    try:
                        # 打开 ZIP 文件中的 PDF 文件并读取其内容
                        with zf.open(name) as pdf_in_zip:
                            pdf_content = pdf_in_zip.read()
                            # 调用之前定义的 PDF 解析函数来处理提取出的 PDF 内容
                            result = parse_pdf_from_bytes(pdf_content, name)
                            parsed_pdfs.append(result)
                    except Exception as e:
                        # 记录解析单个 PDF 文件时发生的警告和错误
                        logging.warning(f"解压或解析ZIP文件中的PDF '{name}' 时发生错误: {e}")
                        # 将错误信息添加到结果中，以便调用者知晓
                        parsed_pdfs.append({
                            "pdfname": name,
                            "content": f"解析失败: {str(e)}"
                        })
                else:
                    # 跳过非 PDF 文件
                    logging.info(f"跳过非PDF文件: {name}")
    except zipfile.BadZipFile:
        # 如果传入的数据不是有效的 ZIP 文件，则抛出错误
        raise ValueError("请求体不是有效的ZIP文件。")
    except Exception as e:
        # 捕获其他所有异常并记录
        logging.error(f"处理ZIP解析请求时发生错误: {e}")
        raise # 重新抛出异常

    if not parsed_pdfs:
        logging.warning("ZIP文件中未找到可解析的PDF文件。")
        # 即使没有找到 PDF，也返回一个空列表，而不是抛出错误
        # 这样调用者可以根据列表是否为空来判断
        return [] 

    logging.info('ZIP文件解析完成。')
    return parsed_pdfs

# 示例用法（如果需要独立测试，可以取消注释）
# if __name__ == "__main__":
#     # 假设有一个名为 'sample.zip' 的ZIP文件，其中包含PDF
#     try:
#         with open('sample.zip', 'rb') as f:
#             sample_zip_data = f.read()
#         results = parse_pdfs_from_zip(sample_zip_data)
#         print(json.dumps(results, ensure_ascii=False, indent=2))
#     except FileNotFoundError:
#         print("请创建一个 'sample.zip' 文件用于测试。")
#     except Exception as e:
#         print(f"测试时发生错误: {e}")
