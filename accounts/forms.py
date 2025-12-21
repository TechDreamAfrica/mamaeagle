from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Company, UserCompany

User = get_user_model()


class DreamBizAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form with enhanced styling
    """
    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'Username or Email',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        })
    )


class DreamBizUserCreationForm(UserCreationForm):
    """
    Enhanced user registration form
    """
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'First Name',
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'Last Name',
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'Email Address',
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'Username',
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'Password',
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'Confirm Password',
        })
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 rounded border-gray-300 text-dreambiz-600 focus:ring-dreambiz-600',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        from datetime import date
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.role = 'admin'  # First user becomes admin of their company
        
        if commit:
            user.save()
            
            # Create default company with user's name
            company_name = f"{user.first_name} {user.last_name}'s Company"
            company = Company.objects.create(
                name=company_name,
                email=user.email,
                fiscal_year_start=date(date.today().year, 1, 1),  # Default fiscal year start
                created_by=user
            )
            
            # Add user to company as admin
            from .models import UserCompany
            UserCompany.objects.create(
                user=user,
                company=company,
                role='admin'
            )
        
        return user


class DreamBizPasswordResetForm(PasswordResetForm):
    """
    Custom password reset form
    """
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'Email Address',
            'autocomplete': 'email',
        })
    )


class DreamBizSetPasswordForm(SetPasswordForm):
    """
    Custom set password form
    """
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'New Password',
            'autocomplete': 'new-password',
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            'placeholder': 'Confirm New Password',
            'autocomplete': 'new-password',
        })
    )


class UserProfileForm(forms.ModelForm):
    """
    User profile update form
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'department']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            }),
            'department': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-dreambiz-600 sm:text-sm sm:leading-6 px-3',
            }),
        }


class UserProfileDetailForm(forms.ModelForm):
    """
    Extended user profile form with additional fields
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'department', 
                  'date_of_birth', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-dreambiz-500 focus:ring-dreambiz-500',
                'placeholder': 'First Name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-dreambiz-500 focus:ring-dreambiz-500',
                'placeholder': 'Last Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-dreambiz-500 focus:ring-dreambiz-500',
                'placeholder': 'email@example.com',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-dreambiz-500 focus:ring-dreambiz-500',
                'placeholder': '+1234567890',
            }),
            'department': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-dreambiz-500 focus:ring-dreambiz-500',
                'placeholder': 'Department',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-dreambiz-500 focus:ring-dreambiz-500',
                'type': 'date',
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-dreambiz-50 file:text-dreambiz-700 hover:file:bg-dreambiz-100',
            }),
        }


class UserPreferencesForm(forms.ModelForm):
    """
    User preferences and settings form
    """
    class Meta:
        model = User
        fields = ['ai_insights_enabled']
        widgets = {
            'ai_insights_enabled': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border-gray-300 text-dreambiz-600 focus:ring-dreambiz-500',
            }),
        }


class PasswordChangeForm(forms.Form):
    """
    Custom password change form
    """
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-dreambiz-500 focus:ring-dreambiz-500',
            'placeholder': 'Current Password',
        }),
        label='Current Password'
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-dreambiz-500 focus:ring-dreambiz-500',
            'placeholder': 'New Password',
        }),
        label='New Password',
        min_length=8,
        help_text='Password must be at least 8 characters long.'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-dreambiz-500 focus:ring-dreambiz-500',
            'placeholder': 'Confirm New Password',
        }),
        label='Confirm Password'
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise ValidationError('Current password is incorrect.')
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError('New passwords do not match.')
        
        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()
        return self.user


class NotificationPreferencesForm(forms.Form):
    """
    Notification preferences form
    """
    email_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 rounded border-gray-300 text-dreambiz-600 focus:ring-dreambiz-500',
        }),
        label='Email Notifications'
    )
    invoice_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 rounded border-gray-300 text-dreambiz-600 focus:ring-dreambiz-500',
        }),
        label='Invoice Status Updates'
    )
    expense_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 rounded border-gray-300 text-dreambiz-600 focus:ring-dreambiz-500',
        }),
        label='Expense Approvals'
    )
    report_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 rounded border-gray-300 text-dreambiz-600 focus:ring-dreambiz-500',
        }),
        label='Report Generation'
    )
    ai_insights_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 rounded border-gray-300 text-dreambiz-600 focus:ring-dreambiz-500',
        }),
        label='AI Insights & Recommendations'
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        # Load existing preferences
        prefs = user.notification_preferences or {}
        self.fields['email_notifications'].initial = prefs.get('email_notifications', True)
        self.fields['invoice_notifications'].initial = prefs.get('invoice_notifications', True)
        self.fields['expense_notifications'].initial = prefs.get('expense_notifications', True)
        self.fields['report_notifications'].initial = prefs.get('report_notifications', True)
        self.fields['ai_insights_notifications'].initial = prefs.get('ai_insights_notifications', True)

    def save(self):
        self.user.notification_preferences = {
            'email_notifications': self.cleaned_data['email_notifications'],
            'invoice_notifications': self.cleaned_data['invoice_notifications'],
            'expense_notifications': self.cleaned_data['expense_notifications'],
            'report_notifications': self.cleaned_data['report_notifications'],
            'ai_insights_notifications': self.cleaned_data['ai_insights_notifications'],
        }
        self.user.save()
        return self.user


class CompanyCreationForm(forms.ModelForm):
    """
    Form for creating a new company
    """
    # Add field to select user to assign as company owner
    assign_to_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username'),
        empty_label="Select User to Assign as Owner",
        required=True,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
        }),
        help_text="Select which user will be the owner of this company"
    )
    
    class Meta:
        model = Company
        fields = ['name', 'email', 'phone', 'address_line_1', 'address_line_2', 'city', 'state', 'country', 'fiscal_year_start']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Company Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'company@example.com',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '+1234567890',
            }),
            'address_line_1': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Street Address',
            }),
            'address_line_2': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Apartment, suite, etc. (optional)',
            }),
            'city': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'City',
            }),
            'state': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'State/Province',
            }),
            'country': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Country',
            }),
            'fiscal_year_start': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # Allow filtering users in the form initialization if needed
        user_queryset = kwargs.pop('user_queryset', None)
        super().__init__(*args, **kwargs)
        
        if user_queryset is not None:
            self.fields['assign_to_user'].queryset = user_queryset
        
        # Set default to show full name and username for better user identification
        self.fields['assign_to_user'].label_from_instance = lambda obj: (
            f"{obj.get_full_name()} ({obj.username})" if obj.get_full_name() 
            else f"{obj.username} ({obj.email})"
        )
    
    def clean_assign_to_user(self):
        user = self.cleaned_data.get('assign_to_user')
        if not user:
            raise ValidationError('Please select a user to assign to this company.')
        return user


class UserCompanyAssignmentForm(forms.ModelForm):
    """
    Form for assigning users to companies with specific roles
    """
    class Meta:
        model = UserCompany
        fields = ['user', 'company', 'role', 'permissions']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'company': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'role': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'permissions': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Additional permissions (optional)',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # Handle company and manager parameters
        company = kwargs.pop('company', None)
        manager = kwargs.pop('manager', None)
        self.request_user = kwargs.pop('request_user', None) or manager
        super().__init__(*args, **kwargs)
        
        # Make permissions field optional
        self.fields['permissions'].required = False
        
        # Set company field if company was provided
        if company:
            self.fields['company'].queryset = Company.objects.filter(id=company.id)
            self.fields['company'].initial = company
            self.fields['company'].widget.attrs['readonly'] = True
        
        # Filter companies based on user permissions
        if self.request_user:
            if self.request_user.is_super_admin:
                # Super admin can assign users to any company
                if not company:
                    self.fields['company'].queryset = Company.objects.all()
            else:
                # Company managers can only assign users to companies they manage
                if not company:
                    self.fields['company'].queryset = self.request_user.get_companies_as_manager()
            
            # Filter users appropriately
            self.fields['user'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # Improve user display
        self.fields['user'].label_from_instance = lambda obj: (
            f"{obj.get_full_name()} ({obj.username})" if obj.get_full_name() 
            else f"{obj.username} ({obj.email})"
        )
    
    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        company = cleaned_data.get('company')
        
        if user and company:
            # Check if user is already assigned to this company
            if UserCompany.objects.filter(user=user, company=company, is_active=True).exists():
                raise ValidationError('This user is already assigned to this company.')
            
            # Check if request user has permission to assign to this company
            if self.request_user and not self.request_user.can_manage_company(company):
                raise ValidationError('You do not have permission to assign users to this company.')
        
        return cleaned_data


class UserRoleUpdateForm(forms.ModelForm):
    """
    Form for updating user roles within a company
    """
    class Meta:
        model = UserCompany
        fields = ['role', 'permissions', 'is_active']
        widgets = {
            'role': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'permissions': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Additional permissions (optional)',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # Handle manager parameter
        manager = kwargs.pop('manager', None)
        super().__init__(*args, **kwargs)


class CreateUserForCompanyForm(forms.ModelForm):
    """
    Form for creating a new user and assigning them to a company
    """
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Password',
        })
    )
    password2 = forms.CharField(
        label='Password Confirmation',
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Confirm Password',
        })
    )
    company_role = forms.ChoiceField(
        choices=UserCompany.COMPANY_ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
        }),
        initial='employee'
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Username',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'First Name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Last Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Email Address',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Phone Number',
            }),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email
    
    def save(self, commit=True, company=None, assigned_by=None):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            
            # Create company assignment if company is provided
            if company:
                UserCompany.objects.create(
                    user=user,
                    company=company,
                    role=self.cleaned_data['company_role'],
                    assigned_by=assigned_by,
                    is_active=True
                )
        
        return user

