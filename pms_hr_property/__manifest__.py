# Copyright 2023 OsoTranquilo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "PMS Hr Property",
    "summary": """
        Adds to the employee the property on which he works.""",
<<<<<<< HEAD
    "version": "14.0.1.1.0",
=======
    "version": "14.0.2.0.0",
>>>>>>> [FIX]pms_hr_property: module test
    "license": "AGPL-3",
    "author": "OsoTranquilo,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/pms",
    "category": "PMS/HR",
    "depends": [
        "hr",
        "pms",
    ],
    "data": ["views/hr_employee_view.xml", "views/pms_hr_property_view.xml"],
    "installable": True,
}
