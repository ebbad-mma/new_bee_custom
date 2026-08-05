// A3/A4 - three-section, camera-first photo capture for the Lucky Bee mobile forms.
//
// Replaces the Lucky Bee Images child-table grid (add row -> pick type -> attach ->
// set sequence, four taps, and easy to file under the wrong type) with three labelled
// sections that each own their capture button, so the section is decided by which
// button you press rather than by a dropdown you might get wrong.
//
// Photos save immediately via api/item_photos.py rather than waiting for the form's
// own Save - a phone that backgrounds a half-filled form otherwise loses the lot.
window.render_photo_sections = function () {
    if (!frappe.web_form || !frappe.web_form.doc || !frappe.web_form.doc.name) return;
    if ($('#lb-photo-sections').length) return;

    const itemCode = frappe.web_form.doc.name;
    const $form = $('form.web-form');
    if (!$form.length) return;

    // Hide the raw grid - the sections below are the supported way in.
    // Keep it in the DOM so the web form's own value handling stays intact.
    const $grid = $('[data-fieldname="lb_images"]').closest('.form-group, .frappe-control');
    if ($grid.length) $grid.hide();
    $('[data-fieldname="lb_primary_image"]').closest('.form-group, .frappe-control').hide();

    const $panel = $(`
        <div id="lb-photo-sections" class="card p-3 mb-3 shadow-sm bg-light">
            <h5 class="mb-1">Photos</h5>
            <div class="small text-muted mb-3">Tap a camera button to add a photo to that group.</div>
            <div id="lb-photo-body">
                <span class="text-muted small">Loading photos&hellip;</span>
            </div>
        </div>
    `);
    $panel.insertBefore($form);

    const $body = $panel.find('#lb-photo-body');

    // A single reusable file input. capture="environment" asks the OS to open the
    // rear camera directly; the "Upload instead" button clears that attribute so the
    // normal gallery/files chooser still works.
    const $picker = $('<input type="file" accept="image/*" style="display:none">');
    $panel.append($picker);

    let pendingSection = null;

    function esc(s) { return frappe.utils.escape_html(s == null ? '' : String(s)); }

    function setBusy(msg) {
        $body.find('.lb-photo-status').remove();
        if (msg) {
            $body.prepend(`<div class="lb-photo-status small text-muted mb-2">${esc(msg)}</div>`);
        }
    }

    function showError(msg) {
        $body.find('.lb-photo-status').remove();
        $body.prepend(`<div class="lb-photo-status small text-danger mb-2">${esc(msg)}</div>`);
    }

    function render(data) {
        if (!data) return;
        const max = data.max_per_section || 5;

        const sectionsHtml = (data.sections || []).map(section => {
            const photos = (data.photos && data.photos[section]) || [];
            const full = photos.length >= max;

            const thumbs = photos.length
                ? photos.map(p => `
                    <div class="lb-thumb" style="position:relative; min-width:92px; width:92px; text-align:center;">
                        <img src="${esc(p.image)}" alt="${esc(section)}"
                             style="width:92px; height:92px; object-fit:cover; border-radius:6px; border:1px solid #ddd;"
                             onerror="this.src='/assets/frappe/images/default-image.png'">
                        <button type="button" class="btn btn-link p-0 lb-del"
                                data-row="${esc(p.name)}"
                                style="position:absolute; top:-6px; right:-6px; background:#fff; border-radius:50%; width:22px; height:22px; line-height:1; border:1px solid #ccc; color:#c0392b;"
                                aria-label="Remove photo">&times;</button>
                        ${section === 'Product' ? (
                            p.is_primary
                                ? '<div class="badge bg-success text-white mt-1" style="font-size:10px;">Primary</div>'
                                : `<button type="button" class="btn btn-outline-primary btn-sm mt-1 lb-primary"
                                        data-url="${esc(p.image)}" style="font-size:10px; padding:1px 4px;">Set primary</button>`
                        ) : ''}
                    </div>`).join('')
                : '<span class="text-muted small">No photos yet.</span>';

            return `
                <div class="mb-3 pb-2" style="border-bottom:1px solid #e4e4e4;">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <strong>${esc(section)}</strong>
                        <span class="small text-muted">${photos.length}/${max}</span>
                    </div>
                    <div class="d-flex flex-wrap gap-2 mb-2" style="gap:8px;">${thumbs}</div>
                    <div class="d-flex" style="gap:8px;">
                        <button type="button" class="btn btn-primary btn-sm lb-capture"
                                data-section="${esc(section)}" ${full ? 'disabled' : ''}>
                            &#128247; Take Photo
                        </button>
                        <button type="button" class="btn btn-link btn-sm lb-upload"
                                data-section="${esc(section)}" ${full ? 'disabled' : ''}>
                            Upload instead
                        </button>
                    </div>
                </div>`;
        }).join('');

        $body.html(sectionsHtml);
    }

    function load() {
        frappe.call({
            method: 'luckybee_customization.api.item_photos.get_item_photos',
            args: { item_code: itemCode },
            callback: r => render(r.message),
            error: () => showError('Could not load photos. Pull down to refresh and try again.')
        });
    }

    // --- capture / upload -------------------------------------------------

    $body.on('click', '.lb-capture', function () {
        pendingSection = $(this).data('section');
        // Ask the OS for the rear camera directly (A4).
        $picker.attr('capture', 'environment').val('').trigger('click');
    });

    $body.on('click', '.lb-upload', function () {
        pendingSection = $(this).data('section');
        // Same input without capture -> normal gallery / files chooser.
        $picker.removeAttr('capture').val('').trigger('click');
    });

    $picker.on('change', function (e) {
        const file = e.target.files && e.target.files[0];
        if (!file || !pendingSection) return;

        if (file.size > 5 * 1024 * 1024) {
            showError('That photo is larger than 5MB. Please retake it.');
            return;
        }

        setBusy('Uploading photo…');

        const fd = new FormData();
        fd.append('file', file, file.name || 'photo.jpg');
        fd.append('is_private', 0);
        fd.append('doctype', 'Item');
        fd.append('docname', itemCode);
        fd.append('folder', 'Home/Attachments');

        fetch('/api/method/upload_file', {
            method: 'POST',
            headers: { 'X-Frappe-CSRF-Token': frappe.csrf_token || '' },
            body: fd,
            credentials: 'same-origin'
        })
            .then(res => res.json())
            .then(out => {
                const fileUrl = out && out.message && out.message.file_url;
                if (!fileUrl) throw new Error('upload failed');
                return new Promise((resolve, reject) => {
                    frappe.call({
                        method: 'luckybee_customization.api.item_photos.add_item_photo',
                        args: { item_code: itemCode, section: pendingSection, file_url: fileUrl },
                        callback: r => resolve(r.message),
                        error: reject
                    });
                });
            })
            .then(data => {
                setBusy(null);
                render(data);
                frappe.show_alert({ message: 'Photo added', indicator: 'green' });
            })
            .catch(() => showError('Could not save that photo. Please try again.'))
            .then(() => { pendingSection = null; });
    });

    // --- delete / set primary --------------------------------------------

    $body.on('click', '.lb-del', function () {
        const rowName = $(this).data('row');
        frappe.confirm('Remove this photo?', () => {
            setBusy('Removing…');
            frappe.call({
                method: 'luckybee_customization.api.item_photos.delete_item_photo',
                args: { item_code: itemCode, row_name: rowName },
                callback: r => { setBusy(null); render(r.message); },
                error: () => showError('Could not remove that photo.')
            });
        });
    });

    $body.on('click', '.lb-primary', function () {
        const url = $(this).data('url');
        setBusy('Setting primary…');
        frappe.call({
            method: 'luckybee_customization.api.item_photos.set_primary_image',
            args: { item_code: itemCode, file_url: url },
            callback: r => {
                setBusy(null);
                render(r.message);
                frappe.show_alert({ message: 'Primary image set', indicator: 'green' });
            },
            error: () => showError('Could not set the primary image.')
        });
    });

    load();
};

// Same belt-and-braces timing as the other mobile scripts: frappe.web_form.doc
// is populated asynchronously and is often not ready when frappe.ready fires.
// render_photo_sections() bails out if its panel already exists, so retrying is safe.
frappe.ready(function () {
    window.render_photo_sections();
    setTimeout(window.render_photo_sections, 300);
    setTimeout(window.render_photo_sections, 800);
    setTimeout(window.render_photo_sections, 1500);
});
