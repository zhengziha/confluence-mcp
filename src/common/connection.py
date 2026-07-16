import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter, Retry

from .config import CONFLUENCE_CFG, get_api_base_url

logger = logging.getLogger("confluence-mcp-server")


class ConfluenceConnection:
    _session: Optional[requests.Session] = None
    _login_attempts: int = 0
    _MAX_LOGIN_ATTEMPTS: int = 3

    @classmethod
    def get_session(cls) -> requests.Session:
        if cls._session is None:
            cls._session = cls._create_session()
            cls._login()
        return cls._session

    @classmethod
    def _create_session(cls) -> requests.Session:
        session = requests.Session()

        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.timeout = CONFLUENCE_CFG["timeout"]

        return session

    @classmethod
    def _login(cls):
        if cls._login_attempts >= cls._MAX_LOGIN_ATTEMPTS:
            logger.warning(f"已达到最大登录尝试次数 ({cls._MAX_LOGIN_ATTEMPTS})，跳过登录")
            return

        cls._login_attempts += 1
        session = cls._session
        username = CONFLUENCE_CFG["username"]
        password = CONFLUENCE_CFG["api_token"]

        logger.info("使用Basic Auth方式认证...")
        session.auth = (username, password)

    @classmethod
    def request(
        cls,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        **kwargs,
    ) -> requests.Response:
        url = f"{get_api_base_url()}{endpoint}"
        session = cls.get_session()

        logger.debug(f"请求: {method} {url}")
        if params:
            logger.debug(f"参数: {params}")
        if data:
            logger.debug(f"数据: {data}")

        response = session.request(method, url, params=params, json=data, **kwargs)

        logger.debug(f"响应状态码: {response.status_code}")

        if response.status_code == 401 and cls._login_attempts < cls._MAX_LOGIN_ATTEMPTS:
            logger.info("认证失效，重新登录...")
            cls._session = None
            session = cls.get_session()
            response = session.request(method, url, params=params, json=data, **kwargs)

        if response.status_code == 403 and "XSRF" in response.text:
            logger.info("XSRF检查失败，先发送GET请求建立会话...")
            session.get(f"{get_api_base_url()}/space", params={"limit": 1})
            response = session.request(method, url, params=params, json=data, **kwargs)
            logger.debug(f"重试响应状态码: {response.status_code}")
            if response.status_code >= 400:
                logger.error(f"XSRF重试失败: {response.status_code} - {response.text[:200]}")

        if response.status_code >= 400:
            logger.error(f"请求失败: {response.status_code} - {response.text[:200]}")

        response.raise_for_status()
        return response

    @classmethod
    def get(cls, endpoint: str, params: Optional[dict] = None, **kwargs) -> dict:
        response = cls.request("GET", endpoint, params=params, **kwargs)
        return response.json()

    @classmethod
    def post(cls, endpoint: str, data: Optional[dict] = None, **kwargs) -> dict:
        response = cls.request("POST", endpoint, data=data, **kwargs)
        return response.json()

    @classmethod
    def put(cls, endpoint: str, data: Optional[dict] = None, **kwargs) -> dict:
        response = cls.request("PUT", endpoint, data=data, **kwargs)
        return response.json()

    @classmethod
    def delete(cls, endpoint: str, **kwargs) -> None:
        cls.request("DELETE", endpoint, **kwargs)

    @classmethod
    def upload_attachment_bytes(
        cls,
        page_id: str,
        content: bytes,
        file_name: str,
        content_type: str = "application/octet-stream",
        comment: Optional[str] = None,
    ) -> dict:
        """从内存字节上传附件到页面（同名则覆盖更新）。"""
        session = cls.get_session()
        endpoint = f"/content/{page_id}/child/attachment"
        url = f"{get_api_base_url()}{endpoint}"

        try:
            existing = cls.get(endpoint, params={"filename": file_name, "limit": 1})
            if existing.get("size", 0) > 0:
                existing_id = existing["results"][0]["id"]
                url = f"{get_api_base_url()}/content/{page_id}/child/attachment/{existing_id}/data"
                logger.info(f"更新现有附件: {file_name} (ID: {existing_id})")
        except Exception as e:
            logger.debug(f"检查附件时出错（按新附件处理）: {e}")

        files = {"file": (file_name, content, content_type)}
        data = {}
        if comment:
            data["comment"] = comment

        # multipart 不能带默认的 application/json Content-Type
        headers = {"X-Atlassian-Token": "nocheck", "Accept": "application/json"}
        # 去掉 session 默认 Content-Type，让 requests 自动设置 multipart boundary
        prepare_headers = {k: v for k, v in session.headers.items() if k.lower() != "content-type"}
        prepare_headers.update(headers)

        logger.info(f"上传附件: {file_name} -> page {page_id}")
        response = session.post(url, files=files, data=data, headers=prepare_headers)

        if response.status_code == 401 and cls._login_attempts < cls._MAX_LOGIN_ATTEMPTS:
            logger.info("认证失效，重新登录后重试附件上传...")
            cls._is_authenticated = False
            cls._session = None
            session = cls.get_session()
            prepare_headers = {
                k: v for k, v in session.headers.items() if k.lower() != "content-type"
            }
            prepare_headers.update(headers)
            response = session.post(url, files=files, data=data, headers=prepare_headers)

        if response.status_code >= 400:
            logger.error(f"附件上传失败: {response.status_code} - {response.text[:200]}")
            response.raise_for_status()

        result = response.json()
        if "results" in result and result["results"]:
            attachment_info = result["results"][0]
        else:
            attachment_info = result

        logger.info(
            f"附件上传成功: {file_name} "
            f"(ID: {attachment_info.get('id')}, 大小: {len(content)} bytes)"
        )
        return attachment_info

    @classmethod
    def upload_attachment(
        cls,
        page_id: str,
        file_path: str,
        file_name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> dict:
        """从本地文件路径上传附件到页面。"""
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        name = file_name or path.name
        return cls.upload_attachment_bytes(
            page_id=page_id,
            content=path.read_bytes(),
            file_name=name,
            comment=comment,
        )