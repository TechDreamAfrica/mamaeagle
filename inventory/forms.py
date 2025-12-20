from django import forms
from .models import Product

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

