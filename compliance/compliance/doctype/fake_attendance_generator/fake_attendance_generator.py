# Copyright (c) 2025, Compliance and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, time, timedelta
import random
from frappe.utils import getdate, add_days, get_time
from frappe.model.document import Document

def log_message(message, level="info", show_user=True):
	"""
	Custom logging function with different levels and options
	
	Args:
		message (str): The message to log
		level (str): "info", "error", "success", "warning"
		show_user (bool): Whether to show message to user
	"""
	
	# Always log to error log for errors (with shorter messages)
	if level == "error":
		# Truncate long error messages to avoid character length issues
		short_message = message[:100] + "..." if len(message) > 100 else message
		try:
			frappe.log_error(short_message, "Fake Attendance Generator")
		except Exception:
			# If error logging fails, just print to console to avoid cascading errors
			print(f"[ERROR] Failed to log error: {short_message}")
	
	# Show user messages based on level
	if show_user:
		if level == "success":
			frappe.msgprint(f"✅ {message}", indicator="green")
		elif level == "error":
			frappe.msgprint(f"❌ {message}", indicator="red")
		elif level == "warning":
			frappe.msgprint(f"⚠️ {message}", indicator="orange")
		else:
			frappe.msgprint(f"ℹ️ {message}", indicator="blue")
	
	# Also print to console for debugging
	print(f"[{level.upper()}] {message}")

class FakeAttendanceGenerator(Document):
	def validate(self):
		if self.start_date and self.end_date and getdate(self.start_date) > getdate(self.end_date):
			frappe.throw("Start date must be before end date")

@frappe.whitelist()
def test_method():
	return "Test method is working!"

@frappe.whitelist()
def generate_attendance(name):
	"""Generate fake attendance data for all employees as background job"""
	try:
		doc = frappe.get_doc("Fake Attendance Generator", name)
		
		# Set status to In Progress
		doc.status = "In Progress"
		doc.save()
		
		log_message("🚀 Starting Fake Attendance Generation as Background Job...", "info")
		log_message(f"📄 Document: {doc.name}", "info")
		log_message(f"📅 Date range: {doc.start_date} to {doc.end_date}", "info")
		log_message(f"🏢 Company: {doc.company}", "info")
		log_message(f"🏭 Department: {doc.department or 'All Departments'}", "info")
		log_message("⏳ This will run in the background. You can check the status later.", "info")
		
		# Enqueue the background job
		frappe.enqueue(
			method="compliance.compliance.doctype.fake_attendance_generator.fake_attendance_generator.generate_attendance_background",
			doc_name=name,
			queue="long",
			timeout=3600,  # 1 hour timeout
			job_name=f"Generate Fake Attendance - {doc.name}",
			now=False
		)
		
		return {"status": "queued", "message": "Background job queued successfully"}
		
	except Exception as e:
		log_message(f"❌ Error queuing background job: {str(e)}", "error")
		
		# Update document status to failed
		try:
			doc = frappe.get_doc("Fake Attendance Generator", name)
			doc.status = "Failed"
			doc.save()
		except:
			pass
		
		return {"status": "error", "message": str(e)}

def generate_attendance_background(doc_name):
	"""Background job to generate fake attendance"""
	try:
		doc = frappe.get_doc("Fake Attendance Generator", doc_name)
		
		# Update status to running
		doc.status = "In Progress"
		doc.generation_log = "🚀 Starting attendance generation..."
		doc.save()
		
		log_message("🚀 Starting Fake Attendance Generation as Background Job...", "info")
		log_message(f"📄 Document: {doc.name}", "info")
		log_message(f"📅 Date range: {doc.start_date} to {doc.end_date}", "info")
		log_message(f"🏢 Company: {doc.company}", "info")
		log_message(f"🏭 Department: {doc.department}", "info")
		log_message("⏳ This will run in the background. You can check the status later.", "info")
		
		# Get employees
		employees = _get_employees(doc)
		log_message(f"👥 Found {len(employees)} employees to process", "info")
		
		# Get department configurations
		dept_configs = _get_dept_configs()
		log_message(f"⚙️ Found {len(dept_configs)} department configurations", "info")
		
		# Calculate total days to process
		start_date = getdate(doc.start_date)
		end_date = getdate(doc.end_date)
		total_days = (end_date - start_date).days + 1
		log_message(f"📅 Total days to process: {total_days}", "info")
		
		# Process employees
		total_created = 0
		processed_employees = 0
		
		for emp in employees:
			try:
				log_message(f"👤 Processing employee: {emp.name} ({emp.employee_name}) - {emp.department}", "info")
				
				# Get configuration for this employee's department
				cfg = dept_configs.get(emp.department, _default_cfg())
				log_message(f"⚙️ Using config for department: {emp.department}", "info")
				
				# Generate attendance for this employee
				created = _generate_for_employee_fast(doc, emp, cfg)
				log_message(f"✅ Employee {emp.name}: Created {created} records", "info")
				
				total_created += created
				processed_employees += 1
				
				# Update progress in the document
				doc.generation_log = f"Processed {processed_employees}/{len(employees)} employees. Created {total_created} records for {total_days} days ({start_date} to {end_date})."
				doc.save()
				
				# Commit after each employee
				frappe.db.commit()
				
			except Exception as e:
				log_message(f"❌ Error for employee {emp.name}: {str(e)}", "error")
				frappe.db.rollback()
				continue
		
		# Update final status
		doc.status = "Completed"
		doc.generated_records = total_created
		doc.generation_log = f"✅ Completed! Generated {total_created} attendance records for {processed_employees} employees across {total_days} days ({start_date} to {end_date})."
		doc.save()
		
		log_message(f"🎉 Generation completed! Total: {total_created} records for {processed_employees} employees", "success")
		
		# Send notification
		frappe.publish_realtime(
			event="fake_attendance_completed",
			message={
				"title": "Fake Attendance Generation Completed",
				"message": f"Successfully generated {total_created} attendance records for {processed_employees} employees across {total_days} days.",
				"doc_name": doc_name
			},
			user=doc.owner
		)
		
		return {"status": "success", "records_created": total_created, "employees_processed": processed_employees}
		
	except Exception as e:
		log_message(f"❌ Background job error: {str(e)}", "error")
		
		# Update document status to failed
		try:
			doc = frappe.get_doc("Fake Attendance Generator", doc_name)
			doc.status = "Failed"
			doc.generation_log = f"❌ Failed: {str(e)}"
			doc.save()
		except:
			pass
		
		return {"status": "error", "message": str(e)}

@frappe.whitelist()
def get_generation_status(doc_name):
	"""Get the current status of the background job"""
	try:
		doc = frappe.get_doc("Fake Attendance Generator", doc_name)
		return {
			"status": doc.status,
			"generated_records": doc.generated_records or 0,
			"generation_log": doc.generation_log or "",
			"modified": doc.modified
		}
	except Exception as e:
		return {"status": "error", "message": str(e)}

@frappe.whitelist()
def cancel_generation(doc_name):
	"""Cancel the background job"""
	try:
		doc = frappe.get_doc("Fake Attendance Generator", doc_name)
		
		if doc.status == "In Progress":
			# Cancel the job by setting status to Failed with cancellation message
			frappe.db.set_value("Fake Attendance Generator", doc_name, "status", "Failed")
			frappe.db.set_value("Fake Attendance Generator", doc_name, "generation_log", "Cancelled by user")
			
			log_message("✅ Generation cancelled successfully", "success")
			return {"status": "cancelled"}
		else:
			log_message("❌ Cannot cancel - job is not running", "warning")
			return {"status": "error", "message": "Job is not running"}
			
	except Exception as e:
		log_message(f"❌ Error cancelling generation: {str(e)}", "error")
		return {"status": "error", "message": str(e)}

def _get_employees(doc):
	# Get active employees with minimal fields
	try:
		log_message("🔍 Getting employees...", "info")
		
		filters = {"status": "Active"}
		
		if doc.department:
			filters["department"] = doc.department
			log_message(f"📋 Filtering by department: {doc.department}", "info")
		
		log_message(f"🔍 Employee filters: {filters}", "info")
		
		employees = frappe.get_all("Employee", filters=filters, fields=["name", "employee_name", "department", "designation", "biometric_id", "company_email", "date_of_joining", "holiday_list", "branch", "cnic"])
		
		log_message(f"✅ Found {len(employees)} employees", "info")
		
		for i, emp in enumerate(employees):
			log_message(f"👤 Employee {i+1}: {emp.name} - {emp.employee_name} - {emp.department}", "info")
		
		return employees
		
	except Exception as e:
		log_message(f"❌ Error getting employees: {str(e)}", "error")
		return []

def _get_dept_configs():
	# Get department-specific configurations
	configs = {}
	try:
		dept_configs = frappe.get_all("Department Attendance Config", fields=[
			"department", 
			"late_arrival_probability", 
			"absent_probability", 
			"overtime_probability", 
			"early_exit_probability",
			"check_in_start_time", 
			"check_in_end_time", 
			"check_out_start_time", 
			"check_out_end_time",
			"overtime_start_time",
			"overtime_end_time",
			"working_hours"
		])
		
		log_message(f"📋 Found {len(dept_configs)} department configurations", "info")
		
		for config in dept_configs:
			configs[config.department] = config
			log_message(f"✅ Config for {config.department}: Late={config.late_arrival_probability}%, Absent={config.absent_probability}%", "info")
		
	except Exception as e:
		log_message(f"❌ Error getting department configs: {str(e)}", "error")
	
	return configs

def _default_cfg():
	# Default configuration if no department-specific config exists
	return frappe._dict({
		"late_arrival_probability": 10,
		"absent_probability": 5,
		"overtime_probability": 15,
		"check_in_start_time": "08:00:00",
		"check_in_end_time": "09:00:00",
		"check_out_start_time": "17:00:00",
		"check_out_end_time": "18:00:00"
	})

def _create_employee_attendance_fast(doc, emp, month_name, year):
	try:
		log_message(f"Creating Employee Attendance for {emp.name} - {month_name} {year}", "info")
		
		# Check if exists
		existing = frappe.get_all(
			"Employee Attendance",
			filters={"employee": emp.name, "month": month_name, "year": year},
			limit=1
		)
		
		if existing:
			log_message(f"Employee Attendance already exists: {existing[0].name}", "info")
			return frappe.get_doc("Employee Attendance", existing[0].name)
		
		# Create new with only essential fields
		emp_data = {
			"doctype": "Employee Attendance",
			"employee": emp.name,
			"month": month_name,
			"year": year,
			"company": doc.company
		}
		
		# Add optional fields only if they exist
		if hasattr(emp, 'department') and emp.department:
			emp_data["department"] = emp.department
		if hasattr(emp, 'designation') and emp.designation:
			emp_data["designation"] = emp.designation
		if hasattr(emp, 'biometric_id') and emp.biometric_id:
			emp_data["biometric_id"] = emp.biometric_id
		if hasattr(emp, 'employee_name') and emp.employee_name:
			emp_data["employee_name"] = emp.employee_name
		if hasattr(emp, 'company_email') and emp.company_email:
			emp_data["email_id"] = emp.company_email
		if hasattr(emp, 'date_of_joining') and emp.date_of_joining:
			emp_data["joining_date"] = emp.date_of_joining
		if hasattr(emp, 'holiday_list') and emp.holiday_list:
			emp_data["holiday_list"] = emp.holiday_list
		if hasattr(emp, 'branch') and emp.branch:
			emp_data["unit"] = emp.branch
		if hasattr(emp, 'cnic') and emp.cnic:
			emp_data["cnic"] = emp.cnic
		
		log_message(f"Creating Employee Attendance with data: {emp_data}", "info")
		
		emp_attendance = frappe.get_doc(emp_data)
		emp_attendance.insert()
		
		log_message(f"✅ Successfully created Employee Attendance: {emp_attendance.name}", "success")
		return emp_attendance
		
	except Exception as e:
		log_message(f"❌ Error creating Employee Attendance: {str(e)}", "error")
		return None

def _add_daily_attendance_fast(emp_attendance_name, date, check_in_time, check_out_time, is_absent):
	try:
		# Get a fresh copy of the document to avoid modification conflicts
		emp_attendance = frappe.get_doc("Employee Attendance", emp_attendance_name)
		
		# Check if exists
		existing_record = None
		for record in emp_attendance.table1:
			if record.date == date:
				existing_record = record
				break
		
		# Calculate hours
		total_hours = 0
		if check_in_time and check_out_time:
			check_in_dt = datetime.combine(date, check_in_time)
			check_out_dt = datetime.combine(date, check_out_time)
			total_hours = (check_out_dt - check_in_dt).total_seconds() / 3600
		
		# Prepare daily record data with correct field names
		daily_record_data = {
			"date": date,
			"day": date.strftime("%A"),
			"check_in_1": check_in_time.strftime("%H:%M:%S") if check_in_time else "",
			"check_out_1": check_out_time.strftime("%H:%M:%S") if check_out_time else "",
			"difference": f"{int(total_hours):02d}:{int((total_hours % 1) * 60):02d}:00" if total_hours > 0 else "",
			"absent": is_absent,
			"present": not is_absent,
			"weekday": date.weekday() < 5,
			"day_type": "Weekday" if date.weekday() < 5 else "Weekly Off"
		}
		
		if existing_record:
			# Update existing record
			for key, value in daily_record_data.items():
				setattr(existing_record, key, value)
		else:
			# Add new record
			emp_attendance.append("table1", daily_record_data)
		
		# Save the document
		emp_attendance.save()
		
		# Log success for debugging
		log_message(f"Added daily attendance for {date}: Check-in={check_in_time}, Check-out={check_out_time}, Absent={is_absent}", "info")
		
	except Exception as e:
		log_message(f"❌ Error adding daily attendance for {date}: {str(e)}", "error")
		# Re-raise the exception to see what's happening
		raise e

def _generate_for_employee_fast(doc, emp, cfg):
	try:
		log_message(f"🚀 Starting _generate_for_employee_fast for {emp.name}", "info")
		
		created = 0
		current_date = getdate(doc.start_date)
		end_date = getdate(doc.end_date)
		
		log_message(f"📅 Date range: {current_date} to {end_date}", "info")
		
		# Process the full date range as specified by user
		days_processed = 0
		
		log_message(f"🔍 Processing employee {emp.name} from {current_date} to {end_date}", "info")
		log_message(f"📊 Config: Late={cfg.late_arrival_probability}%, Absent={cfg.absent_probability}%, OT={cfg.overtime_probability}%", "info")
		
		# STEP 1: Create Attendance Logs first
		attendance_logs_batch = []
		
		while current_date <= end_date:
			try:
				log_message(f"📅 Processing date: {current_date} (day {days_processed + 1})", "info")
				
				# Skip weekends if configured
				if not doc.include_weekends and current_date.weekday() >= 5:
					log_message(f"🏖️ Skipping weekend: {current_date}", "info")
					current_date = add_days(current_date, 1)
					continue
				
				# Randomly determine if employee is absent
				absent_roll = random.randint(1, 100)
				log_message(f"🎲 Absent roll: {absent_roll} vs threshold: {cfg.absent_probability}", "info")
				
				if absent_roll <= cfg.absent_probability:
					# Create leave application
					log_message(f"🏠 Employee absent on {current_date}, creating leave application", "info")
					_create_leave_application_fast(doc, emp, current_date)
					# Don't add attendance logs for absent days
				else:
					# Generate times
					log_message(f"⏰ Generating times for {current_date}", "info")
					check_in_time, check_out_time = _generate_times_fast(cfg)
					
					log_message(f"⏰ Generated times for {current_date}: Check-in={check_in_time}, Check-out={check_out_time}", "info")
					
					# Add to batch for attendance logs
					attendance_logs_batch.extend([
						{
							"doctype": "Attendance Logs",
							"employee": emp.name,
							"employee_name": emp.employee_name,
							"attendance_date": current_date,
							"attendance_time": check_in_time,
							"attendance": f" : {emp.biometric_id or '505'} : {current_date} {check_in_time.strftime('%H:%M:%S')} (1, 0)",
							"company": doc.company,
							"department": emp.department,
							"designation": emp.designation,
							"biometric_id": emp.biometric_id or "505",
							"log_type": "Check In"
						},
						{
							"doctype": "Attendance Logs",
							"employee": emp.name,
							"employee_name": emp.employee_name,
							"attendance_date": current_date,
							"attendance_time": check_out_time,
							"attendance": f" : {emp.biometric_id or '505'} : {current_date} {check_out_time.strftime('%H:%M:%S')} (0, 1)",
							"company": doc.company,
							"department": emp.department,
							"designation": emp.designation,
							"biometric_id": emp.biometric_id or "505",
							"log_type": "Check Out"
						}
					])
					
					log_message(f"📝 Added 2 attendance logs to batch for {current_date}. Total batch size: {len(attendance_logs_batch)}", "info")
				
				days_processed += 1
				current_date = add_days(current_date, 1)
				
			except Exception as e:
				log_message(f"❌ Error processing date {current_date}: {str(e)}", "error")
				current_date = add_days(current_date, 1)
				continue
		
		log_message(f"📊 Total days processed: {days_processed}", "info")
		log_message(f"📦 Attendance logs in batch: {len(attendance_logs_batch)}", "info")
		
		# STEP 2: Insert Attendance Logs first
		if attendance_logs_batch:
			log_message(f"🚀 Preparing to insert {len(attendance_logs_batch)} attendance logs", "info")
			inserted_logs = _insert_batch(attendance_logs_batch)
			log_message(f"✅ Successfully inserted {inserted_logs} attendance logs out of {len(attendance_logs_batch)}", "success")
			created = inserted_logs  # Update created count based on actual insertions
		else:
			log_message("⚠️ No attendance logs to insert", "warning")
			created = 0
		
		# STEP 3: Now create Employee Attendance
		month_name = getdate(doc.start_date).strftime("%B")
		year = getdate(doc.start_date).year
		
		log_message(f"📋 Creating Employee Attendance for {month_name} {year}", "info")
		emp_attendance = _create_employee_attendance_fast(doc, emp, month_name, year)
		
		# Debug: Check if Employee Attendance was created
		if not emp_attendance:
			log_message(f"❌ Failed to create Employee Attendance for {emp.name}", "error")
			return created
		
		log_message(f"✅ Created Employee Attendance: {emp_attendance.name} for {emp.name}", "success")
		
		# STEP 4: Now add daily attendance records to Employee Attendance
		current_date = getdate(doc.start_date)
		while current_date <= end_date:
			try:
				# Skip weekends if configured
				if not doc.include_weekends and current_date.weekday() >= 5:
					current_date = add_days(current_date, 1)
					continue
				
				# Check if employee was absent on this date
				absent_roll = random.randint(1, 100)
				is_absent = absent_roll <= cfg.absent_probability
				
				if is_absent:
					# Add absent record
					try:
						_add_daily_attendance_fast(emp_attendance.name, current_date, None, None, True)
						log_message(f"✅ Added absent record for {current_date}", "success")
					except Exception as e:
						log_message(f"❌ Error adding absent record for {current_date}: {str(e)}", "error")
				else:
					# Generate times again for consistency
					check_in_time, check_out_time = _generate_times_fast(cfg)
					
					# Add present record
					try:
						_add_daily_attendance_fast(emp_attendance.name, current_date, check_in_time, check_out_time, False)
						log_message(f"✅ Added present record for {current_date}: {check_in_time} - {check_out_time}", "success")
					except Exception as e:
						log_message(f"❌ Error adding present record for {current_date}: {str(e)}", "error")
				
				current_date = add_days(current_date, 1)
				
			except Exception as e:
				log_message(f"❌ Error processing date {current_date} for Employee Attendance: {str(e)}", "error")
				current_date = add_days(current_date, 1)
				continue
		
		# Final save of Employee Attendance to ensure all changes are persisted
		if emp_attendance:
			try:
				# Get a fresh copy to avoid modification conflicts
				fresh_emp_attendance = frappe.get_doc("Employee Attendance", emp_attendance.name)
				fresh_emp_attendance.save()
				log_message(f"Final save of Employee Attendance {fresh_emp_attendance.name} with {len(fresh_emp_attendance.table1)} daily records", "info")
			except Exception as e:
				log_message(f"❌ Error in final save of Employee Attendance: {str(e)}", "error")
		
		log_message(f"Employee {emp.name}: Created {created} attendance records, processed {days_processed} days", "info")
		return created
		
	except Exception as e:
		log_message(f"❌ Error in _generate_for_employee_fast for {emp.name}: {str(e)}", "error")
		return 0

def _generate_times_fast(cfg):
	check_in_start = get_time(cfg.check_in_start_time)
	check_in_end = get_time(cfg.check_in_end_time)
	check_out_start = get_time(cfg.check_out_start_time)
	check_out_end = get_time(cfg.check_out_end_time)
	
	check_in_time = _random_time_fast(check_in_start, check_in_end)
	check_out_time = _random_time_fast(check_out_start, check_out_end)
	
	return check_in_time, check_out_time

def _random_time_fast(start_time, end_time):
	start_minutes = start_time.hour * 60 + start_time.minute
	end_minutes = end_time.hour * 60 + end_time.minute
	random_minutes = random.randint(start_minutes, end_minutes)
	hours = random_minutes // 60
	minutes = random_minutes % 60
	return time(hours, minutes)

def _create_leave_application_fast(doc, emp, date):
	try:
		# Check if there's a valid leave allocation for this employee and date
		leave_allocations = frappe.get_all("Leave Allocation", 
			filters={
				"employee": emp.name,
				"from_date": ["<=", date],
				"to_date": [">=", date],
				"docstatus": 1
			},
			fields=["leave_type", "from_date", "to_date"],
			limit=1
		)
		
		if not leave_allocations:
			log_message(f"No valid leave allocation found for {emp.name} on {date}, skipping leave application", "warning")
			return
		
		leave_allocation = leave_allocations[0]
		leave_type = leave_allocation.leave_type
		
		# Check if there's already a leave application for this date
		existing_leave = frappe.get_all("Leave Application",
			filters={
				"employee": emp.name,
				"from_date": ["<=", date],
				"to_date": [">=", date],
				"docstatus": ["!=", 2]  # Not cancelled
			},
			limit=1
		)
		
		if existing_leave:
			log_message(f"Leave application already exists for {emp.name} on {date}, skipping", "info")
			return
		
		# Create leave application directly
		leave_doc = frappe.get_doc({
			"doctype": "Leave Application",
			"employee": emp.name,
			"leave_type": leave_type,
			"from_date": date,
			"to_date": date,
			"half_day": 0,
			"company": doc.company,
			"status": "Open",
			"description": "Auto-generated for fake attendance"
		})
		leave_doc.insert()
		log_message(f"Created leave application for {emp.name} on {date}", "success")
		
	except Exception as e:
		log_message(f"Failed to create Leave Application for {emp.name} on {date}: {str(e)}", "error")

def _insert_batch(docs_batch):
	"""Insert multiple documents in batch for better performance"""
	try:
		log_message(f"🚀 Starting batch insert of {len(docs_batch)} documents", "info")
		inserted_count = 0
		
		for i, doc_data in enumerate(docs_batch):
			try:
				log_message(f"📝 Inserting document {i+1}/{len(docs_batch)}: {doc_data.get('doctype')} for {doc_data.get('employee')} on {doc_data.get('attendance_date')}", "info")
				
				doc = frappe.get_doc(doc_data)
				doc.insert()
				inserted_count += 1
				
				log_message(f"✅ Successfully inserted document {i+1}: {doc.name}", "success")
				
				if i % 10 == 0:  # Log every 10th document
					log_message(f"📊 Progress: Inserted {inserted_count}/{len(docs_batch)} documents", "info")
					
			except Exception as e:
				log_message(f"❌ Error inserting document {i+1}: {str(e)}", "error")
				log_message(f"📋 Document data: {doc_data}", "info")
				continue
		
		log_message(f"🎉 Batch insert completed: {inserted_count}/{len(docs_batch)} documents inserted successfully", "success")
		return inserted_count
		
	except Exception as e:
		log_message(f"❌ Error in batch insert: {str(e)}", "error")
		return 0
