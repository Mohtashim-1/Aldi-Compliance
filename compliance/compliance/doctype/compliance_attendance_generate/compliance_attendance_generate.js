// Copyright (c) 2025, mohtashi and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Compliance Attendance Generate", {
// 	refresh(frm) {

// 	},
// });


// frappe.ui.form.on('Compliance Attendance Generate', {
//     refresh: function (frm) {
//         // Add a custom button to fetch employees
//         frm.add_custom_button(__('Fetch Employees'), function () {
//             if (!frm.doc.from_date || !frm.doc.to_date) {
//                 frappe.msgprint(__('Please select From Date and To Date.'));
//                 return;
//             }
            
//             frappe.call({
//                 method: "compliance.compliance.doctype.compliance_attendance_generate.compliance_attendance_generate.get_employees",
//                 args: {
//                     from_date: frm.doc.from_date,
//                     to_date: frm.doc.to_date,
//                 },
//                 callback: function (r) {
//                     if (r.message) {
//                         console.log(r.message)
//                         frm.clear_table("employee"); // Replace 'employees' with your child table fieldname
//                         r.message.forEach(emp => {
//                             console.log("row")
//                             let row = frm.add_child("employee");
//                             row.employee = emp.employee;
//                             console.log(row)
//                             row.employee_name = emp.employee_name; // Assuming you also want the employee name
//                         });
//                         frm.refresh_field("employee");
//                         frappe.msgprint(__('Employees fetched successfully.'));
//                     }
//                 }
//             });
//         });
//     }
// });

frappe.ui.form.on("Compliance Attendance Generate", {
    refresh(frm) {
        // Optional: You can add custom logic here to refresh the form or add actions
    },
    get_data(frm) {
        frm.call({
            method: 'get_employees',
            doc: frm.doc,
            args: {},
            callback: function(r) {
                // Refresh the form after fetching the data
                frm.reload_doc();
            }
        });
    }
});


frappe.ui.form.on("Compliance Attendance Generate", {
    refresh(frm) {
        frm.add_custom_button(__('Generate Attendance'), function() {
            frm.call({
                method: 'generate_attendance',
                doc: frm.doc,
                args: {},
                callback: function(r) {
                    frappe.msgprint(__('Attendance has been generated for all employees.'));
                    frm.reload_doc();  // Reload the form after generating attendance
                }
            });
        });
    }
});
