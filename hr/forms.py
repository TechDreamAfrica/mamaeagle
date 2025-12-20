from django import forms
from .models import Employee


class EmployeeForm(forms.ModelForm):
    """Custom form for Employee with proper date widgets"""
    
    # Define common departments
    DEPARTMENT_CHOICES = [
        ('', '---------'),
        ('Accounting', 'Accounting'),
        ('Administration', 'Administration'),
        ('Customer Service', 'Customer Service'),
        ('Engineering', 'Engineering'),
        ('Finance', 'Finance'),
        ('Human Resources', 'Human Resources'),
        ('Information Technology', 'Information Technology'),
        ('Legal', 'Legal'),
        ('Marketing', 'Marketing'),
        ('Operations', 'Operations'),
        ('Research & Development', 'Research & Development'),
        ('Sales', 'Sales'),
        ('Supply Chain', 'Supply Chain'),
    ]
    
    department = forms.ChoiceField(
        choices=DEPARTMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-input'}),
        required=True
    )
    
    class Meta:
        model = Employee
        fields = [
            'user', 'employee_id', 'employment_type', 'status', 'job_title', 'department',
            'manager', 'hire_date', 'termination_date', 'base_salary', 'hourly_rate', 
            'tax_id', 'tax_exemptions', 'health_insurance', 'dental_insurance', 
            'vision_insurance', 'retirement_plan', 'emergency_contact_name', 
            'emergency_contact_phone', 'emergency_contact_relationship'
        ]
        widgets = {
            'hire_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input',
                'placeholder': 'YYYY-MM-DD'
            }),
            'termination_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input',
                'placeholder': 'YYYY-MM-DD'
            }),
            'user': forms.Select(attrs={'class': 'form-input'}),
            'employee_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., EMP001'
            }),
            'employment_type': forms.Select(attrs={'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
            'job_title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Software Engineer'
            }),
            'manager': forms.Select(attrs={'class': 'form-input'}),
            'base_salary': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'hourly_rate': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'XXX-XX-XXXX'
            }),
            'tax_exemptions': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'max': '99'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Full Name'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '(XXX) XXX-XXXX'
            }),
            'emergency_contact_relationship': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Spouse, Parent'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Filter user choices based on company
        if self.request:
            # Get the company for the current user
            company = None
            if hasattr(self.request, 'company') and self.request.company:
                company = self.request.company
            else:
                from accounts.models import UserCompany
                try:
                    user_company = UserCompany.objects.filter(
                        user=self.request.user,
                        is_active=True
                    ).first()
                    if user_company:
                        company = user_company.company
                except:
                    pass
            
            if company:
                # Get users associated with this company
                from accounts.models import UserCompany
                company_users = UserCompany.objects.filter(
                    company=company,
                    is_active=True
                ).values_list('user', flat=True)
                
                # Filter user field to only show company users
                from django.contrib.auth import get_user_model
                User = get_user_model()
                self.fields['user'].queryset = User.objects.filter(id__in=company_users)
                
                # Filter manager field to only show existing employees from same company
                self.fields['manager'].queryset = self.Meta.model.objects.filter(company=company)
            else:
                # If no company found, show no users (or all users as fallback)
                from django.contrib.auth import get_user_model
                User = get_user_model()
                self.fields['user'].queryset = User.objects.none()
                self.fields['manager'].queryset = self.Meta.model.objects.none()

        # Import User model at the top of the method
        from django.contrib.auth import get_user_model
        from accounts.models import UserCompany
        User = get_user_model()

        # Filter users and managers by company if request is available
        if self.request and hasattr(self.request, 'company') and self.request.company:
            # Get company user IDs - users added by the logged-in user to their company
            company_user_ids = UserCompany.objects.filter(
                company=self.request.company,
                is_active=True
            ).values_list('user_id', flat=True)

            # For new employee creation, show only company users who don't have an employee record yet
            # For editing, show all company users
            if not self.instance.pk:
                # Creating new employee - show only company users who don't have an employee record yet
                # Exclude users who already have an employee record in this company
                existing_employee_user_ids = Employee.objects.filter(
                    company=self.request.company
                ).values_list('user_id', flat=True)

                available_users = User.objects.filter(
                    id__in=company_user_ids
                ).exclude(id__in=existing_employee_user_ids).exclude(
                    id=self.request.user.id  # Exclude the logged-in user
                )

                self.fields['user'].queryset = available_users
                self.fields['user'].help_text = 'Only users added to your company who don\'t have an employee record yet are shown'
            else:
                # Editing existing employee - show all company users
                company_users = User.objects.filter(
                    id__in=company_user_ids
                ).distinct()

                self.fields['user'].queryset = company_users

            # Filter managers to only employees in this company
            self.fields['manager'].queryset = Employee.objects.filter(
                company=self.request.company
            )
        else:
            # No company available - show error message in help text
            self.fields['user'].queryset = User.objects.none()
            self.fields['user'].help_text = 'No company associated with your account. Please contact administrator.'

        # Get existing departments from database
        existing_depts = Employee.objects.values_list('department', flat=True).distinct().order_by('department')
        existing_depts = [dept for dept in existing_depts if dept]  # Filter out empty values

        # Combine predefined choices with existing departments
        dept_set = set([choice[0] for choice in self.DEPARTMENT_CHOICES if choice[0]])
        dept_set.update(existing_depts)

        # Create sorted choices list
        dept_choices = [('', '---------')] + [(dept, dept) for dept in sorted(dept_set)]
        self.fields['department'].choices = dept_choices

        # If editing existing employee, make sure their department is in choices
        if self.instance and self.instance.pk and self.instance.department:
            if not any(choice[0] == self.instance.department for choice in dept_choices):
                dept_choices.append((self.instance.department, self.instance.department))
                self.fields['department'].choices = dept_choices
    
    def clean_hire_date(self):
        """Validate hire date is not in the future"""
        from datetime import date
        hire_date = self.cleaned_data.get('hire_date')
        if hire_date and hire_date > date.today():
            raise forms.ValidationError('Hire date cannot be in the future.')
        return hire_date
    
    def clean(self):
        """Validate termination date is after hire date"""
        cleaned_data = super().clean()
        hire_date = cleaned_data.get('hire_date')
        termination_date = cleaned_data.get('termination_date')
        
        if hire_date and termination_date:
            if termination_date <= hire_date:
                raise forms.ValidationError({
                    'termination_date': 'Termination date must be after hire date.'
                })
        
        return cleaned_data
