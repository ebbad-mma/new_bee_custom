frappe.ready(function() {
    $.getScript("/assets/luckybee_customization/js/mobile_preview.js");

    // These fields' DOM elements may not exist yet at frappe.ready time on a
    // real device/network. Both setup functions are idempotent (bail out once
    // their UI already exists), so retrying is safe.
    setup_ean_camera_scanner();
    setTimeout(setup_ean_camera_scanner, 300);
    setTimeout(setup_ean_camera_scanner, 800);
    setTimeout(setup_ean_camera_scanner, 1500);

    setup_asin_live_preview();
    setTimeout(setup_asin_live_preview, 300);
    setTimeout(setup_asin_live_preview, 800);
    setTimeout(setup_asin_live_preview, 1500);

    // frappe.web_form.doc loads asynchronously and is frequently not populated
    // yet when frappe.ready fires (reproduced live on Form 4, which has the
    // identical guard clause: the page silently rendered nothing but the bare
    // Save/Discard form). Retry on a timer rather than a single attempt. Not
    // using frappe.web_form.after_load here - mobile_preview.js (loaded above
    // via getScript, so it may not have run yet at this point) claims that same
    // hook for its own photo panel, and assigning to it here would race with
    // and potentially clobber that assignment depending on load order.
    setup_optional_stock_count();
    setTimeout(setup_optional_stock_count, 300);
    setTimeout(setup_optional_stock_count, 800);
    setTimeout(setup_optional_stock_count, 1500);

    // --- EAN camera scanner (same behavior as Form 2 / Trusted Staff) ---
    function setup_ean_camera_scanner() {
        const $eanField = $('[data-fieldname="ean"]');
        if (!$eanField.length) return;
        if ($eanField.find('#scan-ean-btn').length) return;

        if (typeof ZXingBrowser === 'undefined') {
            $.getScript("https://unpkg.com/@zxing/browser@0.1.3/umd/zxing-browser.min.js", attach_scan_button);
        } else {
            attach_scan_button();
        }

        function attach_scan_button() {
            const $btn = $('<button type="button" id="scan-ean-btn" class="btn btn-secondary btn-sm ml-2" style="margin-top: 4px;"><i class="fa fa-camera"></i> 📷 Scan EAN</button>');
            $eanField.find('.frappe-control').append($btn);

            const modalHtml = `
                <div class="modal fade" id="eanScannerModal" tabindex="-1" role="dialog" aria-hidden="true">
                    <div class="modal-dialog modal-dialog-centered" role="document">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Scan EAN Barcode</h5>
                                <button type="button" class="close" data-dismiss="modal" aria-label="Close" onclick="$('#eanScannerModal').modal('hide')">
                                    <span aria-hidden="true">&times;</span>
                                </button>
                            </div>
                            <div class="modal-body text-center">
                                <div class="form-group text-left mb-2">
                                    <label for="ean-camera-select" class="small">Select Camera:</label>
                                    <select id="ean-camera-select" class="form-control form-control-sm"></select>
                                </div>
                                <div class="mb-2">
                                    <span class="small text-muted">Or Upload Barcode Image:</span>
                                    <input type="file" accept="image/*" id="ean-image-upload" class="form-control-file mt-1">
                                </div>
                                <video id="ean-video-preview" style="width: 100%; max-height: 250px; border: 1px solid #ccc; border-radius: 8px; background: #000;"></video>
                                <div id="ean-scan-alert" class="alert alert-danger mt-2" style="display: none;"></div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary btn-sm" onclick="$('#eanScannerModal').modal('hide')">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            if (!$('#eanScannerModal').length) {
                $('body').append(modalHtml);
            }

            let codeReader = null;
            let controls = null;

            $btn.on('click', async function(e) {
                e.preventDefault();
                $('#eanScannerModal').modal('show');
                $('#ean-scan-alert').hide();

                if (!codeReader) {
                    codeReader = new ZXingBrowser.BrowserMultiFormatReader();
                }

                const videoElement = document.getElementById('ean-video-preview');
                const cameraSelect = document.getElementById('ean-camera-select');

                try {
                    const devices = await codeReader.listVideoInputDevices();
                    $(cameraSelect).empty();
                    let selectedId = null;
                    if (devices && devices.length > 0) {
                        devices.forEach(d => {
                            $(cameraSelect).append(new Option(d.label || `Camera ${d.deviceId.slice(0, 6)}`, d.deviceId));
                        });
                        selectedId = devices[devices.length - 1].deviceId;
                        $(cameraSelect).val(selectedId);
                    }

                    controls = await codeReader.decodeFromVideoDevice(selectedId, videoElement, (result, err) => {
                        if (result) {
                            const scannedText = result.getText();
                            frappe.web_form.set_value('ean', scannedText);
                            if (controls) {
                                controls.stop();
                                controls = null;
                            }
                            $('#eanScannerModal').modal('hide');
                            frappe.show_alert({ message: `EAN Scanned: ${scannedText}`, indicator: 'green' });
                        }
                    });
                } catch (err) {
                    console.warn("EAN Camera scan error:", err);
                    $('#ean-scan-alert').text("Camera error: " + (err.message || err)).show();
                }
            });

            $('#eanScannerModal').on('hidden.bs.modal', function () {
                if (controls) {
                    controls.stop();
                    controls = null;
                }
            });

            $(document).on('change', '#ean-image-upload', async function(e) {
                const file = e.target.files[0];
                if (file && codeReader) {
                    try {
                        const imgUrl = URL.createObjectURL(file);
                        const result = await codeReader.decodeFromImageUrl(imgUrl);
                        if (result) {
                            const text = result.getText();
                            frappe.web_form.set_value('ean', text);
                            $('#eanScannerModal').modal('hide');
                            frappe.show_alert({ message: `EAN Scanned: ${text}`, indicator: 'green' });
                        } else {
                            $('#ean-scan-alert').text("Could not decode barcode from image.").show();
                        }
                    } catch (err) {
                        $('#ean-scan-alert').text("Could not decode barcode from image.").show();
                    }
                }
            });
        }
    }

    // --- Live ASIN preview (same behavior as Form 3 / Matching Staff) ---
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

        function get_current_asin() {
            return ($asinField.find('input').val() || '').trim();
        }

        function render_loading() {
            $body.html('<span class="text-muted small">Looking up ASIN&hellip;</span>');
        }

        function render_result(asin, data) {
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

        function fetch_preview() {
            const asin = get_current_asin();
            if (!asin) {
                $body.html('<span class="text-muted small">Enter an ASIN to preview the Amazon listing.</span>');
                return;
            }
            render_loading();
            frappe.call({
                method: 'luckybee_customization.api.mobile_forms.fetch_keepa_preview',
                args: { asin: asin },
                callback: function(r) { render_result(asin, r.message); },
                error: function() {
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

        if (get_current_asin()) {
            fetch_preview();
        }
    }

    // --- Optional stock count (off by default - leaving it blank does nothing to stock) ---
    function setup_optional_stock_count() {
        if (!frappe.web_form || !frappe.web_form.doc || !frappe.web_form.doc.name) return;
        if ($('#stock-count-panel').length) return;

        const itemCode = frappe.web_form.doc.name;
        // Frappe's actual template nests .web-form-wrapper INSIDE <form class="web-form">,
        // not the other way around - ".web-form-wrapper form" matches nothing on any
        // form, ever. See count_stock_take_staff.js for how this was confirmed live.
        const $form = $('form.web-form');
        if (!$form.length) return;

        const $panel = $(`
            <div id="stock-count-panel" class="card p-3 mb-3 shadow-sm bg-light">
                <h5 class="mb-1">Stock Count <span class="text-muted small font-weight-normal">(optional - leave blank to skip)</span></h5>
                <div id="stock-count-body">
                    <span class="text-muted small">Loading&hellip;</span>
                </div>
            </div>
        `);
        // Placed after the main product-info form, before the shared media
        // preview redirect logic - this is a clearly separate, opt-in action
        // from saving the item's own fields, not bundled into the Save button.
        $panel.insertAfter($form);

        const $body = $panel.find('#stock-count-body');

        frappe.call({
            method: 'luckybee_customization.api.stock_recount.get_stock_recount_context',
            args: { item_code: itemCode },
            callback: function(r) { render(r.message); },
            error: function() {
                $body.html('<span class="text-danger small">Could not load stock details.</span>');
            }
        });

        function render(ctx) {
            if (!ctx || !ctx.is_eligible) {
                const reason = (ctx && ctx.reason) ? ctx.reason : 'Stock count is not available for this item.';
                $body.html(`<span class="text-muted small">${frappe.utils.escape_html(reason)}</span>`);
                return;
            }

            const warehouses = ctx.warehouses || [];
            if (!warehouses.length) {
                $body.html('<span class="text-muted small">No warehouses available for this item.</span>');
                return;
            }

            const optionsHtml = warehouses.map(w =>
                `<option value="${frappe.utils.escape_html(w.warehouse)}" data-current-qty="${w.current_qty}">${frappe.utils.escape_html(w.warehouse)}</option>`
            ).join('');

            $body.html(`
                <div class="form-group">
                    <label class="small text-muted">Warehouse</label>
                    <select id="count-warehouse" class="form-control">${optionsHtml}</select>
                </div>
                <div class="form-group">
                    <label class="small text-muted">Current Stock</label>
                    <input type="text" id="count-current-qty" class="form-control" readonly value="${warehouses[0].current_qty} ${ctx.stock_uom || ''}">
                </div>
                <div class="form-group">
                    <label class="small text-muted">New Count (leave blank to skip)</label>
                    <input type="number" id="count-new-qty" class="form-control" min="0" step="any" placeholder="Only enter this to change stock">
                </div>
                <button type="button" id="count-submit-btn" class="btn btn-outline-primary btn-block">Update Stock</button>
                <div id="count-status" class="mt-2 small"></div>
            `);

            const $warehouseSelect = $body.find('#count-warehouse');
            const $newQty = $body.find('#count-new-qty');
            const $status = $body.find('#count-status');

            function currentQtyForSelected() {
                return parseFloat($warehouseSelect.find('option:selected').data('current-qty'));
            }

            $warehouseSelect.on('change', function() {
                $body.find('#count-current-qty').val(`${currentQtyForSelected()} ${ctx.stock_uom || ''}`);
                $status.text('');
            });

            $body.find('#count-submit-btn').on('click', function() {
                $status.removeClass('text-danger text-success').text('');

                const newQtyRaw = $newQty.val();
                if (newQtyRaw === '' || newQtyRaw === null) {
                    // Blank is the expected default path - do nothing to stock, just remind them it's optional
                    $status.addClass('text-danger').text('Leave this blank to skip, or enter a count to change stock.');
                    return;
                }
                const newQty = parseFloat(newQtyRaw);
                if (isNaN(newQty) || newQty < 0) {
                    $status.addClass('text-danger').text('Enter a valid, non-negative quantity.');
                    return;
                }

                const warehouse = $warehouseSelect.val();
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
                                if (res && res.status === 'no_change') {
                                    $status.addClass('text-success').text('Stock already matches this count.');
                                } else if (res && res.status === 'success') {
                                    $status.addClass('text-success').text(`Stock updated (${res.stock_reconciliation}).`);
                                    $body.find('#count-current-qty').val(`${res.new_qty} ${ctx.stock_uom || ''}`);
                                    $warehouseSelect.find('option:selected').data('current-qty', res.new_qty);
                                    $newQty.val('');
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
