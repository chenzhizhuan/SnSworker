#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天翼云盘助手 - 云盘命令行工具（全功能版）
包含：登录、Token状态、搜索文件、列出文件、获取下载链接、智能搜图、创建目录、上传文件

基于各云盘子技能脚本合并，涵盖所有功能。
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote

import requests

TOKEN_FILE = os.path.expanduser("~/.cloud189_token.json")
API_URL = "https://api.cloud.189.cn/smart/server/api/open/cloud/skills"
XKEY = "e87f4d25953fg"

DEBUG_PRINT_RESPONSE = True


def load_token():
    """加载保存的token"""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("access_token", "")
        except Exception:
            pass
    return ""


def save_token(access_token):
    """保存token到文件"""
    try:
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            json.dump({"access_token": access_token}, f)
        return True
    except Exception:
        return False


def call_cloud_api(access_token, function_name, function_data):
    """调用云接口，返回原始响应"""
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "xkey": XKEY
    }
    data = {
        "accessToken": access_token,
        "functionName": function_name,
        "functionData": function_data
    }
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        raw_text = response.text

        if DEBUG_PRINT_RESPONSE:
            print(json.dumps({
                "debug": "raw_response",
                "content": raw_text[:500] if len(raw_text) > 500 else raw_text
            }, ensure_ascii=False))

        return response.json()
    except Exception as e:
        return {"errCode": -1, "errMsg": str(e), "data": None}


def parse_api_response(result):
    """解析API响应，处理外层和内层错误"""
    if result.get("errCode", 0) != 0:
        return False, result.get("errMsg", "接口调用失败"), None

    data_raw = result.get("data")
    data_dict = None

    if data_raw:
        if isinstance(data_raw, str):
            try:
                data_dict = json.loads(data_raw)
            except Exception:
                return False, "data字段解析失败", None
        elif isinstance(data_raw, dict):
            data_dict = data_raw

    if data_dict and data_dict.get("errorCode"):
        error_msg = data_dict.get("errorMsg", data_dict.get("errorCode", "业务错误"))
        return False, error_msg, None

    return True, None, data_dict


def cmd_login(args):
    """登录命令"""
    if args.auth_code:
        url = f"https://api.cloud.189.cn/open/oauth2/getAccessTokenByCloudCode?authCode={args.auth_code}"
        try:
            response = requests.get(url)
            data = response.json()
            if data.get("errCode") == "0":
                access_token = data.get("data", {}).get("accessToken", "")
                if access_token:
                    save_token(access_token)
                    print(json.dumps({
                        "success": True,
                        "message": "登录成功，Token已保存",
                        "access_token": access_token,
                        "token_file": TOKEN_FILE
                    }, ensure_ascii=False))
                else:
                    print(json.dumps({
                        "success": False,
                        "message": "获取Token失败，响应中无accessToken"
                    }, ensure_ascii=False))
            else:
                print(json.dumps({
                    "success": False,
                    "message": f"登录失败: {data.get('errMsg', '未知错误')}"
                }, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({
                "success": False,
                "message": f"请求失败: {str(e)}"
            }, ensure_ascii=False))
    else:
        print(json.dumps({
            "success": True,
            "message": "请按以下步骤完成登录",
            "steps": [
                "1. 在浏览器中打开: https://cloud.189.cn/web/ecloud-auth/index.html",
                "2. 使用天翼云盘账号登录",
                "3. 登录成功后，复制页面显示的授权码(authCode)",
                "4. 执行命令: python scripts/cloud189_lite.py login --auth-code <授权码>"
            ],
            "auth_url": "https://cloud.189.cn/web/ecloud-auth/index.html"
        }, ensure_ascii=False))


def cmd_info(args):
    """显示Token状态"""
    access_token = load_token()
    print(json.dumps({
        "success": True,
        "has_token": bool(access_token),
        "token_file": TOKEN_FILE,
        "token_preview": access_token[:20] + "..." if access_token and len(access_token) > 20 else access_token
    }, ensure_ascii=False))


def cmd_get_folder(args):
    """查询目录信息"""
    access_token = load_token()
    if not access_token:
        print(json.dumps({"success": False, "message": "请先登录"}, ensure_ascii=False))
        return

    function_data = {}
    if args.folder_id:
        function_data["folderId"] = args.folder_id
    if args.path:
        function_data["folderPath"] = args.path

    result = call_cloud_api(access_token, "getFolderInfo", json.dumps(function_data))
    success, message, data = parse_api_response(result)

    if not success:
        print(json.dumps({"success": False, "message": message}, ensure_ascii=False))
        return

    print(json.dumps({
        "success": True,
        "folder_id": data.get("fileId"),
        "folder_name": data.get("fileName"),
        "folder_path": data.get("filePath"),
        "parent_id": data.get("parentId"),
        "create_time": data.get("createTime"),
    }, ensure_ascii=False))


def cmd_list_files(args):
    """查询文件列表"""
    access_token = load_token()
    if not access_token:
        print(json.dumps({"success": False, "message": "请先登录"}, ensure_ascii=False))
        return

    if not args.folder_id:
        print(json.dumps({"success": False, "message": "请提供--folder-id参数"}, ensure_ascii=False))
        return

    function_data = {"folderId": args.folder_id}
    if args.page:
        function_data["pageNum"] = args.page
    if args.size:
        function_data["pageSize"] = args.size

    result = call_cloud_api(access_token, "listFiles", json.dumps(function_data))
    success, message, data = parse_api_response(result)

    if not success:
        print(json.dumps({"success": False, "message": message}, ensure_ascii=False))
        return

    try:
        file_list_ao = data.get("fileListAO", {})
        files = []
        folders = []

        for f in file_list_ao.get("fileList", []):
            files.append({
                "id": f.get("id"),
                "name": f.get("name"),
                "size": f.get("size"),
                "media_type": f.get("mediaType"),
                "create_time": f.get("createDate"),
                "last_op_time": f.get("lastOpTime")
            })

        for f in file_list_ao.get("folderList", []):
            folders.append({
                "id": f.get("id"),
                "name": f.get("name"),
                "parent_id": f.get("parentId"),
                "file_count": f.get("fileCount"),
                "create_time": f.get("createDate")
            })

        print(json.dumps({
            "success": True,
            "count": file_list_ao.get("count", 0),
            "files": files,
            "folders": folders
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"success": False, "message": f"解析数据失败: {str(e)}"}, ensure_ascii=False))


def cmd_search_files(args):
    """搜索文件"""
    access_token = load_token()
    if not access_token:
        print(json.dumps({"success": False, "message": "请先登录"}, ensure_ascii=False))
        return

    if not args.folder_id:
        print(json.dumps({"success": False, "message": "请提供--folder-id参数"}, ensure_ascii=False))
        return

    function_data = {
        "fileName": args.keyword or "",
        "folderId": args.folder_id
    }
    if args.recursive:
        function_data["recursive"] = 1

    result = call_cloud_api(access_token, "searchFiles", json.dumps(function_data))
    success, message, data = parse_api_response(result)

    if not success:
        print(json.dumps({"success": False, "message": message}, ensure_ascii=False))
        return

    try:
        files = []
        folders = []

        for f in data.get("fileList", []):
            files.append({
                "id": f.get("id"),
                "name": f.get("name"),
                "size": f.get("size"),
                "media_type": f.get("mediaType"),
                "create_time": f.get("createDate")
            })

        for f in data.get("folderList", []):
            folders.append({
                "id": f.get("id"),
                "name": f.get("name"),
                "parent_id": f.get("parentId"),
                "file_count": f.get("fileCount")
            })

        print(json.dumps({
            "success": True,
            "count": data.get("count", 0),
            "files": files,
            "folders": folders
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"success": False, "message": f"解析数据失败: {str(e)}"}, ensure_ascii=False))


def cmd_download(args):
    """获取文件下载链接"""
    access_token = load_token()
    if not access_token:
        print(json.dumps({"success": False, "message": "请先登录"}, ensure_ascii=False))
        return

    if not args.file_id:
        print(json.dumps({"success": False, "message": "请提供--file-id参数"}, ensure_ascii=False))
        return

    function_data = {"fileId": args.file_id}

    result = call_cloud_api(access_token, "getFileInfo", json.dumps(function_data))
    success, message, data = parse_api_response(result)

    if not success:
        print(json.dumps({"success": False, "message": message}, ensure_ascii=False))
        return

    print(json.dumps({
        "success": True,
        "file_id": data.get("id"),
        "file_name": data.get("name"),
        "file_size": data.get("size"),
        "file_path": data.get("filePath"),
        "download_url": data.get("fileDownloadUrl")
    }, ensure_ascii=False))


def cmd_search_images(args):
    """智能图片搜索 — 全盘搜索图片"""
    access_token = load_token()
    if not access_token:
        print(json.dumps({"success": False, "message": "请先登录"}, ensure_ascii=False))
        return

    function_data = json.dumps({
        "text": args.text,
        "pageNum": args.page or 1,
        "pageSize": args.size or 50,
        "searchType": 1
    })

    result = call_cloud_api(access_token, "searchByText", function_data)
    success, message, data = parse_api_response(result)

    if not success:
        print(json.dumps({"success": False, "message": message}, ensure_ascii=False))
        return

    try:
        files = data.get("data", {}).get("cloudBaseFile", [])
        images = []
        for f in files:
            icon = f.get("icon", {})
            images.append({
                "file_id": f.get("userFileId"),
                "file_name": f.get("fileName"),
                "file_size": f.get("fileSize"),
                "thumbnail_url": icon.get("smallUrl", ""),
                "preview_url": icon.get("largeUrl", ""),
                "media_type": f.get("mediaType", ""),
                "create_time": f.get("createDate", ""),
            })
        print(json.dumps({
            "success": True,
            "query": args.text,
            "count": len(images),
            "page": args.page or 1,
            "page_size": args.size or 50,
            "images": images
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"success": False, "message": f"解析数据失败: {str(e)}"}, ensure_ascii=False))


# ============================================================
# 上传相关：数据类、工具函数、API调用、命令处理
# ============================================================

@dataclass
class UploadPartInfo:
    part_number: int
    size: int
    etag: str

@dataclass
class UploadFileInfo:
    file_name: str
    slice_size: int
    file_md5: str
    file_size: int
    slice_md5: str
    slice_count: int
    part_info_list: List[UploadPartInfo]

@dataclass
class InitUploadVO:
    upload_type: int
    upload_host: str
    upload_file_id: str
    file_data_exists: int  # 1=秒传, 0=需要上传

@dataclass
class MultipleUploadUrl:
    http_method: str
    http_url: str
    content_type: str
    upload_id: str
    authorization: str
    date: str
    part_number: int
    part_size: int
    part_md5: str
    limit_rate: str = ""
    request_time: float = 0.0
    slice_size: int = 0

@dataclass
class PartUploadStatus:
    upload_status: bool
    part_number: int
    msg: str

@dataclass
class CommitUploadResult:
    success: bool
    user_file_id: str = ""
    file_name: str = ""
    file_size: int = 0
    file_md5: str = ""
    msg: str = ""


def _calculate_md5(file_path, chunk_size=8192):
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def _calculate_md5_from_bytes(data):
    return hashlib.md5(data).hexdigest()


def _get_upload_file_info(file_path, slice_size=10*1024*1024):
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    file_md5 = _calculate_md5(file_path).upper()
    slice_count = (file_size + slice_size - 1) // slice_size

    part_md5_hex_list = []
    part_info_list = []
    for i in range(slice_count):
        start = i * slice_size
        end = min(start + slice_size, file_size)
        part_size = end - start
        with open(file_path, "rb") as f:
            f.seek(start)
            part_data = f.read(part_size)
            part_md5_hex = _calculate_md5_from_bytes(part_data).upper()
            part_md5 = base64.b64encode(bytes.fromhex(part_md5_hex)).decode("utf-8")
            part_md5_hex_list.append(part_md5_hex)
        part_info_list.append(UploadPartInfo(part_number=i+1, size=part_size, etag=part_md5))

    if file_size <= slice_size:
        slice_md5 = file_md5
    else:
        slice_md5_input = "\n".join(part_md5_hex_list)
        slice_md5 = hashlib.md5(slice_md5_input.encode("utf-8")).hexdigest().upper()

    return UploadFileInfo(
        file_name=file_name, slice_size=slice_size, file_md5=file_md5,
        file_size=file_size, slice_md5=slice_md5,
        slice_count=slice_count, part_info_list=part_info_list
    )


def _call_upload_api(access_token, function_name, function_data):
    """调用云接口（上传专用，返回原始 data 字符串）"""
    headers = {"Content-Type": "application/json;charset=UTF-8", "xkey": XKEY}
    data = {"accessToken": access_token, "functionName": function_name, "functionData": function_data}
    try:
        resp = requests.post(API_URL, headers=headers, json=data)
        return resp.json().get("data") or "{}"
    except Exception:
        return "{}"


def _init_multi_upload(access_token, parent_folder_id, file_info):
    params = (
        f"fileMd5={file_info.file_md5}"
        f"&fileName={quote(file_info.file_name, safe='')}"
        f"&fileSize={file_info.file_size}"
        f"&parentFolderId={parent_folder_id}"
        f"&sliceMd5={file_info.slice_md5}"
        f"&sliceSize={file_info.slice_size}"
    )
    response = _call_upload_api(access_token, "initMultiUploadV2", params)
    d = json.loads(response)
    result = d.get("data", {})
    return InitUploadVO(
        upload_type=result.get("uploadType", 0),
        upload_host=result.get("uploadHost", ""),
        upload_file_id=result.get("uploadFileId", ""),
        file_data_exists=result.get("fileDataExists", 0),
    )


def _get_multi_upload_urls(access_token, upload_file_id, file_info):
    all_urls = []
    max_each_count = 20
    part_info_list = file_info.part_info_list
    part_count = len(part_info_list)

    if part_count > max_each_count:
        batch_count = (part_count + max_each_count - 1) // max_each_count
        for i in range(batch_count):
            start_idx = i * max_each_count
            end_idx = min((i + 1) * max_each_count, part_count)
            sub_parts = part_info_list[start_idx:end_idx]
            part_info_str = ",".join([f"{p.part_number}-{p.etag}" for p in sub_parts])
            urls = _get_upload_urls_batch(access_token, upload_file_id, part_info_str, file_info.slice_size, file_info.file_size)
            all_urls.extend(urls)
    else:
        part_info_str = ",".join([f"{p.part_number}-{p.etag}" for p in part_info_list])
        all_urls = _get_upload_urls_batch(access_token, upload_file_id, part_info_str, file_info.slice_size, file_info.file_size)

    return all_urls


def _get_upload_urls_batch(access_token, upload_file_id, part_info, part_size, file_size):
    params = f"partInfo={part_info}&uploadFileId={upload_file_id}"
    response = _call_upload_api(access_token, "getMultiUploadUrlsV2", params)
    d = json.loads(response)
    upload_urls_json = d.get("uploadUrls", "{}")
    upload_urls_map = upload_urls_json if isinstance(upload_urls_json, dict) else json.loads(upload_urls_json)
    request_time = time.time()
    result = []
    for key, val in upload_urls_map.items():
        part_number = int(key.replace("partNumber_", ""))
        request_url = val.get("requestURL", "")
        head_params = val.get("requestHeader", "")
        header_map = {}
        if head_params:
            for header in head_params.split("&"):
                parts = header.split("=", 1)
                if len(parts) == 2:
                    header_map[parts[0]] = parts[1].replace("&amp;", "&")
        date_val = header_map.get("Date", "")
        if not date_val:
            date_val = header_map.get("x-amz-date", "")
            if date_val:
                date_val = f"x-amz-date:{date_val}"
        x_amz_limit = header_map.get("x-amz-limit", "")
        limit_rate = x_amz_limit.replace("rate=", "") if x_amz_limit else ""
        result.append(MultipleUploadUrl(
            http_method="PUT", http_url=request_url,
            content_type=header_map.get("Content-Type", ""),
            upload_id=upload_file_id,
            authorization=header_map.get("Authorization", ""),
            date=date_val, part_number=part_number,
            part_size=part_size, slice_size=part_size,
            part_md5=header_map.get("Content-MD5", ""),
            limit_rate=limit_rate, request_time=request_time,
        ))
    result.sort(key=lambda x: x.part_number)
    if len(result) == 1:
        result[0].part_size = file_size
    elif len(result) > 1:
        result[-1].part_size = file_size - part_size * (len(result) - 1)
    return result


def _upload_single_part(part_data, upload_url):
    if upload_url.request_time > 0:
        elapsed = time.time() - upload_url.request_time
        if elapsed > 900:
            return PartUploadStatus(upload_status=False, part_number=upload_url.part_number, msg="上传地址已过期")
    headers = {
        "Content-Type": "application/octet-stream",
        "Authorization": upload_url.authorization,
        "Content-Length": str(len(part_data)),
        "Content-MD5": upload_url.part_md5,
        "User-Agent": "cloudDiskServer_1.0.0_python",
    }
    if upload_url.date.startswith("x-amz-date:"):
        headers["x-amz-Date"] = upload_url.date.replace("x-amz-date:", "")
    else:
        headers["Date"] = upload_url.date
    if upload_url.limit_rate:
        headers["x-amz-limit"] = f"rate={upload_url.limit_rate}"
    try:
        resp = requests.put(upload_url.http_url, headers=headers, data=part_data)
        if resp.status_code == 200:
            return PartUploadStatus(upload_status=True, part_number=upload_url.part_number, msg="上传成功")
        else:
            return PartUploadStatus(upload_status=False, part_number=upload_url.part_number, msg=f"上传失败: {resp.status_code}")
    except Exception as e:
        return PartUploadStatus(upload_status=False, part_number=upload_url.part_number, msg=str(e))


def _commit_multi_upload(access_token, upload_file_id, file_info=None, lazy_check=0):
    params_list = [f"uploadFileId={upload_file_id}", "opertype=3"]
    if lazy_check == 1 and file_info:
        params_list.append(f"fileMd5={file_info.file_md5}")
        params_list.append(f"sliceMd5={file_info.slice_md5}")
    params = "&".join(params_list)
    response = _call_upload_api(access_token, "commitMultiUploadFileV2", params)
    result = json.loads(response)
    if result.get("code") == "SUCCESS":
        file_data = result.get("file", {})
        return CommitUploadResult(
            success=True, user_file_id=file_data.get("userFileId", ""),
            file_name=file_data.get("fileName", ""), file_size=file_data.get("fileSize", 0),
            file_md5=file_data.get("fileMd5", ""),
        )
    else:
        return CommitUploadResult(success=False, msg=result.get("msg", "提交失败"))


def _do_upload(access_token, file_path, parent_folder_id, slice_size=10*1024*1024, max_workers=5):
    """完整上传流程，返回 bool"""
    file_info = _get_upload_file_info(file_path, slice_size)
    init_result = _init_multi_upload(access_token, parent_folder_id, file_info)
    if init_result.file_data_exists == 1:
        result = _commit_multi_upload(access_token, init_result.upload_file_id, file_info=file_info, lazy_check=1)
        return result.success
    upload_urls = _get_multi_upload_urls(access_token, init_result.upload_file_id, file_info)
    if not upload_urls:
        return False
    # 多线程上传分片
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_part = {}
        for url_info in upload_urls:
            with open(file_path, "rb") as f:
                f.seek((url_info.part_number - 1) * url_info.slice_size)
                part_data = f.read(url_info.part_size)
            future_to_part[executor.submit(_upload_single_part, part_data, url_info)] = url_info
        for future in as_completed(future_to_part):
            results.append(future.result())
    failed = [r for r in results if not r.upload_status]
    if failed:
        return False
    result = _commit_multi_upload(access_token, init_result.upload_file_id, file_info=file_info)
    return result.success


def cmd_create_folder(args):
    """创建目录"""
    access_token = load_token()
    if not access_token:
        print(json.dumps({"success": False, "message": "请先登录"}, ensure_ascii=False))
        return
    if not args.name:
        print(json.dumps({"success": False, "message": "请提供--name参数"}, ensure_ascii=False))
        return
    function_data = {"folderName": args.name}
    if args.parent_id:
        function_data["parentFolderId"] = args.parent_id
    if args.path:
        function_data["relativePath"] = args.path
    result = call_cloud_api(access_token, "createFolder", json.dumps(function_data))
    success, message, data = parse_api_response(result)
    if not success:
        print(json.dumps({"success": False, "message": message}, ensure_ascii=False))
        return
    print(json.dumps({
        "success": True,
        "folder_id": data.get("id"),
        "folder_name": data.get("name"),
        "parent_id": data.get("parentId"),
        "path": data.get("pathStr"),
        "create_time": data.get("createDate")
    }, ensure_ascii=False))


def cmd_upload(args):
    """上传文件"""
    access_token = load_token()
    if not access_token:
        print(json.dumps({"success": False, "message": "请先登录"}, ensure_ascii=False))
        return
    if not args.local:
        print(json.dumps({"success": False, "message": "请提供--local参数指定本地文件路径"}, ensure_ascii=False))
        return
    if not args.folder_id:
        print(json.dumps({"success": False, "message": "请提供--folder-id参数指定目标文件夹ID"}, ensure_ascii=False))
        return
    try:
        success = _do_upload(
            access_token, args.local, args.folder_id,
            slice_size=args.slice_size or 10*1024*1024,
            max_workers=args.workers or 5
        )
        print(json.dumps({"success": success, "message": "上传成功" if success else "上传失败"}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"success": False, "message": str(e)}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="天翼云盘助手 - 云盘操作（全功能版）")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # login
    login_parser = subparsers.add_parser("login", help="登录天翼云盘")
    login_parser.add_argument("--auth-code", help="授权码（从网页获取）")

    # info
    subparsers.add_parser("info", help="显示Token状态")

    # get-folder
    get_folder_parser = subparsers.add_parser("get-folder", help="查询目录信息")
    get_folder_parser.add_argument("--folder-id", help="文件夹ID")
    get_folder_parser.add_argument("--path", help="文件夹路径")

    # list-files
    list_files_parser = subparsers.add_parser("list-files", help="查询文件列表")
    list_files_parser.add_argument("--folder-id", required=True, help="文件夹ID")
    list_files_parser.add_argument("--page", type=int, help="页码")
    list_files_parser.add_argument("--size", type=int, help="每页数量")

    # search-files
    search_files_parser = subparsers.add_parser("search-files", help="搜索文件")
    search_files_parser.add_argument("--folder-id", required=True, help="文件夹ID")
    search_files_parser.add_argument("--keyword", help="搜索关键词")
    search_files_parser.add_argument("--recursive", action="store_true", help="递归搜索")

    # download
    download_parser = subparsers.add_parser("download", help="获取文件下载链接")
    download_parser.add_argument("--file-id", required=True, help="文件ID")

    # search-images
    search_images_parser = subparsers.add_parser("search-images", help="智能图片搜索（全盘）")
    search_images_parser.add_argument("--text", required=True, help="搜索关键词/自然语言描述")
    search_images_parser.add_argument("--page", type=int, default=1, help="页码")
    search_images_parser.add_argument("--size", type=int, default=50, help="每页数量")

    # create-folder
    create_folder_parser = subparsers.add_parser("create-folder", help="创建目录")
    create_folder_parser.add_argument("--name", required=True, help="文件夹名称")
    create_folder_parser.add_argument("--parent-id", help="父文件夹ID")
    create_folder_parser.add_argument("--path", help="相对路径")

    # upload
    upload_parser = subparsers.add_parser("upload", help="上传文件到云盘")
    upload_parser.add_argument("--local", required=True, help="本地文件路径")
    upload_parser.add_argument("--folder-id", required=True, help="目标文件夹ID")
    upload_parser.add_argument("--slice-size", type=int, default=10*1024*1024, help="分片大小")
    upload_parser.add_argument("--workers", type=int, default=5, help="并发线程数")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "login": cmd_login,
        "info": cmd_info,
        "get-folder": cmd_get_folder,
        "list-files": cmd_list_files,
        "search-files": cmd_search_files,
        "download": cmd_download,
        "search-images": cmd_search_images,
        "create-folder": cmd_create_folder,
        "upload": cmd_upload,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        print(json.dumps({"success": False, "message": f"未知命令: {args.command}"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
