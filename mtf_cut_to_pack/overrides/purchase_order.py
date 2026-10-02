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
		if not row.get("custom_fabric_item"):
			continue
		stock_uom = frappe.db.get_value("Item", row.custom_fabric_item, "stock_uom")
		se.append(
			"items",
			{
				"item_code": row.custom_fabric_item,
				"qty": flt(row.qty),
				"transfer_qty": flt(row.qty),
				"uom": stock_uom,
				"stock_uom": stock_uom,
				"conversion_factor": 1,
				"t_warehouse": po.custom_supplier_warehouse,
			},
		)

	if not se.items:
		frappe.throw(_("No Fabric Item found in Purchase Order {0}").format(po.name))

	return se
