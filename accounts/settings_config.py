"""
Settings Configuration for Multi-Tenant Authorization System

Add these configurations to your Django settings.py file to enable
the comprehensive authorization system.
"""

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

# Add these middleware classes to your MIDDLEWARE setting (order matters)
ENHANCED_MIDDLEWARE = [
    # ... your existing middleware ...
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # Add our custom authorization middleware
    'accounts.enhanced_middleware.SecurityAuditMiddleware',
    'accounts.enhanced_middleware.CompanyAccessControlMiddleware', 
    'accounts.enhanced_middleware.QuerySetAuthorizationMiddleware',
    'accounts.enhanced_middleware.RateLimitMiddleware',
    
    # Keep existing company isolation middleware
    'accounts.middleware.CompanyIsolationMiddleware',
    'accounts.middleware.BranchAccessControlMiddleware',
    
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'audit': {
            'format': '[AUDIT] {asctime} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
            'formatter': 'verbose',
        },
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/audit.log',
            'formatter': 'audit',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'logs/security.log',
            'formatter': 'audit',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts.authorization': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts.enhanced_middleware': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# Session settings for company switching
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Rate limiting settings
RATE_LIMIT_ENABLE = True
RATE_LIMIT_REQUESTS_PER_MINUTE = 100
RATE_LIMIT_BLOCK_DURATION = 300  # 5 minutes

# =============================================================================
# CUSTOM SETTINGS FOR AUTHORIZATION SYSTEM
# =============================================================================

# Company settings
MAX_COMPANIES_PER_USER = 10  # Limit for non-super-admin users
REQUIRE_COMPANY_FOR_ACCESS = True
AUTO_ASSIGN_NEW_USERS_TO_COMPANY = False

# Audit settings
AUDIT_LOG_RETENTION_DAYS = 365
AUDIT_LOG_SENSITIVE_ACTIONS = True
AUDIT_LOG_SUPER_ADMIN_ACTIONS = True

# Permission settings
ENFORCE_STRICT_COMPANY_ISOLATION = True
ALLOW_CROSS_COMPANY_QUERIES_FOR_SUPER_ADMIN = True

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Add database indexes for better performance
DATABASE_INDEXES = {
    'audit_logs': [
        ('user_id', 'timestamp'),
        ('company_id', 'timestamp'),
        ('action', 'timestamp'),
        ('is_security_event', 'timestamp'),
        ('is_super_admin_action', 'timestamp'),
    ]
}

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

# Cache settings for authorization data
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'mama_eagle',
        'TIMEOUT': 300,  # 5 minutes
    },
    'authorization': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'KEY_PREFIX': 'auth',
        'TIMEOUT': 60,  # 1 minute for authorization data
    }
}

# =============================================================================
# EMAIL CONFIGURATION FOR NOTIFICATIONS
# =============================================================================

# Email settings for security notifications
SECURITY_EMAIL_NOTIFICATIONS = True
SECURITY_NOTIFICATION_RECIPIENTS = ['admin@example.com']

EMAIL_TEMPLATES = {
    'security_alert': 'emails/security_alert.html',
    'access_revoked': 'emails/access_revoked.html',
    'role_changed': 'emails/role_changed.html',
}

# =============================================================================
# CELERY CONFIGURATION (if using)
# =============================================================================

# Celery settings for background tasks
CELERY_TASK_ROUTES = {
    'accounts.tasks.cleanup_audit_logs': {'queue': 'maintenance'},
    'accounts.tasks.send_security_alerts': {'queue': 'notifications'},
    'accounts.tasks.generate_access_reports': {'queue': 'reports'},
}

# =============================================================================
# API CONFIGURATION
# =============================================================================

# Django REST Framework settings for API authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# =============================================================================
# EXAMPLE USAGE IN SETTINGS.PY
# =============================================================================

"""
# In your main settings.py file, add:

# Import the enhanced middleware configuration
from accounts.settings_config import ENHANCED_MIDDLEWARE

# Replace or update your MIDDLEWARE setting
MIDDLEWARE = ENHANCED_MIDDLEWARE

# Add logging configuration
LOGGING = {
    # ... copy the LOGGING configuration from above
}

# Add custom settings
MAX_COMPANIES_PER_USER = 10
AUDIT_LOG_RETENTION_DAYS = 365
ENFORCE_STRICT_COMPANY_ISOLATION = True

# Ensure your INSTALLED_APPS includes:
INSTALLED_APPS = [
    # ... other apps ...
    'accounts',
    'rest_framework',  # if using API endpoints
    # ... other apps ...
]
"""