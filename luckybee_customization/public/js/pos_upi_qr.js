// A "Show UPI QR" button on the POS payment screen.
//
// ERPNext's POS has no slot for this, so the button is added by wrapping the
// payment screen's own render_payment_mode_dom() - it redraws that section
// whenever a mode is picked, and anything appended outside that call gets wiped.
// Wrapping rather than replacing means an ERPNext update to the original method
// still takes effect; the worst case if the internals change is that the button
// stops appearing, never that payment breaks.
//
// The amount is read from the live invoice and the VPA comes from the server,
// so what the customer scans is always the real amount due into the shop's own
// account.
(function () {
	const BUTTON_CLASS = "lb-upi-btn";

	function amount_due(doc) {
		const grand = flt(doc.grand_total);
		const paid = flt(doc.paid_amount);
		// Part-paid bills (cash first, rest on UPI) are the common case at a
		// counter, so collect the remainder rather than the whole bill again.
		const due = flt(grand - paid, 2);
		return due > 0 ? due : grand;
	}

	function show_qr(payment) {
		const doc = payment.events.get_frm().doc;
		const due = amount_due(doc);

		if (due <= 0) {
			frappe.show_alert({ message: __("Nothing left to collect"), indicator: "orange" });
			return;
		}

		frappe.call({
			method: "luckybee_customization.api.pos_upi.get_upi_qr",
			args: { pos_profile: doc.pos_profile, amount: due, reference: doc.name },
			freeze: true,
			freeze_message: __("Building QR…"),
			callback: (r) => {
				const data = r.message;
				if (!data) return;
				const dialog = new frappe.ui.Dialog({
					title: __("Scan to pay {0}", [data.amount_formatted]),
					primary_action_label: __("Done"),
					primary_action: () => dialog.hide(),
				});
				dialog.$body.html(`
					<div style="text-align:center; padding:8px 0;">
						<div style="display:inline-block; padding:10px; background:#fff; border:1px solid var(--border-color); border-radius:8px;">
							${data.svg}
						</div>
						<div style="margin-top:10px; font-size:20px; font-weight:700;">
							${frappe.utils.escape_html(data.amount_formatted)}
						</div>
						<div class="text-muted" style="font-size:12px;">
							${frappe.utils.escape_html(data.payee)} &middot;
							<span style="font-family:monospace;">${frappe.utils.escape_html(data.vpa)}</span>
						</div>
						<div class="text-muted" style="font-size:11px; margin-top:8px;">
							${__("Ask the customer to scan with any UPI app. Confirm the payment lands before completing the bill.")}
						</div>
					</div>
				`);
				dialog.show();
			},
		});
	}

	function add_button(payment) {
		const $modes = payment.$payment_modes;
		if (!$modes || !$modes.length || $modes.find("." + BUTTON_CLASS).length) return;

		const $btn = $(`
			<div class="payment-mode-wrapper" style="padding:4px 0;">
				<button type="button" class="btn btn-default btn-block ${BUTTON_CLASS}">
					&#128241; ${__("Show UPI QR")}
				</button>
			</div>
		`);
		$btn.on("click", () => show_qr(payment));
		$modes.append($btn);
	}

	function patch() {
		const Payment = window.erpnext && erpnext.PointOfSale && erpnext.PointOfSale.Payment;
		if (!Payment || Payment.prototype.__lb_upi_patched) return !!Payment;

		const original = Payment.prototype.render_payment_mode_dom;
		Payment.prototype.render_payment_mode_dom = function () {
			const result = original.apply(this, arguments);
			// A failure here must never take the payment screen down with it.
			try {
				add_button(this);
			} catch (e) {
				console.error("UPI QR button could not be added:", e);
			}
			return result;
		};
		Payment.prototype.__lb_upi_patched = true;
		return true;
	}

	// The POS bundle loads asynchronously, so the class may not exist yet when
	// this file runs. Poll briefly, then give up rather than spin forever.
	if (!patch()) {
		const timer = setInterval(() => {
			if (patch()) clearInterval(timer);
		}, 400);
		setTimeout(() => clearInterval(timer), 20000);
	}
})();
