from django import forms
from django.contrib.auth import get_user_model
from .models import Product, InventoryCount, Category, StockMovement, Warehouse

User = get_user_model()

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku', 'barcode', 'name', 'slug', 'description', 'category', 'product_type',
            'unit_type', 'cost_price', 'selling_price', 'minimum_stock_level',
            'maximum_stock_level', 'reorder_point', 'reorder_quantity',
            'weight', 'dimensions', 'is_active', 'is_serialized', 'tax_exempt'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'weight': forms.NumberInput(attrs={'step': '0.01'}),
            'cost_price': forms.NumberInput(attrs={'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'step': '0.01'}),
            'sku': forms.TextInput(attrs={'placeholder': 'Auto-generated from product name'}),
            'slug': forms.TextInput(attrs={'placeholder': 'auto-generated-slug'}),
        }

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        company = self.instance.company if self.instance.pk else None
        
        # Get company from form if not available in instance
        if not company and hasattr(self, 'company'):
            company = self.company
            
        if company and sku:
            # Check if SKU exists within the same company, excluding current instance
            sku_exists = Product.objects.filter(company=company, sku=sku)
            if self.instance.pk:
                sku_exists = sku_exists.exclude(pk=self.instance.pk)
            if sku_exists.exists():
                raise forms.ValidationError("SKU already exists for this company. Please use a different SKU.")
        return sku

    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode')
        company = self.instance.company if self.instance.pk else None
        
        # Get company from form if not available in instance
        if not company and hasattr(self, 'company'):
            company = self.company
            
        if company and barcode:
            # Check if barcode exists within the same company, excluding current instance
            barcode_exists = Product.objects.filter(company=company, barcode=barcode)
            if self.instance.pk:
                barcode_exists = barcode_exists.exclude(pk=self.instance.pk)
            if barcode_exists.exists():
                raise forms.ValidationError("Barcode already exists for this company. Please use a different barcode.")
        return barcode
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Make SKU optional since it will be auto-generated
        if 'sku' in self.fields:
            self.fields['sku'].required = False
            self.fields['sku'].help_text = 'Leave empty to auto-generate from product name'
            
        # Make slug optional since it will be auto-generated
        if 'slug' in self.fields:
            self.fields['slug'].required = False
            self.fields['slug'].help_text = 'Leave empty to auto-generate from product name'


class InventoryCountForm(forms.ModelForm):
    # Additional fields for the template
    count_name = forms.CharField(
        max_length=100, 
        label="Count Name",
        help_text="Descriptive name for this inventory count"
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}), 
        required=False,
        label="Description",
        help_text="Additional details about this count"
    )
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.none(), 
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Categories to Count",
        help_text="Leave empty to count all categories"
    )
    assigned_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(), 
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Assigned Users",
        help_text="Users who will perform the count"
    )
    supervisor = forms.ModelChoiceField(
        queryset=User.objects.none(), 
        required=False,
        label="Supervisor",
        help_text="User who will supervise this count"
    )
    include_zero_stock = forms.BooleanField(
        required=False,
        initial=False,
        label="Include Zero Stock Items",
        help_text="Include products with zero stock in the count"
    )
    freeze_transactions = forms.BooleanField(
        required=False,
        initial=False,
        label="Freeze Transactions",
        help_text="Prevent inventory transactions during count"
    )
    
    class Meta:
        model = InventoryCount
        fields = ['count_number', 'warehouse', 'count_date', 'count_type', 'notes', 'status']
        widgets = {
            'count_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate dropdowns (you might want to filter by company)
        self.fields['categories'].queryset = Category.objects.filter(is_active=True)
        self.fields['assigned_users'].queryset = User.objects.filter(is_active=True)
        self.fields['supervisor'].queryset = User.objects.filter(is_active=True)
        
        # Set initial values
        if self.instance and self.instance.count_number:
            self.fields['count_name'].initial = self.instance.count_number
        if self.instance and self.instance.notes:
            self.fields['description'].initial = self.instance.notes
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Map additional fields to model fields
        instance.count_number = self.cleaned_data.get('count_name', instance.count_number)
        if self.cleaned_data.get('description'):
            instance.notes = self.cleaned_data['description']
        
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance


class StockMovementForm(forms.ModelForm):
    # Additional fields for the template
    processed_by = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Processed By",
        help_text="User processing this movement"
    )
    from_location = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        required=False,
        label="From Location",
        help_text="Source location (for transfers)"
    )
    to_location = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        required=False,
        label="To Location",
        help_text="Destination location (for transfers)"
    )
    quantity = forms.IntegerField(
        label="Quantity",
        help_text="Quantity to move",
        widget=forms.NumberInput(attrs={'min': '1'})
    )
    reason = forms.CharField(
        max_length=255,
        required=False,
        label="Reason for Movement",
        help_text="Brief reason for this movement"
    )
    
    class Meta:
        model = StockMovement
        fields = ['product', 'warehouse', 'movement_type', 'unit_cost', 'reference_number', 'notes', 'movement_date']
        widgets = {
            'movement_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'unit_cost': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate dropdowns
        self.fields['processed_by'].queryset = User.objects.filter(is_active=True)
        self.fields['from_location'].queryset = Warehouse.objects.filter(is_active=True)
        self.fields['to_location'].queryset = Warehouse.objects.filter(is_active=True)
        
        # Map quantity_change to quantity for display
        if self.instance and hasattr(self.instance, 'quantity_change'):
            self.fields['quantity'].initial = abs(self.instance.quantity_change)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Map quantity to quantity_change (positive for in, negative for out)
        quantity = self.cleaned_data.get('quantity', 0)
        movement_type = self.cleaned_data.get('movement_type')
        
        # Determine if quantity should be positive or negative
        if movement_type in ['purchase', 'transfer_in', 'return', 'initial']:
            instance.quantity_change = quantity
        elif movement_type in ['sale', 'transfer_out', 'damage', 'theft', 'expired']:
            instance.quantity_change = -quantity
        else:  # adjustment
            # For adjustments, let the user specify positive or negative
            instance.quantity_change = quantity
        
        # Add reason to notes if provided
        reason = self.cleaned_data.get('reason')
        if reason:
            if instance.notes:
                instance.notes += f"\nReason: {reason}"
            else:
                instance.notes = f"Reason: {reason}"
        
        if commit:
            instance.save()
        
        return instance
