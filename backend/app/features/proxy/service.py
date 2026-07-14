"""
AutoWebAgent - Proxy Service
==============================
Webshare rotating residential proxy management.
Handles proxy URL construction, rotation, and health checks.
"""

from typing import Optional, Dict, Any, List
import asyncio
import random
import httpx
from loguru import logger

from app.core.config import settings
from app.utils.helpers import build_proxy_url


class ProxyService:
    """
    Proxy management service.

    Uses Webshare rotating residential proxies with sticky sessions.
    Each browser session should maintain the same proxy IP for
    fingerprint consistency (sticky session).
    """

    _cached_proxies: List[Dict[str, Any]] = []

    @classmethod
    async def _fetch_proxies(cls) -> List[Dict[str, Any]]:
        """
        Fetch the list of valid proxies from Webshare API.
        Caches the result in memory to avoid hitting rate limits.
        """
        if cls._cached_proxies:
            return cls._cached_proxies

        api_key = settings.WEBSHARE_API_KEY
        if not api_key:
            logger.warning("⚠️ No WEBSHARE_API_KEY configured for proxy fetching")
            return []

        url = "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page_size=100"
        headers = {"Authorization": f"Token {api_key}"}

        try:
            logger.info("Fetching proxy list from Webshare...")
            response = None
            
            # 1. Try standard connection
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url, headers=headers)
            except httpx.ConnectError as ce:
                # 2. DNS Fallback: Resolve proxy.webshare.io manually over TCP DNS
                logger.warning(f"Default DNS failed ({ce}), attempting manual TCP DNS resolution...")
                import dns.query
                import dns.message
                q = dns.message.make_query('proxy.webshare.io', 'A')
                # Run sync TCP query in executor
                r = await asyncio.to_thread(dns.query.tcp, q, '8.8.8.8', timeout=5)
                
                ips = []
                for section in r.answer:
                    for item in section:
                        if hasattr(item, 'address'):
                            ips.append(item.address)
                
                if not ips:
                    raise Exception("Failed to resolve proxy.webshare.io manually")

                resolved_ip = ips[0]
                direct_url = url.replace("proxy.webshare.io", resolved_ip)
                logger.info(f"Resolved proxy.webshare.io to {resolved_ip}, fetching from {direct_url}")
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(direct_url, headers={**headers, "Host": "proxy.webshare.io"})

            if response and response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                valid_proxies = [p for p in results if p.get("valid", True)]
                if valid_proxies:
                    cls._cached_proxies = valid_proxies
                    logger.info(f"Successfully cached {len(valid_proxies)} proxies from Webshare.")
                    return cls._cached_proxies
            
            logger.error(f"Failed to fetch Webshare proxy list: {response.status_code if response else 'No Response'} - {response.text if response else ''}")
        except Exception as e:
            logger.error(f"Error fetching Webshare proxy list: {e}")

        return []

    @classmethod
    async def get_proxy_config(
        cls,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        proxy_host: Optional[str] = None,
        proxy_port: Optional[int] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a proxy configuration for Playwright.

        Args:
            proxy_username: Proxy username.
            proxy_password: Proxy password.
            proxy_host: Custom proxy host.
            proxy_port: Custom proxy port.
            country: Optional country code for geo-targeting.

        Returns:
            Dict with 'server', 'username', 'password', 'host', 'port' keys.
        """
        # If custom credentials/host are explicitly requested, use them
        if proxy_host and proxy_port:
            username = proxy_username or ""
            password = proxy_password or ""
            server = f"http://{username}:{password}@{proxy_host}:{proxy_port}" if username else f"http://{proxy_host}:{proxy_port}"
            return {"server": server, "username": username, "password": password, "host": proxy_host, "port": proxy_port}

        # Otherwise, dynamically load list from Webshare API
        proxies = await cls._fetch_proxies()
        if not proxies:
            # Fallback to local default proxy settings from env
            username = proxy_username or settings.WEBSHARE_PROXY_USERNAME or ""
            password = proxy_password or settings.WEBSHARE_PROXY_PASSWORD or ""
            host = proxy_host or settings.WEBSHARE_PROXY_HOST
            port = proxy_port or settings.WEBSHARE_PROXY_PORT

            if not username or not password:
                logger.warning("⚠️ No proxies available — running without proxy")
                return {}

            server = build_proxy_url(
                username=username,
                password=password,
                host=host,
                port=port,
            )
            return {"server": server, "username": username, "password": password, "host": host, "port": port}

        # Pick a proxy randomly from pool
        selected = random.choice(proxies)
        host = selected["proxy_address"]
        port = selected["port"]
        username = selected["username"]
        password = selected["password"]

        server = f"http://{username}:{password}@{host}:{port}"
        logger.info(f"🔌 Using Webshare Proxy from pool: {host}:{port} (Country: {selected.get('country_code')})")
        return {"server": server, "username": username, "password": password, "host": host, "port": port}

    @classmethod
    async def rotate_proxy(
        cls,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request a new proxy IP by selecting a different proxy from the cached pool.

        Returns:
            New proxy config with different IP.
        """
        proxies = await cls._fetch_proxies()
        if not proxies:
            import uuid
            rotation_id = uuid.uuid4().hex[:8]

            username = proxy_username or settings.WEBSHARE_PROXY_USERNAME or ""
            password = proxy_password or settings.WEBSHARE_PROXY_PASSWORD or ""

            if not username or not password:
                return {}

            server = (
                f"http://{username}-rotate-{rotation_id}:{password}"
                f"@{settings.WEBSHARE_PROXY_HOST}:{settings.WEBSHARE_PROXY_PORT}"
            )
            logger.info(f"🔄 Proxy rotated via backconnect (session: {rotation_id})")
            return {
                "server": server,
                "username": username,
                "password": password,
            }

        # Rotate to a different proxy randomly from pool
        selected = random.choice(proxies)
        host = selected["proxy_address"]
        port = selected["port"]
        username = selected["username"]
        password = selected["password"]

        server = f"http://{username}:{password}@{host}:{port}"
        logger.info(f"🔄 Proxy rotated to different Webshare pool IP: {host}:{port}")
        return {
            "server": server,
            "username": username,
            "password": password,
            "host": host,
            "port": port,
        }

    @classmethod
    async def validate_proxy(
        cls,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
        proxy_host: Optional[str] = None,
        proxy_port: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Test proxy connection by making a request to ipinfo.io.

        Returns:
            Dict with 'valid', 'ip', 'country', 'response_time_ms'.
        """
        import time

        config = await cls.get_proxy_config(
            proxy_username, proxy_password, proxy_host, proxy_port
        )

        if not config:
            return {"valid": False, "error": "No proxy credentials configured"}

        try:
            start = time.time()
            async with httpx.AsyncClient(proxy=config["server"], timeout=15) as client:
                response = await client.get("https://ipinfo.io/json")
                data = response.json()
                elapsed_ms = (time.time() - start) * 1000

                return {
                    "valid": True,
                    "ip": data.get("ip"),
                    "country": data.get("country"),
                    "city": data.get("city"),
                    "org": data.get("org"),
                    "response_time_ms": round(elapsed_ms),
                }
        except Exception as e:
            logger.error(f"Proxy validation failed: {e}")
            return {"valid": False, "error": str(e)}
