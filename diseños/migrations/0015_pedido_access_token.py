import uuid

from django.db import migrations, models


def generar_tokens(apps, schema_editor):
    Pedido = apps.get_model('diseños', 'Pedido')
    for pedido in Pedido.objects.filter(access_token__isnull=True):
        pedido.access_token = uuid.uuid4()
        pedido.save(update_fields=['access_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('diseños', '0014_pedido_estado_pago_pedido_fecha_pago_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='access_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(generar_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='pedido',
            name='access_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
