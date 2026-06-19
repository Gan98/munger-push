#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享工具模块 - 芒格推送 & 逻辑训练 共用
功能：DAY持久化 / 推送API / 时间问候 / 重试机制
"""

import os
import json
import time
import requests
from datetime import datetime
from pathlib import Path

# ============ 配置 ============
STATE_DIR = Path(__file__).parent / ".push_state"
STATE_DIR.mkdir(exist_ok=True)

# SendKey 优先级：环境变量 > 配置文件 > 默认值
SENDKEY = os.environ.get("SENDKEY", "SCT48447TlAHtWwhj7BfUIrWTrkkzBuMo")

# 最大内容长度（Server酱单次限制约10万字符，留余量）
MAX_CONTENT_LENGTH = 80000


# ============ DAY 状态持久化 ============

def get_day(script_name: str) -> int:
    """
    从文件中读取当前天数，不存在则返回1。
    文件名格式：.push_state/day_{script_name}.json
    """
    state_file = STATE_DIR / f"day_{script_name}.json"
    try:
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            day = data.get("day", 1)
            return day
    except (json.JSONDecodeError, IOError):
        pass
    return 1


def save_day(script_name: str, day: int) -> None:
    """
    保存当前天数到文件。
    """
    state_file = STATE_DIR / f"day_{script_name}.json"
    data = {
        "day": day,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "script": script_name
    }
    state_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ============ 时间问候语 ============

def get_time_greeting() -> str:
    """根据当前小时返回问候语"""
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return "🌅 早安！"
    elif 12 <= hour < 18:
        return "🌞 午安！"
    else:
        return "🌙 晚安！"


# ============ 推送API（带重试） ============

def push_to_wechat(title: str, desp: str, sendkey: str = None, max_retries: int = 3) -> bool:
    """
    推送到微信（Server酱），失败自动重试。

    参数：
        title: 消息标题
        desp: 消息内容（支持Markdown）
        sendkey: Server酱SendKey，默认使用全局SENDKEY
        max_retries: 最大重试次数

    返回：True=成功，False=失败
    """
    key = sendkey or SENDKEY
    url = f"https://sctapi.ftqq.com/{key}.send"

    # 截断过长内容
    if len(desp) > MAX_CONTENT_LENGTH:
        truncate_msg = f"\n\n---\n⚠️ 内容过长已截断（原{len(desp)}字符 → {MAX_CONTENT_LENGTH}字符）"
        desp = desp[:MAX_CONTENT_LENGTH - len(truncate_msg)] + truncate_msg

    for attempt in range(1, max_retries + 1):
        try:
            # 禁用代理，避免代理连接失败问题
            response = requests.post(
                url,
                data={"title": title, "desp": desp},
                timeout=30,
                proxies={"http": None, "https": None}
            )
            result = response.json()

            code = result.get("code")
            errno = result.get("errno")

            if code == 0 or errno == 0:
                remaining = result.get("data", {}).get("pushcount", "?")
                quota = result.get("data", {}).get("readkey", "")
                print(f"  ✅ 推送成功 | 今日已用配额: {remaining} |")
                return True
            else:
                msg = result.get("message") or result.get("info") or "未知错误"
                print(f"  ❌ 推送失败 [{attempt}/{max_retries}]: {msg}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)  # 指数退避

        except requests.exceptions.Timeout:
            print(f"  ⚠️ 请求超时 [{attempt}/{max_retries}]")
            if attempt < max_retries:
                time.sleep(3)
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ 网络异常 [{attempt}/{max_retries}]: {e}")
            if attempt < max_retries:
                time.sleep(3)
        except Exception as e:
            print(f"  ❌ 未知异常 [{attempt}/{max_retries}]: {e}")
            if attempt < max_retries:
                time.sleep(2)

    print(f"  ❌ 推送最终失败（已重试{max_retries}次）")
    return False


# ============ 命令行工具 ============

if __name__ == "__main__":
    # 测试：显示当前状态
    print("=" * 40)
    print("共享工具模块测试")
    print("=" * 40)
    print(f"  SENDKEY: {'已配置' if SENDKEY else '未配置'}")
    print(f"  状态目录: {STATE_DIR}")
    print(f"  MUNGER Day: {get_day('munger')}")
    print(f"  LOGIC  Day: {get_day('logic')}")
    print(f"  当前时间: {get_time_greeting()}")
    print("=" * 40)
