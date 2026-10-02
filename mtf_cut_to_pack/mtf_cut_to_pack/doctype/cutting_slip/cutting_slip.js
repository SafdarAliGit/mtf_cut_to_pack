// Copyright (c) 2026, Safdar Ali and contributors
// For license information, please see license.txt

const CUTTING_SLIP_METHOD = "mtf_cut_to_pack.mtf_cut_to_pack.doctype.cutting_slip.cutting_slip";

frappe.ui.form.on("Cutting Slip", {
	setup(frm) {
		frm.set_query("service_item", () => ({ filters: { is_stock_item: 0, disabled: 0 } }));
		frm.set_query("article", () => ({ filters: { disabled: 0 } }));
		frm.set_query("source_warehouse", () => ({ filters: { is_group: 0 } }));
		frm.set_query("target_warehouse", () => ({ filters: { is_group: 0 } }));
		frm.set_query("purchase_receipt", "fabrics", () => ({ filters: { docstatus: 1 } }));

		frm.set_query("fabric", "fabrics", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			if (!row.purchase_receipt) {
				frappe.throw(__("Please select Purchase Receipt No first"));
			}
			return {
				query: `${CUTTING_SLIP_METHOD}.fabric_query`,
				filters: { purchase_receipt: row.purchase_receipt },
			};
		});

		frm.set_query("lot_no", "fabrics", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			if (!row.purchase_receipt || !row.fabric) {
				frappe.throw(__("Please select Purchase Receipt No and Fabric first"));
			}
			return {
				query: `${CUTTING_SLIP_METHOD}.lot_query`,
				filters: { purchase_receipt: row.purchase_receipt, fabric: row.fabric },
			};
		});
	},

	qty(frm) {
		frm.trigger("calculate_amount");
	},

	rate(frm) {
		frm.trigger("calculate_amount");
	},

	calculate_amount(frm) {
		frm.set_value("amount", flt(frm.doc.qty) * flt(frm.doc.rate));
	},

	supplier(frm) {
		frm.trigger("set_service_rate");
	},

	service_item(frm) {
		frm.trigger("set_service_rate");
	},

	posting_date(frm) {
		frm.trigger("set_service_rate");
	},

	set_service_rate(frm) {
		if (!frm.doc.supplier || !frm.doc.service_item) return;
		frappe.call({
			method: `${CUTTING_SLIP_METHOD}.get_service_rate`,
			args: {
				service_item: frm.doc.service_item,
				supplier: frm.doc.supplier,
				posting_date: frm.doc.posting_date,
			},
			callback: (r) => {
				if (r.message) frm.set_value("rate", r.message);
			},
		});
	},

	source_warehouse(frm) {
		(frm.doc.fabrics || []).forEach((row) => update_available_qty(frm, row.doctype, row.name));
	},
});

frappe.ui.form.on("Cutting Slip Fabric", {
	purchase_receipt(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "fabric", "");
	},

	fabric(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "lot_no", "");
	},

	lot_no(frm, cdt, cdn) {
		update_available_qty(frm, cdt, cdn);
	},
});

function update_available_qty(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.lot_no || !frm.doc.source_warehouse) {
		frappe.model.set_value(cdt, cdn, "available_qty", 0);
		return;
	}
	frappe.call({
		method: `${CUTTING_SLIP_METHOD}.get_available_qty`,
		args: { batch_no: row.lot_no, warehouse: frm.doc.source_warehouse },
		callback: (r) => frappe.model.set_value(cdt, cdn, "available_qty", r.message || 0),
	});
}
