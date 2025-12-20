from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.views.generic import (
    ListView, CreateView, DetailView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Q, Count, Sum
from django.utils.decorators import method_decorator

# Import all models
from accounts.models import User, Company, UserCompany
from website.models import (
    ProductCategory, Product, ProductImage, Cart, CartItem, 
    Order, OrderItem, Newsletter, ContactMessage
)
from inventory.models import (
    Category, Supplier, Product as InventoryProduct, ProductSupplier,
    Warehouse, StockMovement, StockLevel, PurchaseOrder, PurchaseOrderItem,
    InventoryCount, InventoryCountItem
)
from invoicing.models import Customer, Invoice, InvoiceItem, Payment
from sales.models import (
    SalesTerritory, SalesRep, Lead, Opportunity, SalesActivity, Commission
)
from expenses.models import (
    ExpenseCategory, Vendor, Expense, ExpenseReport, ExpenseReportItem, MileageLog
)
from hr.models import Employee, PayrollPeriod, Payroll, TimeEntry, LeaveRequest, PerformanceReview
from reports.models import AccountType, Account, JournalEntry, JournalEntryLine, FinancialPeriod, FinancialStatement


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require staff/admin permissions"""
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


@method_decorator(staff_member_required, name='dispatch')
class AdminDashboardView(TemplateView):
    template_name = 'admin_panel/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics for dashboard
        try:
            context.update({
                'stats': {
                    'users_count': User.objects.count(),
                    'companies_count': Company.objects.count(),
                    'website_products_count': Product.objects.count(),
                    'orders_count': Order.objects.count(),
                    'invoices_count': Invoice.objects.count() if Invoice else 0,
                    'customers_count': Customer.objects.count(),
                    'inventory_products_count': InventoryProduct.objects.count(),
                    'employees_count': Employee.objects.count() if Employee else 0,
                    'expenses_count': Expense.objects.count() if Expense else 0,
                    'leads_count': Lead.objects.count() if Lead else 0,
                    'suppliers_count': Supplier.objects.count(),
                    'pending_orders': Order.objects.filter(status='pending').count(),
                    'draft_invoices': Invoice.objects.filter(status='draft').count() if Invoice else 0,
                },
                'recent_orders': Order.objects.order_by('-created_at')[:5],
                'recent_users': User.objects.order_by('-date_joined')[:5],
                'pending_leaves': [],  # Placeholder until HR module is ready
            })
        except Exception as e:
            # Fallback if some models don't exist
            context.update({
                'stats': {
                    'users_count': User.objects.count(),
                    'companies_count': Company.objects.count(),
                    'website_products_count': Product.objects.count(),
                    'orders_count': Order.objects.count(),
                    'invoices_count': 0,
                    'customers_count': Customer.objects.count() if Customer else 0,
                    'inventory_products_count': InventoryProduct.objects.count() if InventoryProduct else 0,
                    'employees_count': 0,
                    'expenses_count': 0,
                    'leads_count': 0,
                    'suppliers_count': Supplier.objects.count() if Supplier else 0,
                    'pending_orders': 0,
                    'draft_invoices': 0,
                },
                'recent_orders': Order.objects.order_by('-created_at')[:5] if Order else [],
                'recent_users': User.objects.order_by('-date_joined')[:5],
                'pending_leaves': [],
            })
        return context


# =============================================================================
# USER MANAGEMENT VIEWS
# =============================================================================

class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'admin_panel/users/list.html'
    context_object_name = 'users'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset


class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    template_name = 'admin_panel/users/form.html'
    fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser']
    success_url = reverse_lazy('admin_panel:user_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'User created successfully!')
        return super().form_valid(form)


class UserDetailView(AdminRequiredMixin, DetailView):
    model = User
    template_name = 'admin_panel/users/detail.html'
    context_object_name = 'user_obj'


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    template_name = 'admin_panel/users/form.html'
    fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser']
    success_url = reverse_lazy('admin_panel:user_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'User updated successfully!')
        return super().form_valid(form)


class UserDeleteView(AdminRequiredMixin, DeleteView):
    model = User
    template_name = 'admin_panel/users/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:user_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'User deleted successfully!')
        return super().delete(request, *args, **kwargs)


# =============================================================================
# COMPANY MANAGEMENT VIEWS
# =============================================================================

class CompanyListView(AdminRequiredMixin, ListView):
    model = Company
    template_name = 'admin_panel/companies/list.html'
    context_object_name = 'companies'
    paginate_by = 25


class CompanyCreateView(AdminRequiredMixin, CreateView):
    model = Company
    template_name = 'admin_panel/companies/form.html'
    fields = ['name', 'email', 'phone', 'address_line_1', 'city', 'country', 'currency']
    success_url = reverse_lazy('admin_panel:company_list')


class CompanyDetailView(AdminRequiredMixin, DetailView):
    model = Company
    template_name = 'admin_panel/companies/detail.html'


class CompanyUpdateView(AdminRequiredMixin, UpdateView):
    model = Company
    template_name = 'admin_panel/companies/form.html'
    fields = ['name', 'email', 'phone', 'address_line_1', 'city', 'country', 'currency']
    success_url = reverse_lazy('admin_panel:company_list')


class CompanyDeleteView(AdminRequiredMixin, DeleteView):
    model = Company
    template_name = 'admin_panel/companies/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:company_list')


# =============================================================================
# WEBSITE PRODUCT MANAGEMENT VIEWS
# =============================================================================

class WebsiteProductListView(AdminRequiredMixin, ListView):
    model = Product
    template_name = 'admin_panel/website/products/list.html'
    context_object_name = 'products'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Product.objects.all().order_by('-created_at')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(sku__icontains=search)
            )
        return queryset


class WebsiteProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    template_name = 'admin_panel/website/products/form.html'
    fields = ['name', 'description', 'sku', 'price', 'category', 'is_active', 'is_featured']
    success_url = reverse_lazy('admin_panel:website_product_list')


class WebsiteProductDetailView(AdminRequiredMixin, DetailView):
    model = Product
    template_name = 'admin_panel/website/products/detail.html'


class WebsiteProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    template_name = 'admin_panel/website/products/form.html'
    fields = ['name', 'description', 'sku', 'price', 'category', 'is_active', 'is_featured']
    success_url = reverse_lazy('admin_panel:website_product_list')


class WebsiteProductDeleteView(AdminRequiredMixin, DeleteView):
    model = Product
    template_name = 'admin_panel/website/products/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:website_product_list')


# =============================================================================
# WEBSITE CATEGORY MANAGEMENT VIEWS
# =============================================================================

class WebsiteCategoryListView(AdminRequiredMixin, ListView):
    model = ProductCategory
    template_name = 'admin_panel/website/categories/list.html'
    context_object_name = 'categories'


class WebsiteCategoryCreateView(AdminRequiredMixin, CreateView):
    model = ProductCategory
    template_name = 'admin_panel/website/categories/form.html'
    fields = ['name', 'description', 'parent', 'is_active']
    success_url = reverse_lazy('admin_panel:website_category_list')


class WebsiteCategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = ProductCategory
    template_name = 'admin_panel/website/categories/form.html'
    fields = ['name', 'description', 'parent', 'is_active']
    success_url = reverse_lazy('admin_panel:website_category_list')


class WebsiteCategoryDeleteView(AdminRequiredMixin, DeleteView):
    model = ProductCategory
    template_name = 'admin_panel/website/categories/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:website_category_list')


# =============================================================================
# ORDER MANAGEMENT VIEWS
# =============================================================================

class OrderListView(AdminRequiredMixin, ListView):
    model = Order
    template_name = 'admin_panel/orders/list.html'
    context_object_name = 'orders'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Order.objects.all().order_by('-created_at')
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class OrderDetailView(AdminRequiredMixin, DetailView):
    model = Order
    template_name = 'admin_panel/orders/detail.html'


class OrderUpdateView(AdminRequiredMixin, UpdateView):
    model = Order
    template_name = 'admin_panel/orders/form.html'
    fields = ['status', 'notes']
    success_url = reverse_lazy('admin_panel:order_list')


class OrderDeleteView(AdminRequiredMixin, DeleteView):
    model = Order
    template_name = 'admin_panel/orders/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:order_list')


# =============================================================================
# INVENTORY PRODUCT MANAGEMENT VIEWS
# =============================================================================

class InventoryProductListView(AdminRequiredMixin, ListView):
    model = InventoryProduct
    template_name = 'admin_panel/inventory/products/list.html'
    context_object_name = 'products'
    paginate_by = 25


class InventoryProductCreateView(AdminRequiredMixin, CreateView):
    model = InventoryProduct
    template_name = 'admin_panel/inventory/products/form.html'
    fields = ['name', 'sku', 'description', 'category', 'unit_of_measure', 'cost_price', 'selling_price', 'reorder_level', 'is_active']
    success_url = reverse_lazy('admin_panel:inventory_product_list')


class InventoryProductDetailView(AdminRequiredMixin, DetailView):
    model = InventoryProduct
    template_name = 'admin_panel/inventory/products/detail.html'


class InventoryProductUpdateView(AdminRequiredMixin, UpdateView):
    model = InventoryProduct
    template_name = 'admin_panel/inventory/products/form.html'
    fields = ['name', 'sku', 'description', 'category', 'unit_of_measure', 'cost_price', 'selling_price', 'reorder_level', 'is_active']
    success_url = reverse_lazy('admin_panel:inventory_product_list')


class InventoryProductDeleteView(AdminRequiredMixin, DeleteView):
    model = InventoryProduct
    template_name = 'admin_panel/inventory/products/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:inventory_product_list')


# =============================================================================
# INVENTORY CATEGORY MANAGEMENT VIEWS
# =============================================================================

class InventoryCategoryListView(AdminRequiredMixin, ListView):
    model = Category
    template_name = 'admin_panel/inventory/categories/list.html'
    context_object_name = 'categories'


class InventoryCategoryCreateView(AdminRequiredMixin, CreateView):
    model = Category
    template_name = 'admin_panel/inventory/categories/form.html'
    fields = ['name', 'description', 'parent_category', 'is_active']
    success_url = reverse_lazy('admin_panel:inventory_category_list')


class InventoryCategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = Category
    template_name = 'admin_panel/inventory/categories/form.html'
    fields = ['name', 'description', 'parent_category', 'is_active']
    success_url = reverse_lazy('admin_panel:inventory_category_list')


class InventoryCategoryDeleteView(AdminRequiredMixin, DeleteView):
    model = Category
    template_name = 'admin_panel/inventory/categories/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:inventory_category_list')


# =============================================================================
# SUPPLIER MANAGEMENT VIEWS
# =============================================================================

class SupplierListView(AdminRequiredMixin, ListView):
    model = Supplier
    template_name = 'admin_panel/suppliers/list.html'
    context_object_name = 'suppliers'
    paginate_by = 25


class SupplierCreateView(AdminRequiredMixin, CreateView):
    model = Supplier
    template_name = 'admin_panel/suppliers/form.html'
    fields = ['name', 'contact_person', 'email', 'phone', 'address', 'city', 'country', 'is_active']
    success_url = reverse_lazy('admin_panel:supplier_list')


class SupplierDetailView(AdminRequiredMixin, DetailView):
    model = Supplier
    template_name = 'admin_panel/suppliers/detail.html'


class SupplierUpdateView(AdminRequiredMixin, UpdateView):
    model = Supplier
    template_name = 'admin_panel/suppliers/form.html'
    fields = ['name', 'contact_person', 'email', 'phone', 'address', 'city', 'country', 'is_active']
    success_url = reverse_lazy('admin_panel:supplier_list')


class SupplierDeleteView(AdminRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'admin_panel/suppliers/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:supplier_list')


# =============================================================================
# CONTINUE WITH OTHER VIEWS (INVOICING, SALES, HR, EXPENSES)
# =============================================================================

class CustomerListView(AdminRequiredMixin, ListView):
    model = Customer
    template_name = 'admin_panel/customers/list.html'
    context_object_name = 'customers'
    paginate_by = 25


class CustomerCreateView(AdminRequiredMixin, CreateView):
    model = Customer
    template_name = 'admin_panel/customers/form.html'
    fields = ['name', 'email', 'phone', 'address', 'city', 'country', 'customer_type', 'is_active']
    success_url = reverse_lazy('admin_panel:customer_list')


class CustomerDetailView(AdminRequiredMixin, DetailView):
    model = Customer
    template_name = 'admin_panel/customers/detail.html'


class CustomerUpdateView(AdminRequiredMixin, UpdateView):
    model = Customer
    template_name = 'admin_panel/customers/form.html'
    fields = ['name', 'email', 'phone', 'address', 'city', 'country', 'customer_type', 'is_active']
    success_url = reverse_lazy('admin_panel:customer_list')


class CustomerDeleteView(AdminRequiredMixin, DeleteView):
    model = Customer
    template_name = 'admin_panel/customers/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:customer_list')


# Continue with other models...
# Due to length constraints, I'll create additional view classes in separate files if needed