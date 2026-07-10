import base64
import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter, Retry

from .config import CONFLUENCE_CFG, get_api_base_url

logger = logging.getLogger("confluence-mcp-server")


class ConfluenceConnection:
    _session: Optional[requests.Session] = None
    _is_authenticated: bool = False
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
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
    def _get_login_url(cls, path: str) -> str:
        base_url = CONFLUENCE_CFG["base_url"]
        context_path = CONFLUENCE_CFG.get("context_path", "/confluence")
        if not context_path.startswith("/"):
            context_path = f"/{context_path}"
        return f"{base_url}{context_path}{path}"

    @classmethod
    def _login(cls):
        if cls._login_attempts >= cls._MAX_LOGIN_ATTEMPTS:
            logger.warning(f"已达到最大登录尝试次数 ({cls._MAX_LOGIN_ATTEMPTS})，跳过登录")
            return

        cls._login_attempts += 1
        session = cls._session
        username = CONFLUENCE_CFG["username"]
        password = CONFLUENCE_CFG["api_token"]

        logger.info(f"尝试表单登录 (第 {cls._login_attempts}/{cls._MAX_LOGIN_ATTEMPTS} 次)...")

        try:
            login_page_url = cls._get_login_url("/login.action")
            response = session.get(login_page_url)
            logger.debug(f"获取登录页面: {response.status_code}")
        except Exception as e:
            logger.error(f"获取登录页面失败: {str(e)}")
            return

        login_data = {
            "os_username": username,
            "os_password": password,
            "os_cookie": "true",
            "os_destination": "",
            "login": "登录"
        }

        try:
            dologin_url = cls._get_login_url("/dologin.action")
            response = session.post(
                dologin_url,
                data=login_data,
                allow_redirects=True
            )
            logger.debug(f"登录请求: {response.status_code}")
            logger.debug(f"登录后URL: {response.url}")

            if "login.action" not in response.url:
                cls._is_authenticated = True
                logger.info("✅ 表单登录成功")
            else:
                logger.info("登录页面未跳转，可能是匿名访问模式或凭据需要验证")

        except Exception as e:
            logger.error(f"表单登录失败: {str(e)}")

        if not cls._is_authenticated:
            logger.info("尝试Basic Auth方式...")
            auth_string = f"{username}:{password}"
            auth_bytes = auth_string.encode("utf-8")
            auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
            session.headers.update({"Authorization": f"Basic {auth_base64}"})

    @classmethod
    def _test_authentication(cls) -> bool:
        try:
            response = cls.get("/space", params={"limit": 1})
            return response.get("size", 0) >= 0
        except Exception:
            return False

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
            cls._is_authenticated = False
            cls._session = None
            session = cls.get_session()
            response = session.request(method, url, params=params, json=data, **kwargs)

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