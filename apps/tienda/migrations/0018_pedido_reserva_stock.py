from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diseños', '0017_stocktalla_stocktalla_stock_unico_por_diseno_talla'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='fecha_expiracion_pago',
            field=models.DateTimeField(blank=True, null=True, verbose_name='fin de la reserva de stock'),
        ),
        migrations.AddField(
            model_name='pedido',
            name='stock_reservado',
            field=models.BooleanField(default=False, verbose_name='stock reservado'),
        ),
    ]
