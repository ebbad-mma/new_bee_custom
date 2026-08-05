"""B2 - catalogue-wide Keepa re-sync.

Only a handful of the ~1,595 ASIN-matched items had ever been re-synced, so
amz_best_price / amz_search_keywords and friends were blank across the rest.

This cannot be a single pass. Keepa bills per lookup and the account refills at
a fixed rate (5 tokens/minute at time of writing), so a full sweep is a
multi-hour job that must survive being interrupted. Two design points follow
from that:

  * Resumable with no bookkeeping doctype - items are processed oldest-synced
    first, never-synced ahead of everything, so simply running it again picks
    up exactly where it stopped.
  * Token-aware - it checks the balance before each item and stops cleanly
    when it drops below a reserve, rather than dying mid-catalogue on a
    PAYMENT_REQUIRED / throttle.

Wired to run hourly, so the backlog drains on its own; it is also safe to
invoke by hand for a bounded batch.
"""

import frappe
from frappe.utils import cint

# Leave a little headroom so an interactive "Refresh Amazon Data" press, or the
# nightly velocity job, is not starved by the bulk sweep.
TOKEN_RESERVE = 20

# Bound each run so an hourly schedule cannot pile up overlapping jobs.
DEFAULT_MAX_ITEMS = 200


def _tokens_left():
	"""Return Keepa's current token balance, or None if it cannot be read."""
	try:
		import keepa

		api = keepa.Keepa(frappe.conf.get("keepa_api_key"))
		api.update_status()
		return cint(getattr(api.status, "tokensLeft", None))
	except Exception:
		return None


# custom_asin_no is a 30-char field, but 81 items hold several comma-separated
# ASINs and overflow it. Those rows cannot be saved at all - Frappe's length
# validation rejects the existing value - so they would fail on every pass and
# never drain. They also cannot be looked up: the sync passes the whole field to
# Keepa as one ASIN. Excluded here so the sweep makes progress, and counted
# separately by bulk_keepa_sync_status() so they stay visible rather than
# silently dropping out of the catalogue.
ASIN_FIELD_LIMIT = 30


def pending_items(limit):
	"""ASIN-matched items, least recently synced first, never-synced first of all."""
	return frappe.db.sql(
		"""
		SELECT name
		FROM `tabItem`
		WHERE IFNULL(custom_asin_no, '') != ''
		  AND IFNULL(disabled, 0) = 0
		  AND CHAR_LENGTH(custom_asin_no) <= %s
		ORDER BY (amz_last_successful_sync IS NOT NULL),
				 amz_last_successful_sync ASC,
				 (amz_last_synced IS NOT NULL),
				 amz_last_synced ASC
		LIMIT %s
		""",
		(ASIN_FIELD_LIMIT, limit),
		pluck=True,
	)


@frappe.whitelist()
def bulk_keepa_sync(max_items=None, ignore_tokens=False):
	"""Re-sync a bounded batch of ASIN-matched items.

	Saving the Item re-runs sync_keepa_item on before_save, so this reuses the
	exact mapping the nightly sync and the manual refresh button use - there is
	no second copy of the Keepa logic to keep in step.
	"""
	if not frappe.conf.get("keepa_api_key"):
		return {"status": "error", "message": "Keepa API key is not configured."}

	max_items = cint(max_items) or DEFAULT_MAX_ITEMS
	items = pending_items(max_items)

	result = {
		"attempted": 0,
		"succeeded": 0,
		"failed": 0,
		"skipped_no_tokens": 0,
		"tokens_at_start": _tokens_left(),
		"candidates": len(items),
		"errors": [],
	}

	for item_code in items:
		if not ignore_tokens:
			left = _tokens_left()
			if left is not None and left <= TOKEN_RESERVE:
				# Out of budget for now. The ordering above means the next run
				# resumes here, so simply stopping is the correct behaviour.
				result["skipped_no_tokens"] = len(items) - result["attempted"]
				break

		result["attempted"] += 1
		try:
			doc = frappe.get_doc("Item", item_code)
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			result["succeeded"] += 1
		except Exception as e:
			frappe.db.rollback()
			result["failed"] += 1
			# Keep the run going - one bad ASIN must not stall the sweep - but
			# record enough to chase it afterwards.
			if len(result["errors"]) < 20:
				result["errors"].append({"item": item_code, "error": str(e)[:200]})
			frappe.log_error(
				title=f"Bulk Keepa sync failed for {item_code}",
				message=frappe.get_traceback(),
			)

	result["tokens_at_end"] = _tokens_left()
	result["remaining_unsynced"] = frappe.db.count(
		"Item", {"custom_asin_no": ["!=", ""], "amz_last_successful_sync": ["is", "not set"]}
	)
	return result


def bulk_keepa_sync_scheduled():
	"""Hourly entry point - drains the backlog a batch at a time."""
	if not frappe.conf.get("keepa_api_key"):
		return
	bulk_keepa_sync()


# B4 - "Stale: last sync succeeded but over 90 days old".
STALE_AFTER_DAYS = 90


@frappe.whitelist()
def flag_stale_amazon_data():
	"""Move items whose last *successful* sync has aged past the threshold to
	"Stale".

	This cannot be decided at sync time: an item is Matched the moment it syncs
	and only becomes Stale later through the passage of time, with nothing
	running against it. So it needs its own sweep.

	Deliberately only touches rows currently marked "Matched" - "Refresh
	Failed" and "Out of Stock / Discontinued" say something more specific about
	why the data is untrustworthy, and overwriting them with the blander
	"Stale" would lose that. Done as a single UPDATE rather than per-document
	saves: this is a status recalculation over thousands of rows and must not
	re-trigger the Keepa sync on before_save.
	"""
	updated = frappe.db.sql(
		"""
		UPDATE `tabItem`
		SET amz_data_status = 'Stale'
		WHERE amz_data_status = 'Matched'
		  AND amz_last_successful_sync IS NOT NULL
		  AND amz_last_successful_sync < DATE_SUB(CURDATE(), INTERVAL %s DAY)
		""",
		(STALE_AFTER_DAYS,),
	)
	frappe.db.commit()
	return {
		"marked_stale": frappe.db.count("Item", {"amz_data_status": "Stale"}),
		"threshold_days": STALE_AFTER_DAYS,
	}


@frappe.whitelist()
def bulk_keepa_sync_status():
	"""How much of the catalogue still needs a successful Amazon sync."""
	total = frappe.db.count("Item", {"custom_asin_no": ["!=", ""], "disabled": 0})
	synced = frappe.db.count(
		"Item",
		{"custom_asin_no": ["!=", ""], "disabled": 0, "amz_last_successful_sync": ["is", "set"]},
	)
	unsyncable = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabItem`
		   WHERE IFNULL(custom_asin_no,'') != '' AND IFNULL(disabled,0) = 0
			 AND CHAR_LENGTH(custom_asin_no) > %s""",
		(ASIN_FIELD_LIMIT,),
	)[0][0]

	tokens = _tokens_left()
	syncable_remaining = max(total - synced - unsyncable, 0)

	return {
		"asin_matched_items": total,
		"successfully_synced": synced,
		"remaining": total - synced,
		# Items whose custom_asin_no overflows the 30-char field: unsaveable as
		# they stand, so excluded from the sweep and needing a data decision.
		"blocked_over_length_asin": unsyncable,
		"syncable_remaining": syncable_remaining,
		"tokens_left": tokens,
		# ~10 tokens per item measured live; Keepa refills at 5/min (300/hour).
		"estimated_tokens_needed": syncable_remaining * 10,
		"estimated_hours_at_refill_rate": round(syncable_remaining * 10 / 300.0, 1),
	}
