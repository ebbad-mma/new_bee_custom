// Reusable media preview script for Lucky Bee Mobile Web Forms
window.render_mobile_media_preview = function() {
    if (!frappe.web_form || !frappe.web_form.doc) return;
    if ($('#mobile-media-preview').length) return; // Already rendered

    const itemCode = frappe.web_form.doc.name;
    // Frappe's actual template nests .web-form-wrapper INSIDE <form class="web-form">,
    // not the other way around (form.web-form > .web-form-body > .web-form-wrapper,
    // plus a sibling .web-form-footer with the Save/Discard buttons) - the old
    // ".web-form-wrapper form" selector matched nothing on any form, ever. Confirmed
    // live: the media preview panel never actually appeared on a real device.
    const $form = $('form.web-form');
    if (!$form.length) return;

    // Inject a container above the form
    const container = $('<div id="mobile-media-preview" class="card mb-4 p-3 shadow-sm bg-light"></div>');
    container.insertBefore($form);

    // On the forms that carry the three-section photo editor (photo_sections.js)
    // this strip listed exactly the same photos again, read-only, directly above
    // it - two identical rows of thumbnails on a phone screen. There, the
    // preview earns its place only as the Amazon-vs-primary comparison.
    const showOurPhotos = !window.lb_photo_sections_enabled;

    container.html(`
        <h5 class="mb-3">Media Preview</h5>
        ${showOurPhotos ? `
        <div id="our-photos-container" class="mb-3">
            <h6 class="text-muted text-uppercase text-xs font-weight-bold">Our Photos</h6>
            <div class="d-flex overflow-auto gap-2" id="our-photos-list">
                <span class="text-muted small">Loading...</span>
            </div>
        </div>` : ''}
        <div class="row">
            <div class="col-6">
                <h6 class="text-muted text-uppercase text-xs font-weight-bold">Amazon Reference</h6>
                <div id="amazon-preview-container" class="text-center p-2 bg-white border rounded">
                    <span class="text-muted small">Loading...</span>
                </div>
            </div>
            <div class="col-6">
                <h6 class="text-muted text-uppercase text-xs font-weight-bold">Current Primary</h6>
                <div id="primary-preview-container" class="text-center p-2 bg-white border rounded">
                    <span class="text-muted small">Loading...</span>
                </div>
            </div>
        </div>
    `);

    // Helper to render Our Photos list with primary image controls
    const render_our_photos = (currentPrimary) => {
        const $ourPhotos = container.find('#our-photos-list');
        if (!$ourPhotos.length) return;   // three-section editor owns the photos here
        const images = frappe.web_form.doc.lb_images || [];
        if (images.length > 0) {
            $ourPhotos.empty();
            images.forEach(img => {
                const section = img.photo_section || "Uncategorized";
                let primaryBtn = '';
                if (section === "Product" && img.image) {
                    if (img.image === currentPrimary) {
                        primaryBtn = `<span class="badge bg-success text-white mt-1 d-block" style="font-size: 10px;">Primary</span>`;
                    } else {
                        primaryBtn = `<a href="#" onclick="window.set_primary_image('${img.image}'); return false;" class="btn btn-xs btn-outline-primary mt-1 d-block" style="font-size: 10px; padding: 2px 4px;">Make Primary</a>`;
                    }
                }
                $ourPhotos.append(`
                    <div class="card p-1 mr-2" style="min-width: 100px; text-align: center;">
                        <img src="${img.image}" alt="${section}" style="width: 80px; height: 80px; object-fit: cover;" onerror="this.src='/assets/frappe/images/default-image.png'" />
                        <small class="mt-1 d-block" style="line-height: 1.1; font-size: 11px; font-weight: bold;">${section}</small>
                        ${primaryBtn}
                    </div>
                `);
            });
        } else {
            $ourPhotos.html('<span class="text-muted small">No existing photos.</span>');
        }
    };

    window.set_primary_image = (url) => {
        frappe.web_form.set_value("lb_primary_image", url);
        const $primaryContainer = $('#primary-preview-container');
        $primaryContainer.html(`<img src="${url}" class="img-fluid" style="max-height: 150px; object-fit: contain;" />`);
        render_our_photos(url);
    };

    // Render Our Photos initially
    const primaryImg = frappe.web_form.doc.lb_primary_image;
    render_our_photos(primaryImg);

    // Render Primary
    const $primaryContainer = container.find('#primary-preview-container');
    if (primaryImg) {
        $primaryContainer.html(`<img src="${primaryImg}" class="img-fluid" style="max-height: 150px; object-fit: contain;" />`);
    } else {
        $primaryContainer.html('<span class="text-muted small">No primary image.</span>');
    }

    // Fetch Keepa Photo
    frappe.call({
        method: 'luckybee_customization.api.mobile_forms.fetch_keepa_photo',
        args: { item_code: itemCode },
        callback: function(r) {
            const $amazonContainer = container.find('#amazon-preview-container');
            if (r.message) {
                $amazonContainer.html(`<img src="${r.message}" class="img-fluid" style="max-height: 150px; object-fit: contain;" />`);
            } else {
                $amazonContainer.html('<span class="text-muted small">No Keepa image available.</span>');
            }
        }
    });

    // Save-and-next redirection
    frappe.web_form.after_save = () => {
        window.location.href = "/mobile_scan";
    };
};

frappe.web_form.after_load = window.render_mobile_media_preview;

$(document).ready(function() {
    setTimeout(window.render_mobile_media_preview, 200);
    setTimeout(window.render_mobile_media_preview, 600);
});
