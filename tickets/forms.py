import os
from django import forms
from .models import Ticket, TicketStatus, TicketUrgency, IssueFormField, ServiceCatalogItem, SolutionArticle, CampusLocation, get_admin_max_upload_size_bytes


from django.utils.text import slugify

class TicketCreateForm(forms.ModelForm):
    category = forms.CharField(required=False, widget=forms.HiddenInput())
    campus_location = forms.ModelChoiceField(
        queryset=CampusLocation.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label="-- Select Campus Block / Location * --",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_campus_location'})
    )
    location_details = forms.CharField(
        required=False,
        label="Room / Lab / Specific Location *",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. VLSI Lab, Lab 2 - Table 4, Room 204',
            'id': 'id_location_details'
        })
    )

    class Meta:
        model = Ticket
        fields = ('title', 'description', 'category', 'urgency', 'campus_location', 'location_details', 'location', 'attachment')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., WiFi disconnected in CS Lab 2'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Provide details about what happened...'}),
            'location': forms.TextInput(attrs={'placeholder': 'e.g., Tech Park - VLSI Lab'}),
            'category': forms.HiddenInput(),
        }

    def clean_category(self):
        val = self.cleaned_data.get('category')
        if not val:
            return None
        from .models import Category
        if isinstance(val, Category):
            return val
        if str(val).isdigit():
            cat = Category.objects.filter(pk=int(val)).first()
            if cat:
                return cat
        cat = Category.objects.filter(name__iexact=str(val).strip()).first()
        if cat:
            return cat
        return None

    def clean(self):
        cleaned_data = super().clean()
        camp_loc = cleaned_data.get('campus_location')
        loc_det = (cleaned_data.get('location_details') or '').strip()
        raw_loc = (cleaned_data.get('location') or '').strip()

        if camp_loc:
            if loc_det:
                cleaned_data['location'] = f"{camp_loc.name} - {loc_det}"
            else:
                cleaned_data['location'] = camp_loc.name
        elif loc_det:
            cleaned_data['location'] = loc_det
        elif raw_loc:
            cleaned_data['location'] = raw_loc

        return cleaned_data

    def __init__(self, *args, issue_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False
        self.fields['description'].required = False
        self.fields['location'].required = False

        from .models import CoreFieldSetting
        try:
            core_settings = CoreFieldSetting.get_all_settings()
            if 'title' in self.fields and 'title' in core_settings:
                t_set = core_settings['title']
                if t_set.label: self.fields['title'].label = t_set.label
                if t_set.placeholder: self.fields['title'].widget.attrs['placeholder'] = t_set.placeholder
            if 'description' in self.fields and 'description' in core_settings:
                d_set = core_settings['description']
                if d_set.label: self.fields['description'].label = d_set.label
                if d_set.placeholder: self.fields['description'].widget.attrs['placeholder'] = d_set.placeholder
            if 'campus_location' in self.fields and 'location' in core_settings:
                loc_set = core_settings['location']
                if loc_set.label:
                    self.fields['campus_location'].label = loc_set.label
                    self.fields['campus_location'].empty_label = f"-- Select {loc_set.label} * --"
            if 'location_details' in self.fields and 'location' in core_settings:
                loc_set = core_settings['location']
                if loc_set.placeholder:
                    self.fields['location_details'].widget.attrs['placeholder'] = loc_set.placeholder
                room_lbl = loc_set.extra_config.get('room_details_label') if loc_set.extra_config else None
                if room_lbl:
                    self.fields['location_details'].label = room_lbl
            if 'urgency' in self.fields and 'urgency' in core_settings:
                u_set = core_settings['urgency']
                if u_set.label: self.fields['urgency'].label = u_set.label
                def_u = u_set.extra_config.get('default_urgency') if u_set.extra_config else None
                if def_u and not self.is_bound:
                    self.fields['urgency'].initial = def_u
            if 'attachment' in self.fields and 'attachment' in core_settings:
                att_set = core_settings['attachment']
                if att_set.label: self.fields['attachment'].label = att_set.label
        except Exception:
            pass

        self.issue_fields = issue_fields or []

        for issue_field in self.issue_fields:
            choices = [(option, option) for option in issue_field.options]
            field_kwargs = {
                'label': issue_field.label,
                'required': False if issue_field.field_key in ('problem_description', 'description') else issue_field.required,
                'help_text': issue_field.help_text,
            }


            if issue_field.field_type == IssueFormField.FieldType.RADIO:
                field_obj = forms.ChoiceField(**field_kwargs, choices=choices, widget=forms.RadioSelect)
            elif issue_field.field_type == IssueFormField.FieldType.CHECKBOX:
                field_obj = forms.MultipleChoiceField(**field_kwargs, choices=choices, widget=forms.CheckboxSelectMultiple)
            elif issue_field.field_type == IssueFormField.FieldType.SELECT:
                field_obj = forms.ChoiceField(**field_kwargs, choices=[('', '-- Select an option --')] + choices)
            elif issue_field.field_type == IssueFormField.FieldType.TEXTAREA:
                field_obj = forms.CharField(**field_kwargs, widget=forms.Textarea(attrs={'rows': 3, 'placeholder': issue_field.help_text or 'Enter details...'}))
            elif issue_field.field_type == IssueFormField.FieldType.FILE:
                field_obj = forms.FileField(**field_kwargs, widget=forms.ClearableFileInput())
            else:
                field_obj = forms.CharField(**field_kwargs, widget=forms.TextInput(attrs={'placeholder': issue_field.help_text or 'Enter details...'}))


            # Attach GLPI condition metadata to field object for dynamic JS toggling
            field_obj.category_id = issue_field.category_id if issue_field.category else 'global'
            field_obj.condition_type = issue_field.condition_type
            field_obj.condition_field_key = issue_field.condition_field_key
            field_obj.condition_operator = issue_field.condition_operator
            field_obj.condition_value = issue_field.condition_value
            field_obj.custom_field_type = issue_field.field_type
            field_obj.max_file_size_mb = issue_field.max_file_size_mb
            self.fields[issue_field.field_key] = field_obj

    def clean(self):
        cleaned_data = super().clean()
        
        # Check file size limit for attachment and any dynamic file fields
        max_size_map = {}
        for f in self.issue_fields:
            if f.field_type == IssueFormField.FieldType.FILE:
                max_size_map[f.field_key] = f.max_file_size_mb
        
        admin_max_bytes = get_admin_max_upload_size_bytes()
        admin_max_mb = int(admin_max_bytes / (1024 * 1024))
        global_max_mb = max_size_map.get('attachment', admin_max_mb)
        allowed_ticket_extensions = ['jpg', 'jpeg', 'png', 'gif']
        
        attachment = cleaned_data.get('attachment')
        if attachment:
            if hasattr(attachment, 'size'):
                limit_bytes = global_max_mb * 1024 * 1024
                if attachment.size > limit_bytes:
                    self.add_error('attachment', f"File size ({attachment.size / (1024*1024):.1f} MB) exceeds maximum allowed limit of {global_max_mb} MB.")
            
            ext = os.path.splitext(attachment.name)[1].lstrip('.').lower()
            if ext not in allowed_ticket_extensions:
                self.add_error('attachment', f"File type '.{ext}' is not allowed. Allowed image formats: {', '.join(allowed_ticket_extensions)}.")

        for key, max_mb in max_size_map.items():
            if key != 'attachment':
                file_obj = cleaned_data.get(key)
                if file_obj:
                    if hasattr(file_obj, 'size'):
                        limit_bytes = max_mb * 1024 * 1024
                        if file_obj.size > limit_bytes:
                            self.add_error(key, f"File size ({file_obj.size / (1024*1024):.1f} MB) exceeds maximum allowed limit of {max_mb} MB.")
                    allowed_doc_extensions = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'docx', 'txt', 'zip']
                    doc_ext = os.path.splitext(file_obj.name)[1].lstrip('.').lower()
                    if doc_ext not in allowed_doc_extensions:
                        self.add_error(key, f"File type '.{doc_ext}' is not allowed. Allowed formats: {', '.join(allowed_doc_extensions)}.")

        return cleaned_data


class AdminTicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('title', 'description', 'category', 'urgency', 'campus_location', 'location_details', 'location', 'assigned_group', 'assigned_technician', 'status', 'is_sla_breached')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'location_details': forms.TextInput(attrs={'placeholder': 'e.g. VLSI Lab, Lab 2, Room 204'}),
            'location': forms.TextInput(attrs={'placeholder': 'Full Location string e.g. Tech Park - VLSI Lab'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_technician'].queryset = self.fields['assigned_technician'].queryset.filter(
            profile__role='technician', profile__is_active=True, profile__is_suspended=False
        ).order_by('username')
        self.fields['location'].required = False

    def clean(self):
        cleaned_data = super().clean()
        camp_loc = cleaned_data.get('campus_location')
        loc_det = (cleaned_data.get('location_details') or '').strip()
        raw_loc = (cleaned_data.get('location') or '').strip()

        if camp_loc:
            if loc_det:
                cleaned_data['location'] = f"{camp_loc.name} - {loc_det}"
            else:
                cleaned_data['location'] = camp_loc.name
        elif loc_det:
            cleaned_data['location'] = loc_det
        elif raw_loc:
            cleaned_data['location'] = raw_loc

        return cleaned_data


class CampusLocationForm(forms.ModelForm):
    class Meta:
        model = CampusLocation
        fields = ('name', 'code', 'description', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Admin Block, Tech Park, Academic Block'}),
            'code': forms.TextInput(attrs={'placeholder': 'e.g. TECH_PARK, ADMIN_BLOCK'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional details about facilities in this block...'}),
        }


class IssueFormFieldForm(forms.ModelForm):
    options_text = forms.CharField(
        required=False, 
        label='Options (one per line)', 
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Network Issue\nPC Issue\nSEB Exam Issue\nOther'})
    )

    class Meta:
        model = IssueFormField
        fields = (
            'label', 'field_key', 'field_type', 'max_file_size_mb', 'help_text', 'category', 
            'options_text', 'required', 'order', 'is_active',
            'condition_type', 'condition_field_key', 'condition_operator', 'condition_value'
        )
        widgets = {
            'label': forms.TextInput(attrs={'placeholder': 'e.g. Facing Issue In, Which Network Problem?'}),
            'field_key': forms.TextInput(attrs={'placeholder': 'e.g. facing_issue_in, network_problem_type'}),
            'max_file_size_mb': forms.NumberInput(attrs={'placeholder': '5', 'min': 1, 'max': 100}),
            'help_text': forms.TextInput(attrs={'placeholder': 'Short helper note shown below the question'}),
            'condition_field_key': forms.TextInput(attrs={'placeholder': 'Parent field key, e.g. facing_issue_in'}),
            'condition_value': forms.TextInput(attrs={'placeholder': 'Trigger value, e.g. Network Issue or Other'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['max_file_size_mb'].initial = 5
        self.fields['max_file_size_mb'].required = False

        self.fields['category'].empty_label = "Global / General (Applies across all categories)"
        self.fields['category'].required = False
        self.fields['field_key'].required = False  # Can auto-generate from label if left blank
        self.fields['condition_type'].required = False
        self.fields['condition_operator'].required = False
        self.fields['condition_field_key'].required = False
        self.fields['condition_value'].required = False
        self.fields['order'].required = False
        if self.instance and self.instance.pk:
            self.fields['options_text'].initial = '\n'.join(self.instance.options)

    def clean_field_key(self):
        key = self.cleaned_data.get('field_key')
        label = self.cleaned_data.get('label', '')
        if not key and label:
            key = slugify(label).replace('-', '_')
        elif key:
            key = slugify(key).replace('-', '_')
        return key

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.field_key:
            instance.field_key = slugify(instance.label).replace('-', '_')
        instance.options = [item.strip() for item in self.cleaned_data['options_text'].splitlines() if item.strip()]
        if commit:
            instance.save()
        return instance


class ServiceCatalogItemForm(forms.ModelForm):
    class Meta:
        model = ServiceCatalogItem
        fields = ('title', 'description', 'icon', 'category', 'show_on_homepage', 'is_active', 'order')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Brief description of service for normal users'}),
            'icon': forms.TextInput(attrs={'placeholder': '📌 or 🌐 or 💻'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False
        self.fields['category'].empty_label = "General / No preselected category"
        self.fields['description'].required = False
        self.fields['icon'].required = False
        self.fields['order'].required = False

    def clean_icon(self):
        icon = self.cleaned_data.get('icon', '').strip()
        return icon if icon else 'network'

    def clean_order(self):
        order = self.cleaned_data.get('order')
        return order if order is not None else 0


class SolutionArticleForm(forms.ModelForm):
    class Meta:
        model = SolutionArticle
        fields = ('title', 'target_category', 'category', 'summary', 'symptoms', 'solution_steps', 'verification_checklist', 'order', 'is_active')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Campus Wi-Fi Connected but No Internet Access'}),
            'summary': forms.TextInput(attrs={'placeholder': 'Brief description of the problem (1 sentence)'}),
            'symptoms': forms.Textarea(attrs={'rows': 3, 'placeholder': 'One symptom indicator per line...'}),
            'solution_steps': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Step 1: Check your Wi-Fi settings\nStep 2: Turn off Private MAC...\nStep 3: ...'}),
            'verification_checklist': forms.Textarea(attrs={'rows': 3, 'placeholder': 'One verification check per line before submitting a ticket...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False
        self.fields['category'].empty_label = "-- Select Category for Ticket Pre-fill (Optional) --"
        self.fields['symptoms'].required = False
        self.fields['verification_checklist'].required = False
        self.fields['order'].required = False


