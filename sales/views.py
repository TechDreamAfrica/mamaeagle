from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from common.bulk_operations import bulk_delete_view, bulk_export_view

from .models import (
    SalesTerritory, SalesRep, Lead, Opportunity, 
    SalesActivity, Commission
)
from .forms import LeadForm, OpportunityForm, SalesActivityForm


# Dashboard and Overview Views
@login_required
def sales_dashboard(request):
    """Sales dashboard with key metrics and charts."""
    # Get user's companies
    from accounts.models import UserCompany
    user_companies = UserCompany.objects.filter(
        user=request.user,
        is_active=True
    ).values_list('company_id', flat=True)
    
    # Get date ranges
    today = timezone.now().date()
    this_month_start = timezone.make_aware(datetime.combine(today.replace(day=1), datetime.min.time()))
    last_month_start = timezone.make_aware(datetime.combine((today.replace(day=1) - timedelta(days=1)).replace(day=1), datetime.min.time()))
    this_year_start = timezone.make_aware(datetime.combine(today.replace(month=1, day=1), datetime.min.time()))
    
    # Key metrics - filtered by user's companies
    total_leads = Lead.objects.filter(
        company_id__in=user_companies,
        created_at__gte=this_month_start
    ).count()
    total_opportunities = Opportunity.objects.filter(
        Q(lead__company_id__in=user_companies) | Q(sales_rep__company_id__in=user_companies),
        created_at__gte=this_month_start
    ).count()
    
    # Revenue metrics - filtered by user's companies
    won_opportunities = Opportunity.objects.filter(
        Q(lead__company_id__in=user_companies) | Q(sales_rep__company_id__in=user_companies),
        stage='closed_won',
        actual_close_date__gte=this_month_start.date()
    )
    monthly_revenue = won_opportunities.aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Pipeline value - filtered by user's companies
    pipeline_value = Opportunity.objects.filter(
        Q(lead__company_id__in=user_companies) | Q(sales_rep__company_id__in=user_companies),
        stage__in=['qualification', 'needs_analysis', 'proposal', 'negotiation']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Conversion rates - filtered by user's companies
    leads_this_month = Lead.objects.filter(
        company_id__in=user_companies,
        created_at__gte=this_month_start
    ).count()
    converted_leads = Lead.objects.filter(
        company_id__in=user_companies,
        created_at__gte=this_month_start,
        status='converted'
    ).count()
    conversion_rate = (converted_leads / leads_this_month * 100) if leads_this_month > 0 else 0
    
    # Recent activities - filtered by user's companies
    recent_activities = SalesActivity.objects.filter(
        Q(lead__company_id__in=user_companies) |
        Q(opportunity__lead__company_id__in=user_companies) |
        Q(sales_rep__company_id__in=user_companies)
    ).select_related(
        'lead', 'opportunity', 'sales_rep'
    ).order_by('-created_at')[:10]
    
    # Top performers - filtered by user's companies
    top_sales_reps = SalesRep.objects.filter(
        company_id__in=user_companies
    ).annotate(
        monthly_sales=Sum(
            'opportunity__amount',
            filter=Q(
                opportunity__stage='closed_won',
                opportunity__actual_close_date__gte=this_month_start
            )
        )
    ).order_by('-monthly_sales')[:5]
    
    context = {
        'total_leads': total_leads,
        'total_opportunities': total_opportunities,
        'monthly_revenue': monthly_revenue,
        'pipeline_value': pipeline_value,
        'conversion_rate': round(conversion_rate, 1),
        'recent_activities': recent_activities,
        'top_sales_reps': top_sales_reps,
    }
    
    return render(request, 'sales/dashboard.html', context)


# Lead Views
class LeadListView(LoginRequiredMixin, ListView):
    """List all leads with filtering and search."""
    model = Lead
    template_name = 'sales/lead_list.html'
    context_object_name = 'leads'
    paginate_by = 20
    
    def get_queryset(self):
        # Get user's companies
        from accounts.models import UserCompany
        user_companies = UserCompany.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('company_id', flat=True)
        
        # Only show leads from user's companies
        queryset = Lead.objects.filter(
            company_id__in=user_companies
        ).select_related('assigned_to', 'territory', 'company').order_by('-created_at')
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(company__name__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by source
        source = self.request.GET.get('source')
        if source:
            queryset = queryset.filter(source=source)
        
        # Filter by sales rep (assigned_to)
        sales_rep = self.request.GET.get('sales_rep')
        if sales_rep:
            queryset = queryset.filter(assigned_to_id=sales_rep)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user's companies
        from accounts.models import UserCompany
        user_companies = UserCompany.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('company_id', flat=True)
        
        # Only show sales reps from user's companies
        context['sales_reps'] = SalesRep.objects.filter(
            company_id__in=user_companies,
            is_active=True
        )
        context['lead_statuses'] = Lead.LEAD_STATUS
        context['lead_sources'] = Lead.LEAD_SOURCES
        return context


class LeadDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a single lead."""
    model = Lead
    template_name = 'sales/lead_detail.html'
    context_object_name = 'lead'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activities'] = self.object.activities.order_by('-created_at')
        context['opportunities'] = self.object.opportunity_set.all()
        return context


class LeadCreateView(LoginRequiredMixin, CreateView):
    """Create a new lead."""
    model = Lead
    form_class = LeadForm
    template_name = 'sales/lead_form.html'
    success_url = reverse_lazy('sales:lead_list')
    
    def get_form_kwargs(self):
        """Pass the current user to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Lead created successfully!')
        return super().form_valid(form)


class LeadUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing lead."""
    model = Lead
    form_class = LeadForm
    template_name = 'sales/lead_form.html'
    success_url = reverse_lazy('sales:lead_list')
    
    def get_form_kwargs(self):
        """Pass the current user to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Lead updated successfully!')
        return super().form_valid(form)


# Opportunity Views
class OpportunityListView(LoginRequiredMixin, ListView):
    """List all opportunities with filtering."""
    model = Opportunity
    template_name = 'sales/opportunity_list.html'
    context_object_name = 'opportunities'
    paginate_by = 20
    
    def get_queryset(self):
        # Get user's companies
        from accounts.models import UserCompany
        user_companies = UserCompany.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('company_id', flat=True)
        
        # Only show opportunities where the lead's company is in user's companies
        # or where sales_rep's company is in user's companies
        queryset = Opportunity.objects.filter(
            Q(lead__company_id__in=user_companies) |
            Q(sales_rep__company_id__in=user_companies)
        ).select_related(
            'lead', 'sales_rep', 'lead__company'
        ).order_by('-created_at')
        
        # Filter by stage
        stage = self.request.GET.get('stage')
        if stage:
            queryset = queryset.filter(stage=stage)
        
        # Filter by sales rep
        sales_rep = self.request.GET.get('sales_rep')
        if sales_rep:
            queryset = queryset.filter(sales_rep_id=sales_rep)
        
        # Filter by amount range
        min_amount = self.request.GET.get('min_amount')
        max_amount = self.request.GET.get('max_amount')
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)
        if max_amount:
            queryset = queryset.filter(amount__lte=max_amount)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user's companies
        from accounts.models import UserCompany
        user_companies = UserCompany.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('company_id', flat=True)
        
        # Only show sales reps from user's companies
        context['sales_reps'] = SalesRep.objects.filter(
            company_id__in=user_companies,
            is_active=True
        )
        context['opportunity_stages'] = Opportunity.STAGE_CHOICES
        
        # Calculate totals
        queryset = self.get_queryset()
        context['total_amount'] = queryset.aggregate(
            total=Sum('amount')
        )['total'] or 0
        context['total_weighted'] = sum(
            opp.weighted_amount for opp in queryset
        )
        
        return context


class OpportunityDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a single opportunity."""
    model = Opportunity
    template_name = 'sales/opportunity_detail.html'
    context_object_name = 'opportunity'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activities'] = self.object.salesactivity_set.order_by('-created_at')
        return context


class OpportunityCreateView(LoginRequiredMixin, CreateView):
    """Create a new opportunity."""
    model = Opportunity
    form_class = OpportunityForm
    template_name = 'sales/opportunity_form.html'
    success_url = reverse_lazy('sales:opportunity_list')
    
    def get_form_kwargs(self):
        """Pass the current user to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Opportunity created successfully!')
        return super().form_valid(form)


class OpportunityUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing opportunity."""
    model = Opportunity
    form_class = OpportunityForm
    template_name = 'sales/opportunity_form.html'
    success_url = reverse_lazy('sales:opportunity_list')
    
    def get_form_kwargs(self):
        """Pass the current user to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Auto-set actual_close_date if stage is closed won or closed lost
        if form.instance.stage in ['closed_won', 'closed_lost'] and not form.instance.actual_close_date:
            form.instance.actual_close_date = timezone.now().date()
        
        messages.success(self.request, 'Opportunity updated successfully!')
        return super().form_valid(form)


# Sales Activity Views
class SalesActivityListView(LoginRequiredMixin, ListView):
    """List all sales activities."""
    model = SalesActivity
    template_name = 'sales/activity_list.html'
    context_object_name = 'activities'
    paginate_by = 30
    
    def get_queryset(self):
        # Get user's companies
        from accounts.models import UserCompany
        user_companies = UserCompany.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('company_id', flat=True)
        
        # Only show activities related to user's companies
        return SalesActivity.objects.filter(
            Q(lead__company_id__in=user_companies) |
            Q(opportunity__lead__company_id__in=user_companies) |
            Q(sales_rep__company_id__in=user_companies)
        ).select_related(
            'lead', 'opportunity', 'sales_rep', 'lead__company'
        ).order_by('-created_at')


class SalesActivityCreateView(LoginRequiredMixin, CreateView):
    """Create a new sales activity."""
    model = SalesActivity
    form_class = SalesActivityForm
    template_name = 'sales/activity_form.html'
    success_url = reverse_lazy('sales:activity_list')
    
    def get_form_kwargs(self):
        """Pass the current user to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Activity logged successfully!')
        return super().form_valid(form)


# Sales Rep Views
class SalesRepListView(LoginRequiredMixin, ListView):
    """List all sales representatives."""
    model = SalesRep
    template_name = 'sales/sales_rep_list.html'
    context_object_name = 'sales_reps'
    
    def get_queryset(self):
        return SalesRep.objects.select_related('user', 'territory').annotate(
            total_leads=Count('lead_set'),
            total_opportunities=Count('opportunity_set'),
            total_sales=Sum(
                'opportunity_set__amount',
                filter=Q(opportunity_set__stage='closed_won')
            )
        )


class SalesRepDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a sales representative."""
    model = SalesRep
    template_name = 'sales/sales_rep_detail.html'
    context_object_name = 'sales_rep'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Performance metrics
        today = timezone.now().date()
        this_month_start = timezone.make_aware(datetime.combine(today.replace(day=1), datetime.min.time()))
        
        context['monthly_leads'] = self.object.lead_set.filter(
            created_at__gte=this_month_start
        ).count()
        
        context['monthly_opportunities'] = self.object.opportunity_set.filter(
            created_at__gte=this_month_start
        ).count()
        
        context['monthly_sales'] = self.object.opportunity_set.filter(
            stage='closed_won',
            actual_close_date__gte=this_month_start.date()
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        context['pipeline_value'] = self.object.opportunity_set.filter(
            stage__in=['qualification', 'needs_analysis', 'proposal', 'negotiation']
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        context['recent_activities'] = self.object.salesactivity_set.order_by(
            '-created_at'
        )[:10]
        
        context['commissions'] = self.object.commission_set.order_by(
            '-created_at'
        )[:10]
        
        return context


# Commission Views
class CommissionListView(LoginRequiredMixin, ListView):
    """List all commissions."""
    model = Commission
    template_name = 'sales/commission_list.html'
    context_object_name = 'commissions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Commission.objects.select_related(
            'sales_rep', 'opportunity'
        ).order_by('-created_at')
        
        # Filter by sales rep
        sales_rep = self.request.GET.get('sales_rep')
        if sales_rep:
            queryset = queryset.filter(sales_rep_id=sales_rep)
        
        # Filter by status (based on is_paid field)
        status = self.request.GET.get('status')
        if status == 'paid':
            queryset = queryset.filter(is_paid=True)
        elif status == 'unpaid':
            queryset = queryset.filter(is_paid=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sales_reps'] = SalesRep.objects.filter(is_active=True)
        # Commission statuses based on is_paid field
        context['commission_statuses'] = [
            ('', 'All'),
            ('paid', 'Paid'),
            ('unpaid', 'Unpaid'),
        ]
        
        # Calculate totals
        queryset = self.get_queryset()
        context['total_commission'] = queryset.aggregate(
            total=Sum('commission_amount')
        )['total'] or 0
        
        return context


# AJAX Views
@login_required
def convert_lead_to_opportunity(request, lead_id):
    """Convert a lead to an opportunity."""
    lead = get_object_or_404(Lead, id=lead_id)
    
    if request.method == 'POST':
        from datetime import datetime, timedelta
        
        # Prevent converting already converted leads
        if lead.status == 'won':
            messages.warning(request, 'This lead has already been converted to an opportunity.')
            return redirect('sales:lead_detail', pk=lead.id)
        
        # Create opportunity from lead with all available data
        opportunity = Opportunity.objects.create(
            lead=lead,
            name=f"{lead.company or lead.full_name} Opportunity",
            description=f"Converted from lead: {lead.full_name}\n\n{lead.description}",
            customer_name=lead.full_name,
            customer_email=lead.email,
            customer_phone=lead.phone,
            customer_company=lead.company,
            amount=lead.estimated_value or Decimal('0.00'),
            probability=lead.probability,
            expected_close_date=lead.expected_close_date or (datetime.now().date() + timedelta(days=30)),
            stage='qualification',
            sales_rep=lead.assigned_to,
            territory=lead.territory,
        )
        
        # Update lead status to won (converted)
        lead.status = 'won'
        lead.save()
        
        # Log activity if SalesActivity model is available
        try:
            SalesActivity.objects.create(
                activity_type='meeting',
                subject='Lead Converted to Opportunity',
                description=f'Lead {lead.full_name} from {lead.company or "N/A"} converted to opportunity',
                lead=lead,
                opportunity=opportunity,
                sales_rep=lead.assigned_to,
                outcome='positive'
            )
        except:
            pass  # If SalesActivity has different fields
        
        messages.success(request, f'Lead successfully converted to opportunity: {opportunity.name}')
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Lead converted to opportunity successfully!',
                'opportunity_id': opportunity.id,
                'redirect_url': reverse('sales:opportunity_detail', kwargs={'pk': opportunity.id})
            })
        
        return redirect('sales:opportunity_detail', pk=opportunity.id)
    
    # GET request - show conversion confirmation page
    context = {
        'lead': lead,
    }
    return render(request, 'sales/lead_convert_confirm.html', context)


@login_required
def sales_pipeline_data(request):
    """Get sales pipeline data for charts."""
    pipeline_data = {}
    
    for stage, stage_name in Opportunity.OPPORTUNITY_STAGES:
        opportunities = Opportunity.objects.filter(stage=stage)
        pipeline_data[stage_name] = {
            'count': opportunities.count(),
            'value': opportunities.aggregate(total=Sum('amount'))['total'] or 0
        }
    
    return JsonResponse(pipeline_data)


@login_required
def sales_performance_data(request):
    """Get sales performance data for charts."""
    from calendar import monthrange
    
    # Monthly sales data for the last 12 months
    today = timezone.now().date()
    months_data = []
    
    for i in range(11, -1, -1):  # Start from 11 months ago to current month
        # Calculate the target month and year
        target_month = today.month - i
        target_year = today.year
        
        # Adjust year if month goes negative
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        # Month start (first day of the month)
        month_start = today.replace(year=target_year, month=target_month, day=1)
        
        # Month end (last day of the month)
        last_day = monthrange(target_year, target_month)[1]
        month_end = today.replace(year=target_year, month=target_month, day=last_day)
        
        # For current month, use today as the end date
        if i == 0:
            month_end = today
        
        monthly_sales = Opportunity.objects.filter(
            stage='closed_won',
            actual_close_date__gte=month_start,
            actual_close_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        months_data.append({
            'month': month_start.strftime('%Y-%m'),
            'sales': float(monthly_sales)
        })
    
    return JsonResponse({'monthly_sales': months_data})


# Territory Views
class TerritoryListView(LoginRequiredMixin, ListView):
    """List all sales territories."""
    model = SalesTerritory
    template_name = 'sales/territory_list.html'
    context_object_name = 'territories'
    
    def get_queryset(self):
        return SalesTerritory.objects.annotate(
            total_leads=Count('lead'),
            total_sales_reps=Count('salesrep'),
            total_sales=Sum(
                'lead__opportunity__amount',
                filter=Q(lead__opportunity__stage='closed_won')
            )
        )


class TerritoryDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a sales territory."""
    model = SalesTerritory
    template_name = 'sales/territory_detail.html'
    context_object_name = 'territory'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sales_reps'] = self.object.sales_reps.filter(is_active=True)
        context['leads'] = self.object.leads.order_by('-created_at')[:20]
        context['total_leads'] = self.object.leads.count()
        context['total_opportunities'] = Opportunity.objects.filter(
            lead__territory=self.object
        ).count()
        return context


# Bulk Operations
@login_required
def bulk_delete_leads(request):
    """Bulk delete leads"""
    return bulk_delete_view(
        request=request,
        model=Lead,
        filter_kwargs={'created_by': request.user},
        success_message="leads deleted successfully"
    )


@login_required  
def bulk_export_leads(request):
    """Bulk export leads to CSV"""
    return bulk_export_view(
        request=request,
        model=Lead,
        filter_kwargs={'created_by': request.user},
        filename="leads_export"
    )


@login_required
def bulk_delete_opportunities(request):
    """Bulk delete opportunities"""
    return bulk_delete_view(
        request=request,
        model=Opportunity,
        filter_kwargs={'created_by': request.user},
        success_message="opportunities deleted successfully"
    )


@login_required  
def bulk_export_opportunities(request):
    """Bulk export opportunities to CSV"""
    return bulk_export_view(
        request=request,
        model=Opportunity,
        filter_kwargs={'created_by': request.user},
        filename="opportunities_export"
    )
