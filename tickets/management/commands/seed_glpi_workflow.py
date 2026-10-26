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
        hostel_grp, _ = TechnicianGroup.objects.get_or_create(
            name='Hostel Facilities & Network Support',
            defaults={
                'description': 'Dedicated technician support for student hostels and residential blocks',
                'max_tickets_per_tech': 8,
                'location_condition': 'Hostel, Boys Hostel, Girls Hostel'
            }
        )
        techpark_grp, _ = TechnicianGroup.objects.get_or_create(
            name='Tech Park & Academic Lab Team',
            defaults={
                'description': 'On-ground technical team for Tech Park, computer labs, and engineering blocks',
                'max_tickets_per_tech': 8,
                'location_condition': 'Tech Park, Lab, CS Lab'
            }
        )

        # 1b. Seed Campus Locations
        from tickets.models import CampusLocation
        admin_loc, _ = CampusLocation.objects.get_or_create(
            name='Admin Block',
            defaults={'code': 'ADMIN_BLOCK', 'description': 'Main Administrative and Registrar Offices'}
        )
        tp_loc, _ = CampusLocation.objects.get_or_create(
            name='Tech Park',
            defaults={'code': 'TECH_PARK', 'description': 'Computer Science, IT, AI & VLSI Engineering Labs'}
        )
        acad_loc, _ = CampusLocation.objects.get_or_create(
            name='Academic Block',
            defaults={'code': 'ACADEMIC_BLOCK', 'description': 'Lecture halls, smart classrooms, and faculty rooms'}
        )
        bh_loc, _ = CampusLocation.objects.get_or_create(
            name='Boys Hostel',
            defaults={'code': 'BOYS_HOSTEL', 'description': 'Boys Hostels Block A, B & C'}
        )
        gh_loc, _ = CampusLocation.objects.get_or_create(
            name='Girls Hostel',
            defaults={'code': 'GIRLS_HOSTEL', 'description': 'Girls Hostels Block 1 & 2'}
        )
        lib_loc, _ = CampusLocation.objects.get_or_create(
            name='Central Library',
            defaults={'code': 'LIBRARY', 'description': 'Central Library, digital reference labs & reading halls'}
        )

        hostel_grp.campus_locations.add(bh_loc, gh_loc)
        techpark_grp.campus_locations.add(tp_loc, acad_loc)

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

        # 5. Solutions & Quick-Fixes Articles (Wi-Fi, LAN & SEB)
        from tickets.models import SolutionArticle

        SolutionArticle.objects.get_or_create(
            title="Wi-Fi Connected but Shows 'No Internet Access' (Android / iPhone)",
            defaults={
                'category': cat_net,
                'target_category': SolutionArticle.TargetCategory.WIFI_LAN,
                'summary': "Device connects to SIET Wi-Fi but displays an exclamation mark or 'Connected without internet' prompt.",
                'symptoms': "Exclamation mark next to the Wi-Fi icon\nWeb pages fail to load or show DNS lookup error\nOther students in the room are able to browse normally",
                'solution_steps': "Step 1: Open Phone Settings -> Wi-Fi -> Tap gear icon next to 'SIET_WIFI'.\nStep 2: Look for 'MAC Address Type' or 'Privacy' setting. Change it from 'Randomized MAC' to 'Use Device MAC'.\nStep 3: Turn off any active 3rd-party VPN apps or Private DNS (Settings -> Connections -> More connection settings -> Private DNS: Off).\nStep 4: Toggle Airplane Mode on for 10 seconds, then reconnect to 'SIET_WIFI'.",
                'verification_checklist': "Confirm Private DNS is set to Automatic or Off\nVerify Device MAC is selected instead of Randomized MAC\nCheck if your device received an IP address starting with 10.x.x.x or 172.x.x.x",
                'order': 1,
                'is_active': True,
            }
        )

        SolutionArticle.objects.get_or_create(
            title="Weak Wi-Fi Signal & Frequent Disconnections in Rooms",
            defaults={
                'category': cat_net,
                'target_category': SolutionArticle.TargetCategory.WIFI_LAN,
                'summary': "Wi-Fi signal drops to 1 bar or phone repeatedly flips between mobile data and campus Wi-Fi.",
                'symptoms': "Signal drops when moving away from doorway or corridor\nPhone continuously reconnects every few minutes\nOlder budget phones struggle to maintain connection on dual-band access points",
                'solution_steps': "Step 1: Check Wi-Fi frequency: Connect to 'SIET_5G' if your device supports 5 GHz for faster, cleaner throughput.\nStep 2: If using an older laptop or phone, connect to 'SIET_2.4G' which penetrates walls and doors much better.\nStep 3: Disable 'Auto-switch to mobile data' or 'Adaptive Wi-Fi' in advanced Wi-Fi settings so your device does not disconnect aggressively.\nStep 4: Keep your laptop or phone out in the open (avoid placing it behind metal cupboards or under metal bed frames).",
                'verification_checklist': "Tested with 'Adaptive Wi-Fi' turned OFF\nVerified signal difference near doorway vs room interior\nChecked if roommate on the same floor has normal signal",
                'order': 2,
                'is_active': True,
            }
        )

        SolutionArticle.objects.get_or_create(
            title="Lab PC / Laptop LAN Cable Shows 'Unidentified Network' or No IP",
            defaults={
                'category': cat_net,
                'target_category': SolutionArticle.TargetCategory.WIFI_LAN,
                'summary': "Ethernet cable is plugged into workstation or laptop, but Windows displays a yellow warning triangle or 169.254.x.x IP.",
                'symptoms': "Ethernet adapter shows 'Unidentified Network'\nPhysical port light is orange or not blinking\nCommand prompt ipconfig shows an Autoconfiguration IPv4 address (169.254.x.x)",
                'solution_steps': "Step 1: Check physical connection: Unplug the RJ-45 LAN cable and firmly plug it back in until an audible click is heard. Verify the port LED is blinking green.\nStep 2: Set IPv4 to Automatic DHCP: Open Network Connections (Win + R -> ncpa.cpl) -> Right-click Ethernet -> Properties -> Internet Protocol Version 4 (TCP/IPv4) -> Select 'Obtain an IP address automatically' and 'Obtain DNS server automatically'.\nStep 3: Reset TCP/IP stack: Open Command Prompt as Administrator and run: netsh int ip reset followed by ipconfig /renew.\nStep 4: Restart your computer to apply fresh DHCP lease.",
                'verification_checklist': "Physical LAN cable firmly clicked in with blinking LED\nTCP/IPv4 set to Automatic (DHCP enabled)\nVerified cable by testing in adjacent lab port if available",
                'order': 3,
                'is_active': True,
            }
        )

        SolutionArticle.objects.get_or_create(
            title="Safe Exam Browser (SEB) Red Screen: 'Prohibited Process Running'",
            defaults={
                'category': cat_seb,
                'target_category': SolutionArticle.TargetCategory.SEB,
                'summary': "Safe Exam Browser displays a red warning screen and blocks exam launch due to active background processes.",
                'symptoms': "Red screen appears with message naming a running app (Discord.exe, Teams.exe, Zoom.exe, TeamViewer.exe, AnyDesk.exe)\nExam window refuses to advance to login screen",
                'solution_steps': "Step 1: Press Ctrl + Shift + Esc to open Windows Task Manager. (If locked, press Alt + Tab or use SEB exit button with password 'siet').\nStep 2: Click 'More details', scroll through Apps and Background Processes.\nStep 3: Right-click and 'End Task' on prohibited apps: Discord, Zoom, Microsoft Teams, AnyDesk, TeamViewer, Telegram, WhatsApp, Skype, and Steam.\nStep 4: Disable Discord and Teams from starting automatically: Open Task Manager -> Startup apps tab -> Disable auto-start.\nStep 5: Relaunch the official .seb configuration file provided by the exam coordinator.",
                'verification_checklist': "Task Manager shows 0 communication or screen-sharing tools active\nDual monitors disconnected (SEB only allows 1 physical display)\nLaptop plugged into AC power adapter",
                'order': 4,
                'is_active': True,
            }
        )

        SolutionArticle.objects.get_or_create(
            title="Safe Exam Browser (SEB) Camera & Microphone Permission Blocked",
            defaults={
                'category': cat_seb,
                'target_category': SolutionArticle.TargetCategory.SEB,
                'summary': "Exam proctor screen shows black video feed or error: 'Media stream failed / Camera not detected'.",
                'symptoms': "Camera LED does not illuminate when exam starts\nProctor page displays warning: 'Unable to capture video stream'",
                'solution_steps': "Step 1: Open Windows Settings -> Privacy & Security -> Camera. Ensure 'Camera access' is turned ON.\nStep 2: Under 'Let desktop apps access your camera', ensure the toggle is ON.\nStep 3: Check antivirus webcam protection: Programs like Kaspersky, Bitdefender, or Windows Defender SmartScreen can block SEB from webcam streaming. Temporarily allow SEB in antivirus settings.\nStep 4: Close other browser tabs (Chrome, Edge) that may have locked the camera hardware before launching SEB.\nStep 5: Test camera in Windows Camera app first, then restart SEB.",
                'verification_checklist': "Camera confirmed working in default Windows Camera app\nWindows Privacy Settings allows desktop apps camera access\nExternal USB webcams firmly plugged directly into laptop port (not loose USB hub)",
                'order': 5,
                'is_active': True,
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

