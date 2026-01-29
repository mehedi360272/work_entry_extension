{
    'name': "Work Entry Extension",

    'summary': "Enhances HR work entries with additional tracking and customization",

    'description': """
    This module extends the standard Odoo Work Entry functionality.
    It allows additional customization, tracking, and control over employee
    work entries to better support HR and payroll operations.

    Key Features:
    - Extend existing work entry records
    - Add custom fields or logic if required
    - Improve visibility and management of employee attendance data
        """,

    'author': "Khondokar Md. Mehedi Hasan",
    'website': "https://github.com/mehedi360272",

    'category': 'Human Resources',
    'version': '19.0.1.0.0',

    # Dependencies
    'depends': [
        'base',
        'hr',
        'hr_payroll',
        'hr_attendance',
        'hr_work_entry',
    ],

    # Data files
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/work_entry_views.xml',
    ],

    # Demo data
    'demo': [
        # 'demo/work_entry_demo.xml',
    ],

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
