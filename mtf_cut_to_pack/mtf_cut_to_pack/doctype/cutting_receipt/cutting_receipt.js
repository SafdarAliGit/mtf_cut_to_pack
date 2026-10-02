// Copyright (c) 2026, Safdar Ali and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cutting Receipt", {
	setup(frm) {
		frm.set_query("article", () => ({ filters: { disabled: 0 } }));
		frm.set_query("cutting_slip", () => ({
			filters: { docstatus: 1, article: frm.doc.article || "" },
		}));
	},

	article(frm) {
		frm.set_value("cutting_slip", "");
	},

	no_of_bundle(frm) {
		frm.trigger("calculate_totals");
	},

	pcs_per_bundle(frm) {
		frm.trigger("calculate_totals");
	},

	rate(frm) {
		frm.trigger("calculate_totals");
	},

	calculate_totals(frm) {
		const qty = cint(frm.doc.no_of_bundle) * cint(frm.doc.pcs_per_bundle);
		frm.set_value("qty", qty);
		frm.set_value("amount", qty * flt(frm.doc.rate));
	},
});
