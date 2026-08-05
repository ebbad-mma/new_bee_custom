frappe.ready(function() {
    // Wrapping title + scanned-item/barcode strip, shared by every mobile form.
    $.getScript("/assets/luckybee_customization/js/mobile_common.js");

    // frappe.web_form.doc loads asynchronously - it is frequently NOT populated
    // yet when frappe.ready fires (confirmed live: on a real device the page
    // rendered only the bare, empty Save/Discard form with no Stock Count panel
    // at all, because this ran once, found doc undefined, and silently gave up).
    // Mirror mobile_preview.js's belt-and-suspenders approach: try via the
    // after_load hook (fires once the doc genuinely has loaded) AND via timed
    // retries as a fallback, since this form doesn't share that hook with
    // anything else that could clobber it.
    frappe.web_form.after_load = setup_stock_count_ui;
    setup_stock_count_ui();
    setTimeout(setup_stock_count_ui, 300);
    setTimeout(setup_stock_count_ui, 800);
    setTimeout(setup_stock_count_ui, 1500);

    function setup_stock_count_ui() {
        if (!frappe.web_form || !frappe.web_form.doc || !frappe.web_form.doc.name) return;
        if ($('#stock-count-panel').length) return;

        const itemCode = frappe.web_form.doc.name;
        // Frappe's actual template nests .web-form-wrapper INSIDE <form class="web-form">,
        // not the other way around - ".web-form-wrapper form" matches nothing on any
        // form, ever. Confirmed live: this was the real reason nothing rendered at all,
        // not (only) the async-timing race the retries above also guard against.
        const $form = $('form.web-form');
        if (!$form.length) return;

        // This form never edits the Item doc itself (Stock-take Staff has no
        // editable Item fields) - hide the standard empty form/Save button and
        // replace the whole interaction with the recount UI below.
        $form.hide();

        const $panel = $(`
            <div id="stock-count-panel" class="card p-3 mb-3 shadow-sm bg-light">
                <h5 class="mb-3">Stock Count</h5>
                <div id="stock-count-body">
                    <span class="text-muted small">Loading item details&hellip;</span>
                </div>
            </div>
        `);
        $panel.insertBefore($form);

        const $body = $panel.find('#stock-count-body');

        frappe.call({
            method: 'luckybee_customization.api.stock_recount.get_stock_recount_context',
            args: { item_code: itemCode },
            callback: function(r) {
                render(r.message);
            },
            error: function() {
                $body.html('<span class="text-danger small">Could not load item details. Please go back and try again.</span>');
            }
        });

        function render(ctx) {
            if (!ctx || !ctx.is_eligible) {
                const reason = (ctx && ctx.reason) ? ctx.reason : 'This item cannot be recounted here.';
                $body.html(`<span class="text-danger small">${frappe.utils.escape_html(reason)}</span>`);
                return;
            }

            const warehouses = ctx.warehouses || [];
            if (!warehouses.length) {
                $body.html('<span class="text-danger small">No warehouses available for this item.</span>');
                return;
            }

            const optionsHtml = warehouses.map(w =>
                `<option value="${frappe.utils.escape_html(w.warehouse)}" data-current-qty="${w.current_qty}">${frappe.utils.escape_html(w.warehouse)}</option>`
            ).join('');

            $body.html(`
                <div class="mb-2 font-weight-bold">${frappe.utils.escape_html(ctx.item_name || itemCode)}</div>
                <div class="form-group">
                    <label class="small text-muted">Warehouse</label>
                    <select id="count-warehouse" class="form-control">${optionsHtml}</select>
                </div>
                <div class="form-group">
                    <label class="small text-muted">Current Stock</label>
                    <input type="text" id="count-current-qty" class="form-control" readonly value="${warehouses[0].current_qty} ${ctx.stock_uom || ''}">
                </div>
                <div class="form-group">
                    <label class="small text-muted">New Count</label>
                    <input type="number" id="count-new-qty" class="form-control" min="0" step="any"
                           inputmode="numeric" autocomplete="off" placeholder="Enter counted quantity">
                    <div id="count-delta" class="small mt-1"></div>
                </div>
                <button type="button" id="count-submit-btn" class="btn btn-primary btn-block">Update Stock</button>
                <div id="count-status" class="mt-2 small"></div>
            `);

            const $warehouseSelect = $body.find('#count-warehouse');
            const $currentQty = $body.find('#count-current-qty');
            const $newQty = $body.find('#count-new-qty');
            const $status = $body.find('#count-status');
            const $delta = $body.find('#count-delta');

            function currentQtyForSelected() {
                const opt = $warehouseSelect.find('option:selected');
                return parseFloat(opt.data('current-qty'));
            }

            // Live "12 to 3 (-9)" readout under the entry box. A large unexpected swing is
            // visible before the staff member ever reaches the confirm dialog, which is the
            // real safeguard against a 3-for-30 style typo.
            function renderDelta() {
                const raw = $newQty.val();
                if (raw === '' || raw === null) {
                    $delta.text('').removeClass('text-danger text-success text-muted');
                    return;
                }
                const entered = parseFloat(raw);
                if (isNaN(entered)) {
                    $delta.text('').removeClass('text-danger text-success text-muted');
                    return;
                }
                const current = currentQtyForSelected();
                const diff = entered - current;
                $delta.removeClass('text-danger text-success text-muted');
                if (diff === 0) {
                    $delta.addClass('text-muted').text('No change');
                    return;
                }
                const sign = diff > 0 ? '+' : '';
                $delta.addClass(diff > 0 ? 'text-success' : 'text-danger')
                      .text(`${current} to ${entered} (${sign}${diff})`);
            }

            $newQty.on('input', renderDelta);

            // Staff can start typing the count immediately without tapping the field first.
            $newQty.trigger('focus');

            $warehouseSelect.on('change', function() {
                $currentQty.val(`${currentQtyForSelected()} ${ctx.stock_uom || ''}`);
                $status.text('');
                renderDelta();
            });

            // Replace the form with a clear result + a big "Scan Next" action, rather than
            // silently bouncing back to the scanner. Staff get confirmation that the change
            // landed, and one obvious tap to start the next item.
            function showDone(message) {
                $body.html(`
                    <div class="text-center py-2">
                        <div class="mb-2" style="font-size: 32px; line-height: 1;">&#10003;</div>
                        <div class="font-weight-bold mb-1">${frappe.utils.escape_html(message)}</div>
                        <div class="small text-muted mb-3">${frappe.utils.escape_html(ctx.item_name || itemCode)}</div>
                        <button type="button" id="count-scan-next" class="btn btn-primary btn-block btn-lg">Scan Next</button>
                    </div>
                `);
                $body.find('#count-scan-next').on('click', function() {
                    // autoscan tells /mobile_scan to open the camera straight away
                    window.location.href = '/mobile_scan?autoscan=1';
                });
            }

            $body.find('#count-submit-btn').on('click', function() {
                $status.removeClass('text-danger text-success').text('');

                const warehouse = $warehouseSelect.val();
                const newQtyRaw = $newQty.val();
                if (newQtyRaw === '' || newQtyRaw === null) {
                    $status.addClass('text-danger').text('Enter the counted quantity first.');
                    return;
                }
                const newQty = parseFloat(newQtyRaw);
                if (isNaN(newQty) || newQty < 0) {
                    $status.addClass('text-danger').text('Enter a valid, non-negative quantity.');
                    return;
                }

                const current = currentQtyForSelected();
                const $btn = $body.find('#count-submit-btn');

                frappe.confirm(
                    `Change stock in <b>${frappe.utils.escape_html(warehouse)}</b> from <b>${current}</b> to <b>${newQty}</b>?`,
                    () => {
                        $btn.prop('disabled', true).text('Updating&hellip;');
                        frappe.call({
                            method: 'luckybee_customization.api.stock_recount.submit_stock_recount',
                            args: { item_code: itemCode, warehouse: warehouse, new_qty: newQty },
                            callback: function(r) {
                                $btn.prop('disabled', false).text('Update Stock');
                                const res = r.message;
                                if (!res) {
                                    $status.addClass('text-danger').text('Something went wrong. Nothing was changed.');
                                    return;
                                }
                                if (res.status === 'no_change') {
                                    showDone('Stock already matches this count - nothing to update.');
                                } else if (res.status === 'success') {
                                    showDone(`Updated - stock is now ${res.new_qty}.`);
                                } else {
                                    $status.addClass('text-danger').text('Something went wrong. Nothing was changed.');
                                }
                            },
                            error: function() {
                                $btn.prop('disabled', false).text('Update Stock');
                                $status.addClass('text-danger').text('Could not update stock. Nothing was changed - please try again.');
                            }
                        });
                    }
                );
            });
        }
    }
});
