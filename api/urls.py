from django.urls import path, include

app_name = 'api'

urlpatterns = [
    path('auth/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('invoicing/', include('invoicing.urls')),
    path('expenses/', include('expenses.urls')),
    path('reports/', include('reports.urls')),
    path('hr/', include('hr.urls')),
    path('ai-insights/', include('ai_insights.urls')),
]
