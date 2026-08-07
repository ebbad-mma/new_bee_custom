// Phase 2 - "Product info on scan": a read-only lookup for staff on the shop
// floor. Deliberately not an edit form - scan a code, see the price and stock,
// change nothing. Opens as a dialog so it can be triggered from anywhere in
// Desk without losing the page behind it.
//
// Bound to Ctrl/Cmd+Shift+F, and available as frappe.lb_scan_lookup() so a
// button or workspace shortcut can call it too.

frappe.provide('frappe.lb');

frappe.lb.scan_lookup = function () {
    const d = new frappe.ui.Dialog({
        title: __('Product Lookup'),
        fields: [
            {
                fieldname: 'search_term',
                fieldtype: 'Data',
                label: __('Scan barcode or type a code / name'),
                description: __('Works with L#####, LX#####, or a supplier barcode.'),
            },
            // Two ways in, because there are two places this gets used: a
            // hardware scanner at the counter types into the field above and
            // sends Enter, while in-aisle on a phone there is no keyboard and
            // no scanner - only a camera.
            { fieldname: 'camera_area', fieldtype: 'HTML' },
            { fieldname: 'result', fieldtype: 'HTML' },
        ],
    });

    const $result = () => d.fields_dict.result.$wrapper;
    const $camera = () => d.fields_dict.camera_area.$wrapper;
    // Declared up here rather than beside d.show(): the camera loop writes the
    // scanned code into it, and relying on that running late enough to dodge
    // the temporal dead zone would be a trap for the next person editing this.
    const $input = d.fields_dict.search_term.$input;

    function money(v) {
        if (v == null) return '-';
        return '₹' + format_number(v, null, 0);
    }

    function render(res) {
        if (!res || res.status === 'not_found') {
            $result().html(
                `<div class="text-muted" style="padding:12px 0;">${
                    frappe.utils.escape_html((res && res.message) || __('No product matches that code.'))
                }</div>`
            );
            return;
        }

        const stockRows = (res.stock || []).length
            ? res.stock.map(s =>
                `<div style="display:flex; justify-content:space-between;">
                    <span>${frappe.utils.escape_html(s.warehouse)}</span>
                    <strong>${format_number(s.qty, null, 0)}</strong>
                 </div>`).join('')
            : `<div class="text-muted">${__('No stock on hand')}</div>`;

        // Price is what a customer asks about, so it leads and is the largest
        // thing in the dialog - same hierarchy as the printed label.
        $result().html(`
            <div style="display:flex; gap:14px; padding-top:8px;">
                <div style="flex:0 0 96px;">
                    ${res.image
                        ? `<img src="${frappe.utils.escape_html(res.image)}"
                                style="width:96px;height:96px;object-fit:cover;border-radius:6px;border:1px solid #ddd;"
                                onerror="this.style.display='none'">`
                        : `<div style="width:96px;height:96px;border:1px dashed #ccc;border-radius:6px;
                                    display:flex;align-items:center;justify-content:center;color:#999;font-size:11px;">
                             ${__('No photo')}
                           </div>`}
                </div>
                <div style="flex:1 1 auto; min-width:0;">
                    <div style="font-weight:600; line-height:1.2;">
                        ${frappe.utils.escape_html(res.item_name || '')}
                    </div>
                    <div class="text-muted" style="font-size:11px; margin-bottom:6px;">
                        ${frappe.utils.escape_html(res.item_code)}
                        ${res.brand ? ' &middot; ' + frappe.utils.escape_html(res.brand) : ''}
                        ${res.disabled ? ' &middot; <span style="color:#c0392b;">' + __('DISABLED') + '</span>' : ''}
                    </div>

                    <div style="display:flex; align-items:baseline; gap:8px;">
                        <span style="font-size:24px; font-weight:800;">${money(res.our_price)}</span>
                        ${res.mrp ? `<span style="text-decoration:line-through; color:#777; font-size:12px;">${money(res.mrp)}</span>` : ''}
                        ${res.save_amount ? `<span style="font-weight:700; color:#1e7e34; font-size:12px;">${__('SAVE')} ${money(res.save_amount)}</span>` : ''}
                    </div>
                </div>
            </div>

            <hr style="margin:10px 0;">

            <div style="display:flex; gap:18px; font-size:12px;">
                <div style="flex:1 1 0; min-width:0;">
                    <div class="text-muted" style="text-transform:uppercase; font-size:10px; letter-spacing:.4px;">${__('Stock')}</div>
                    ${stockRows}
                </div>
                <div style="flex:1 1 0; min-width:0;">
                    <div class="text-muted" style="text-transform:uppercase; font-size:10px; letter-spacing:.4px;">${__('Detail')}</div>
                    <div style="display:flex; justify-content:space-between;">
                        <span>${__('Category')}</span>
                        <span>${frappe.utils.escape_html(res.category || '-')}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span>${__('Velocity')}</span>
                        <span>${frappe.utils.escape_html(res.velocity_band || '-')}</span>
                    </div>
                    ${res.days_cover != null ? `
                    <div style="display:flex; justify-content:space-between;">
                        <span>${__('Days cover')}</span>
                        <span>${format_number(res.days_cover, null, 0)}</span>
                    </div>` : ''}
                </div>
            </div>

            <div style="margin-top:12px;">
                <a class="btn btn-xs btn-default"
                   href="/app/item/${encodeURIComponent(res.item_code)}" target="_blank">
                   ${__('Open item')}
                </a>
            </div>
        `);
    }

    // ---- camera scanning --------------------------------------------------
    //
    // Same engine as /mobile_scan: prefer the browser's native BarcodeDetector
    // (Android Chrome), which is hardware-accelerated and reads any
    // orientation - our labels print the bars sideways. ZXing is only fetched
    // as a fallback where the native API is missing, so the common case loads
    // no library at all.
    let camStream = null;
    let camTimer = null;
    let detector = null;
    let zxingReader = null;

    function stopCamera() {
        if (camTimer) { clearInterval(camTimer); camTimer = null; }
        if (camStream) {
            camStream.getTracks().forEach(t => { try { t.stop(); } catch (e) {} });
            camStream = null;
        }
        $camera().find('#lb-cam-wrap').remove();
        $camera().find('#lb-cam-btn').text(__('Scan with camera'));
    }

    async function ensureDetector() {
        if (detector !== null) return detector;
        if ('BarcodeDetector' in window) {
            try {
                const supported = await window.BarcodeDetector.getSupportedFormats();
                const want = ['code_128', 'code_39', 'code_93', 'codabar', 'itf',
                              'ean_13', 'ean_8', 'upc_a', 'upc_e'].filter(f => supported.includes(f));
                if (want.length) {
                    detector = new window.BarcodeDetector({ formats: want });
                    return detector;
                }
            } catch (e) { /* fall through to ZXing */ }
        }
        detector = false;
        return detector;
    }

    function loadZXing() {
        if (window.ZXingBrowser) return Promise.resolve();
        return new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = 'https://unpkg.com/@zxing/browser@0.1.3/umd/zxing-browser.min.js';
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    async function startCamera() {
        const $btn = $camera().find('#lb-cam-btn');
        $btn.text(__('Stop camera'));

        $camera().find('#lb-cam-wrap').remove();
        $camera().append(`
            <div id="lb-cam-wrap" style="margin-top:8px;">
                <video id="lb-cam-video" playsinline muted
                       style="width:100%; max-height:230px; background:#000; border-radius:6px;"></video>
                <div class="text-muted" style="font-size:11px; margin-top:4px;">
                    ${__('Hold the barcode steady, about 10-15cm away.')}
                </div>
            </div>
        `);
        const video = document.getElementById('lb-cam-video');

        try {
            camStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: 1920 },
                    height: { ideal: 1080 },
                    advanced: [{ focusMode: 'continuous' }],
                },
                audio: false,
            });
        } catch (e) {
            stopCamera();
            // Camera needs HTTPS (or localhost); on a plain-http LAN address the
            // browser refuses outright, and that is worth saying rather than
            // failing silently.
            $result().html(
                `<div class="text-danger" style="padding:12px 0;">${
                    __('Camera unavailable. It needs an https address, or type the code above.')
                }</div>`
            );
            return;
        }

        video.srcObject = camStream;
        await video.play().catch(() => {});

        const det = await ensureDetector();
        if (!det) {
            try { await loadZXing(); zxingReader = new window.ZXingBrowser.BrowserMultiFormatReader(); }
            catch (e) { /* handled per-frame below */ }
        }

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        let busy = false;

        camTimer = setInterval(async () => {
            if (busy || !video.videoWidth) return;
            busy = true;
            try {
                if (det) {
                    const codes = await det.detect(video);
                    if (codes && codes.length && codes[0].rawValue) {
                        const text = codes[0].rawValue.trim();
                        stopCamera();
                        $input.val(text);
                        doLookup(text);
                        return;
                    }
                } else if (zxingReader) {
                    // Rotated pass too - our labels print the bars vertically.
                    canvas.width = video.videoHeight;
                    canvas.height = video.videoWidth;
                    ctx.save();
                    ctx.translate(canvas.width / 2, canvas.height / 2);
                    ctx.rotate(Math.PI / 2);
                    ctx.drawImage(video, -video.videoWidth / 2, -video.videoHeight / 2);
                    ctx.restore();
                    let res = null;
                    try { res = zxingReader.decodeFromCanvas(canvas); } catch (e) { res = null; }
                    if (res) {
                        const text = res.getText().trim();
                        stopCamera();
                        $input.val(text);
                        doLookup(text);
                        return;
                    }
                }
            } catch (e) {
                // a bad frame must never kill the loop
            } finally {
                busy = false;
            }
        }, 120);
    }

    $camera().html(`
        <button type="button" id="lb-cam-btn" class="btn btn-sm btn-default">
            &#128247; ${__('Scan with camera')}
        </button>
    `);
    $camera().on('click', '#lb-cam-btn', function () {
        if (camStream) { stopCamera(); } else { startCamera(); }
    });

    // Releasing the camera when the dialog closes matters - otherwise the
    // sensor stays live and the phone keeps burning battery.
    d.$wrapper.on('hidden.bs.modal', stopCamera);

    let pending = false;
    function doLookup(term) {
        term = (term || '').trim();
        if (!term || pending) return;
        pending = true;
        $result().html(`<div class="text-muted" style="padding:12px 0;">${__('Looking up...')}</div>`);
        frappe.call({
            method: 'luckybee_customization.api.scan_lookup.lookup_product',
            args: { search_term: term },
            callback: r => { pending = false; render(r.message); },
            error: () => {
                pending = false;
                $result().html(`<div class="text-danger" style="padding:12px 0;">${__('Lookup failed. Try again.')}</div>`);
            },
        });
    }

    d.show();

    // A hardware scanner types the code then sends Enter, so this is the whole
    // interaction: scan, read, scan the next one.
    $input.on('keydown', e => {
        if (e.key === 'Enter') {
            e.preventDefault();
            doLookup($input.val());
            $input.select();   // ready for the next scan without a manual clear
        }
    });
    setTimeout(() => $input.focus(), 150);
};

// Convenience alias plus a keyboard shortcut for the aisle.
frappe.lb_scan_lookup = frappe.lb.scan_lookup;

$(document).on('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'F' || e.key === 'f')) {
        e.preventDefault();
        frappe.lb.scan_lookup();
    }
});
