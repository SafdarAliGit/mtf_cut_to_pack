# Copyright (c) 2026, Safdar Ali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class CuttingReceipt(Document):
	def validate(self):
		self.validate_cutting_slip()
		self.qty = cint(self.no_of_bundle) * cint(self.pcs_per_bundle)
		self.amount = flt(self.qty) * flt(self.rate)

	def validate_cutting_slip(self):
		if not self.cutting_slip:
			self.supplier = None
			return

		slip = frappe.db.get_value(
			"Cutting Slip", self.cutting_slip, ["docstatus", "article", "supplier"], as_dict=True
		)
		if slip.docstatus != 1:
			frappe.throw(_("Cutting Slip {0} must be submitted").format(frappe.bold(self.cutting_slip)))

		if slip.article != self.article:
			frappe.throw(
				_("Cutting Slip {0} is for Article {1}, not {2}").format(
					frappe.bold(self.cutting_slip), frappe.bold(slip.article), frappe.bold(self.article)
				)
			)

		self.supplier = slip.supplier
