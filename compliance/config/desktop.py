# apps/compliance/compliance/config/desktop.py
from frappe import _

def get_data():
    return [
        {
            "module_name": "Compliance",
            "color": "grey",
            "icon": "octicon octicon-check",
            "type": "module",
            "label": _("Compliance"),
        }
    ]
