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
