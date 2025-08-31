// Copyright (c) 2025, mohtashi and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fake Attendance Generator', {
	refresh: function(frm) {
		// Add Generate Attendance button
		frm.add_custom_button(__('Generate Attendance'), function() {
			frm.call({
				method: 'compliance.compliance.doctype.fake_attendance_generator.fake_attendance_generator.generate_attendance',
				args: {
					name: frm.doc.name
				},
				callback: function(r) {
					if (r.message && r.message.status === 'queued') {
						frappe.msgprint({
							title: __('Background Job Queued'),
							message: __('The attendance generation has been queued as a background job. You can check the status using the "Check Status" button.'),
							indicator: 'green'
						});
						// Start polling for status updates
						startStatusPolling(frm);
					} else {
						frappe.msgprint({
							title: __('Error'),
							message: r.message ? r.message.message : 'Unknown error occurred',
							indicator: 'red'
						});
					}
				}
			});
		}, __('Actions'));

		// Add Check Status button
		frm.add_custom_button(__('Check Status'), function() {
			checkGenerationStatus(frm);
		}, __('Actions'));

		// Add Cancel Generation button (only show if running)
		if (frm.doc.status === 'In Progress') {
			frm.add_custom_button(__('Cancel Generation'), function() {
				frappe.confirm(
					__('Are you sure you want to cancel the attendance generation?'),
					function() {
						frm.call({
							method: 'compliance.compliance.doctype.fake_attendance_generator.fake_attendance_generator.cancel_generation',
							args: {
								doc_name: frm.doc.name
							},
							callback: function(r) {
								if (r.message && r.message.status === 'cancelled') {
									frappe.msgprint({
										title: __('Cancelled'),
										message: __('Attendance generation has been cancelled.'),
										indicator: 'orange'
									});
									frm.reload_doc();
								} else {
									frappe.msgprint({
										title: __('Error'),
										message: r.message ? r.message.message : 'Failed to cancel generation',
										indicator: 'red'
									});
								}
							}
						});
					}
				);
			}, __('Actions'));
		}

		// Add View buttons
		frm.add_custom_button(__('View Employee Attendance'), function() {
			frappe.set_route('List', 'Employee Attendance');
		}, __('View'));

		frm.add_custom_button(__('View Leave Applications'), function() {
			frappe.set_route('List', 'Leave Application');
		}, __('View'));

		frm.add_custom_button(__('View Attendance Logs'), function() {
			frappe.set_route('List', 'Attendance Logs');
		}, __('View'));

		// Show status information
		if (frm.doc.status && frm.doc.status !== 'Draft') {
			showStatusInfo(frm);
		}

		// Listen for real-time completion events
		frappe.realtime.on('fake_attendance_completed', function(data) {
			if (data.doc_name === frm.doc.name) {
				frappe.msgprint({
					title: data.title,
					message: data.message,
					indicator: 'green'
				});
				frm.reload_doc();
			}
		});
	}
});

function checkGenerationStatus(frm) {
	frm.call({
		method: 'compliance.compliance.doctype.fake_attendance_generator.fake_attendance_generator.get_generation_status',
		args: {
			doc_name: frm.doc.name
		},
		callback: function(r) {
			if (r.message) {
				const status = r.message;
				let message = `Status: ${status.status}\n`;
				message += `Generated Records: ${status.generated_records || 0}\n`;
				if (status.generation_log) {
					message += `\nLog: ${status.generation_log}`;
				}
				if (status.modified) {
					message += `\nLast Updated: ${status.modified}`;
				}

				frappe.msgprint({
					title: __('Generation Status'),
					message: message,
					indicator: getStatusIndicator(status.status)
				});

				// Reload the form to show updated status
				frm.reload_doc();
			}
		}
	});
}

function showStatusInfo(frm) {
	const statusColors = {
		'In Progress': 'orange',
		'Completed': 'green',
		'Failed': 'red'
	};

	const statusMessages = {
		'In Progress': 'Background job is currently running.',
		'Completed': 'Attendance generation completed successfully.',
		'Failed': 'Attendance generation failed. Check the logs for details.'
	};

	const color = statusColors[frm.doc.status] || 'gray';
	let message = statusMessages[frm.doc.status] || '';
	
	// Check if it was cancelled
	if (frm.doc.status === 'Failed' && frm.doc.generation_log && frm.doc.generation_log.includes('Cancelled')) {
		message = 'Attendance generation was cancelled by user.';
	}

	if (message) {
		frm.dashboard.add_comment(
			`<div class="alert alert-${color}">
				<strong>Status:</strong> ${frm.doc.status}<br>
				${message}<br>
				${frm.doc.generated_records ? `<strong>Records Generated:</strong> ${frm.doc.generated_records}<br>` : ''}
				${frm.doc.generation_log ? `<strong>Log:</strong> ${frm.doc.generation_log}` : ''}
			</div>`,
			'blue'
		);
	}
}

function getStatusIndicator(status) {
	const indicators = {
		'In Progress': 'orange',
		'Completed': 'green',
		'Failed': 'red'
	};
	return indicators[status] || 'gray';
}

function startStatusPolling(frm) {
	// Poll for status updates every 5 seconds
	const pollInterval = setInterval(function() {
		frm.call({
			method: 'compliance.compliance.doctype.fake_attendance_generator.fake_attendance_generator.get_generation_status',
			args: {
				doc_name: frm.doc.name
			},
			callback: function(r) {
				if (r.message && r.message.status) {
					const status = r.message.status;
					
					// Update the form status
					frm.set_value('status', status);
					if (r.message.generated_records) {
						frm.set_value('generated_records', r.message.generated_records);
					}
					if (r.message.generation_log) {
						frm.set_value('generation_log', r.message.generation_log);
					}
					
					// Stop polling if job is completed or failed
					if (['Completed', 'Failed'].includes(status)) {
						clearInterval(pollInterval);
						
						// Show final message
						if (status === 'Completed') {
							frappe.msgprint({
								title: __('Generation Completed'),
								message: `Successfully generated ${r.message.generated_records || 0} attendance records!`,
								indicator: 'green'
							});
						} else if (status === 'Failed' && r.message.generation_log && r.message.generation_log.includes('Cancelled')) {
							frappe.msgprint({
								title: __('Generation Cancelled'),
								message: 'Attendance generation was cancelled by user.',
								indicator: 'orange'
							});
						}
					}
				}
			}
		});
	}, 5000); // Poll every 5 seconds

	// Store the interval ID so we can clear it if needed
	frm.statusPollInterval = pollInterval;
}
