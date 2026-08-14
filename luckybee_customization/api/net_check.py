"""Outbound connectivity check, for diagnosing the Flipkart scraper on a host
with no shell access.

The Flipkart fetch fails on the production server with a TCP connect timeout,
while the identical code succeeds from a desktop. That distinction matters: a
timeout is not a blocked scraper, it is a host that cannot open a connection.
This narrows it down without needing a terminal - Frappe Cloud does not give
one, and guessing from the outside has already cost several rounds.

The host list is fixed on purpose. A whitelisted method that fetched an
arbitrary URL would be a server-side request forgery hole, letting any caller
use the server to probe addresses it can reach and the caller cannot.
"""

import re
import socket
import time

import frappe
from frappe import _

# Chosen to separate the possible causes:
#   flipkart      - the host we actually care about
#   keepa         - known to work, since the hourly sync succeeds
#   google/github - ordinary internet, to tell "Flipkart is blocked" apart
#                   from "outbound is restricted generally"
TARGETS = [
	("www.flipkart.com", 443),
	("api.keepa.com", 443),
	("www.google.com", 443),
	("github.com", 443),
]

CONNECT_TIMEOUT = 8


@frappe.whitelist()
def check_outbound():
	"""Try a TCP connection to each known host and report what happened.

	Deliberately a bare socket connection rather than an HTTP request: it
	separates "cannot reach the host" from "reached it and got an unhelpful
	page", which is exactly the ambiguity that made this hard to pin down.
	"""
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	results = []
	for host, port in TARGETS:
		entry = {"host": host, "port": port}

		# DNS first - a name that will not resolve is a different fault from a
		# name that resolves to an address nothing answers on.
		started = time.time()
		try:
			ip = socket.gethostbyname(host)
			entry["resolved_to"] = ip
			entry["dns_ms"] = int((time.time() - started) * 1000)
		except Exception as e:
			entry["resolved_to"] = None
			entry["dns_error"] = str(e)[:120]
			results.append(entry)
			continue

		started = time.time()
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(CONNECT_TIMEOUT)
		try:
			sock.connect((ip, port))
			entry["connected"] = True
			entry["connect_ms"] = int((time.time() - started) * 1000)
		except Exception as e:
			entry["connected"] = False
			entry["connect_ms"] = int((time.time() - started) * 1000)
			entry["connect_error"] = f"{type(e).__name__}: {str(e)[:100]}"
		finally:
			try:
				sock.close()
			except Exception:
				pass

		results.append(entry)

	reachable = [r["host"] for r in results if r.get("connected")]
	blocked = [r["host"] for r in results if r.get("resolved_to") and not r.get("connected")]

	if "www.flipkart.com" in blocked and len(reachable) >= 2:
		verdict = ("Flipkart specifically is unreachable while other hosts "
				   "answer - the address is being dropped at their end or "
				   "filtered at yours. A parser change cannot fix this.")
	elif not reachable:
		verdict = ("Nothing is reachable - outbound connections are blocked "
				   "for this host generally, not just to Flipkart.")
	elif "www.flipkart.com" in reachable:
		verdict = ("Flipkart is reachable from here, so the failure is in the "
				   "request or the response, not connectivity.")
	else:
		verdict = "Mixed result - see the per-host detail."

	return {"results": results, "reachable": reachable,
			"unreachable": blocked, "verdict": verdict}


# A product that has been listed for years, so a failure here is the connection
# rather than a dead listing. Nothing is written anywhere - this only fetches.
PROBE_FSN = "PEPGDUTJDQYUWZG5"


def _masked_proxy():
	"""The configured proxy with its credentials hidden.

	The proxy URL routinely carries user:password, and this method's output ends
	up pasted into chats and tickets - so it must never return the secret.
	"""
	proxy = frappe.conf.get("flipkart_proxy")
	if not proxy:
		return None
	return re.sub(r"//[^@/]+@", "//***:***@", proxy)


@frappe.whitelist()
def check_flipkart_fetch():
	"""Fetch a real Flipkart product page the way the scraper does, and report.

	Written for bringing an outbound proxy online: the socket check above says
	whether the address answers, this says whether the whole request works
	end to end - through `flipkart_proxy` when one is configured, directly when
	not. Reports the same three failure modes the scraper distinguishes, so a
	proxy can be proved working before anyone waits on an item save to tell them.
	"""
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	from luckybee_customization.overrides.scraper_utils import (
		_HEADERS,
		_product_ld_json,
		_proxies,
		_timeout,
	)

	out = {
		"proxy_configured": bool(frappe.conf.get("flipkart_proxy")),
		"proxy": _masked_proxy(),
		"timeout": _timeout(),
		"fsn": PROBE_FSN,
	}

	import requests
	from bs4 import BeautifulSoup as bs

	url = f"https://www.flipkart.com/product/p/itme?pid={PROBE_FSN}"
	started = time.time()
	try:
		page = requests.get(url, headers=_HEADERS, timeout=_timeout(), proxies=_proxies())
	except Exception as e:
		out["elapsed_ms"] = int((time.time() - started) * 1000)
		out["ok"] = False
		out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
		out["verdict"] = (
			"The request never completed. Through a proxy this is usually the "
			"proxy itself - wrong host/port, bad credentials, or slower than the "
			"timeout. Directly, it is the datacenter-IP block."
			if out["proxy_configured"] else
			"The request never completed and no proxy is configured - this is the "
			"datacenter-IP block. Set flipkart_proxy in site_config.json."
		)
		return out

	out["elapsed_ms"] = int((time.time() - started) * 1000)
	out["http_status"] = page.status_code
	out["bytes"] = len(page.content)

	soup = bs(page.content, "html.parser")
	product = _product_ld_json(soup)
	out["product_block"] = bool(product)
	out["title"] = (product.get("name") or "")[:120] if product else ""

	if product:
		out["ok"] = True
		out["verdict"] = (
			"Working. Flipkart served the full product page"
			+ (" through the proxy." if out["proxy_configured"] else " directly.")
		)
	else:
		out["ok"] = False
		page_title = ""
		try:
			if soup.title and soup.title.string:
				page_title = soup.title.string.strip()[:120]
		except Exception:
			pass
		out["page_title"] = page_title
		out["verdict"] = (
			"Reached Flipkart but got no product data - a bot-check or captcha "
			"page rather than the product. The connection works; this IP is being "
			"challenged. A different proxy (residential rather than datacenter) "
			"is what changes this."
		)

	return out
