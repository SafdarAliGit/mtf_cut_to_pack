import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def make_gate_pass(source_name):
	"""Return an unsaved Material Transfer Stock Entry moving each row's Fabric Item to the Supplier Warehouse."""
	po = frappe.get_doc("Purchase Order", source_name)
	po.check_permission("read")

	if po.docstatus != 1:
		frappe.throw(_("Purchase Order {0} must be submitted").format(po.name))
	if not po.get("custom_supplier_warehouse"):
		frappe.throw(_("Please set Supplier Warehouse on Purchase Order {0}").format(po.name))

	se = frappe.new_doc("Stock Entry")
	se.purpose = "Material Transfer"
	se.set_stock_entry_type()
	se.company = po.company
	se.to_warehouse = po.custom_supplier_warehouse
	se.remarks = _("Gate Pass against Purchase Order {0} ({1})").format(po.name, po.supplier)

	for row in po.items:
		# Fall back to the PO row's own item when it is itself a stock (fabric) item
		item_code = row.get("custom_fabric_item")
		if not item_code and frappe.db.get_value("Item", row.item_code, "is_stock_item"):
			item_code = row.item_code
		if not item_code:
			continue
		stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
		qty = flt(row.stock_qty) if item_code == row.item_code else flt(row.qty)
		se.append(
			"items",
			{
				"item_code": item_code,
				"qty": qty,
				"transfer_qty": qty,
				"uom": stock_uom,
				"stock_uom": stock_uom,
				"conversion_factor": 1,
				"t_warehouse": po.custom_supplier_warehouse,
			},
		)

	if not se.items:
		frappe.throw(_("No Fabric Item or stock item found in Purchase Order {0}").format(po.name))

	return se
