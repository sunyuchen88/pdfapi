import os
import time
from apscheduler.schedulers.background import BackgroundScheduler
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)

UPLOAD_FOLDER = 'static/png_output'
CLEANUP_INTERVAL_HOURS = 24

def cleanup_old_files():
    """
    清理指定文件夹中超过指定时间的旧文件。
    """
    logging.info("开始执行每日清理任务...")
    now = time.time()
    cutoff = now - (CLEANUP_INTERVAL_HOURS * 3600)

    if not os.path.exists(UPLOAD_FOLDER):
        logging.warning(f"清理目录 {UPLOAD_FOLDER} 不存在，跳过清理。")
        return

    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                try:
                    file_mod_time = os.path.getmtime(file_path)
                    if file_mod_time < cutoff:
                        os.remove(file_path)
                        logging.info(f"已删除旧文件: {filename}")
                except OSError as e:
                    logging.error(f"删除文件 {filename} 时出错: {e}")
    except Exception as e:
        logging.error(f"执行清理任务时发生未知错误: {e}")

def start_scheduler():
    """
    启动后台调度器，用于定期执行清理任务。
    """
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(cleanup_old_files, 'interval', hours=CLEANUP_INTERVAL_HOURS)
    scheduler.start()
    logging.info("清理调度器已启动，将每24小时执行一次。")
