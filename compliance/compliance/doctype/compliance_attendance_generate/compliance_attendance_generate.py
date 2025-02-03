import frappe
import random
from frappe.model.document import Document
from frappe.utils import getdate, add_days
from datetime import time

class ComplianceAttendanceGenerate(Document):
    @frappe.whitelist()
    def get_employees(self):
        # Fetch data using SQL query for active employees
        rec = frappe.db.sql(""" 
            SELECT employee FROM `tabEmployee` WHERE status = 'Active'
        """, as_dict=True)

        # Debug log to see the results
        frappe.log_error(f"SQL Result: {rec}", "Debugging SQL")

        if rec:
            # Clear existing employee entries in the child table
            self.employee = []

            # Append records to the child table
            for r in rec:
                self.append("employee", {
                    "employee": r['employee'],
                    # Add other fields if needed
                })

            # Save the document with the updated child table data
            self.save()

    @frappe.whitelist()
    def generate_attendance(self):
        # Loop through all the employees in the child table
        for employee_data in self.employee:
            employee = employee_data.employee
            from_date = getdate(self.from_date)
            to_date = getdate(self.to_date)

            # Check for the attendance already existing for these dates
            attendance_exists = frappe.db.exists("Employee Attendance", {
                'employee': employee,
                'attendance_date': ('between', [from_date, to_date])
            })

            # If attendance does not exist, create new attendance records
            if not attendance_exists:
                # Create a new Employee Attendance record
                attendance = frappe.get_doc({
                    "doctype": "Employee Attendance",
                    "employee": employee,
                    "month": from_date.strftime('%B'),  # Use the month from the from_date
                    "year": from_date.year,  # Use the year from the from_date
                })

                # Loop through each day from from_date to to_date and add rows to 'table1'
                current_date = from_date
                while current_date <= to_date:
                    # Generate random check-in and check-out times
                    check_in_hour = random.randint(9, 9)  # Random hour between 8 and 10 AM
                    check_in_minute = random.randint(0, 15)
                    check_in_second = random.randint(0, 59)
                    check_in_1 = time(check_in_hour, check_in_minute, check_in_second)
                    check_in_1_str = check_in_1.strftime("%H:%M:%S")  # Convert to string
                    
                    check_out_hour = random.randint(19, 19)  # Random hour between 5 and 7 PM
                    check_out_minute = random.randint(0, 15)
                    check_out_second = random.randint(0, 59)
                    check_out_1 = time(check_out_hour, check_out_minute, check_out_second)  # Random check-out time

                    # Add a row to the 'table1' child table with the current date and random check-in/check-out
                    attendance.append("table1", {
                        "date": current_date,  # Correct field name 'date'
                        "status": "Present",  # Default status
                        "check_in_1": check_in_1_str,  # Use the generated random check-in time string
                        "check_out_1": check_out_1.strftime("%H:%M:%S"),  # Use the generated random check-out time string
                    })

                    # Move to the next date
                    current_date = add_days(current_date, 1)

                # Insert the Employee Attendance record with the child table data
                attendance.insert()

        # No need to manually commit as Frappe handles transaction commit
