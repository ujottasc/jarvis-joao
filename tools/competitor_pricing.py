"""Pull a competitor's pricing/positioning pages per country -> spreadsheet.

Usage: python competitor_pricing.py URL [URL ...] [--out pricing.xlsx]
"""
import re
import sys
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook

COUNTRIES = {  # name: (proxy country code, Accept-Language)
    "US": ("us", "en-US,en;q=0.9"),
    "Germany": ("de", "de-DE,de;q=0.9,en;q=0.5"),
    "India": ("in", "en-IN,hi;q=0.9,en;q=0.5"),
    "Brazil": ("br", "pt-BR,pt;q=0.9,en;q=0.5"),
}
ENV_FILE = Path(__file__).with_name(".env.local")


def proxies_for(code):
    """Per-country proxy from .env.local, or None (direct) if no credentials set."""
    env = dict(
        line.strip().split("=", 1)
        for line in (ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else [])
        if "=" in line and not line.startswith("#")
    )
    if not (env.get("PROXY_USER") and env.get("PROXY_PASS")):
        return None
    user, pw = quote(env["PROXY_USER"], safe=""), quote(env["PROXY_PASS"], safe="")
    url = f"http://{user}__cr.{code}:{pw}@{env['PROXY_HOST']}:{env['PROXY_PORT']}"
    return {"http": url, "https": url}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
PRICE = re.compile(
    r"(?:R\$|US\$|[$€₹£]|\b(?:USD|EUR|INR|BRL)\b)\s?\d[\d.,]*|\d[\d.,]*\s?(?:€|\b(?:USD|EUR|INR|BRL)\b)"
)


def extract(html):
    """Return (title, h1, [(plan, price), ...]) from a page's HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    h1 = soup.h1.get_text(" ", strip=True) if soup.h1 else ""
    plans = []
    # ponytail: plan name = nearest heading above the price. Naive; swap for
    # per-site selectors if a page nests its pricing cards unusually.
    for node in soup.find_all(string=PRICE):
        heading = node.find_previous(["h2", "h3", "h4", "h5"])
        plan = heading.get_text(" ", strip=True) if heading else ""
        for price in PRICE.findall(node):
            if (plan, price) not in plans:
                plans.append((plan, price))
    return title, h1, plans


def main(urls, out):
    if not proxies_for("us"):
        print("no proxy credentials in .env.local: all requests leave from this machine")
    wb = Workbook()
    ws = wb.active
    ws.append(["country", "request_exit_country", "url", "http_status", "page_title", "h1", "plan", "price"])
    for url in urls:
        for country, (code, lang) in COUNTRIES.items():
            proxies = proxies_for(code)
            exit_country = "?"
            try:
                # Verify where the request really exits rather than trusting the config.
                exit_country = requests.get("https://ipinfo.io/country", proxies=proxies, timeout=30).text.strip()
                r = requests.get(
                    url, headers={"User-Agent": UA, "Accept-Language": lang}, proxies=proxies, timeout=30
                )
                status, (title, h1, plans) = r.status_code, extract(r.text)
            except requests.RequestException as e:
                # Exception text can include the proxy URL; never print credentials.
                status, title, h1, plans = f"error: {type(e).__name__}", "", "", []
            for plan, price in plans or [("", "")]:
                ws.append([country, exit_country, url, status, title, h1, plan, price])
            print(f"{country:8} exit={exit_country} status={status} prices={[p for _, p in plans]}")
    wb.save(out)
    print(f"saved {out}")


def demo():
    html = "<title>T</title><h1>Hi</h1><h3>Pro</h3><p>€29 / mo</p><h3>Team</h3><p>R$ 99</p>"
    assert extract(html) == ("T", "Hi", [("Pro", "€29"), ("Team", "R$ 99")])


if __name__ == "__main__":
    demo()
    args = sys.argv[1:]
    out = "pricing.xlsx"
    if "--out" in args:
        i = args.index("--out")
        out = args[i + 1]
        del args[i : i + 2]
    if not args:
        sys.exit(__doc__)
    main(args, out)
