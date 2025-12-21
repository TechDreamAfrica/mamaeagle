# Multi-Tenant Authorization System Implementation Guide

## 🎯 Overview
This comprehensive authorization system provides enterprise-grade security for your multi-tenant Django application with role-based access control, company isolation, and audit logging.

## 📋 System Requirements Met

### ✅ Core Features Implemented
- **Multi-tenant company isolation**: Users can belong to multiple companies with different roles
- **Super Admin privileges**: Complete access across all companies and resources
- **Company Admin restrictions**: Full access within their assigned company only
- **Role-based permissions**: Fine-grained permission system with enum-based controls
- **Comprehensive audit logging**: Track all user actions with security event flagging
- **Company-scoped data access**: Automatic filtering of data by company ownership
- **Permission decorators**: Easy view-level authorization with multiple decorator types
- **Enhanced middleware**: Security audit, access control, and rate limiting
- **Data isolation**: Prevent cross-company data access

### 🏗️ Architecture Components

#### 1. Authorization Service (`accounts/authorization.py`)
Central authorization logic with:
```python
from accounts.authorization import AuthorizationService, Permission, Action

# Initialize service
auth_service = AuthorizationService()

# Check permissions
if auth_service.has_permission(user, Permission.CREATE_INVOICE, company):
    # Allow action
    pass

# Log actions
auth_service.log_action(
    user=request.user,
    company=request.company, 
    action=Action.CREATE,
    resource_type="invoice"
)
```

#### 2. Permission System
Enum-based permissions for consistency:
```python
class Permission(Enum):
    CREATE_COMPANY = "create_company"
    MANAGE_USERS = "manage_users"
    VIEW_REPORTS = "view_reports"
    CREATE_INVOICE = "create_invoice"
    # ... more permissions
```

#### 3. View Decorators (`accounts/decorators.py`)
Easy authorization enforcement:
```python
from accounts.decorators import require_permissions, super_admin_required

@require_permissions([Permission.CREATE_INVOICE])
def create_invoice_view(request):
    # Only users with CREATE_INVOICE permission can access
    pass

@super_admin_required
def system_admin_view(request):
    # Only super admins can access
    pass
```

#### 4. Company-Scoped Managers (`accounts/managers.py`)
Automatic data filtering:
```python
class Invoice(models.Model):
    company = models.ForeignKey(Company)
    # ... other fields
    
    objects = CompanyScopedManager()  # Automatically filters by company
```

#### 5. Audit System (`accounts/models.py`)
Comprehensive logging:
```python
class AuditLog(models.Model):
    user = models.ForeignKey(User)
    company = models.ForeignKey(Company)
    action = models.CharField(max_length=50)
    resource_type = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_security_event = models.BooleanField(default=False)
    # ... more fields
```

## 🚀 Quick Start Integration

### Step 1: Update Django Settings
Add to your `settings.py`:
```python
# Add to MIDDLEWARE (order matters)
MIDDLEWARE = [
    # ... existing middleware
    'accounts.enhanced_middleware.SecurityAuditMiddleware',
    'accounts.enhanced_middleware.CompanyAccessControlMiddleware', 
    'accounts.enhanced_middleware.QuerySetAuthorizationMiddleware',
    'accounts.enhanced_middleware.RateLimitMiddleware',
]

# Rate limiting settings
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_REQUESTS = 1000  # requests per window

# Authorization settings
AUTHORIZATION_ENFORCE_COMPANY_ISOLATION = True
AUTHORIZATION_LOG_ALL_ACTIONS = True
AUTHORIZATION_SECURITY_EVENTS_ONLY = False
```

### Step 2: Apply Database Migrations
```bash
python manage.py makemigrations accounts
python manage.py migrate
```

### Step 3: Update Your Models
For existing models, add company-scoped managers:
```python
from accounts.managers import CompanyScopedManager

class YourModel(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    # ... your fields
    
    objects = CompanyScopedManager()  # Replace default manager
```

### Step 4: Protect Your Views
Add authorization decorators:
```python
from accounts.decorators import require_permissions, require_company_access
from accounts.authorization import Permission

@require_permissions([Permission.VIEW_REPORTS])
@require_company_access
def financial_reports(request):
    # Automatically enforces permissions and company access
    return render(request, 'reports.html')
```

### Step 5: Update Form Processing
Add audit logging to form saves:
```python
from accounts.authorization import AuthorizationService, Action

def save_invoice(request):
    invoice = form.save()
    
    # Log the action
    auth_service = AuthorizationService()
    auth_service.log_action(
        user=request.user,
        company=request.company,
        action=Action.CREATE,
        resource_type="invoice", 
        resource_id=str(invoice.id)
    )
```

## 🔧 Configuration Options

### Middleware Configuration
Each middleware component can be configured:

1. **SecurityAuditMiddleware**: Logs all requests and security events
2. **CompanyAccessControlMiddleware**: Enforces company access rules
3. **QuerySetAuthorizationMiddleware**: Filters querysets by company
4. **RateLimitMiddleware**: Prevents abuse with request limiting

### Permission Configuration
Define custom permissions in `authorization.py`:
```python
class Permission(Enum):
    # Add your business-specific permissions
    APPROVE_EXPENSES = "approve_expenses"
    MANAGE_INVENTORY = "manage_inventory"
    PROCESS_PAYROLL = "process_payroll"
```

### Role Configuration
Create roles through Django admin or programmatically:
```python
from accounts.models import Role

# Create custom roles
Role.objects.create(
    name="Finance Manager",
    description="Manages financial operations"
)
```

## 🔐 Security Best Practices

### 1. Company Isolation
- All models should include `company` foreign key
- Use `CompanyScopedManager` for automatic filtering
- Validate company access in forms and APIs

### 2. Permission Checking
- Always use permission decorators on sensitive views
- Check permissions in business logic, not just views
- Log all permission checks for audit trails

### 3. Audit Logging
- Log all data modifications with user context
- Flag security-sensitive operations
- Regularly review audit logs for anomalies

### 4. Input Validation
- Validate all company-scoped inputs
- Prevent users from accessing other companies' data
- Use form validation for business rules

## 📊 Monitoring and Analytics

### Audit Log Analysis
Query audit logs for insights:
```python
from accounts.models import AuditLog

# Security events in last 24 hours
recent_security = AuditLog.objects.filter(
    is_security_event=True,
    timestamp__gte=timezone.now() - timedelta(days=1)
)

# Most active users
active_users = AuditLog.objects.values('user__username').annotate(
    action_count=Count('id')
).order_by('-action_count')
```

### Performance Monitoring
- Monitor middleware overhead
- Track permission check performance
- Optimize company-scoped queries

## 🧪 Testing

### Run the Test Suite
```bash
cd /path/to/your/project
python accounts/test_authorization_system.py
```

### Manual Testing Checklist
- [ ] Super admin can access all companies
- [ ] Company admins are restricted to their company
- [ ] Standard users have limited permissions
- [ ] Cross-company access is blocked
- [ ] Audit logs are created for all actions
- [ ] Security events are flagged
- [ ] Decorators enforce permissions correctly

## 🚨 Troubleshooting

### Common Issues

#### 1. Import Errors
If you see `CompanyManager` import errors:
```python
# Use the new manager name
from accounts.managers import CompanyScopedManager
```

#### 2. Permission Denied Errors
Check user role assignments:
```python
from accounts.models import UserCompany
UserCompany.objects.filter(user=user, company=company)
```

#### 3. Audit Logs Not Created
Verify middleware is properly configured and ordered in settings.

#### 4. Performance Issues
Consider:
- Adding database indexes for company foreign keys
- Optimizing queryset filtering
- Caching permission checks

### Debug Mode
Enable debug logging:
```python
LOGGING = {
    'loggers': {
        'accounts.authorization': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

## 📚 API Reference

### AuthorizationService Methods
- `is_super_admin(user)`: Check if user has super admin privileges
- `can_access_company(user, company)`: Verify company access
- `has_permission(user, permission, company)`: Check specific permission
- `get_user_role_in_company(user, company)`: Get user's role in company
- `log_action(...)`: Create audit log entry

### Available Decorators
- `@require_permissions([permissions])`: Require specific permissions
- `@super_admin_required`: Super admin only
- `@company_admin_required`: Company admin or super admin
- `@require_company_access`: Must have company access
- `@audit_sensitive_action`: Log security-sensitive actions

## 🔄 Upgrade Path

### From Basic Auth to Enterprise Auth
1. Backup your database
2. Apply new migrations
3. Update model managers
4. Add permission decorators
5. Configure middleware
6. Test thoroughly

### Future Enhancements
- API key authentication
- Two-factor authentication
- Advanced audit analytics
- Real-time security monitoring
- Automated threat detection

## 📞 Support
For implementation assistance or custom requirements, this system provides a solid foundation for enterprise-grade multi-tenant authorization.

---
**Security Notice**: This authorization system implements industry best practices but should be reviewed by security professionals before production deployment.