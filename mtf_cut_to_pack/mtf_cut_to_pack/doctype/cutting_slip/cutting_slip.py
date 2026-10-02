# Copyright (c) 2026, Safdar Ali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.stock.doctype.batch.batch import get_batch_qty


class CuttingSlip(Document):
	def validate(self):
		if flt(self.qty) <= 0:
			frappe.throw(_("Qty must be greater than 0"))

		self.amount = flt(self.qty) * flt(self.rate)
		self.validate_service_item()
		self.validate_warehouses()
		self.validate_fabrics()

	def on_submit(self):
		self.make_stock_entry()

	def on_cancel(self):
		if self.stock_entry:
			se = frappe.get_doc("Stock Entry", self.stock_entry)
			if se.docstatus == 1:
				se.cancel()

	def validate_service_item(self):
		if self.service_item and frappe.get_cached_value("Item", self.service_item, "is_stock_item"):
			frappe.throw(_("Service Item {0} must be a non-stock item").format(frappe.bold(self.service_item)))

	def validate_warehouses(self):
		if not self.fabrics:
			return

		if not (self.source_warehouse and self.target_warehouse):
			frappe.throw(_("Source Warehouse and Target Warehouse are required to issue fabric"))

		if self.source_warehouse == self.target_warehouse:
			frappe.throw(_("Source Warehouse and Target Warehouse cannot be the same"))

		if frappe.get_cached_value("Warehouse", self.source_warehouse, "company") != frappe.get_cached_value(
			"Warehouse", self.target_warehouse, "company"
		):
			frappe.throw(_("Source Warehouse and Target Warehouse must belong to the same company"))

	def validate_fabrics(self):
		issued_per_lot = {}

		for row in self.fabrics:
			pr_items = frappe.get_all(
				"Purchase Receipt Item",
				filters={"parent": row.purchase_receipt, "docstatus": 1, "item_code": row.fabric},
				pluck="batch_no",
			)
			if not pr_items:
				frappe.throw(
					_("Row #{0}: Fabric {1} is not in submitted Purchase Receipt {2}").format(
						row.idx, frappe.bold(row.fabric), frappe.bold(row.purchase_receipt)
					)
				)

			if row.lot_no not in pr_items:
				frappe.throw(
					_("Row #{0}: Lot No {1} was not received against Purchase Receipt {2} for Fabric {3}").format(
						row.idx, frappe.bold(row.lot_no), frappe.bold(row.purchase_receipt), frappe.bold(row.fabric)
					)
				)

			row.available_qty = get_available_qty(row.lot_no, self.source_warehouse)

			if flt(row.issue_qty) <= 0:
				frappe.throw(_("Row #{0}: Issue Qty must be greater than 0").format(row.idx))

			issued_per_lot[row.lot_no] = issued_per_lot.get(row.lot_no, 0) + flt(row.issue_qty)
			if issued_per_lot[row.lot_no] > flt(row.available_qty):
				frappe.throw(
					_("Row #{0}: Issue Qty for Lot No {1} ({2}) exceeds Available Qty {3} in {4}").format(
						row.idx,
						frappe.bold(row.lot_no),
						issued_per_lot[row.lot_no],
						row.available_qty,
						frappe.bold(self.source_warehouse),
					)
				)

	def make_stock_entry(self):
		if not self.fabrics:
			return

		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Transfer"
		se.purpose = "Material Transfer"
		se.company = frappe.get_cached_value("Warehouse", self.source_warehouse, "company")
		se.set_posting_time = 1
		se.posting_date = self.posting_date
		se.from_warehouse = self.source_warehouse
		se.to_warehouse = self.target_warehouse
		se.remarks = _("Fabric issued against Cutting Slip {0}").format(self.name)

		for row in self.fabrics:
			stock_uom = frappe.get_cached_value("Item", row.fabric, "stock_uom")
			se.append(
				"items",
				{
					"item_code": row.fabric,
					"batch_no": row.lot_no,
					"qty": row.issue_qty,
					"transfer_qty": row.issue_qty,
					"uom": stock_uom,
					"stock_uom": stock_uom,
					"conversion_factor": 1,
					"s_warehouse": self.source_warehouse,
					"t_warehouse": self.target_warehouse,
				},
			)

		se.insert()
		se.submit()
		self.db_set("stock_entry", se.name)


@frappe.whitelist()
def get_available_qty(batch_no, warehouse):
	if not (batch_no and warehouse):
		return 0
	return flt(get_batch_qty(batch_no=batch_no, warehouse=warehouse))


@frappe.whitelist()
def get_service_rate(service_item, supplier, posting_date=None):
	"""Rate of the service item from the supplier's buying price list (Item Price)."""
	if not (service_item and supplier):
		return 0

	price_list = frappe.get_cached_value("Supplier", supplier, "default_price_list") or frappe.db.get_single_value(
		"Buying Settings", "buying_price_list"
	)
	if not price_list:
		return 0

	posting_date = posting_date or frappe.utils.today()
	rate = frappe.db.sql(
		"""
		select price_list_rate
		from `tabItem Price`
		where item_code = %(item)s and price_list = %(price_list)s and buying = 1
			and ifnull(supplier, '') in (%(supplier)s, '')
			and ifnull(valid_from, '2000-01-01') <= %(date)s
			and ifnull(valid_upto, '2500-12-31') >= %(date)s
		order by ifnull(supplier, '') = %(supplier)s desc, valid_from desc
		limit 1
		""",
		{"item": service_item, "price_list": price_list, "supplier": supplier, "date": posting_date},
	)
	return flt(rate[0][0]) if rate else 0


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def fabric_query(doctype, txt, searchfield, start, page_len, filters):
	"""Items received on the given (submitted) Purchase Receipt."""
	return frappe.db.sql(
		"""
		select distinct pri.item_code, pri.item_name
		from `tabPurchase Receipt Item` pri
		where pri.parent = %(purchase_receipt)s and pri.docstatus = 1
			and (pri.item_code like %(txt)s or pri.item_name like %(txt)s)
		order by pri.item_code
		limit %(start)s, %(page_len)s
		""",
		{
			"purchase_receipt": filters.get("purchase_receipt"),
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def lot_query(doctype, txt, searchfield, start, page_len, filters):
	"""Batches of the given fabric received on the given Purchase Receipt."""
	return frappe.db.sql(
		"""
		select distinct pri.batch_no, b.custom_color
		from `tabPurchase Receipt Item` pri
		inner join `tabBatch` b on b.name = pri.batch_no
		where pri.parent = %(purchase_receipt)s and pri.docstatus = 1
			and pri.item_code = %(fabric)s
			and pri.batch_no like %(txt)s
		order by pri.batch_no
		limit %(start)s, %(page_len)s
		""",
		{
			"purchase_receipt": filters.get("purchase_receipt"),
			"fabric": filters.get("fabric"),
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)
