from django import forms
from .models import Ticket, TicketStatus, TicketUrgency, IssueFormField, ServiceCatalogItem


from django.utils.text import slugify

class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('title', 'description', 'category', 'urgency', 'location', 'attachment')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., WiFi disconnected in CS Lab 2'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Provide details about what happened...'}),
            'location': forms.TextInput(attrs={'placeholder': 'e.g., Block B - Room 204 / Lab 3'}),
            'category': forms.HiddenInput(),
        }

    def __init__(self, *args, issue_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False
        self.fields['description'].required = False

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
        
        global_max_mb = max_size_map.get('attachment', 5)
        
        attachment = cleaned_data.get('attachment')
        if attachment and hasattr(attachment, 'size'):
            limit_bytes = global_max_mb * 1024 * 1024
            if attachment.size > limit_bytes:
                self.add_error('attachment', f"File size ({attachment.size / (1024*1024):.1f} MB) exceeds maximum allowed limit of {global_max_mb} MB.")

        for key, max_mb in max_size_map.items():
            if key != 'attachment':
                file_obj = cleaned_data.get(key)
                if file_obj and hasattr(file_obj, 'size'):
                    limit_bytes = max_mb * 1024 * 1024
                    if file_obj.size > limit_bytes:
                        self.add_error(key, f"File size ({file_obj.size / (1024*1024):.1f} MB) exceeds maximum allowed limit of {max_mb} MB.")

        return cleaned_data


class AdminTicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('title', 'description', 'category', 'urgency', 'location', 'assigned_group', 'assigned_technician', 'status', 'is_sla_breached')
        widgets = {'description': forms.Textarea(attrs={'rows': 6})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_technician'].queryset = self.fields['assigned_technician'].queryset.filter(
            profile__role='technician', profile__is_active=True, profile__is_suspended=False
        ).order_by('username')


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
        self.fields['category'].empty_label = "General / No preselected category"

