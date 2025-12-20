from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku', 'barcode', 'name', 'description', 'category', 'product_type',
            'unit_type', 'cost_price', 'selling_price', 'minimum_stock_level',
            'maximum_stock_level', 'reorder_point', 'reorder_quantity',
            'weight', 'dimensions', 'is_active', 'is_serialized', 'tax_exempt'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'weight': forms.NumberInput(attrs={'step': '0.01'}),
            'cost_price': forms.NumberInput(attrs={'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        # Check if SKU exists, but exclude current instance during edit
        sku_exists = Product.objects.filter(sku=sku)
        if self.instance.pk:
            sku_exists = sku_exists.exclude(pk=self.instance.pk)
        if sku_exists.exists():
            raise forms.ValidationError("SKU must be unique.")
        return sku

    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode')
        if barcode:
            # Check if barcode exists, but exclude current instance during edit
            barcode_exists = Product.objects.filter(barcode=barcode)
            if self.instance.pk:
                barcode_exists = barcode_exists.exclude(pk=self.instance.pk)
            if barcode_exists.exists():
                raise forms.ValidationError("Barcode must be unique.")
        return barcode

