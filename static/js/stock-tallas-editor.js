document.addEventListener('DOMContentLoaded', () => {
    const mode = document.getElementById('id_modo_stock');
    const source = document.getElementById('id_stock_por_tallas');
    const editor = document.querySelector('[data-stock-editor]');
    const modeCards = document.querySelector('[data-stock-mode-cards]');
    if (!mode || !source || !editor || !modeCards) return;

    const form = source.form;
    const modeField = mode.closest('p');
    const singleSizeField = document.getElementById('id_talla')?.closest('p');
    const generalStockField = document.getElementById('id_stock')?.closest('p');
    const singleFields = document.querySelector('[data-single-stock-fields]');
    const sourceField = source.closest('p');
    const list = editor.querySelector('[data-stock-size-list]');
    const empty = editor.querySelector('[data-stock-empty]');
    const sizeCount = editor.querySelector('[data-size-count]');
    const stockTotal = editor.querySelector('[data-stock-total]');
    const clearButton = editor.querySelector('[data-clear-sizes]');

    const updatePresetStates = () => {
        const currentSizes = new Set(
            [...list.querySelectorAll('[data-size-name]')]
                .map((input) => input.value.trim().toLowerCase())
                .filter(Boolean)
        );
        editor.querySelectorAll('[data-preset-size]').forEach((button) => {
            const active = currentSizes.has(button.dataset.presetSize.toLowerCase());
            button.classList.toggle('is-added', active);
            button.setAttribute('aria-pressed', String(active));
        });
    };

    const serialize = () => {
        const rows = [...list.querySelectorAll('[data-stock-row]')];
        let total = 0;
        const lines = rows.map((row) => {
                const size = row.querySelector('[data-size-name]').value.trim();
                const stock = Math.max(0, Number.parseInt(row.querySelector('[data-size-stock]').value, 10) || 0);
                total += stock;
                row.classList.toggle('has-stock', stock > 0);
                return size ? `${size}: ${stock}` : '';
            })
            .filter(Boolean);
        source.value = lines.join('\n');
        empty.hidden = lines.length > 0;
        clearButton.hidden = rows.length === 0;
        sizeCount.textContent = String(lines.length);
        stockTotal.textContent = String(total);
        updatePresetStates();
    };

    const addRow = (size = '', stock = 0, focus = false) => {
        const normalized = size.trim();
        const existing = [...list.querySelectorAll('[data-size-name]')]
            .find((input) => input.value.trim().toLowerCase() === normalized.toLowerCase() && normalized);
        if (existing) {
            existing.focus();
            return;
        }

        const row = document.createElement('div');
        row.className = 'stock-size-row';
        row.dataset.stockRow = '';

        const marker = document.createElement('span');
        marker.className = 'stock-size-marker';
        marker.setAttribute('aria-hidden', 'true');

        const sizeLabel = document.createElement('label');
        sizeLabel.innerHTML = '<span>Talla</span>';
        const sizeInput = document.createElement('input');
        sizeInput.type = 'text';
        sizeInput.className = 'form-control';
        sizeInput.placeholder = 'Ej. M o 38';
        sizeInput.value = normalized;
        sizeInput.dataset.sizeName = '';
        sizeLabel.append(sizeInput);

        const stockLabel = document.createElement('label');
        stockLabel.innerHTML = '<span>Unidades</span>';
        const stockInput = document.createElement('input');
        stockInput.type = 'number';
        stockInput.className = 'form-control';
        stockInput.min = '0';
        stockInput.value = String(Math.max(0, Number.parseInt(stock, 10) || 0));
        stockInput.dataset.sizeStock = '';
        stockLabel.append(stockInput);

        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'stock-size-remove';
        remove.innerHTML = '<span aria-hidden="true">&times;</span><span>Quitar</span>';
        remove.setAttribute('aria-label', `Quitar talla ${normalized || 'personalizada'}`);

        row.append(marker, sizeLabel, stockLabel, remove);
        list.append(row);
        row.querySelectorAll('input').forEach((input) => input.addEventListener('input', serialize));
        remove.addEventListener('click', () => {
            row.remove();
            serialize();
        });
        serialize();
        if (focus) sizeInput.focus();
    };

    source.value.split(/\r?\n/).forEach((line) => {
        const normalized = line.trim().replace(/[=,]/, ':');
        if (!normalized) return;
        const separator = normalized.lastIndexOf(':');
        if (separator === -1) return;
        addRow(normalized.slice(0, separator), normalized.slice(separator + 1));
    });

    editor.querySelectorAll('[data-preset-size]').forEach((button) => {
        button.addEventListener('click', () => addRow(button.dataset.presetSize, 0));
    });
    editor.querySelectorAll('[data-add-group]').forEach((button) => {
        button.addEventListener('click', () => {
            button.dataset.addGroup.split(',').forEach((size) => addRow(size, 0));
        });
    });
    editor.querySelector('[data-add-custom]').addEventListener('click', () => addRow('', 0, true));
    clearButton.addEventListener('click', () => {
        list.replaceChildren();
        serialize();
    });

    const updateMode = () => {
        const multiple = mode.value === 'multiple';
        if (singleSizeField) singleSizeField.hidden = multiple;
        if (generalStockField) generalStockField.hidden = multiple;
        if (sourceField) sourceField.hidden = true;
        editor.hidden = !multiple;
        modeCards.querySelectorAll('[data-stock-mode]').forEach((button) => {
            const active = button.dataset.stockMode === mode.value;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', String(active));
        });
    };

    modeCards.querySelectorAll('[data-stock-mode]').forEach((button) => {
        button.addEventListener('click', () => {
            mode.value = button.dataset.stockMode;
            mode.dispatchEvent(new Event('change', {bubbles: true}));
        });
    });
    if (singleFields) {
        if (singleSizeField) singleFields.append(singleSizeField);
        if (generalStockField) singleFields.append(generalStockField);
    }
    modeField.hidden = true;
    modeCards.hidden = false;
    mode.addEventListener('change', updateMode);
    form.addEventListener('submit', serialize);
    updateMode();
    serialize();
});
