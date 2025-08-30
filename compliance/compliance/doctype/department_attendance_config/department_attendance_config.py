# Copyright (c) 2025, Compliance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DepartmentAttendanceConfig(Document):
	def validate(self):
		self._validate_probability_fields()
		self._validate_times()
	
	def _validate_probability_fields(self):
		"""Validate that probabilities are within valid range (0-100)"""
		probabilities = [
			self.late_arrival_probability,
			self.absent_probability,
			self.overtime_probability,
			self.early_exit_probability
		]
		
		for prob in probabilities:
			# Convert to float to handle string values
			try:
				prob_value = float(prob) if prob is not None else 0
			except (ValueError, TypeError):
				prob_value = 0
			
			if prob_value < 0 or prob_value > 100:
				frappe.throw("All probabilities must be between 0 and 100")
	
	def _validate_times(self):
		"""Validate that time ranges are logical"""
		from frappe.utils import get_time
		
		# Check-in times
		check_in_start = get_time(self.check_in_start_time)
		check_in_end = get_time(self.check_in_end_time)
		
		if check_in_start >= check_in_end:
			frappe.throw("Check-in start time must be before check-in end time")
		
		# Check-out times
		check_out_start = get_time(self.check_out_start_time)
		check_out_end = get_time(self.check_out_end_time)
		
		if check_out_start >= check_out_end:
			frappe.throw("Check-out start time must be before check-out end time")
		
		# Overtime times
		overtime_start = get_time(self.overtime_start_time)
		overtime_end = get_time(self.overtime_end_time)
		
		if overtime_start >= overtime_end:
			frappe.throw("Overtime start time must be before overtime end time")
		
		# Ensure check-in end is before check-out start
		if check_in_end >= check_out_start:
			frappe.throw("Check-in end time should be before check-out start time")
