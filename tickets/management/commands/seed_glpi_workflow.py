from django.core.management.base import BaseCommand
from tickets.models import Category, IssueFormField, ServiceCatalogItem
from accounts.models import TechnicianGroup

class Command(BaseCommand):
    help = 'Seeds initial GLPI dynamic questions, routing rules, technician groups, and service catalog items'

    def handle(self, *args, **options):
        self.stdout.write('Seeding GLPI Dynamic Workflow & Routing...')

        # 1. Technician Groups
        net_grp, _ = TechnicianGroup.objects.get_or_create(
            name='Network Support Group',
            defaults={'description': 'WiFi and LAN networking team', 'max_tickets_per_tech': 5}
        )
        hw_grp, _ = TechnicianGroup.objects.get_or_create(
            name='Hardware Maintenance Group',
            defaults={'description': 'Lab PCs, monitors, and peripherals', 'max_tickets_per_tech': 5}
        )
        seb_grp, _ = TechnicianGroup.objects.get_or_create(
            name='Online Exam & SEB Tech Support',
            defaults={'description': 'Safe Exam Browser and online examination systems', 'max_tickets_per_tech': 5}
        )

        # 2. Categories with Group Routing
        cat_net, _ = Category.objects.get_or_create(
            name='Network Issue',
            defaults={'description': 'Campus WiFi, LAN, and internet connection issues', 'assigned_group': net_grp}
        )
        cat_net.assigned_group = net_grp
        cat_net.save()

        cat_pc, _ = Category.objects.get_or_create(
            name='PC Issue',
            defaults={'description': 'Lab workstation, monitor, and desktop hardware', 'assigned_group': hw_grp}
        )
        cat_pc.assigned_group = hw_grp
        cat_pc.save()

        cat_seb, _ = Category.objects.get_or_create(
            name='SEB Issue',
            defaults={'description': 'Safe Exam Browser lockups, crashes, and camera issues', 'assigned_group': seb_grp}
        )
        cat_seb.assigned_group = seb_grp
        cat_seb.save()

        cat_other, _ = Category.objects.get_or_create(
            name='Other',
            defaults={'description': 'General IT issues and other inquiries'}
        )

        # 3. Dynamic Form Questions
        # Q0: Facing Issue In (Primary question)
        q0, _ = IssueFormField.objects.get_or_create(
            field_key='facing_issue_in',
            defaults={
                'label': 'Facing Issue In',
                'field_type': IssueFormField.FieldType.CHECKBOX,
                'options': ['Network Issue', 'PC Issue', 'SEB Issue', 'Other'],
                'condition_type': IssueFormField.ConditionType.ALWAYS,
                'required': True,
                'order': 0,
                'is_active': True,
                'help_text': 'Select the main area or problem you are encountering'
            }
        )
        q0.options = ['Network Issue', 'PC Issue', 'SEB Issue', 'Other']
        q0.field_type = IssueFormField.FieldType.CHECKBOX
        q0.condition_type = IssueFormField.ConditionType.ALWAYS
        q0.required = True
        q0.order = 0
        q0.is_active = True
        q0.save()

        # Q1: Which Network Problem ?
        q1, _ = IssueFormField.objects.get_or_create(
            field_key='network_problem_type',
            defaults={
                'label': 'Which Network Problem ?',
                'field_type': IssueFormField.FieldType.CHECKBOX,
                'options': ['LAN Problem', 'WiFi Problem', 'Slow Network', 'Other'],
                'condition_type': IssueFormField.ConditionType.VISIBLE_IF,
                'condition_field_key': 'facing_issue_in',
                'condition_operator': IssueFormField.ConditionOperator.CONTAINS,
                'condition_value': 'Network Issue',
                'required': False,
                'order': 1,
                'is_active': True,
                'help_text': 'Select specific network problem details'
            }
        )
        q1.options = ['LAN Problem', 'WiFi Problem', 'Slow Network', 'Other']
        q1.condition_type = IssueFormField.ConditionType.VISIBLE_IF
        q1.condition_field_key = 'facing_issue_in'
        q1.condition_operator = IssueFormField.ConditionOperator.CONTAINS
        q1.condition_value = 'Network Issue'
        q1.order = 1
        q1.is_active = True
        q1.save()

        # Q2: Type Your Network Problem (Text specification)
        q2, _ = IssueFormField.objects.get_or_create(
            field_key='network_problem_description',
            defaults={
                'label': 'Type Your Network Problem',
                'field_type': IssueFormField.FieldType.TEXT,
                'condition_type': IssueFormField.ConditionType.VISIBLE_IF,
                'condition_field_key': 'facing_issue_in',
                'condition_operator': IssueFormField.ConditionOperator.CONTAINS,
                'condition_value': 'Network Issue',
                'required': False,
                'order': 2,
                'is_active': True,
                'help_text': 'Specify any error codes, IP address, or port numbers'
            }
        )
        q2.condition_type = IssueFormField.ConditionType.VISIBLE_IF
        q2.condition_field_key = 'facing_issue_in'
        q2.condition_operator = IssueFormField.ConditionOperator.CONTAINS
        q2.condition_value = 'Network Issue'
        q2.order = 2
        q2.is_active = True
        q2.save()

        # Q3: Which PC Problem ?
        q3, _ = IssueFormField.objects.get_or_create(
            field_key='pc_problem_type',
            defaults={
                'label': 'Which PC Problem ?',
                'field_type': IssueFormField.FieldType.CHECKBOX,
                'options': ['Will not boot', 'Blue Screen / Crash', 'Peripheral (Mouse/Keyboard)', 'Monitor Issue', 'Other'],
                'condition_type': IssueFormField.ConditionType.VISIBLE_IF,
                'condition_field_key': 'facing_issue_in',
                'condition_operator': IssueFormField.ConditionOperator.CONTAINS,
                'condition_value': 'PC Issue',
                'required': False,
                'order': 3,
                'is_active': True,
                'help_text': 'Select specific workstation / PC hardware issues'
            }
        )
        q3.options = ['Will not boot', 'Blue Screen / Crash', 'Peripheral (Mouse/Keyboard)', 'Monitor Issue', 'Other']
        q3.condition_type = IssueFormField.ConditionType.VISIBLE_IF
        q3.condition_field_key = 'facing_issue_in'
        q3.condition_operator = IssueFormField.ConditionOperator.CONTAINS
        q3.condition_value = 'PC Issue'
        q3.order = 3
        q3.is_active = True
        q3.save()

        # Q4: Which SEB / Exam Problem ?
        q4, _ = IssueFormField.objects.get_or_create(
            field_key='seb_problem_type',
            defaults={
                'label': 'Which SEB / Exam Problem ?',
                'field_type': IssueFormField.FieldType.CHECKBOX,
                'options': ['SEB Lockdown Error', 'Camera not detected', 'Session crashed', 'Certificate error', 'Other'],
                'condition_type': IssueFormField.ConditionType.VISIBLE_IF,
                'condition_field_key': 'facing_issue_in',
                'condition_operator': IssueFormField.ConditionOperator.CONTAINS,
                'condition_value': 'SEB Issue',
                'required': False,
                'order': 4,
                'is_active': True,
                'help_text': 'Select Safe Exam Browser or online test problems'
            }
        )
        q4.options = ['SEB Lockdown Error', 'Camera not detected', 'Session crashed', 'Certificate error', 'Other']
        q4.condition_type = IssueFormField.ConditionType.VISIBLE_IF
        q4.condition_field_key = 'facing_issue_in'
        q4.condition_operator = IssueFormField.ConditionOperator.CONTAINS
        q4.condition_value = 'SEB Issue'
        q4.order = 4
        q4.is_active = True
        q4.save()

        # Q5: Problem Description
        q5, _ = IssueFormField.objects.get_or_create(
            field_key='problem_description',
            defaults={
                'label': 'Problem Description',
                'field_type': IssueFormField.FieldType.TEXTAREA,
                'condition_type': IssueFormField.ConditionType.ALWAYS,
                'required': True,
                'order': 5,
                'is_active': True,
                'help_text': 'Detailed explanation of the problem or error encountered'
            }
        )
        q5.label = 'Problem Description'
        q5.field_type = IssueFormField.FieldType.TEXTAREA
        q5.condition_type = IssueFormField.ConditionType.ALWAYS
        q5.required = True
        q5.order = 5
        q5.is_active = True
        q5.save()

        # Q6: File Attachment
        q6, _ = IssueFormField.objects.get_or_create(
            field_key='attachment',
            defaults={
                'label': 'File Attachment (Screenshot / Photo)',
                'field_type': IssueFormField.FieldType.FILE,
                'condition_type': IssueFormField.ConditionType.ALWAYS,
                'required': False,
                'order': 6,
                'is_active': True,
                'help_text': 'Upload error screenshot or photo. Allowed: JPG, PNG, GIF. Max: 5MB.'
            }
        )
        q6.label = 'File Attachment (Screenshot / Photo)'
        q6.field_type = IssueFormField.FieldType.FILE
        q6.condition_type = IssueFormField.ConditionType.ALWAYS
        q6.required = False
        q6.order = 6
        q6.is_active = True
        q6.save()

        # 4. Service Catalog Items


        ServiceCatalogItem.objects.get_or_create(
            title='Campus WiFi & LAN Access',
            defaults={
                'description': 'WiFi login assistance, slow connection troubleshooting, and lab network drops.',
                'icon': '🌐',
                'category': cat_net,
                'show_on_homepage': True,
                'is_active': True,
                'order': 0,
            }
        )
        ServiceCatalogItem.objects.get_or_create(
            title='Lab Workstation Hardware',
            defaults={
                'description': 'Desktop PC booting, monitors, keyboards, mice, and classroom projector assistance.',
                'icon': '💻',
                'category': cat_pc,
                'show_on_homepage': True,
                'is_active': True,
                'order': 1,
            }
        )
        ServiceCatalogItem.objects.get_or_create(
            title='Safe Exam Browser (SEB)',
            defaults={
                'description': 'Assistance with online exam client lockdown, proctoring camera errors, or session crashes.',
                'icon': '🔒',
                'category': cat_seb,
                'show_on_homepage': True,
                'is_active': True,
                'order': 2,
            }
        )
        ServiceCatalogItem.objects.get_or_create(
            title='General IT Helpdesk',
            defaults={
                'description': 'Assistance with email, printing, college portal access, and general IT inquiries.',
                'icon': '🛠️',
                'category': cat_other,
                'show_on_homepage': True,
                'is_active': True,
                'order': 3,
            }
        )

        # 5. Default Demo Accounts
        from django.contrib.auth.models import User
        from accounts.models import UserRole

        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@siet.edu.in',
                password='Password123!'
            )
            admin_user.profile.role = UserRole.ADMIN
            admin_user.profile.save()

        if not User.objects.filter(username='tech').exists():
            tech_user = User.objects.create_user(
                username='tech',
                email='tech@siet.edu.in',
                password='Password123!'
            )
            tech_user.profile.role = UserRole.TECHNICIAN
            tech_user.profile.save()
            net_grp.technicians.add(tech_user)
            hw_grp.technicians.add(tech_user)
            seb_grp.technicians.add(tech_user)

        if not User.objects.filter(username='student').exists():
            student_user = User.objects.create_user(
                username='student',
                email='student@siet.edu.in',
                password='Password123!'
            )
            student_user.profile.role = UserRole.NORMAL_USER
            student_user.profile.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded GLPI dynamic workflow, routing, and catalog!'))

