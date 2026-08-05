// Shared chrome for every Lucky Bee mobile web form.
//
// Two things every form needed and none of them owned:
//
//   * The item title is rendered by Frappe as <h1 class="ellipsis"> inside a
//     .web-form-title that is also .ellipsis - white-space:nowrap, so a real
//     product name ("KINGSTON 3PC CASSEROLE SET...") was cut off mid-word on a
//     phone with no way to read the rest. Let it wrap onto a second line.
//
//   * After a scan, staff landed on a form with no sign of *what* they had
//     scanned. The strip below the title shows the item code and its barcodes,
//     plus the code actually scanned (passed through as ?scanned= by
//     /mobile_scan), so a mis-scan is caught before anything is edited or
//     photographed.
//
// IMPORTANT - do not wrap any of this in frappe.ready(). This file is pulled in
// with $.getScript from each form's own .js, i.e. from *inside* a frappe.ready
// handler. frappe.ready() only pushes onto frappe.ready_events, and
// trigger_ready() walks that array exactly once with forEach - entries appended
// after the walk began are never visited, so a handler registered here would
// silently never run. Everything below bootstraps itself on load instead.
(function () {
    const STYLE_ID = 'lb-mobile-common-style';
    const HEADER_ID = 'lb-item-header';

    // --- long titles wrap instead of being cut -----------------------------
    function inject_styles() {
        if (document.getElementById(STYLE_ID)) return;
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
            .web-form-head .web-form-title.ellipsis {
                white-space: normal;
                overflow: visible;
                min-width: 0;
            }
            .web-form-head .web-form-title h1.ellipsis,
            .web-form-head .web-form-title p.ellipsis {
                white-space: normal;
                overflow: hidden;
                /* Two lines, then ellipsis - enough for the long product names
                   we actually have, without pushing the form off the screen. */
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow-wrap: anywhere;
                line-height: 1.25;
            }
            #${HEADER_ID} {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                margin-top: 10px;
            }
            #${HEADER_ID} .lb-chip {
                display: inline-flex;
                align-items: baseline;
                gap: 5px;
                padding: 2px 8px;
                border: 1px solid var(--border-color, #d8d8d8);
                border-radius: 12px;
                background: var(--fg-color, #fff);
                font-size: 11px;
                line-height: 1.6;
            }
            #${HEADER_ID} .lb-chip-label {
                color: var(--text-muted, #8d99a6);
                text-transform: uppercase;
                letter-spacing: .03em;
                font-size: 10px;
            }
            #${HEADER_ID} .lb-chip-value {
                font-family: monospace;
                font-size: 12px;
                overflow-wrap: anywhere;
            }
            #${HEADER_ID} .lb-chip-scanned {
                border-color: #2e7d32;
                background: #eef7ee;
            }
        `;
        document.head.appendChild(style);
    }

    // --- "what did I just scan?" strip -------------------------------------
    function esc(s) {
        return frappe.utils.escape_html(s == null ? '' : String(s));
    }

    function scanned_code() {
        try {
            return (new URLSearchParams(window.location.search).get('scanned') || '').trim();
        } catch (e) {
            return '';   // URLSearchParams unavailable on a very old browser
        }
    }

    function chip(label, value, extraClass) {
        return `<span class="lb-chip ${extraClass || ''}">
                    <span class="lb-chip-label">${esc(label)}</span>
                    <span class="lb-chip-value">${esc(value)}</span>
                </span>`;
    }

    function render_header(data) {
        const $strip = $('#' + HEADER_ID);
        if (!$strip.length || !data) return;

        const scanned = scanned_code();
        const all = data.barcodes || [];
        const known = all.map(b => String(b.value));
        // Plenty of items carry a barcode identical to their item code; the Item
        // chip already shows that, so repeating it just crowds the strip.
        const barcodes = all.filter(b => b.value !== data.item_code);

        let html = chip('Item', data.item_code);

        // Only worth its own chip when it isn't already shown as one of the
        // item's own codes - otherwise it says the same thing twice.
        if (scanned && known.indexOf(scanned) === -1 && scanned !== data.item_code) {
            html += chip('Scanned', scanned, 'lb-chip-scanned');
        }

        barcodes.forEach(b => {
            html += chip(b.label, b.value, b.value === scanned ? 'lb-chip-scanned' : '');
        });

        if (!all.length) {
            html += chip('Barcode', 'none on this item');
        }

        $strip.html(html);
    }

    function setup_item_header() {
        if (document.getElementById(HEADER_ID)) return true;
        if (!frappe.web_form || !frappe.web_form.doc || !frappe.web_form.doc.name) return false;

        const $head = $('.web-form-head');
        if (!$head.length) return false;

        const itemCode = frappe.web_form.doc.name;
        $head.append(`<div id="${HEADER_ID}">${chip('Item', itemCode)}</div>`);

        frappe.call({
            method: 'luckybee_customization.api.mobile_forms.get_mobile_item_header',
            args: { item_code: itemCode },
            callback: r => render_header(r.message),
            // A failed lookup must not blank the strip - the item code chip
            // rendered above is already the useful half of it.
            error: () => {}
        });
        return true;
    }

    function boot() {
        inject_styles();
        setup_item_header();
    }

    // frappe.web_form.doc is populated asynchronously and is routinely not ready
    // on first pass; both steps above are idempotent, so retrying is safe.
    boot();
    [300, 800, 1500, 2500].forEach(delay => setTimeout(boot, delay));

    // The dependable signal, for a phone slow enough to outlast the retries
    // above. The events emitter rather than frappe.web_form.after_load, which
    // mobile_preview.js assigns to - .on() adds a handler rather than replacing
    // whatever got there first.
    if (frappe.web_form && frappe.web_form.events) {
        frappe.web_form.events.on('after_load', boot);
    }
})();
