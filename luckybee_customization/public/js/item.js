

frappe.ui.form.on('Item', {

    item_group(frm){
        set_filter_in_cat_basis_of_ite_grp(frm)
    },
   custom_category(frm){
    set_filter_in_subcat_on_the_basis_of_cat(frm)
    },
    refresh(frm){
        move_connections_tab_to_end(frm);
        render_velocity_dashboard(frm);
        render_amazon_image_gallery(frm);
        render_lucky_bee_image_gallery(frm);
        render_supplier_history(frm);
        render_amazon_freshness(frm);
        add_refresh_amazon_button(frm);
        add_label_buttons(frm);
        if(frm.doc.custom_category){
            set_filter_in_subcat_on_the_basis_of_cat(frm)
        }
        if(frm.doc.item_group){
            set_filter_in_cat_basis_of_ite_grp(frm)
        }
        // #call function to sort supplier history 
        sort_supplier_history_desc(frm) 


        // set parent item group in item
        set_parent_group(frm)

        // set group category
        if (!frm.doc.item_group){

            set_category_group(frm)
        }


        // set sub category
        if(!frm.doc.custom_category){

            set_sub_category_group(frm)
        }

        // #hide index in supplier history because we are sorting on refresh 
        $(document).ready(function() {
            // Hide the div with the class 'row-check sortable-handle col'
            $('.row-index.sortable-handle.col').hide();
        });
        
        $("button:contains('Actions')").hide();
        $("button:contains('Duplicate')").hide();
        // Check if the custom_item_detail field has a value
        if (frm.doc.custom_item_detail) {
            // Add custom button
            frm.add_custom_button(__('Item Extra Details'), function() {
                // Set the Frappe route
                frappe.set_route('Form', 'Item Details', frm.doc.custom_item_detail);
            });
        }

        // PRODUCT FINDER
        frm.add_custom_button("Product Finder", async function () {
            try {
                // Initialize variables for product details
                let color = null;
                let size = null;
                let model = null;
                let part_number = null;
        
                // Check if 'asin' is not present
                if (!frm.doc.custom_asin_no && !frm.doc.ean && !frm.doc.custom_url && !frm.doc.custom_fsn_no) {
                    console.log("ppppppp")
                    // Directly create 'Product Finder' document if 'asin' is not available
                    let new_doc = frappe.model.get_new_doc("Product Finder");
                    new_doc.item = frm.doc.name;
                    new_doc.title = frm.doc.item_name;
                    new_doc.brand = frm.doc.brand;
                    new_doc.root_category = frm.doc.category_root;
                    new_doc.sub_category = frm.doc.lb_sub_category;
        
                    frappe.set_route("Form", "Product Finder", new_doc.name);
                    console.log("Created Product Finder without 'asin':", new_doc);
                    return; // Exit the function after creating the document
                }
                console.log("isouayus")
                // Proceed with checking for 'Item Details' only if 'asin' is present
                const amazon_exists =frappe.db.exists('Item Details',null, {'item': frm.doc.name});
                const flipkart_exists = frappe.db.exists('Item Details',null, {'item': frm.doc.name});
        
                // Fetch details only if Amazon details exist
                if (amazon_exists) {
                    const id_data = await frappe.db.get_doc('Item Details',null, {'item': frm.doc.name});
                    if (id_data) {
                        color = id_data.color;
                        size = id_data.size;
                        model = id_data.model;
                        part_number = id_data.product_codes_partnumber;
                    }
                }
        
                // Fetch details only if Flipkart details exist
                if (flipkart_exists) {
                    const id_data_flipkart =  await frappe.db.get_doc('Item Details',null, {'item': frm.doc.name});
                    if (id_data_flipkart) {
                        model = id_data_flipkart.model_flipkart ;
                    }
                }
        
                // Create a new 'Product Finder' document with the fetched fields
                let new_doc = frappe.model.get_new_doc("Product Finder");
                new_doc.item = frm.doc.name;
                new_doc.title = frm.doc.item_name;
                new_doc.brand = frm.doc.brand;
                new_doc.size = size;
                new_doc.model = model;
                new_doc.part_number = part_number;
                new_doc.color = color;
                new_doc.root_category = frm.doc.category_root;
                new_doc.sub_category = frm.doc.lb_sub_category;
        
                frappe.set_route("Form", "Product Finder", new_doc.name);
                console.log("Created Product Finder with fetched details:", new_doc);
        
            } catch (error) {
                console.error("An error occurred while creating Product Finder:", error);
            }
        });
        


        // PUBLISH ITEM 
        if (! frm.doc.custom_published)
        {frm.add_custom_button("Publish Item", function(){            
            frappe.call({
                args: {
                    doc : frm.doc
                },
                method: "luckybee_customization.woocommerce.publish_item.publish_item",
                freeze: true,
                freeze_message: "Publishing item...",
                        
                callback: function(r){
                    cur_frm.refresh()
                    window.location.reload()
                    frappe.msgprint(r.message)
                }
            })
        })}

        // UNPUBLISH ITEM 
        else{
            frm.add_custom_button("Unpublish Item", function(){
                frappe.call({
                    args: {
                        doc : frm.doc
                    },
                    method: "luckybee_customization.woocommerce.publish_item.unpublish_item",
                    callback: function(r){
                        
                        window.location.reload()
                        frappe.msgprint(r.message)
                    }
                })
            })  
        }
    }
})

function move_connections_tab_to_end(frm) {
    requestAnimationFrame(() => {
        const tabs = frm.page.wrapper.find('.form-tabs');
        const connectionsTab = tabs.find("[data-fieldname='dashboard_tab']").closest('.nav-item');
        const connectionsPanel = frm.page.wrapper.find('#item-dashboard_tab');

        if (connectionsTab.length) {
            connectionsTab.removeClass('hide').addClass('show').appendTo(tabs);
            connectionsPanel.removeClass('hide').addClass('show');
        }
    });
}




function render_supplier_history(frm) {
    const wrapper = frm.get_field('custom_supplier_history_html') && frm.get_field('custom_supplier_history_html').$wrapper;
    if (!wrapper || frm.is_new()) return;

    wrapper.html('<div class="text-muted small">Loading purchase history…</div>');

    frappe.call({
        method: 'luckybee_customization.api.supplier_history.get_supplier_history',
        args: { item_code: frm.doc.name },
        callback: function (r) {
            const rows = r.message || [];
            if (!rows.length) {
                wrapper.html('<div class="text-muted small">No purchases recorded for this item yet.</div>');
                return;
            }

            const body = rows.map(row => {
                const date = row.posting_date ? frappe.datetime.str_to_user(row.posting_date) : '';
                const rate = format_currency(row.rate, frm.doc.currency);
                const qty = row.qty != null ? format_number(row.qty) : '';
                const supplier = frappe.utils.escape_html(row.supplier_name || row.supplier || '');
                return `
                    <tr>
                        <td>${supplier}</td>
                        <td class="text-right">${rate}</td>
                        <td class="text-right">${qty}</td>
                        <td>${date}</td>
                        <td><a href="/app/purchase-invoice/${encodeURIComponent(row.invoice)}">${frappe.utils.escape_html(row.invoice)}</a></td>
                    </tr>`;
            }).join('');

            wrapper.html(`
                <div style="overflow-x:auto;">
                    <table class="table table-bordered" style="margin-bottom:6px;">
                        <thead>
                            <tr>
                                <th>Supplier</th>
                                <th class="text-right" style="width:130px;">Rate</th>
                                <th class="text-right" style="width:90px;">Qty</th>
                                <th style="width:120px;">Date</th>
                                <th style="width:170px;">Invoice</th>
                            </tr>
                        </thead>
                        <tbody>${body}</tbody>
                    </table>
                </div>
            `);
        }
    });
}

// #helper function to show latest supplier in first
function sort_supplier_history_desc(frm) {
    if (frm.doc.custom_supplier_history && frm.doc.custom_supplier_history.length > 0) {
        // Sort the child table rows by the modified date in descending order
        frm.doc.custom_supplier_history.sort((a, b) => {
            return new Date(b.creation) - new Date(a.creation);
        });

        // Refresh the field to reflect the sorted rows
        frm.refresh_field('custom_supplier_history');
    }
}




// set filter in  parent group in item
function set_parent_group(frm) {
    frm.set_query('item_group', function() {
        return {
            filters: {
                'parent_item_group': '', // No parent
                'is_group': 1          // Is a group
            }
        };
    });
}


// set filter in  category  group in item
function set_category_group(frm) {
    frm.set_query('custom_category', function() {
        return {
            filters: {
                'parent_item_group': ['!=', ''], // No parent
                'is_group': 1          // Is a group
            }
        };
    });
}


// set filter in  sub category  group in item
function set_sub_category_group(frm) {
    frm.set_query('lb_sub_category', function() {
        return {
            filters: {
                'parent_item_group': ['!=', ''], // No parent
                'is_group': 0         // Is a group
            }
        };
    });
}


// set filter in  sub category  group in item
function set_filter_in_cat_basis_of_ite_grp(frm) {
    frm.set_query('custom_category', function() {
        return {
            filters: {
                'parent_item_group': ['=', frm.doc.item_group], // No parent
                'is_group': 1       // Is a group
            }
        };
    });
}

// set filter in  sub category  group in item
function set_filter_in_subcat_on_the_basis_of_cat(frm) {
    frm.set_query('lb_sub_category', function() {
        return {
            filters: {
                'parent_item_group': ['=', frm.doc.custom_category], // No parent
                'is_group': 0     // Is a group
            }
        };
    });
}

// Our own photos, rendered as pictures. The lb_images grid can only print the
// file path in its cell, so the section used to be a column of
// "/private/files/capture_...jpg" with no way to see what was photographed.
// Grouped by section (Out Box / In Box / Product) in the same order the mobile
// capture form uses, with the primary shot marked.
function render_lucky_bee_image_gallery(frm) {
    const wrapper = frm.get_field('lb_image_gallery') && frm.get_field('lb_image_gallery').$wrapper;
    if (!wrapper) return;

    const rows = (frm.doc.lb_images || []).filter(r => r.image);
    if (!rows.length) {
        wrapper.html('<div class="text-muted small">No photos captured yet.</div>');
        return;
    }

    const esc = s => frappe.utils.escape_html(s == null ? '' : String(s));
    const primary = frm.doc.lb_primary_image;
    const sections = ['Out Box', 'In Box', 'Product'];

    // Anything captured before photo_section existed still has to show up.
    const groups = {};
    rows.forEach(r => {
        const key = sections.includes(r.photo_section) ? r.photo_section : 'Uncategorised';
        (groups[key] = groups[key] || []).push(r);
    });

    const order = sections.concat('Uncategorised').filter(s => groups[s]);

    const html = order.map(section => {
        const thumbs = groups[section]
            .sort((a, b) => (a.sequence || 0) - (b.sequence || 0))
            .map(r => `
                <a href="${esc(r.image)}" target="_blank" rel="noopener"
                   style="display:inline-block; margin:0 8px 8px 0; text-align:center;
                          text-decoration:none; color:inherit;">
                    <img src="${esc(r.image)}"
                         title="${esc(r.caption || r.image)}"
                         style="width:90px; height:90px; object-fit:contain; border:1px solid var(--border-color); border-radius:6px; background:#fff;"
                         onerror="this.closest('a').style.display='none'" />
                    ${r.image === primary
                        ? '<div class="text-success" style="font-size:10px; font-weight:600;">Primary</div>'
                        : (r.caption ? `<div class="text-muted" style="font-size:10px;">${esc(r.caption)}</div>` : '')}
                </a>
            `).join('');

        return `
            <div style="margin-bottom:8px;">
                <div class="text-muted" style="font-size:11px; text-transform:uppercase; letter-spacing:.03em;">
                    ${esc(section)} (${groups[section].length})
                </div>
                <div style="display:flex; flex-wrap:wrap; align-items:flex-start;">${thumbs}</div>
            </div>`;
    }).join('');

    wrapper.html(html);
}

function render_amazon_image_gallery(frm) {
    const wrapper = frm.get_field('amz_image_gallery') && frm.get_field('amz_image_gallery').$wrapper;
    if (!wrapper) return;

    const rows = (frm.doc.amz_image_urls || [])
        .filter(r => r.image_url)
        .sort((a, b) => (a.sequence || 0) - (b.sequence || 0));

    if (!rows.length) {
        wrapper.html('<div class="text-muted small">No Amazon images synced.</div>');
        return;
    }

    const thumbs = rows.map(r => `
        <a href="${frappe.utils.escape_html(r.image_url)}" target="_blank" rel="noopener"
           style="display:inline-block; margin:0 8px 8px 0;">
            <img src="${frappe.utils.escape_html(r.image_url)}"
                 title="${frappe.utils.escape_html(String(r.sequence || ''))}"
                 style="width:90px; height:90px; object-fit:contain; border:1px solid var(--border-color); border-radius:6px; background:#fff;"
                 onerror="this.closest('a').style.display='none'" />
        </a>
    `).join('');

    wrapper.html(`<div style="display:flex; flex-wrap:wrap; align-items:flex-start;">${thumbs}</div>`);
}

function render_velocity_dashboard(frm) {
    if (frm.is_new()) return;

    if (!frm.dashboard || !frm.dashboard.wrapper) return;

    frm.dashboard.wrapper.find('.lb-velocity-dashboard-strip').remove();

    let band = frm.doc.lb_velocity_band || 'No Data';
    let days_cover = (frm.doc.lb_days_cover !== null && frm.doc.lb_days_cover !== undefined) ? frm.doc.lb_days_cover + ' days' : 'N/A';
    let u90 = (frm.doc.lb_units_90d !== null && frm.doc.lb_units_90d !== undefined) ? frm.doc.lb_units_90d : 0;
    let days_since_sale = (frm.doc.lb_days_since_sale !== null && frm.doc.lb_days_since_sale !== undefined) ? frm.doc.lb_days_since_sale + ' days ago' : 'Never';
    let stock_val = (frm.doc.lb_stock_value !== null && frm.doc.lb_stock_value !== undefined) ? '₹' + Number(frm.doc.lb_stock_value).toLocaleString('en-IN') : '₹0';

    let bg_style = 'background-color: #f8fafc; border-color: #cbd5e1; color: #334155;';
    let badge_style = 'background-color: #64748b; color: #ffffff;';

    if (band === 'Fast' || band === 'Healthy') {
        bg_style = 'background-color: #f0fdf4; border-color: #bbf7d0; color: #166534;';
        badge_style = 'background-color: #16a34a; color: #ffffff;';
    } else if (band === 'Slow') {
        bg_style = 'background-color: #fffbeb; border-color: #fef3c7; color: #92400e;';
        badge_style = 'background-color: #d97706; color: #ffffff;';
    } else if (band === 'Dead' || band === 'Never Sold') {
        bg_style = 'background-color: #fef2f2; border-color: #fecaca; color: #991b1b;';
        badge_style = 'background-color: #dc2626; color: #ffffff;';
    }

    let strip_html = `
        <div class="lb-velocity-dashboard-strip" style="margin-bottom: 15px; padding: 12px 16px; border-radius: 8px; border: 1px solid; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; font-size: 13px; font-weight: 500; ${bg_style}">
            <div style="display: flex; gap: 24px; align-items: center; flex-wrap: wrap;">
                <div><span style="opacity: 0.75; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; display: block;">Stock Value</span> <strong>${stock_val}</strong></div>
                <div><span style="opacity: 0.75; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; display: block;">90d Units Sold</span> <strong>${u90}</strong></div>
                <div><span style="opacity: 0.75; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; display: block;">Days Cover</span> <strong>${days_cover}</strong></div>
                <div><span style="opacity: 0.75; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; display: block;">Last Sold</span> <strong>${days_since_sale}</strong></div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
                <span style="opacity: 0.75; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">Velocity Band:</span>
                <span style="padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 700; ${badge_style}">${band}</span>
            </div>
        </div>
    `;

    frm.dashboard.wrapper.prepend(strip_html);
    frm.dashboard.show();
}






// B3 - the sync date existed but was buried on the Market Intelligence tab.
// Surface it next to the Amazon price where the pricing decision is actually
// made, and colour it by age: under 30 days neutral, 30-90 amber, over 90 red.
function render_amazon_freshness(frm) {
    const $wrap = frm.fields_dict.amz_best_price && frm.fields_dict.amz_best_price.$wrapper;
    if (!$wrap) return;

    $wrap.find('.lb-amz-freshness').remove();
    if (frm.is_new()) return;

    const tried = frm.doc.amz_last_synced;
    const succeeded = frm.doc.amz_last_successful_sync;
    if (!tried && !succeeded) return;

    const days = d => d ? frappe.datetime.get_day_diff(frappe.datetime.now_date(), d) : null;
    const successAge = days(succeeded);
    const triedAge = days(tried);

    // Age the badge on when we last got real data, not merely when we last tried.
    const age = successAge === null ? triedAge : successAge;

    let colour = '#6c757d';               // under 30 days - neutral
    if (age !== null && age > 90) colour = '#c0392b';        // over 90 - red
    else if (age !== null && age >= 30) colour = '#b9770e';  // 30-90 - amber

    const human = a => a === null ? 'never'
        : a === 0 ? 'today'
        : a === 1 ? 'yesterday'
        : `${a} days ago`;

    let text = succeeded ? `synced ${human(successAge)}` : 'no successful sync yet';

    // The gap between "tried" and "last got real data" is what exposes a sync
    // that has been quietly failing.
    if (succeeded && triedAge !== null && successAge !== null && successAge - triedAge > 0) {
        text += ` (last attempt ${human(triedAge)})`;
    } else if (!succeeded && tried) {
        text += ` (last attempt ${human(triedAge)})`;
    }

    const status = frm.doc.amz_data_status;
    const statusBit = status && status !== 'Matched'
        ? ` &middot; <strong>${frappe.utils.escape_html(status)}</strong>` : '';

    $wrap.append(`
        <div class="lb-amz-freshness" style="margin-top:4px; font-size:11.5px; color:${colour};">
            ${frappe.utils.escape_html(text)}${statusBit}
        </div>
    `);
}

// B7 - re-pull Keepa for this ASIN on demand, rather than waiting for the
// nightly job, and stamp the sync date.
function add_refresh_amazon_button(frm) {
    if (frm.is_new() || !frm.doc.custom_asin_no) return;

    frm.add_custom_button(__('Refresh Amazon Data'), function () {
        frappe.dom.freeze(__('Refreshing from Amazon...'));
        frappe.call({
            method: 'luckybee_customization.api.keepa_refresh.refresh_amazon_data',
            args: { item_code: frm.doc.name },
            callback: function (r) {
                frappe.dom.unfreeze();
                const res = r.message || {};
                if (res.status === 'ok') {
                    frappe.show_alert({
                        message: __('Amazon data refreshed ({0})', [res.amz_data_status || '-']),
                        indicator: 'green'
                    });
                    frm.reload_doc();
                } else {
                    frappe.msgprint({
                        title: __('Could not refresh'),
                        message: res.message || __('Amazon data could not be refreshed.'),
                        indicator: 'orange'
                    });
                }
            },
            error: function () {
                frappe.dom.unfreeze();
            }
        });
    });
}

// Keep the thumbnails honest while the grid is being edited - otherwise a photo
// swapped or removed here still shows the old picture until the next reload.
frappe.ui.form.on('Lucky Bee Images', {
    image(frm) {
        render_lucky_bee_image_gallery(frm);
    },
    photo_section(frm) {
        render_lucky_bee_image_gallery(frm);
    },
    caption(frm) {
        render_lucky_bee_image_gallery(frm);
    }
});

frappe.ui.form.on('Item', {
    lb_images_remove(frm) {
        render_lucky_bee_image_gallery(frm);
    },
    lb_primary_image(frm) {
        render_lucky_bee_image_gallery(frm);
    }
});

// Phase 2 section 4.3 - Design/Preview and Print buttons for the product label.
// Grouped under "Label" so they do not crowd the header alongside Product
// Finder and Refresh Amazon Data.
function add_label_buttons(frm) {
    if (frm.is_new()) return;

    frm.add_custom_button(__('Design / Preview Label'), function () {
        // The standard print view, which is the preview - staff see exactly what
        // will come out of the printer, on the same 50x25mm page box.
        const url = frappe.urllib.get_full_url(
            '/printview?doctype=' + encodeURIComponent(frm.doc.doctype)
            + '&name=' + encodeURIComponent(frm.doc.name)
            + '&format=Product%20Label&no_letterhead=1&_lang=en'
        );
        window.open(url, '_blank');
    }, __('Label'));

    frm.add_custom_button(__('Print Barcode Label'), function () {
        // Same format, opened straight into the browser print dialog.
        const w = window.open(frappe.urllib.get_full_url(
            '/printview?doctype=' + encodeURIComponent(frm.doc.doctype)
            + '&name=' + encodeURIComponent(frm.doc.name)
            + '&format=Product%20Label&no_letterhead=1&trigger_print=1&_lang=en'
        ), '_blank');
        if (!w) {
            frappe.msgprint({
                title: __('Popup blocked'),
                message: __('Allow popups for this site to print labels.'),
                indicator: 'orange'
            });
        }
    }, __('Label'));
}
