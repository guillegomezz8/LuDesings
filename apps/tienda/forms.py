from django import forms
from .models import Diseño, Pedido, StockTalla


TALLAS_NORMALIZADAS = {
    'xxs', 'xs', 's', 'm', 'l', 'xl', 'xxl', 'xxxl',
}


def normalizar_talla(valor):
    talla = ' '.join((valor or '').strip().split())
    if talla.casefold() in TALLAS_NORMALIZADAS:
        return talla.upper()
    return talla


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        default_attrs = {'class': 'form-control form-control-lg', 'multiple': True, 'accept': 'image/*'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result

class DiseñoForm(forms.ModelForm):
    MODO_STOCK_TALLA_UNICA = 'unica'
    MODO_STOCK_VARIAS_TALLAS = 'multiple'
    MODO_STOCK_CHOICES = (
        (MODO_STOCK_TALLA_UNICA, 'Talla única'),
        (MODO_STOCK_VARIAS_TALLAS, 'Varias tallas'),
    )

    modo_stock = forms.ChoiceField(
        choices=MODO_STOCK_CHOICES,
        label='Tipo de tallaje:',
        widget=forms.Select(attrs={'class': 'form-control form-control-lg stock-mode-select'}),
    )
    stock_por_tallas = forms.CharField(
        required=False,
        label='Stock por tallas:',
        help_text='Escribe una talla por línea. Ejemplo: S: 2',
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-lg stock-size-textarea',
            'rows': 5,
            'placeholder': 'S: 2\nM: 4\nL: 1',
        }),
    )
    imagenes_adicionales = MultipleFileField(required=False)

    class Meta:
        model = Diseño
        fields = ['nombre', 'descripccion', 'categoria', 'precio', 'talla', 'stock', 'disponible', 'imagen_principal', 'imagenes_adicionales']
        labels = {
            'nombre': 'Nombre:',
            'descripccion': 'Descripción:',
            'categoria': 'Categoría:',
            'precio': 'Precio:',
            'talla': 'Talla por defecto:',
            'stock': 'Stock general:',
            'disponible': 'Disponible:',
            'imagen_principal': 'Imagen principal:',
            'imagenes_adicionales': 'Imágenes adicionales:'
        }
        label_suffix = ''
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce el nombre'}),
            'descripccion': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce la descripción'}),
            'categoria': forms.Select(attrs={'class': 'form-control form-control-lg'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce el precio', 'step': '0.01', 'min': '0'}),
            'talla': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Se usa si no configuras stock por talla'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Stock si no hay tallas configuradas', 'min': '0'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'imagen_principal': forms.FileInput(attrs={'class': 'form-control form-control-lg', 'accept': 'image/*'}),
            'imagenes_adicionales': MultipleFileInput(attrs={'class': 'form-control form-control-lg', 'multiple': True, 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['stock'].required = False
        self.fields['talla'].required = False
        self.order_fields([
            'nombre',
            'descripccion',
            'categoria',
            'precio',
            'modo_stock',
            'talla',
            'stock',
            'stock_por_tallas',
            'disponible',
            'imagen_principal',
            'imagenes_adicionales',
        ])

        if self.instance and self.instance.pk:
            stocks = list(self.instance.stocks_talla.all().order_by('talla'))
            if stocks:
                self.initial.setdefault('modo_stock', self.MODO_STOCK_VARIAS_TALLAS)
                self.initial.setdefault(
                    'stock_por_tallas',
                    '\n'.join(f'{stock.talla}: {stock.stock}' for stock in stocks),
                )
            else:
                self.initial.setdefault('modo_stock', self.MODO_STOCK_TALLA_UNICA)
        else:
            self.initial.setdefault('modo_stock', self.MODO_STOCK_TALLA_UNICA)

    def clean_precio(self):
        precio = self.cleaned_data['precio']
        if precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor que 0 para vender online.')
        return precio

    def clean_stock_por_tallas(self):
        if self.data.get(self.add_prefix('modo_stock')) != self.MODO_STOCK_VARIAS_TALLAS:
            return []

        texto = self.cleaned_data.get('stock_por_tallas', '')
        tallas = []
        errores = []
        tallas_repetidas = set()
        tallas_vistas = set()

        for numero_linea, linea in enumerate(texto.splitlines(), start=1):
            linea = linea.strip()
            if not linea:
                continue

            linea_normalizada = linea.replace('=', ':').replace(',', ':')
            if ':' in linea_normalizada:
                talla, stock = linea_normalizada.split(':', 1)
            else:
                partes = linea_normalizada.rsplit(None, 1)
                if len(partes) != 2:
                    errores.append(f'Línea {numero_linea}: usa el formato "S: 2".')
                    continue
                talla, stock = partes

            talla = normalizar_talla(talla)
            stock = stock.strip()
            if not talla:
                errores.append(f'Línea {numero_linea}: indica la talla.')
                continue

            clave_talla = talla.casefold()
            if clave_talla in tallas_vistas:
                tallas_repetidas.add(talla)
                continue
            tallas_vistas.add(clave_talla)

            try:
                stock_numero = int(stock)
            except ValueError:
                errores.append(f'Línea {numero_linea}: el stock debe ser un número entero.')
                continue

            if stock_numero < 0:
                errores.append(f'Línea {numero_linea}: el stock no puede ser negativo.')
                continue

            tallas.append((talla, stock_numero))

        if tallas_repetidas:
            errores.append('No repitas tallas: ' + ', '.join(sorted(tallas_repetidas)))

        if errores:
            raise forms.ValidationError(errores)

        return tallas

    def clean(self):
        cleaned_data = super().clean()
        modo_stock = cleaned_data.get('modo_stock')
        stock_por_tallas = cleaned_data.get('stock_por_tallas') or []

        if modo_stock == self.MODO_STOCK_VARIAS_TALLAS:
            if not stock_por_tallas:
                self.add_error('stock_por_tallas', 'Añade al menos una talla con su stock.')
            cleaned_data['talla'] = ''
            cleaned_data['stock'] = 0
        else:
            stock = cleaned_data.get('stock')
            talla = normalizar_talla(cleaned_data.get('talla'))
            if stock is None:
                self.add_error('stock', 'Indica el stock disponible.')
            if stock is not None and stock < 0:
                self.add_error('stock', 'El stock no puede ser negativo.')
            if not talla:
                self.add_error('talla', 'Indica la talla o usa el modo de varias tallas.')
            cleaned_data['stock_por_tallas'] = []

        return cleaned_data

    def guardar_stock_tallas(self, diseño):
        if self.cleaned_data.get('modo_stock') == self.MODO_STOCK_VARIAS_TALLAS:
            stocks = self.cleaned_data.get('stock_por_tallas') or []
            diseño.talla = ''
            diseño.stock = 0
            diseño.disponible = any(stock > 0 for _, stock in stocks) if diseño.disponible else False
            diseño.save(update_fields=['talla', 'stock', 'disponible'])
            diseño.stocks_talla.all().delete()
            StockTalla.objects.bulk_create([
                StockTalla(
                    diseño=diseño,
                    talla=talla,
                    stock=stock,
                    disponible=stock > 0,
                )
                for talla, stock in stocks
            ])
        else:
            diseño.stocks_talla.all().delete()
            diseño.disponible = diseño.stock > 0 if diseño.disponible else False
            diseño.save(update_fields=['disponible'])

        return diseño

class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['nombre_cliente', 'email', 'telefono', 'direccion', 'ciudad', 'codigo_postal', 'notas']
        labels = {
            'nombre_cliente': 'Nombre',
            'email': 'Correo electrónico',
            'telefono': 'Teléfono',
            'direccion': 'Dirección',
            'ciudad': 'Ciudad',
            'codigo_postal': 'Código postal',
            'notas': 'Notas del pedido',
        }
        widgets = {
            'nombre_cliente': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Nombre para el pedido'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Correo de contacto'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Teléfono de contacto'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Dirección de entrega'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Ciudad'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Código postal'}),
            'notas': forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 3, 'placeholder': 'Talla especial, horario, ajustes o dudas'}),
        }

