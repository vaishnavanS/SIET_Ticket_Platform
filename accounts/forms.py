from django import forms
from django.contrib.auth.models import User
from .models import UserRole, UserProfile, TechnicianGroup
from tickets.models import Category


class AdminUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password_confirmation = forms.CharField(widget=forms.PasswordInput, label='Confirm password')
    role = forms.ChoiceField(choices=UserRole.choices)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'password_confirmation', 'role')

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('password_confirmation'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if self.cleaned_data['role'] == UserRole.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data['role']
            profile.is_active = True
            profile.is_suspended = False
            profile.save()
        return user


class TechnicianGroupForm(forms.ModelForm):
    class Meta:
        model = TechnicianGroup
        fields = ('name', 'description', 'max_tickets_per_tech', 'technicians')
        widgets = {'technicians': forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['technicians'].queryset = User.objects.filter(
            profile__role=UserRole.TECHNICIAN,
            profile__is_active=True,
            profile__is_suspended=False,
        ).order_by('username')


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'description', 'assigned_group')
