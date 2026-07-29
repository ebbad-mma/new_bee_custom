

frappe.ui.form.on('Item', {

    item_group(frm){
        set_filter_in_cat_basis_of_ite_grp(frm)
    },
   custom_category(frm){
    set_filter_in_subcat_on_the_basis_of_cat(frm)
    },
    refresh(frm){
        render_velocity_dashboard(frm);
        setup_4_tab_structure(frm);
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

function setup_4_tab_structure(frm) {
    // 1. Rename the 4 primary tabs
    const primary_tabs = {
        'details': '1. Details',
        'pricing_tab': '2. Pricing & Margin',
        'keepa_description_feature': '3. Market Intelligence',
        'inventory_section': '4. Inventory & Operations'
    };

    Object.keys(primary_tabs).forEach(fieldname => {
        if (frm.fields_dict[fieldname]) {
            frm.set_df_property(fieldname, 'label', primary_tabs[fieldname]);
            frm.set_df_property(fieldname, 'hidden', 0);
        }
    });

    // 2. Hide all extra tabs
    const tabs_to_hide = [
        'custom_amazon_fields',
        'custom_item_images',
        'dashboard_tab',
        'variants_section',
        'accounting',
        'uom_tab',
        'purchasing_tab',
        'sales_details',
        'item_tax_section_break',
        'quality_tab',
        'manufacturing',
        'custom_supplier_history_tab'
    ];

    tabs_to_hide.forEach(tab_name => {
        if (frm.fields_dict[tab_name]) {
            frm.set_df_property(tab_name, 'hidden', 1);
        }
    });

    // 3. Set Collapsed state for specific sections
    const collapsed_sections = [
        'sec_performance',
        'sec_amazon_benchmark',
        'sec_supplier_history',
        'sec_competitive_codes',
        'sec_buying_selling',
        'sec_dimensions',
        'sec_tax_accounts'
    ];

    collapsed_sections.forEach(sec => {
        if (frm.fields_dict[sec]) {
            frm.set_df_property(sec, 'collapsible', 1);
            frm.set_df_property(sec, 'collapsed', 1);
        }
    });
}






