import frappe


def set_batch_color(doc, method=None):
	"""Copy each row's color to its batch so Cutting Slip can fetch it from the Lot No.

	Batches auto-created by ERPNext are made in before_submit, so batch_no is set by now.
	"""
	for row in doc.items:
		if row.batch_no and row.get("custom_color"):
			frappe.db.set_value("Batch", row.batch_no, "custom_color", row.custom_color)
