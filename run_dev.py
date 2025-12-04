#!/usr/bin/env python3
"""
FemSub Hot Reload Development Server
热重载开发服务器 - 监控文件变化自动重启 Bot
"""

import subprocess
import sys
import os
from watchgod import run_process

def run_bot():
    """执行 main.py 脚本"""
    print("🤖 Starting FemSub Bot...")
    process = subprocess.Popen([sys.executable, "main.py"])
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping bot...")
        process.terminate()
        process.wait()
        print("✅ Bot stopped successfully")

if __name__ == "__main__":
    print("🚀 Starting FemSub Bot with hot-reloading for development...")
    print("📁 Monitoring directory: .")
    print("📝 Watching for changes in .py files")
    print("⏹️  Press Ctrl+C to stop")
    print("-" * 50)

    # 监控当前目录，当任何 .py 文件发生变化时，重启 run_bot 函数
    run_process(".", target=run_bot)