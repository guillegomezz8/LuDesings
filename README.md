# LuDesigns

Proyecto Django organizado por áreas funcionales.

## Estructura

```text
LuDesigns/
|-- apps/
|   |-- sitio/       # Sobre mí, blog y solicitudes a medida
|   |-- tienda/      # Catálogo, carrito, pagos y pedidos
|   |   `-- views/   # Catálogo, carrito y pagos separados
|   |-- cuentas/     # Registro, acceso y perfil del cliente
|   `-- panel/       # Gestión interna para administradores
|-- LuDesigns/       # Configuración global de Django
|-- templates/       # Plantillas compartidas, como base.html
|-- static/          # CSS e imágenes que se editan
|-- media/           # Imágenes subidas por usuarios o administradores
|-- staticfiles/     # Salida generada por collectstatic
|-- manage.py
`-- requirements.txt
```

Cada app mantiene juntas sus vistas, modelos, formularios, URLs, pruebas y
plantillas. Las plantillas usan namespaces como `tienda/`, `cuentas/` y
`panel/` para evitar nombres ambiguos.

`staticfiles/`, `db.sqlite3` y los directorios `__pycache__/` son archivos
locales o generados. No deben editarse ni guardarse en Git.

Las etiquetas internas antiguas (`base`, `diseños` y `usuarios`) se conservan
en los `AppConfig` para mantener compatibles las migraciones y la base de
datos existente.

## Desarrollo con Docker

```bash
docker compose up --build
```

El entrypoint ejecuta `collectstatic` y las migraciones antes de iniciar
Django.

## Pagos con Stripe

1. Copia las variables de `.env.example` a un archivo `.env`.
2. Añade tu clave secreta de Stripe en `STRIPE_SECRET_KEY`.
3. Configura un webhook hacia `/diseños/stripe/webhook/`.
4. Suscribe el webhook a estos eventos:
   - `checkout.session.completed`
   - `checkout.session.async_payment_succeeded`
   - `checkout.session.async_payment_failed`
   - `checkout.session.expired`
5. Guarda el secreto `whsec_...` del webhook en `STRIPE_WEBHOOK_SECRET`.

Para probar webhooks en local con Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/diseños/stripe/webhook/
```

El checkout reserva el stock durante 30 minutos por defecto. Si el cliente
cancela o Stripe informa de que la sesión ha expirado, la reserva se libera
automáticamente. Los métodos de pago disponibles se gestionan desde el panel
de Stripe.

## Comprobaciones

```bash
python manage.py check
python manage.py test
```
