// ============================================================
// SELECTOR GENÉRICO DE PRODUCTOS PARA COMPRAS
// ============================================================
(function() {
    'use strict';

    let _productSelComprasData = [];
    let _productSelComprasSelected = new Set();
    let _productSelComprasCallback = null;

    function _closeModalSafe(modalId) {
        // Intenta con closeModal global, si no, lo hace directo
        if (typeof window.closeModal === 'function') {
            window.closeModal(modalId);
        } else {
            const modal = document.getElementById(modalId);
            if (modal) modal.classList.remove('show');
        }
    }

    function _showToastSafe(msg, type) {
        if (typeof window.showToast === 'function') {
            window.showToast(msg, type);
        } else {
            console.log(`[${type}] ${msg}`);
        }
    }

    function _getProductos() {
        // Intentar varias fuentes
        if (typeof window.PRODUCTOS_MAESTROS !== 'undefined' && Array.isArray(window.PRODUCTOS_MAESTROS)) {
            return window.PRODUCTOS_MAESTROS;
        }
        if (typeof PRODUCTOS_MAESTROS !== 'undefined' && Array.isArray(PRODUCTOS_MAESTROS)) {
            return PRODUCTOS_MAESTROS;
        }
        return [];
    }

    async function _cargarProductosSiHaceFalta() {
        let productos = _getProductos();
        if (productos.length > 0) return productos;

        try {
            console.log('🔄 Cargando productos desde /productos/api/productos...');
            const resp = await fetch('/productos/api/productos');
            const data = await resp.json();
            if (data.success && data.data && data.data.length > 0) {
                window.PRODUCTOS_MAESTROS = data.data.map(p => ({
                    id: p.id,
                    codigo: p.codigo || '',
                    producto: p.descripcion || p.nombre || 'Sin nombre',
                    descripcion: p.descripcion_larga || p.descripcion || '',
                    marca: p.marca || '',
                    modelo: p.modelo || '',
                    um: p.unidad || 'UND',
                    stock: p.stock || 0,
                    valorVenta: p.precio_unitario || p.precio_venta || 0
                }));
                console.log(`✅ ${window.PRODUCTOS_MAESTROS.length} productos cargados`);
                return window.PRODUCTOS_MAESTROS;
            }
        } catch (e) {
            console.error('❌ Error cargando productos:', e);
        }
        return [];
    }

    window.openProductSelectorCompras = async function(onAddCallback) {
        console.log('📋 openProductSelectorCompras llamado');

        const productos = await _cargarProductosSiHaceFalta();

        if (!productos || productos.length === 0) {
            _showToastSafe('⚠️ No hay productos cargados. Ve al módulo Productos.', 'warning');
            return;
        }

        _productSelComprasData = [...productos];
        _productSelComprasSelected = new Set();
        _productSelComprasCallback = (typeof onAddCallback === 'function') ? onAddCallback : null;

        const searchInput = document.getElementById('productSelComprasSearch');
        if (searchInput) searchInput.value = '';

        window.renderProductSelectorCompras();

        const modal = document.getElementById('productSelectorComprasModal');
        if (!modal) {
            console.error('❌ #productSelectorComprasModal NO existe en el DOM');
            _showToastSafe('❌ Modal no encontrado. Revisa el include en index.html.', 'error');
            return;
        }
        modal.classList.add('show');
        console.log('✅ Modal de productos abierto');
    };

    window.renderProductSelectorCompras = function() {
        const tbody = document.getElementById('productSelectorComprasRows');
        if (!tbody) return;

        const search = (document.getElementById('productSelComprasSearch')?.value || '').toLowerCase().trim();

        let filtered = _productSelComprasData;
        if (search) {
            filtered = _productSelComprasData.filter(p => {
                return (p.codigo && p.codigo.toLowerCase().includes(search)) ||
                       (p.producto && p.producto.toLowerCase().includes(search)) ||
                       (p.descripcion && p.descripcion.toLowerCase().includes(search)) ||
                       (p.marca && p.marca.toLowerCase().includes(search)) ||
                       (p.modelo && p.modelo.toLowerCase().includes(search));
            });
        }

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:20px;color:#94A3B8;">📭 No se encontraron productos</td></tr>`;
            const cnt = document.getElementById('selectedComprasCount');
            if (cnt) cnt.textContent = _productSelComprasSelected.size;
            return;
        }

        tbody.innerHTML = filtered.map(p => {
            const idKey = p.id || p.codigo;
            const checked = _productSelComprasSelected.has(idKey);
            const precio = parseFloat(p.valorVenta || p.precio_unitario || 0);

            return `
                <tr>
                    <td style="text-align:center;">
                        <input type="checkbox" class="sel-compras-checkbox" data-id="${idKey}" ${checked ? 'checked' : ''}
                               onchange="toggleProductSelectionCompras('${idKey}', this.checked)">
                    </td>
                    <td style="font-weight:900; color:#1D4ED8;">${p.codigo || '-'}</td>
                    <td style="text-align:left; font-weight:800;">${p.producto || p.descripcion || 'Sin nombre'}</td>
                    <td>${p.marca || '-'}</td>
                    <td>${p.modelo || '-'}</td>
                    <td>${p.um || 'UND'}</td>
                    <td>${p.stock || 0}</td>
                    <td style="font-weight:900; color:#059669; text-align:right;">S/ ${precio.toFixed(2)}</td>
                    <td>
                        <input type="number" class="sel-compras-qty" data-id="${idKey}" value="1" min="0.01" step="0.01"
                               style="width:60px; height:26px; border:1px solid #E5E7EB; border-radius:6px; text-align:center; font-size:11px;">
                    </td>
                </tr>
            `;
        }).join('');

        const cnt = document.getElementById('selectedComprasCount');
        if (cnt) cnt.textContent = _productSelComprasSelected.size;

        const total = document.querySelectorAll('.sel-compras-checkbox').length;
        const checkedCount = document.querySelectorAll('.sel-compras-checkbox:checked').length;
        const selectAll = document.getElementById('selectAllComprasCheckbox');
        if (selectAll) {
            selectAll.checked = total > 0 && checkedCount === total;
            selectAll.indeterminate = checkedCount > 0 && checkedCount < total;
        }
    };

    window.toggleProductSelectionCompras = function(idKey, checked) {
        if (checked) _productSelComprasSelected.add(idKey);
        else _productSelComprasSelected.delete(idKey);
        const cnt = document.getElementById('selectedComprasCount');
        if (cnt) cnt.textContent = _productSelComprasSelected.size;
    };

    window.selectAllProductsCompras = function() {
        document.querySelectorAll('.sel-compras-checkbox').forEach(cb => {
            cb.checked = true;
            _productSelComprasSelected.add(cb.dataset.id);
        });
        const cnt = document.getElementById('selectedComprasCount');
        if (cnt) cnt.textContent = _productSelComprasSelected.size;
    };

    window.deselectAllProductsCompras = function() {
        document.querySelectorAll('.sel-compras-checkbox').forEach(cb => {
            cb.checked = false;
            _productSelComprasSelected.delete(cb.dataset.id);
        });
        const cnt = document.getElementById('selectedComprasCount');
        if (cnt) cnt.textContent = _productSelComprasSelected.size;
    };

    window.toggleAllProductCheckboxesCompras = function(checked) {
        document.querySelectorAll('.sel-compras-checkbox').forEach(cb => {
            cb.checked = checked;
            if (checked) _productSelComprasSelected.add(cb.dataset.id);
            else _productSelComprasSelected.delete(cb.dataset.id);
        });
        const cnt = document.getElementById('selectedComprasCount');
        if (cnt) cnt.textContent = _productSelComprasSelected.size;
    };

    window.filterProductSelectorCompras = function() {
        window.renderProductSelectorCompras();
    };

    window.addSelectedProductsCompras = function() {
        if (_productSelComprasSelected.size === 0) {
            _showToastSafe('⚠️ Selecciona al menos un producto', 'warning');
            return;
        }

        const seleccionados = [];
        _productSelComprasSelected.forEach(idKey => {
            const prod = _productSelComprasData.find(p => (p.id == idKey) || (p.codigo == idKey));
            if (!prod) return;
            const qtyInput = document.querySelector(`.sel-compras-qty[data-id="${idKey}"]`);
            const cantidad = parseFloat(qtyInput?.value || 1);

            seleccionados.push({
                codigo: prod.codigo || '',
                producto: prod.producto || prod.descripcion || '',
                descripcion: prod.descripcion || prod.producto || '',
                marca: prod.marca || '',
                modelo: prod.modelo || '',
                um: prod.um || 'UND',
                cantidad: cantidad,
                precio_unitario: parseFloat(prod.valorVenta || prod.precio_unitario || 0),
                stock: parseInt(prod.stock || 0)
            });
        });

        _closeModalSafe('productSelectorComprasModal');

        if (typeof _productSelComprasCallback === 'function') {
            _productSelComprasCallback(seleccionados);
        }

        _showToastSafe(`✅ ${seleccionados.length} producto(s) agregado(s)`, 'success');
    };

    console.log('✅ Selector genérico de productos de Compras cargado');
})();