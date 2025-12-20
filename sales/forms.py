from django import forms
from django.contrib.auth import get_user_model
from .models import Lead, Opportunity, SalesActivity, SalesRep
from accounts.models import Company

User = get_user_model()


class LeadForm(forms.ModelForm):
    """
    Custom form for Lead creation/editing with filtered querysets
    Only shows companies and employees that the current user added/has access to
    """
    
    class Meta:
        model = Lead
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'company',
            'title', 'source', 'status', 'lead_score', 'priority', 'territory',
            'assigned_to', 'estimated_value', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
            'estimated_value': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Filter companies - only show companies the user has access to
            # Get companies where user is a member via UserCompany
            from accounts.models import UserCompany
            user_companies = UserCompany.objects.filter(
                user=user,
                is_active=True
            ).values_list('company_id', flat=True)
            
            # Filter to only companies the user has access to
            self.fields['company'].queryset = Company.objects.filter(
                id__in=user_companies
            )
            
            # Filter assigned_to - only show SalesRep from the user's companies
            self.fields['assigned_to'].queryset = SalesRep.objects.filter(
                company_id__in=user_companies,
                is_active=True
            )
            
            # Filter territory - only show territories from user's companies
            if 'territory' in self.fields:
                from .models import SalesTerritory
                self.fields['territory'].queryset = SalesTerritory.objects.filter(
                    company_id__in=user_companies,
                    is_active=True
                )
        
        # Add Bootstrap classes for better styling
        for field_name, field in self.fields.items():
            if field_name not in ['notes']:
                field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs['class'] = 'form-control'


class OpportunityForm(forms.ModelForm):
    """
    Custom form for Opportunity creation/editing with filtered querysets
    """
    
    class Meta:
        model = Opportunity
        fields = [
            'name', 'lead', 'amount', 'probability',
            'stage', 'expected_close_date', 'sales_rep', 'next_step',
            'description', 'competitors'
        ]
        widgets = {
            'expected_close_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'next_step': forms.Textarea(attrs={'rows': 2}),
            'competitors': forms.Textarea(attrs={'rows': 2}),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Get user's companies
            from accounts.models import UserCompany
            user_companies = UserCompany.objects.filter(
                user=user,
                is_active=True
            ).values_list('company_id', flat=True)
            
            # Filter lead - only leads from user's companies
            self.fields['lead'].queryset = Lead.objects.filter(
                company_id__in=user_companies
            )
            
            # Filter sales_rep - only sales reps from user's companies
            self.fields['sales_rep'].queryset = SalesRep.objects.filter(
                company_id__in=user_companies,
                is_active=True
            )
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class SalesActivityForm(forms.ModelForm):
    """
    Custom form for Sales Activity with filtered querysets
    """
    
    class Meta:
        model = SalesActivity
        fields = [
            'activity_type', 'subject', 'description', 'lead',
            'opportunity', 'sales_rep', 'activity_date', 'duration',
            'outcome', 'requires_follow_up', 'follow_up_date'
        ]
        widgets = {
            'activity_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'outcome': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Get user's companies
            from accounts.models import UserCompany
            user_companies = UserCompany.objects.filter(
                user=user,
                is_active=True
            ).values_list('company_id', flat=True)
            
            # Filter lead - only leads from user's companies
            if 'lead' in self.fields:
                self.fields['lead'].queryset = Lead.objects.filter(
                    company_id__in=user_companies
                )
            
            # Filter opportunity - only opportunities where the lead's company is in user's companies
            if 'opportunity' in self.fields:
                self.fields['opportunity'].queryset = Opportunity.objects.filter(
                    lead__company_id__in=user_companies
                )
            
            # Filter sales_rep - only sales reps from user's companies
            if 'sales_rep' in self.fields:
                self.fields['sales_rep'].queryset = SalesRep.objects.filter(
                    company_id__in=user_companies,
                    is_active=True
                )
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
