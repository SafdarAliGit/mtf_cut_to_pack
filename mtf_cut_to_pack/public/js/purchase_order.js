frappe.ui.form.on("Purchase Order", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status !== "Closed") {
			frm.add_custom_button(__("Gate Pass"), () => {
				frappe.model.open_mapped_doc({
					method: "mtf_cut_to_pack.overrides.purchase_order.make_gate_pass",
					frm,
				});
			});
		}
	},
});
