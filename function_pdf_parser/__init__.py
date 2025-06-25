# function_pdf_parser/__init__.py
#
# 该模块提供了从 PDF 二进制数据中提取文本和表格，并将其转换为 Markdown 格式的功能。
# 主要依赖于 `pdfplumber` 库进行 PDF 内容的提取。

import logging
import io
import json
import re
import pdfplumber

# 配置日志
logging.basicConfig(level=logging.INFO)

def _convert_table_to_markdown(table_data):
    """
    将 pdfplumber 提取的表格数据转换为 Markdown 格式。

    Args:
        table_data (list[list[str]]): 一个列表的列表，每个子列表代表一行，包含单元格内容。
                                      单元格内容可以是字符串或 None。

    Returns:
        str: 转换后的 Markdown 格式表格字符串。如果 table_data 为空，则返回空字符串。
    """
    if not table_data:
        return ""

    markdown_lines = []

    # 获取最大列数，以确保所有行和分隔线对齐
    num_cols = max(len(row) for row in table_data) if table_data else 0

    # 处理表头和内容
    header = table_data[0] if table_data else []
    rows = table_data[1:] if len(table_data) > 1 else []

    # 确保表头所有列都有内容，不足的用空字符串填充
    header = [cell if cell is not None else "" for cell in header]
    header.extend([""] * (num_cols - len(header)))

    # 添加表头行
    markdown_lines.append("| " + " | ".join(header) + " |")

    # 添加 Markdown 表格分隔线
    markdown_lines.append("|" + "---|".join(["---"] * num_cols) + "|")

    # 添加表格数据行
    for row in rows:
        # 确保当前行所有列都有内容，不足的用空字符串填充
        processed_row = [cell if cell is not None else "" for cell in row]
        processed_row.extend([""] * (num_cols - len(processed_row)))
        markdown_lines.append("| " + " | ".join(processed_row) + " |")

    return "\n".join(markdown_lines)

def parse_pdf_from_bytes(pdf_data: bytes, pdf_name: str = 'unknown_pdf.pdf'):
    """
    解析 PDF 二进制数据，提取文本和表格，然后转换为结构化的 Markdown 格式。
    该函数会遍历 PDF 的每一页，提取文本和表格，并尝试根据它们在页面上的
    垂直位置进行排序，以保持内容的逻辑顺序。

    Args:
        pdf_data (bytes): PDF 文件的二进制内容。
        pdf_name (str): PDF 文件的名称，用于日志记录和结果标识。默认为 'unknown_pdf.pdf'。

    Returns:
        dict: 包含 'pdfname' (PDF 文件名) 和 'content' (Markdown 格式的解析内容) 的字典。

    Raises:
        ValueError: 如果 pdf_data 为空。
        Exception: 如果在 PDF 解析过程中发生任何其他错误。
    """
    logging.info(f'开始解析PDF: {pdf_name}')

    if not pdf_data:
        raise ValueError("PDF二进制数据不能为空。")

    # 将二进制数据包装成 BytesIO 对象，以便 pdfplumber 可以像文件一样读取
    pdf_file = io.BytesIO(pdf_data)
    markdown_content_parts = []

    try:
        # 使用 pdfplumber 打开 PDF 文件
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                logging.info(f"处理页面 {page_num + 1}/{len(pdf.pages)}")
                
                # 提取页面文本
                page_text = page.extract_text()
                
                # 提取页面表格数据
                tables = page.extract_tables()

                # 收集页面上的所有文本块和表格块及其边界框，用于后续排序
                page_elements = []
                if page_text:
                    # 对于整个页面文本，我们暂时将其视为一个元素，并使用页面边界框。
                    # 更精确的文本块排序需要使用 page.extract_words() 或 page.extract_text_boxes()
                    # 来获取每个文本块的精确坐标。这里为了简化，假设 extract_text() 已经按阅读顺序。
                    page_elements.append({"type": "text", "content": page_text, "bbox": page.bbox})

                for table_data_extracted in tables:
                    # pdfplumber.extract_tables() 返回的是表格内容，
                    # 我们需要通过 page.find_tables() 找到对应的 Table 对象来获取其边界框 (bbox)。
                    found_tables = page.find_tables()
                    for ft in found_tables:
                        # 比较提取的表格内容与找到的 Table 对象的提取内容，以匹配正确的 bbox
                        if ft.extract() == table_data_extracted:
                            page_elements.append({"type": "table", "content": table_data_extracted, "bbox": ft.bbox})
                            break
                
                # 根据元素的 Y 坐标（从上到下）进行排序。
                # bbox 格式为 (x0, y0, x1, y1)，其中 y0 是元素的顶部 Y 坐标。
                page_elements.sort(key=lambda x: x["bbox"][1]) # 按 y0 排序

                # 遍历排序后的元素，并将其转换为 Markdown 格式
                for element in page_elements:
                    if element["type"] == "text":
                        # 添加文本内容，并在文本块之间添加双换行符作为段落分隔
                        markdown_content_parts.append(element["content"])
                        markdown_content_parts.append("\n\n")
                    elif element["type"] == "table":
                        # 将表格数据转换为 Markdown 格式，并添加双换行符
                        markdown_table = _convert_table_to_markdown(element["content"])
                        if markdown_table:
                            markdown_content_parts.append(markdown_table)
                            markdown_content_parts.append("\n\n")

    except Exception as e:
        logging.error(f"解析PDF {pdf_name} 时发生错误: {e}")
        # 重新抛出异常，以便上层调用者可以捕获并处理
        raise

    # 合并所有 Markdown 部分并去除首尾空白
    final_markdown_content = "".join(markdown_content_parts).strip()

    response_data = {
        "pdfname": pdf_name,
        "content": final_markdown_content
    }
    logging.info(f'PDF {pdf_name} 解析完成。')
    return response_data

# 示例用法（如果需要独立测试，可以取消注释）
# if __name__ == "__main__":
#     # 假设有一个名为 'test/199.pdf' 的PDF文件
#     try:
#         with open('test/199.pdf', 'rb') as f:
#             sample_pdf_data = f.read()
#         result = parse_pdf_from_bytes(sample_pdf_data, '199.pdf')
#         print(json.dumps(result, ensure_ascii=False, indent=2))
#     except FileNotFoundError:
#         print("请创建一个 'test/199.pdf' 文件用于测试。")
#     except Exception as e:
#         print(f"测试时发生错误: {e}")
