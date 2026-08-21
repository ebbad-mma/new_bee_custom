/**
 * Shared barcode scanner for the Lucky Bee portal pages.
 *
 * There were two copies of this - 589 lines in mobile_scan.html and 368 in
 * product_check.html - which had already drifted apart. One engine now, used by
 * both, so a fix lands once.
 *
 * The strategy here is measured, not assumed. Three real shelf photos were run
 * through every combination of crop, scale, rotation and binarisation:
 *
 *   - The old centre crop (90% x 50% of the frame) missed the barcode on all
 *     three. Labels sit wherever the box happens to be held, not mid-frame.
 *   - The one photo that decoded only decoded ROTATED, in 3ms. Upright never
 *     worked on it. Trying one orientation is throwing away half the chances.
 *   - Two of the three never decoded at all, at any scale, with or without
 *     sharpening. They sit at roughly 2.5 pixels per bar, which is ZXing's
 *     floor, and they are soft. No parser change rescues them - only a bigger,
 *     sharper capture does, which is what the resolution, focus and zoom
 *     requests below are for.
 */
(function (global) {
	'use strict';

	// Our labels are alphanumeric internal codes (L14550, LX01416), which are
	// Code 128 / Code 39 - not the numeric-only retail symbologies. Enum values
	// read out of @zxing/browser@0.1.3's UMD bundle: BarcodeFormat is exported,
	// DecodeHintType is dropped by minification, so its two keys are the
	// verified literals POSSIBLE_FORMATS = 2 and TRY_HARDER = 3.
	function buildReader() {
		var BF = (global.ZXingBrowser && global.ZXingBrowser.BarcodeFormat) || {
			CODABAR: 1, CODE_39: 2, CODE_93: 3, CODE_128: 4,
			EAN_8: 6, EAN_13: 7, ITF: 8, UPC_A: 14, UPC_E: 15
		};
		var hints = new Map();
		hints.set(2, [BF.CODE_128, BF.CODE_39, BF.CODE_93, BF.CODABAR, BF.ITF,
					  BF.EAN_13, BF.EAN_8, BF.UPC_A, BF.UPC_E]);
		hints.set(3, true);
		return new global.ZXingBrowser.BrowserMultiFormatReader(hints, {
			delayBetweenScanAttempts: 30
		});
	}

	function LBScanner(options) {
		options = options || {};
		this.video = options.video;
		this.onCode = options.onCode || function () {};
		this.onStatus = options.onStatus || function () {};
		this.reader = null;
		this.stream = null;
		this.native = null;
		this.running = false;
		this.track = null;
		this._upright = document.createElement('canvas');
		this._rotated = document.createElement('canvas');
	}

	LBScanner.prototype.isSecure = function () {
		return global.isSecureContext ||
			   location.protocol === 'https:' ||
			   location.hostname === 'localhost';
	};

	LBScanner.prototype.start = async function () {
		if (this.running) return true;

		if (!this.isSecure()) {
			this.onStatus('The camera needs a secure (https) connection. Type the code instead.');
			return false;
		}
		if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
			this.onStatus('This browser cannot open the camera. Type the code instead.');
			return false;
		}

		// Ask for as much detail as the camera will give. The limiting factor on
		// these labels is pixels per bar, so a 1280x720 request throws away the
		// resolution that decides whether a scan succeeds.
		var constraints = {
			video: {
				facingMode: { ideal: 'environment' },
				width: { ideal: 2560 },
				height: { ideal: 1440 },
				frameRate: { ideal: 30 }
			}
		};
		try {
			this.stream = await navigator.mediaDevices.getUserMedia(constraints);
		} catch (e) {
			try {
				this.stream = await navigator.mediaDevices.getUserMedia(
					{ video: { facingMode: { ideal: 'environment' } } });
			} catch (e2) {
				this.onStatus('Could not open the camera. Type the code instead.');
				return false;
			}
		}

		this.video.srcObject = this.stream;
		this.video.setAttribute('playsinline', '');
		this.video.muted = true;
		try { await this.video.play(); } catch (e) { /* autoplay quirks */ }

		this.track = this.stream.getVideoTracks()[0];
		await this._applyCameraTuning();
		this.native = await this._initNative();

		this.running = true;
		this._loop();
		return true;
	};

	LBScanner.prototype.stop = function () {
		this.running = false;
		if (this.stream) {
			this.stream.getTracks().forEach(function (t) { t.stop(); });
			this.stream = null;
		}
		if (this.video) this.video.srcObject = null;
		this.track = null;
	};

	/** Focus, zoom and torch, where the device exposes them. */
	LBScanner.prototype._applyCameraTuning = async function () {
		if (!this.track || !this.track.getCapabilities) return;
		var caps = {};
		try { caps = this.track.getCapabilities() || {}; } catch (e) { return; }
		var advanced = [];

		// A label held close needs continuous refocus; a fixed focus reads the
		// shelf behind it and leaves the bars soft, which is exactly the failure
		// these photos show.
		if (caps.focusMode && caps.focusMode.indexOf('continuous') !== -1) {
			advanced.push({ focusMode: 'continuous' });
		}
		// A modest optical/digital zoom buys pixels per bar directly.
		if (caps.zoom && caps.zoom.max) {
			var target = Math.min(caps.zoom.max, Math.max(caps.zoom.min || 1, 2));
			advanced.push({ zoom: target });
		}
		if (advanced.length) {
			try { await this.track.applyConstraints({ advanced: advanced }); } catch (e) {}
		}
		this.capabilities = caps;
	};

	LBScanner.prototype.setTorch = function (on) {
		if (!this.track) return Promise.resolve(false);
		return this.track.applyConstraints({ advanced: [{ torch: !!on }] })
			.then(function () { return true; })
			.catch(function () { return false; });
	};

	LBScanner.prototype.setZoom = function (value) {
		if (!this.track) return Promise.resolve(false);
		return this.track.applyConstraints({ advanced: [{ zoom: Number(value) }] })
			.then(function () { return true; })
			.catch(function () { return false; });
	};

	LBScanner.prototype.hasTorch = function () {
		return !!(this.capabilities && this.capabilities.torch);
	};

	LBScanner.prototype.zoomRange = function () {
		return (this.capabilities && this.capabilities.zoom) || null;
	};

	/**
	 * The browser's own detector, where it exists (Android Chrome). It is
	 * hardware-accelerated, reads any orientation, and copes with the blur and
	 * skew that defeat the JS decoder - so it is always tried first.
	 */
	LBScanner.prototype._initNative = async function () {
		if (!('BarcodeDetector' in global)) return null;
		try {
			var supported = await global.BarcodeDetector.getSupportedFormats();
			var wanted = ['code_128', 'code_39', 'code_93', 'codabar', 'itf',
						  'ean_13', 'ean_8', 'upc_a', 'upc_e']
				.filter(function (f) { return supported.indexOf(f) !== -1; });
			if (!wanted.length) return null;
			return new global.BarcodeDetector({ formats: wanted });
		} catch (e) {
			return null;
		}
	};

	/**
	 * Draw a region of the frame, optionally turned a quarter turn.
	 *
	 * Both orientations are always tried. On the one shelf photo that decoded at
	 * all, upright never worked and rotated worked in 3ms - so scanning one way
	 * round discards half the opportunities for no saving worth having.
	 */
	LBScanner.prototype._draw = function (canvas, sx, sy, sw, sh, scale, rotate) {
		var dw = Math.round(sw * scale), dh = Math.round(sh * scale);
		if (rotate) { canvas.width = dh; canvas.height = dw; }
		else { canvas.width = dw; canvas.height = dh; }
		var g = canvas.getContext('2d', { willReadFrequently: true });
		g.save();
		if (rotate) {
			g.translate(dh / 2, dw / 2);
			g.rotate(Math.PI / 2);
			g.translate(-dw / 2, -dh / 2);
		}
		g.drawImage(this.video, sx, sy, sw, sh, 0, 0, dw, dh);
		g.restore();
		return canvas;
	};

	LBScanner.prototype._zxing = function (canvas) {
		if (!this.reader) {
			if (!(global.ZXingBrowser && global.ZXingBrowser.BrowserMultiFormatReader)) return null;
			this.reader = buildReader();
		}
		try {
			var r = this.reader.decodeFromCanvas(canvas);
			return (r && r.getText) ? r.getText() : null;
		} catch (e) {
			return null;
		}
	};

	/**
	 * One pass over the current frame.
	 *
	 * A generous central region rather than the old 90% x 50% strip, which
	 * missed the barcode on every test photo - a label sits wherever the box is
	 * held. Upscaled, because pixels per bar is the binding constraint, and
	 * tried both ways round.
	 */
	LBScanner.prototype._scanFrame = function () {
		var w = this.video.videoWidth, h = this.video.videoHeight;
		if (!w || !h) return null;

		var cw = Math.floor(w * 0.85), ch = Math.floor(h * 0.85);
		var sx = Math.floor((w - cw) / 2), sy = Math.floor((h - ch) / 2);
		// Keep the working canvas near 1000px on its long side: below that the
		// bars blur together, far above it the decode gets slow for no gain.
		var scale = Math.min(2, Math.max(1, 1000 / Math.max(cw, ch)));

		var hit = this._zxing(this._draw(this._upright, sx, sy, cw, ch, scale, false));
		if (hit) return hit;
		return this._zxing(this._draw(this._rotated, sx, sy, cw, ch, scale, true));
	};

	/**
	 * Decode a still photograph - the upload fallback, and the easiest way to
	 * check a troublesome label without fighting the live camera.
	 *
	 * Tries harder than the live path can afford to: a still is decoded once,
	 * so it can spend a few hundred milliseconds on larger upscales that would
	 * be far too slow at fifteen frames a second.
	 */
	LBScanner.prototype.decodeImage = async function (img) {
		var native = this.native || await this._initNative();
		if (native) {
			try {
				var found = await native.detect(img);
				if (found && found.length && found[0].rawValue) {
					return String(found[0].rawValue).trim();
				}
			} catch (e) { /* fall through to ZXing */ }
		}

		var w = img.naturalWidth || img.width, h = img.naturalHeight || img.height;
		if (!w || !h) return null;

		var canvas = document.createElement('canvas');
		var scales = [1, 2, 3];
		for (var i = 0; i < scales.length; i++) {
			for (var r = 0; r < 2; r++) {
				var rotate = (r === 1);
				var dw = Math.round(w * scales[i]), dh = Math.round(h * scales[i]);
				if (rotate) { canvas.width = dh; canvas.height = dw; }
				else { canvas.width = dw; canvas.height = dh; }
				var g = canvas.getContext('2d', { willReadFrequently: true });
				g.save();
				if (rotate) {
					g.translate(dh / 2, dw / 2);
					g.rotate(Math.PI / 2);
					g.translate(-dw / 2, -dh / 2);
				}
				g.drawImage(img, 0, 0, w, h, 0, 0, dw, dh);
				g.restore();
				var hit = this._zxing(canvas);
				if (hit) return hit;
			}
		}
		return null;
	};

	LBScanner.prototype._loop = async function () {
		while (this.running) {
			var code = null;
			try {
				if (this.native) {
					var found = await this.native.detect(this.video);
					if (found && found.length) code = found[0].rawValue;
				}
				if (!code) code = this._scanFrame();
			} catch (e) { /* a bad frame must not end the session */ }

			if (code) {
				this.stop();
				this.onCode(String(code).trim());
				return;
			}
			// Yield to the renderer so the preview stays smooth.
			await new Promise(function (r) { setTimeout(r, this.native ? 100 : 40); }.bind(this));
		}
	};

	global.LBScanner = LBScanner;
})(window);
