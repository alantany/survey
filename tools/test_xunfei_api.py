#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试科大讯飞 API
"""
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("需要安装 requests: pip install requests")
    sys.exit(1)

# 配置
APPID = "92106442"
SECRET_KEY = "ZjY2NGQ5OWZmY2Y0OGQ1NDRjMzViOGFl"

lfasr_host = 'https://raasr.xfyun.cn/v2/api'
api_upload = '/upload'
api_get_result = '/getResult'


def get_signa(appid: str, secret_key: str, ts: str) -> str:
    """科大讯飞签名生成"""
    m2 = hashlib.md5()
    m2.update((appid + ts).encode('utf-8'))
    md5 = m2.hexdigest()
    md5 = bytes(md5, encoding='utf-8')
    signa = hmac.new(secret_key.encode('utf-8'), md5, hashlib.sha1).digest()
    signa = base64.b64encode(signa)
    return str(signa, 'utf-8')


def test_xunfei_api(audio_path: str):
    """测试科大讯飞 API"""
    audio_path = Path(audio_path)
    if not audio_path.exists():
        print(f"错误：音频文件不存在: {audio_path}")
        return

    ts = str(int(time.time()))
    signa = get_signa(APPID, SECRET_KEY, ts)

    # 第一步：上传文件
    print("=" * 60)
    print("第一步：上传文件")
    print("=" * 60)
    file_len = audio_path.stat().st_size
    file_name = audio_path.name

    param_dict = {
        'appId': APPID,
        'signa': signa,
        'ts': ts,
        'fileSize': file_len,
        'fileName': file_name,
        'duration': '200'
    }

    print(f"参数: {param_dict}")
    print(f"上传 URL: {lfasr_host + api_upload}")

    with open(audio_path, 'rb') as f:
        audio_data = f.read()

    upload_url = lfasr_host + api_upload + "?" + urllib.parse.urlencode(param_dict)
    upload_resp = requests.post(
        url=upload_url,
        headers={"Content-type": "application/json"},
        data=audio_data,
        timeout=60
    )

    print(f"状态码: {upload_resp.status_code}")
    print(f"响应: {json.dumps(upload_resp.json(), ensure_ascii=False, indent=2)}")

    if upload_resp.status_code != 200:
        print("上传失败")
        return

    upload_result = upload_resp.json()
    if upload_result.get('code') != 0:
        print(f"上传失败: {upload_result.get('desc', '未知错误')}")
        return

    order_id = upload_result.get('content', {}).get('orderId')
    if not order_id:
        print(f"上传响应中未找到 orderId")
        return

    print(f"\n✅ 上传成功，orderId: {order_id}")

    # 第二步：轮询查询结果
    print("\n" + "=" * 60)
    print("第二步：查询结果")
    print("=" * 60)

    param_dict = {
        'appId': APPID,
        'signa': signa,
        'ts': ts,
        'orderId': order_id,
        'resultType': 'transfer,predict'
    }

    max_polls = 120
    poll_count = 0
    status = 3

    while status == 3 and poll_count < max_polls:
        poll_count += 1
        print(f"\n第 {poll_count} 次查询...")

        result_url = lfasr_host + api_get_result + "?" + urllib.parse.urlencode(param_dict)
        result_resp = requests.post(
            url=result_url,
            headers={"Content-type": "application/json"},
            timeout=30
        )

        if result_resp.status_code != 200:
            print(f"查询失败，状态码: {result_resp.status_code}")
            print(f"响应: {result_resp.text[:500]}")
            break

        result_data = result_resp.json()
        print(f"响应: {json.dumps(result_data, ensure_ascii=False, indent=2)}")

        if result_data.get('code') != 0:
            print(f"查询失败: {result_data.get('desc', '未知错误')}")
            break

        order_info = result_data.get('content', {}).get('orderInfo', {})
        status = order_info.get('status', 3)
        print(f"状态: {status} (3=处理中, 4=完成)")

        if status == 4:
            print("\n✅ 转写完成！")
            print("\n完整响应结构:")
            print(json.dumps(result_data, ensure_ascii=False, indent=2))
            break

        time.sleep(5)

    if status != 4:
        print(f"\n❌ 转写未完成（已查询 {poll_count} 次），最后状态: {status}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python test_xunfei_api.py <音频文件路径>")
        print("示例: python test_xunfei_api.py survey/test.wav")
        sys.exit(1)

    test_xunfei_api(sys.argv[1])

