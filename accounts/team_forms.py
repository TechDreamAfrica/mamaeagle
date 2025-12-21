"""
Team Management Forms
Forms for inviting users, managing roles, and setting permissions
"""
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .team_models import UserInvitation, TeamMember, RoleTemplate
from .models import Company, UserCompany

User = get_user_model()


class InviteUserForm(forms.ModelForm):
    """
    Form for inviting new users to the company
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'user@example.com'
        })
    )
    
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'First name (optional)'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Last name (optional)'
        })
    )
    
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )
    
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'e.g., Finance, Marketing'
        })
    )
    
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'rows': 4,
            'placeholder': 'Add a personal welcome message (optional)'
        })
    )
    
    class Meta:
        model = UserInvitation
        fields = ['email', 'role', 'department', 'message']
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
    
    def clean_email(self):
        email = self.cleaned_data['email']
        
        # Check if user already exists in the company
        if self.company:
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                if UserCompany.objects.filter(user=existing_user, company=self.company).exists():
                    raise ValidationError(f"{email} is already a member of your company.")
            
            # Check for pending invitations
            pending_invitation = UserInvitation.objects.filter(
                email=email,
                company=self.company,
                status='pending'
            ).first()
            
            if pending_invitation and pending_invitation.is_valid():
                raise ValidationError(f"An invitation has already been sent to {email}.")
        
        return email


class BulkInviteForm(forms.Form):
    """
    Form for inviting multiple users at once
    """
    emails = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'rows': 6,
            'placeholder': 'Enter email addresses, one per line'
        }),
        help_text="Enter one email address per line"
    )
    
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )
    
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Department (optional)'
        })
    )
    
    def clean_emails(self):
        emails_text = self.cleaned_data['emails']
        emails = [email.strip() for email in emails_text.split('\n') if email.strip()]
        
        # Validate each email
        validated_emails = []
        for email in emails:
            try:
                forms.EmailField().clean(email)
                validated_emails.append(email)
            except ValidationError:
                raise ValidationError(f"Invalid email address: {email}")
        
        if not validated_emails:
            raise ValidationError("Please enter at least one valid email address.")
        
        return validated_emails


class ChangeRoleForm(forms.Form):
    """
    Form for changing a user's role
    """
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )
    
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )


class PermissionsForm(forms.ModelForm):
    """
    Form for managing user permissions
    """
    MODULES = [
        ('dashboard', 'Dashboard'),
        ('invoicing', 'Invoicing'),
        ('expenses', 'Expenses'),
        ('inventory', 'Inventory'),
        ('hr', 'Human Resources'),
        ('reports', 'Reports'),
        ('sales', 'Sales & CRM'),
        ('bank_reconciliation', 'Bank Reconciliation'),
        ('ai_insights', 'AI Insights'),
        ('welfare', 'Employee Welfare'),
    ]
    
    ACTIONS = [
        ('view', 'View'),
        ('create', 'Create'),
        ('edit', 'Edit'),
        ('delete', 'Delete'),
    ]
    
    can_invite_users = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        }),
        label="Can invite team members"
    )
    
    can_manage_roles = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        }),
        label="Can manage roles and permissions"
    )
    
    # Make module_permissions not required since we build it from checkboxes
    module_permissions = forms.JSONField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    class Meta:
        model = TeamMember
        fields = ['can_invite_users', 'can_manage_roles']


class RoleTemplateForm(forms.ModelForm):
    """
    Form for creating/editing custom role templates
    """
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'e.g., Sales Manager, Accountant'
        })
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'rows': 3,
            'placeholder': 'Describe this role and its responsibilities'
        })
    )
    
    is_default = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        }),
        label="Set as default role for new members"
    )
    
    class Meta:
        model = RoleTemplate
        fields = ['name', 'description', 'is_default', 'permissions']
        widgets = {
            'permissions': forms.HiddenInput()
        }


class TeamMemberFilterForm(forms.Form):
    """
    Form for filtering team members
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Search by name or email...'
        })
    )
    
    role = forms.ChoiceField(
        required=False,
        choices=[('', 'All Roles')] + list(User.ROLE_CHOICES),
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )
    
    department = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Department'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Status'),
            ('active', 'Active'),
            ('inactive', 'Inactive'),
        ],
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )


class UserBranchAssignmentForm(forms.Form):
    """
    Form for assigning users to branches - DISABLED
    Branch management functionality has been disabled
    """
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Branch functionality disabled - no fields initialized
