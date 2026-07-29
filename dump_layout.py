import frappe

frappe.init(site="lucky-bee")
frappe.connect()

meta = frappe.get_meta("Item")
fields = meta.fields

lines = []
lines.append("=== CURRENT ITEM FORM LAYOUT ===\n")
for i, f in enumerate(fields):
    prefix = ""
    if f.fieldtype == "Tab Break":
        prefix = "\n>>> TAB: "
    elif f.fieldtype == "Section Break":
        prefix = "\n  >> SECTION: "
    elif f.fieldtype == "Column Break":
        prefix = "    | COL: "
    else:
        prefix = "      "
    
    label = f.label or f.fieldname or ""
    coll = " [collapsed]" if f.collapsible else ""
    hidden = " [HIDDEN]" if f.hidden else ""
    custom = " *CUSTOM*" if f.is_custom_field else ""
    lines.append(f"{i:3d}{prefix}{f.fieldname} ({f.fieldtype}) {label}{coll}{hidden}{custom}")

lines.append(f"\n\nTotal fields: {len(fields)}")

with open("/tmp/item_layout.txt", "w") as out:
    out.write("\n".join(lines))

print(f"Wrote {len(fields)} fields to /tmp/item_layout.txt")
frappe.destroy()
