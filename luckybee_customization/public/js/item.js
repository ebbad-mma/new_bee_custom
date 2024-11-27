

frappe.ui.form.on('Item', {
    refresh(frm){
        // #call function to sort supplier history 
        sort_supplier_history_desc(frm) 


        // set parent item group in item
        set_parent_group(frm)

        // set group category
        set_category_group(frm)


        // set sub category
        set_sub_category_group(frm)

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
                if (!frm.doc.custom_asin_no && !frm.doc.custom_ean && !frm.doc.custom_url && !frm.doc.custom_fsn_no) {
                    console.log("ppppppp")
                    // Directly create 'Product Finder' document if 'asin' is not available
                    let new_doc = frappe.model.get_new_doc("Product Finder");
                    new_doc.item = frm.doc.name;
                    new_doc.title = frm.doc.item_name;
                    new_doc.brand = frm.doc.brand;
                    new_doc.root_category = frm.doc.custom_category_root;
                    new_doc.sub_category = frm.doc.custom_category_sub;
        
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
                new_doc.root_category = frm.doc.custom_category_root;
                new_doc.sub_category = frm.doc.custom_category_sub;
        
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
    frm.set_query('custom_category_sub', function() {
        return {
            filters: {
                'parent_item_group': ['!=', ''], // No parent
                'is_group': 0         // Is a group
            }
        };
    });
}

