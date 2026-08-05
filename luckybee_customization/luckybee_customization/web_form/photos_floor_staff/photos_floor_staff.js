frappe.ready(function() {
    // Wrapping title + scanned-item/barcode strip, shared by every mobile form.
    $.getScript("/assets/luckybee_customization/js/mobile_common.js");

    $.getScript("/assets/luckybee_customization/js/mobile_preview.js");
    // A3/A4 - three labelled sections with camera-first capture, replacing the
    // raw Lucky Bee Images grid.
    $.getScript("/assets/luckybee_customization/js/photo_sections.js");
});