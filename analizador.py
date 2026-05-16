import time
from typing import Optional

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


def _meta_content(soup: BeautifulSoup, *, name: str | None = None, property_: str | None = None) -> Optional[str]:
    selector = {}
    if name:
        selector["name"] = name
    if property_:
        selector["property"] = property_

    tag = soup.find("meta", attrs=selector)
    if not tag:
        return None

    content = tag.get("content")
    if not content:
        return None

    limpio = content.strip()
    return limpio or None


def analizar_web(url: str) -> dict:
    try:
        inicio = time.perf_counter()
        response = requests.get(url, headers=HEADERS, timeout=10)
        fin = time.perf_counter()
    except requests.RequestException as exc:
        return {"error": f"No se pudo analizar la web: {exc}"}

    soup = BeautifulSoup(response.text, "lxml")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    meta_description = _meta_content(soup, name="description")
    imagenes = soup.find_all("img")
    h1s = soup.find_all("h1")
    response_url = response.url if isinstance(response.url, str) else url

    return {
        "https": response_url.startswith("https://"),
        "tiempo_carga_ms": int(round((fin - inicio) * 1000)),
        "status_code": response.status_code,
        "title": title,
        "title_length": len(title) if title else 0,
        "meta_description": meta_description,
        "meta_description_length": len(meta_description) if meta_description else 0,
        "open_graph": _meta_content(soup, property_="og:title") is not None,
        "twitter_card": _meta_content(soup, name="twitter:card") is not None,
        "schema_org": soup.find("script", attrs={"type": "application/ld+json"}) is not None,
        "viewport_responsive": _meta_content(soup, name="viewport") is not None,
        "favicon": soup.find("link", rel=lambda value: value and "icon" in value) is not None,
        "cantidad_imagenes": len(imagenes),
        "imagenes_sin_alt": sum(1 for imagen in imagenes if not imagen.get("alt", "").strip()),
        "cantidad_h1": len(h1s),
        "tiene_h1": len(h1s) > 0,
    }


def analizar_instagram(handle: str) -> dict:
    if not handle or not handle.strip():
        return {"analizado": False}

    limpio = handle.strip().lstrip("@").strip().strip("/")
    if not limpio:
        return {"analizado": False}

    url_perfil = f"https://www.instagram.com/{limpio}/"

    try:
        response = requests.get(url_perfil, headers=HEADERS, timeout=10)
    except requests.RequestException as exc:
        return {"analizado": False, "error": f"No se pudo analizar Instagram: {exc}"}

    soup = BeautifulSoup(response.text, "lxml")
    og_title = _meta_content(soup, property_="og:title")
    bio_snippet = _meta_content(soup, property_="og:description")
    imagen_perfil = _meta_content(soup, property_="og:image")

    return {
        "analizado": True,
        "handle": limpio,
        "perfil_existe": response.status_code == 200 and bool(og_title or bio_snippet or imagen_perfil),
        "bio_snippet": bio_snippet,
        "imagen_perfil": imagen_perfil,
        "url_perfil": url_perfil,
    }
