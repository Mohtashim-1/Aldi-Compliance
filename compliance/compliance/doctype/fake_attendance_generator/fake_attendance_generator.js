// Copyright (c) 2025, mohtashi and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fake Attendance Generator', {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			
			frm.add_custom_button(__('Generate Attendance'), () => {
				frappe.call({
					method: 'compliance.compliance.doctype.fake_attendance_generator.fake_attendance_generator.generate_attendance',
					args: {
						name: frm.doc.name
					},
					freeze: true,
					freeze_message: __('Generating attendance...'),
				}).then((r) => {
					frappe.msgprint(r.message);
					frm.reload_doc();
				});
			}).addClass('btn-primary');
		}
		if (frm.doc.status === 'Completed' && frm.doc.generated_records) {
			frm.add_custom_button(__('View Employee Attendance'), () => {
				frappe.set_route('List', 'Employee Attendance');
			}).addClass('btn-secondary');
			
			frm.add_custom_button(__('View Leave Applications'), () => {
				frappe.set_route('List', 'Leave Application', {
					from_date: ['between', [frm.doc.start_date, frm.doc.end_date]]
				});
			}).addClass('btn-secondary');
			
			frm.add_custom_button(__('View Attendance Logs'), () => {
				frappe.set_route('List', 'Attendance Logs', {
					attendance_date: ['between', [frm.doc.start_date, frm.doc.end_date]]
				});
			}).addClass('btn-secondary');
		}
	}
});
