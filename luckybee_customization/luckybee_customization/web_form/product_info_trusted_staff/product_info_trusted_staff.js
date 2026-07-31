frappe.ready(function() {
    // 1. Load media preview component & auto-redirection
    $.getScript("/assets/luckybee_customization/js/mobile_preview.js");

    // 2. Load ZXing library for camera EAN barcode scanning
    if (typeof ZXingBrowser === 'undefined') {
        $.getScript("https://unpkg.com/@zxing/browser@0.1.3/umd/zxing-browser.min.js", setup_ean_camera_scanner);
    } else {
        setup_ean_camera_scanner();
    }

    function setup_ean_camera_scanner() {
        const $eanField = $('[data-fieldname="ean"]');
        if (!$eanField.length) return;
        if ($eanField.find('#scan-ean-btn').length) return;

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
});
