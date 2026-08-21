/**
 * "Scan Next" on the mobile capture forms.
 *
 * Staff reach these forms by scanning a barcode. When the wrong box comes up -
 * and it does, in a stock room, holding a carton - the only way out was the
 * browser's back button. The risk is not the inconvenience: it is that someone
 * saves a record they did not mean to, simply to get moving again.
 *
 * Loaded for every web form on Item via the webform_include_js hook, so the five
 * capture forms share one control rather than five copies of it.
 */
frappe.ready(function () {
	// The forms are only ever reached from the scanner, and that is the only
	// place this button sends people back to.
	var SCANNER_URL = '/mobile_scan?autoscan=1';

	/**
	 * A snapshot of everything the user could have typed.
	 *
	 * Read from the DOM rather than frappe.web_form.get_values(): the count form
	 * has no Web Form Field rows at all - its inputs are built by its own script -
	 * so get_values() reports nothing changed however much was entered. Walking
	 * the controls works whoever built them.
	 */
	function currentValues() {
		// The whole page, not a form container: the count form builds its inputs
		// outside .web-form-wrapper, so scoping to the wrapper reported "nothing
		// changed" no matter what had been typed into it.
		var scope = document;
		var parts = [];
		var nodes = scope.querySelectorAll('input, select, textarea, [contenteditable="true"]');
		for (var i = 0; i < nodes.length; i++) {
			var el = nodes[i];
			if (el.type === 'hidden' || el.id === 'lb-scan-next') continue;
			if (el.type === 'checkbox' || el.type === 'radio') {
				parts.push(el.name + '=' + (el.checked ? 1 : 0));
			} else if (el.isContentEditable) {
				parts.push((el.id || i) + '=' + el.textContent);
			} else {
				parts.push((el.name || el.id || i) + '=' + el.value);
			}
		}
		// A file chosen for upload counts as work in progress too.
		var files = scope.querySelectorAll('input[type="file"]');
		for (var f = 0; f < files.length; f++) {
			if (files[f].files && files[f].files.length) parts.push('file' + f);
		}
		return parts.join('|');
	}

	function mount() {
		if (document.getElementById('lb-scan-next')) return true;

		// Sit beside the form's own actions so it reads as an alternative to
		// Save rather than something unrelated further down the page.
		var host = document.querySelector('.web-form-actions')
			|| document.querySelector('.web-form-footer')
			|| document.querySelector('.web-form-container')
			|| document.querySelector('.page_content');
		if (!host) return false;

		var btn = document.createElement('button');
		btn.type = 'button';
		btn.id = 'lb-scan-next';
		btn.className = 'btn btn-outline-secondary btn-sm';
		btn.style.cssText = 'margin:8px 8px 0 0;';
		btn.textContent = __('Scan Next');

		// Snapshot after the form has populated, so a prefilled record does not
		// read as "changed" the moment it loads.
		var baseline = null;
		setTimeout(function () { baseline = currentValues(); }, 800);

		btn.addEventListener('click', function () {
			var now = currentValues();
			var changed = baseline !== null && now !== null && now !== baseline;

			if (!changed) {
				// Nothing typed - no reason to interrupt anyone.
				window.location.href = SCANNER_URL;
				return;
			}

			frappe.confirm(
				__('You have unsaved changes on this item. Leave without saving?'),
				function () { window.location.href = SCANNER_URL; }
			);
		});

		host.appendChild(btn);
		return true;
	}

	// The form renders asynchronously, so poll briefly rather than assuming it
	// is ready. Gives up quietly - a missing button must never break the form.
	var tries = 0;
	var timer = setInterval(function () {
		if (mount() || ++tries > 40) clearInterval(timer);
	}, 250);
});
