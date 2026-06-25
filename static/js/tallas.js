document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-size-form]').forEach((form) => {
        const quantity = form.querySelector('[data-size-quantity]');
        const radios = [...form.querySelectorAll('input[type="radio"][name="talla"]')];
        const help = form.querySelector('[data-size-help]');
        const submit = form.querySelector('[data-add-to-cart]');

        if (!radios.length) return;

        const updateSize = () => {
            const selected = radios.find((radio) => radio.checked);
            const stock = selected ? Number(selected.dataset.stock) : 0;

            quantity.disabled = !selected;
            submit.disabled = !selected;
            if (selected) {
                quantity.max = String(stock);
                quantity.value = String(Math.min(Math.max(Number(quantity.value) || 1, 1), stock));
                help.textContent = `${stock} unidades disponibles`;
            } else {
                help.textContent = '';
            }
        };

        radios.forEach((radio) => radio.addEventListener('change', updateSize));
        updateSize();
    });

    document.querySelectorAll('.carrito-form').forEach((form) => {
        const select = form.querySelector('[data-cart-size]');
        const quantity = form.querySelector('[data-cart-quantity]');
        if (!select || !quantity) return;

        const updateLimit = () => {
            const stock = Number(select.selectedOptions[0]?.dataset.stock || 1);
            quantity.max = String(stock);
            quantity.value = String(Math.min(Math.max(Number(quantity.value) || 1, 1), stock));
        };

        select.addEventListener('change', updateLimit);
        updateLimit();
    });
});
