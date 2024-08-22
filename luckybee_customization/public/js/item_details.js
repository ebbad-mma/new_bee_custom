frappe.ui.form.on('Item Details', {
    refresh(frm){
        // display specification from html to normal
        show_specification(frm)}})

function show_specification(frm) {
    let template = '';
		template =frm.doc.spec_html_data;
        $(frm.fields_dict.specification.wrapper).html(template);}