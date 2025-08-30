# Copyright (c) 2025, Compliance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days, get_first_day, get_last_day, get_time
from datetime import datetime, timedelta, time
import random

class FakeAttendanceGenerator(Document):
	def validate(self):
		if self.start_date and self.end_date and getdate(self.start_date) > getdate(self.end_date):
			frappe.throw("Start date must be before end date")

@frappe.whitelist()
def test_method():
	return "Test method is working!"

@frappe.whitelist()
def generate_attendance(name):
	"""Generate fake attendance data for all employees"""
	try:
		doc = frappe.get_doc("Fake Attendance Generator", name)
		
		frappe.msgprint("Starting Fake Attendance Generation Process")
		frappe.msgprint(f"📄 Document: {doc.name}")
		frappe.msgprint(f"📅 Date range: {doc.start_date} to {doc.end_date}")
		frappe.msgprint(f"🏢 Company: {doc.company}")
		frappe.msgprint(f"🏭 Department: {doc.department}")
		frappe.msgprint(f"📅 Include Weekends: {doc.include_weekends}")
		frappe.msgprint(f"🎉 Include Holidays: {doc.include_holidays}")
		
		# Set status to In Progress
		doc.status = "In Progress"
		doc.save()
		frappe.msgprint("✅ Document status set to 'In Progress'")
		
		# Get employees
		employees = _get_employees(doc)
		frappe.msgprint(f"👥 Found {len(employees)} employees")
		
		# Get department configurations
		dept_configs = _get_dept_configs()
		frappe.msgprint(f"⚙️ Found {len(dept_configs)} department configurations")
		
		# Process employees in smaller batches to avoid database locks
		batch_size = 1  # Reduced from 5 to 1 to minimize locks
		total_created = 0
		
		frappe.msgprint(f"🔄 Processing employees in batches of {batch_size}")
		
		for i in range(0, len(employees), batch_size):
			batch = employees[i:i + batch_size]
			batch_num = (i // batch_size) + 1
			total_batches = (len(employees) + batch_size - 1) // batch_size
			
			frappe.msgprint(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} employees)")
			
			for emp in batch:
				try:
					frappe.msgprint(f"👤 Processing employee: {emp.name} ({emp.employee_name})")
					
					# Get configuration for this employee's department
					cfg = dept_configs.get(emp.department, _default_cfg())
					frappe.msgprint(f"🏭 Using config for department: {emp.department}")
					
					# Generate attendance for this employee
					created = _generate_for_employee(doc, emp, cfg)
					total_created += created
					
					frappe.msgprint(f"✅ Generated {created} records for employee {emp.name}")
					
					# Commit after each employee to prevent database locks
					frappe.db.commit()
					frappe.msgprint(f"💾 Committed changes for employee {emp.name}")
					
				except Exception as e:
					frappe.msgprint(f"❌ Error generating for employee {emp.name}: {str(e)}")
					frappe.log_error(f"Error generating for employee {emp.name}: {str(e)}", "Fake Attendance Generator")
					frappe.db.rollback()
					continue
			
			# Commit after each batch
			frappe.db.commit()
			frappe.msgprint(f"💾 Committed batch {batch_num}")
		
		frappe.msgprint(f"📊 Total records created: {total_created}")
		
		# Update Employee Attendance summaries
		frappe.msgprint("🔄 Updating Employee Attendance summaries...")
		_update_employee_attendance_summary(doc)
		
		# Update document status
		doc.status = "Completed"
		doc.generated_records = total_created
		doc.save()
		
		frappe.msgprint(f"🎉 Successfully generated {total_created} attendance records!")
		frappe.msgprint("✅ Process completed successfully!")
		
		return {"status": "success", "records_created": total_created}
		
	except Exception as e:
		frappe.msgprint(f"❌ Error generating attendance: {str(e)}")
		frappe.log_error(f"Error generating attendance: {str(e)}", "Fake Attendance Generator")
		
		# Update document status to failed
		try:
			doc = frappe.get_doc("Fake Attendance Generator", name)
			doc.status = "Failed"
			doc.save()
		except:
			pass
		
		return {"status": "error", "message": str(e)}

def _get_employees(doc):
	# Get active employees
	filters = {"status": "Active"}
	
	if doc.department:
		filters["department"] = doc.department
		frappe.msgprint(f"Filtering by department: {doc.department}")
	
	frappe.msgprint(f"Employee filters: {filters}")
	
	employees = frappe.get_all("Employee", filters=filters, fields=["name", "employee_name", "department", "designation", "biometric_id", "company_email", "date_of_joining", "holiday_list", "branch", "cnic", "image"])
	
	frappe.msgprint(f"Raw employee query returned {len(employees)} employees")
	
	# Debug: Show first few employees
	for i, emp in enumerate(employees[:3]):
		frappe.msgprint(f"Employee {i+1}: {emp.name} - {emp.employee_name} - {emp.department}")
	
	return employees

def _get_dept_configs():
	# Get department-specific configurations
	configs = {}
	try:
		dept_configs = frappe.get_all("Department Attendance Config", fields=["department", "company", "shift_type", "late_arrival_probability", "absent_probability", "overtime_probability", "early_exit_probability", "working_hours", "grace_period_minutes", "overtime_threshold_minutes", "check_in_start_time", "check_in_end_time", "check_out_start_time", "check_out_end_time", "overtime_start_time", "overtime_end_time"])
		
		frappe.msgprint(f"Found {len(dept_configs)} Department Attendance Configs")
		
		for config in dept_configs:
			configs[config.department] = config
			frappe.msgprint(f"Config for {config.department}: Late={config.late_arrival_probability}%, Absent={config.absent_probability}%, OT={config.overtime_probability}%")
		
	except Exception as e:
		frappe.msgprint(f"Error getting department configs: {str(e)}")
		frappe.log_error(f"Error getting department configs: {str(e)}", "Fake Attendance Generator")
	
	return configs

def _default_cfg():
	# Default configuration if no department-specific config exists
	frappe.msgprint("Using default configuration")
	return frappe._dict({
		"late_arrival_probability": 10,
		"absent_probability": 5,
		"overtime_probability": 15,
		"early_exit_probability": 5,
		"working_hours": 8,
		"grace_period_minutes": 15,
		"overtime_threshold_minutes": 30,
		"check_in_start_time": "08:00:00",
		"check_in_end_time": "09:00:00",
		"check_out_start_time": "17:00:00",
		"check_out_end_time": "18:00:00",
		"overtime_start_time": "18:00:00",
		"overtime_end_time": "20:00:00"
	})

def _create_employee_attendance(doc, emp, month_name, year):
	# Create Employee Attendance record for the month
	try:
		# Check if Employee Attendance already exists for this employee and month
		existing_attendance = frappe.get_all(
			"Employee Attendance",
			filters={
				"employee": emp.name,
				"month": month_name,
				"year": year
			},
			limit=1
		)
		
		if existing_attendance:
			frappe.msgprint(f"Employee Attendance already exists for {emp.name} - {month_name} {year}")
			return frappe.get_doc("Employee Attendance", existing_attendance[0].name)
		
		# Prepare employee data WITHOUT image to avoid file issues
		emp_data = {
			"doctype": "Employee Attendance",
			"employee": emp.name,
			"month": month_name,
			"year": year,
			"company": doc.company,
			"department": emp.department,
			"designation": emp.designation,
			"biometric_id": emp.biometric_id,
			"employee_name": emp.employee_name,
			"email_id": emp.company_email,
			"joining_date": emp.date_of_joining,
			"holiday_list": emp.holiday_list,
			"unit": emp.branch,
			"cnic": emp.cnic
			# Intentionally NOT including image field to avoid file errors
		}
		
		emp_attendance = frappe.get_doc(emp_data)
		emp_attendance.insert()
		frappe.msgprint(f"✅ SUCCESS: Created Employee Attendance '{emp_attendance.name}' for {emp.name} - {month_name} {year}")
		return emp_attendance
	except Exception as e:
		frappe.log_error(f"Error creating Employee Attendance for {emp.name}: {str(e)}", "Fake Attendance Generator")
		frappe.msgprint(f"❌ FAILED: Could not create Employee Attendance for {emp.name} - {month_name} {year}: {str(e)}")
		return None

def _add_daily_attendance_to_employee_attendance(emp_attendance, date, check_in_time, check_out_time, is_absent=False):
	# Add daily attendance record to the Employee Attendance table
	try:
		if not emp_attendance.table1:
			emp_attendance.table1 = []
		
		# Calculate total hours worked
		if check_in_time and check_out_time:
			check_in_dt = datetime.combine(date, check_in_time)
			check_out_dt = datetime.combine(date, check_out_time)
			total_hours = (check_out_dt - check_in_dt).total_seconds() / 3600
		else:
			total_hours = 0
		
		daily_record = {
			"date": date,
			"day": date.strftime("%A"),
			"check_in_1": check_in_time.strftime("%H:%M:%S") if check_in_time else "",
			"check_out_1": check_out_time.strftime("%H:%M:%S") if check_out_time else "",
			"difference": f"{int(total_hours):02d}:{int((total_hours % 1) * 60):02d}:00" if total_hours > 0 else "",
			"absent": is_absent,
			"present": not is_absent,
			"weekday": date.weekday() < 5,  # Monday-Friday
			"day_type": "Weekday" if date.weekday() < 5 else "Weekly Off"
		}
		
		emp_attendance.append("table1", daily_record)
		frappe.msgprint(f"📝 Added daily attendance for {date}: Check-in={check_in_time}, Check-out={check_out_time}, Absent={is_absent}")
		
	except Exception as e:
		frappe.msgprint(f"❌ Error adding daily attendance for {date}: {str(e)}")
		frappe.log_error(f"Error adding daily attendance for {date}: {str(e)}", "Fake Attendance Generator")

def _generate_for_employee(doc, emp, cfg):
	created = 0
	current_date = getdate(doc.start_date)
	end_date = getdate(doc.end_date)
	
	frappe.msgprint(f"🔍 Generating for employee {emp.name} from {current_date} to {end_date}")
	frappe.msgprint(f"📊 Config: Late={cfg.late_arrival_probability}%, Absent={cfg.absent_probability}%, OT={cfg.overtime_probability}%")
	
	# Limit the number of days to prevent database overload
	max_days = min((end_date - current_date).days + 1, 30)  # Max 30 days at a time
	days_processed = 0
	
	frappe.msgprint(f"📅 Max days to process: {max_days}")
	
	# Track months for Employee Attendance creation
	months_created = set()
	current_emp_attendance = None
	
	while current_date <= end_date and days_processed < max_days:
		frappe.msgprint(f"📆 Processing date: {current_date} (day {days_processed + 1}/{max_days})")
		
		# Skip weekends if configured
		if not doc.include_weekends and current_date.weekday() >= 5:
			frappe.msgprint(f"🏖️ Skipping weekend: {current_date}")
			current_date = add_days(current_date, 1)
			continue
		
		# Skip holidays if configured
		if not doc.include_holidays:
			# Check if it's a holiday (you can add holiday checking logic here)
			pass
		
		# Create Employee Attendance for this month if not already created
		month_name = current_date.strftime("%B")
		year = current_date.year
		month_key = f"{month_name}_{year}"
		
		if month_key not in months_created:
			frappe.msgprint(f"📋 Creating Employee Attendance for {month_name} {year}")
			current_emp_attendance = _create_employee_attendance(doc, emp, month_name, year)
			if current_emp_attendance:
				months_created.add(month_key)
				frappe.msgprint(f"✅ Employee Attendance ready for {month_name} {year}")
			else:
				frappe.msgprint(f"❌ Failed to create Employee Attendance for {month_name} {year}")
		
		# Randomly determine if employee is absent
		absent_roll = random.randint(1, 100)
		frappe.msgprint(f"🎲 Absent roll: {absent_roll} vs threshold: {cfg.absent_probability}")
		
		if absent_roll <= cfg.absent_probability:
			frappe.msgprint(f"🏠 Creating Leave Application for {current_date}")
			_create_leave_application(doc, emp, current_date)
			# Add absent record to Employee Attendance
			if current_emp_attendance:
				_add_daily_attendance_to_employee_attendance(current_emp_attendance, current_date, None, None, is_absent=True)
		else:
			# Generate check-in and check-out times
			frappe.msgprint(f"⏰ Creating Attendance Logs for {current_date}")
			check_in_time, check_out_time = _generate_times(cfg)
			frappe.msgprint(f"🕐 Generated times: Check-in={check_in_time}, Check-out={check_out_time}")
			logs_created = _create_attendance_logs(doc, emp, current_date, check_in_time, check_out_time)
			created += logs_created
			
			# Add present record to Employee Attendance
			if current_emp_attendance:
				_add_daily_attendance_to_employee_attendance(current_emp_attendance, current_date, check_in_time, check_out_time, is_absent=False)
		
		created += 1
		days_processed += 1
		current_date = add_days(current_date, 1)
	
	# Save the Employee Attendance document with all daily records
	if current_emp_attendance:
		try:
			current_emp_attendance.save()
			frappe.msgprint(f"💾 Saved Employee Attendance '{current_emp_attendance.name}' with {len(current_emp_attendance.table1)} daily records")
		except Exception as e:
			frappe.msgprint(f"❌ Error saving Employee Attendance: {str(e)}")
			frappe.log_error(f"Error saving Employee Attendance: {str(e)}", "Fake Attendance Generator")
	
	frappe.msgprint(f"📈 Total records created for employee {emp.name}: {created}")
	return created

def _get_months_in_range(start_date, end_date):
	months = []
	current = get_first_day(start_date)
	while current <= end_date:
		months.append(current)
		# Move to next month
		if current.month == 12:
			current = current.replace(year=current.year + 1, month=1)
		else:
			current = current.replace(month=current.month + 1)
	return months

def _get_or_create_employee_attendance(doc, emp, month, year):
	# Check if Employee Attendance exists for this month
	existing = frappe.get_all(
		"Employee Attendance",
		filters={
			"employee": emp.name,
			"month": month,
			"year": year
		},
		limit=1
	)
	
	if existing:
		return frappe.get_doc("Employee Attendance", existing[0].name)
	else:
		# Create new Employee Attendance
		emp_attendance_doc = frappe.get_doc({
			"doctype": "Employee Attendance",
			"employee": emp.name,
			"month": month,
			"year": year,
			"company": doc.company
		})
		emp_attendance_doc.insert()
		return emp_attendance_doc

def _generate_times(cfg):
	# Generate random check-in and check-out times based on configuration
	check_in_start = get_time(cfg.check_in_start_time)
	check_in_end = get_time(cfg.check_in_end_time)
	check_out_start = get_time(cfg.check_out_start_time)
	check_out_end = get_time(cfg.check_out_end_time)
	
	# Generate random check-in time
	check_in_time = _random_time(check_in_start, check_in_end)
	
	# Generate random check-out time (after check-in)
	check_out_time = _random_time(check_out_start, check_out_end)
	
	return check_in_time, check_out_time

def _random_time(start_time, end_time):
	# Generate a random time between start_time and end_time
	start_minutes = start_time.hour * 60 + start_time.minute
	end_minutes = end_time.hour * 60 + end_time.minute
	
	random_minutes = random.randint(start_minutes, end_minutes)
	hours = random_minutes // 60
	minutes = random_minutes % 60
	
	return time(hours, minutes)

def _create_leave_application(doc, emp, date):
	# Create Leave Application for absent days
	# Try to get leave types without the is_active filter first
	try:
		leave_types = frappe.get_all("Leave Type", limit=1)
	except:
		# If that fails, try without any filters
		leave_types = frappe.db.sql("SELECT name FROM `tabLeave Type` LIMIT 1", as_dict=True)
	
	if leave_types:
		leave_type = leave_types[0].name
		
		# Check if allocation already exists for this period
		try:
			existing_allocation = frappe.get_all(
				"Leave Allocation",
				filters={
					"employee": emp.name,
					"leave_type": leave_type,
					"from_date": ["<=", date],
					"to_date": [">=", date]
				},
				limit=1
			)
			
			if not existing_allocation:
				# Check if there's already an allocation for this year
				year_allocation = frappe.get_all(
					"Leave Allocation",
					filters={
						"employee": emp.name,
						"leave_type": leave_type,
						"from_date": ["<=", getdate(f"{date.year}-12-31")],
						"to_date": [">=", getdate(f"{date.year}-01-01")]
					},
					limit=1
				)
				
				if not year_allocation:
					# Create a leave allocation for this period (covering the entire year)
					year_start = getdate(f"{date.year}-01-01")
					year_end = getdate(f"{date.year}-12-31")
					
					allocation_doc = frappe.get_doc({
						"doctype": "Leave Allocation",
						"employee": emp.name,
						"leave_type": leave_type,
						"from_date": year_start,
						"to_date": year_end,
						"new_leaves_allocated": 10,  # Reduced to 10 days to avoid max allocation error
						"company": doc.company,
						"description": "Auto-generated for fake attendance"
					})
					allocation_doc.insert()
					allocation_doc.submit()
					frappe.msgprint(f"Created Leave Allocation for {emp.name} for {date.year}")
				else:
					frappe.msgprint(f"Leave Allocation already exists for {emp.name} for {date.year}")
		except Exception as e:
			# If allocation creation fails, continue without it
			frappe.msgprint(f"Could not create Leave Allocation for {emp.name}: {str(e)}")
		
		# Create the leave application with "Open" status instead of "Draft"
		leave_doc = frappe.get_doc({
			"doctype": "Leave Application",
			"employee": emp.name,
			"leave_type": leave_type,
			"from_date": date,
			"to_date": date,
			"half_day": 0,
			"company": doc.company,
			"status": "Open",  # Changed from "Draft" to "Open"
			"description": "Auto-generated for fake attendance"
		})
		
		try:
			leave_doc.insert()
			frappe.msgprint(f"✅ SUCCESS: Created Leave Application '{leave_doc.name}' for {emp.name} on {date}")
		except Exception as e:
			# If creation fails, log the error but continue
			frappe.msgprint(f"❌ FAILED: Could not create Leave Application for {emp.name} on {date}: {str(e)}")
			frappe.log_error(f"Failed to create Leave Application for {emp.name} on {date}: {str(e)}", "Fake Attendance Generator")
	else:
		frappe.msgprint("No Leave Type found to create Leave Application")

def _create_attendance_logs(doc, emp, date, check_in_time, check_out_time):
	# Create Attendance Logs for check-in and check-out
	logs_created = 0
	biometric_id = emp.biometric_id or "505"  # Default biometric ID
	
	try:
		# Create check-in log
		check_in_attendance_string = f" : {biometric_id} : {date} {check_in_time.strftime('%H:%M:%S')} (1, 0)"
		frappe.msgprint(f"Creating check-in log with attendance string: {check_in_attendance_string}")
		
		check_in_log = frappe.get_doc({
			"doctype": "Attendance Logs",
			"employee": emp.name,
			"employee_name": emp.employee_name,
			"attendance_date": date,
			"attendance_time": check_in_time,
			"attendance": check_in_attendance_string,
			"company": doc.company,
			"department": emp.department,
			"designation": emp.designation,
			"biometric_id": biometric_id,
			"log_type": "Check In"
		})
		
		# Retry logic for database locks
		max_retries = 3
		for attempt in range(max_retries):
			try:
				check_in_log.insert()
				frappe.msgprint(f"✅ SUCCESS: Created check-in log '{check_in_log.name}' for {emp.name} on {date} at {check_in_time}")
				logs_created += 1
				break
			except Exception as e:
				if "Lock wait timeout" in str(e) and attempt < max_retries - 1:
					frappe.msgprint(f"⚠️ Database lock timeout, retrying check-in log (attempt {attempt + 1}/{max_retries})")
					time.sleep(0.5)  # Wait longer between retries
					frappe.db.rollback()
				else:
					frappe.msgprint(f"❌ FAILED: Could not create check-in log for {emp.name} on {date} after retry: {str(e)}")
					frappe.log_error(f"Failed to create check-in log for {emp.name} on {date} after retry: {str(e)}", "Fake Attendance Generator")
					break
		
		# Create check-out log
		check_out_attendance_string = f" : {biometric_id} : {date} {check_out_time.strftime('%H:%M:%S')} (0, 1)"
		frappe.msgprint(f"Creating check-out log with attendance string: {check_out_attendance_string}")
		
		check_out_log = frappe.get_doc({
			"doctype": "Attendance Logs",
			"employee": emp.name,
			"employee_name": emp.employee_name,
			"attendance_date": date,
			"attendance_time": check_out_time,
			"attendance": check_out_attendance_string,
			"company": doc.company,
			"department": emp.department,
			"designation": emp.designation,
			"biometric_id": biometric_id,
			"log_type": "Check Out"
		})
		
		# Retry logic for database locks
		for attempt in range(max_retries):
			try:
				check_out_log.insert()
				frappe.msgprint(f"✅ SUCCESS: Created check-out log '{check_out_log.name}' for {emp.name} on {date} at {check_out_time}")
				logs_created += 1
				break
			except Exception as e:
				if "Lock wait timeout" in str(e) and attempt < max_retries - 1:
					frappe.msgprint(f"⚠️ Database lock timeout, retrying check-out log (attempt {attempt + 1}/{max_retries})")
					time.sleep(0.5)  # Wait longer between retries
					frappe.db.rollback()
				else:
					frappe.msgprint(f"❌ FAILED: Could not create check-out log for {emp.name} on {date} after retry: {str(e)}")
					frappe.log_error(f"Failed to create check-out log for {emp.name} on {date} after retry: {str(e)}", "Fake Attendance Generator")
					break
		
		frappe.msgprint(f"📊 RESULT: Created {logs_created} attendance logs for {emp.name} on {date}")
		return logs_created
		
	except Exception as e:
		frappe.msgprint(f"❌ Error creating attendance logs for {emp.name} on {date}: {str(e)}")
		frappe.log_error(f"Error creating attendance logs for {emp.name} on {date}: {str(e)}", "Fake Attendance Generator")
		return logs_created

def _update_employee_attendance_summary(doc):
	# This function updates Employee Attendance summaries for the generated period
	# Employee Attendance uses month and year fields, not attendance_date
	
	start_date = getdate(doc.start_date)
	end_date = getdate(doc.end_date)
	
	frappe.msgprint(f"📋 Updating Employee Attendance summaries for period: {start_date} to {end_date}")
	
	# Get all Employee Attendance records for the period
	employee_attendances = frappe.get_all(
		"Employee Attendance",
		filters={
			"month": ["in", ["January", "February", "March", "April", "May", "June", 
							 "July", "August", "September", "October", "November", "December"]],
			"year": ["between", [start_date.year, end_date.year]],
			"docstatus": 0  # Only unsubmitted/draft
		},
		fields=["name", "employee", "month", "year"]
	)
	
	frappe.msgprint(f"📊 Found {len(employee_attendances)} Employee Attendance records to update")
	
	for emp_attendance_doc in employee_attendances:
		try:
			frappe.msgprint(f"🔄 Updating Employee Attendance: {emp_attendance_doc.name}")
			emp_attendance = frappe.get_doc("Employee Attendance", emp_attendance_doc.name)
			
			# Calculate summary for the month
			month_num = {
				"January": 1, "February": 2, "March": 3, "April": 4,
				"May": 5, "June": 6, "July": 7, "August": 8,
				"September": 9, "October": 10, "November": 11, "December": 12
			}[emp_attendance.month]
			
			month_start = get_first_day(getdate(f"{emp_attendance.year}-{month_num:02d}-01"))
			month_end = get_last_day(month_start)
			
			# Count present days, absents, etc. for this month
			total_working_days = (month_end - month_start).days + 1
			present_days = random.randint(int(total_working_days * 0.8), total_working_days - 2)  # 80-95% present
			total_absents = total_working_days - present_days
			hours_worked = present_days * 8  # Assuming 8 hours per day
			
			frappe.msgprint(f"📈 Summary for {emp_attendance.month} {emp_attendance.year}: Present={present_days}, Absent={total_absents}, Hours={hours_worked}")
			
			# Update the Employee Attendance record
			emp_attendance.present_days = str(present_days)
			emp_attendance.total_absents = str(total_absents)
			emp_attendance.total_working_days = str(total_working_days)
			emp_attendance.hours_worked = str(hours_worked)
			emp_attendance.save()
			
			frappe.msgprint(f"✅ Updated Employee Attendance: {emp_attendance.name}")
			
		except Exception as e:
			frappe.log_error(f"Error updating Employee Attendance {emp_attendance_doc.name}: {str(e)}", "Fake Attendance Generator")
			frappe.msgprint(f"❌ Failed to update Employee Attendance {emp_attendance_doc.name}: {str(e)}")
			continue
	
	frappe.msgprint(f"✅ Employee Attendance summaries update completed")
