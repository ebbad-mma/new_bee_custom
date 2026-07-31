frappe.ready(function() {
    $.getScript("/assets/luckybee_customization/js/mobile_preview.js");

    // The field's DOM element may not exist yet at frappe.ready time on a real
    // device/network (confirmed live elsewhere in these forms - see Form 4's
    // fix for the same class of timing race). setup_asin_live_preview() is
    // idempotent (bails out if its panel already exists), so retrying is safe.
    setup_asin_live_preview();
    setTimeout(setup_asin_live_preview, 300);
    setTimeout(setup_asin_live_preview, 800);
    setTimeout(setup_asin_live_preview, 1500);

    function setup_asin_live_preview() {
        const $asinField = $('[data-fieldname="custom_asin_no"]');
        if (!$asinField.length) return;
        if ($asinField.find('#asin-preview-panel').length) return;

        const $panel = $(`
            <div id="asin-preview-panel" class="card p-2 mt-2 mb-2 bg-white border" style="max-width: 260px;">
                <div id="asin-preview-body" class="text-center">
                    <span class="text-muted small">Enter an ASIN to preview the Amazon listing.</span>
                </div>
            </div>
        `);
        $asinField.find('.frappe-control').append($panel);

        const $body = $panel.find('#asin-preview-body');
        let debounceTimer = null;
        let lastRequestedAsin = null;

        function render_loading() {
            $body.html('<span class="text-muted small">Looking up ASIN&hellip;</span>');
        }

        function render_result(asin, data) {
            // Ignore stale responses if the field has changed again since this request went out
            if (asin !== get_current_asin()) return;

            if (!data || (!data.image && data.price == null)) {
                $body.html('<span class="text-muted small">No Keepa listing found for this ASIN.</span>');
                return;
            }

            const imgHtml = data.image
                ? `<img src="${data.image}" class="img-fluid" style="max-height: 130px; object-fit: contain;" />`
                : '<div class="text-muted small py-3">No image available</div>';

            const priceHtml = (data.price != null)
                ? `<div class="font-weight-bold mt-1">₹${data.price}</div>`
                : '<div class="text-muted small mt-1">Price unavailable</div>';

            const titleHtml = data.title
                ? `<div class="small text-muted mt-1" style="line-height:1.2;">${frappe.utils.escape_html(data.title)}</div>`
                : '';

            $body.html(imgHtml + priceHtml + titleHtml);
        }

        function get_current_asin() {
            return ($asinField.find('input').val() || '').trim();
        }

        function fetch_preview() {
            const asin = get_current_asin();
            if (!asin) {
                $body.html('<span class="text-muted small">Enter an ASIN to preview the Amazon listing.</span>');
                return;
            }
            lastRequestedAsin = asin;
            render_loading();
            frappe.call({
                method: 'luckybee_customization.api.mobile_forms.fetch_keepa_preview',
                args: { asin: asin },
                callback: function(r) {
                    render_result(asin, r.message);
                },
                error: function() {
                    // Keepa being slow/down must never block the form - just show a graceful message
                    if (asin === get_current_asin()) {
                        $body.html('<span class="text-muted small">Could not reach Keepa right now. You can still save.</span>');
                    }
                }
            });
        }

        $asinField.on('input', 'input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(fetch_preview, 600);
        });

        // Initial preview if the field is pre-filled (editing an item that already has an ASIN)
        if (get_current_asin()) {
            fetch_preview();
        }
    }
});
