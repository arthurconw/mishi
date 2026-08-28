# pdf_generator.py - VERSIÓN CORREGIDA

import os
from jinja2 import Template
from weasyprint import HTML
from datetime import datetime
import json
import base64
import re


class PDFGenerator:
    def __init__(self):
        self.templates_dir = 'templates/cotizacion_oc/'
        self.logo_base64 = None

    # ============================================================
    # OBTENER LOGO EN BASE64
    # ============================================================
    def _obtener_logo_base64(self):
        if self.logo_base64:
            return self.logo_base64
        
        posibles_rutas = [
            os.path.join('templates', 'pdf', 'logo-kcf.png'),
            os.path.join('templates', 'logo-kcf.png'),
            os.path.join('static', 'img', 'logo-kcf.png'),
            os.path.join('static', 'logo-kcf.png'),
            'logo-kcf.png',
        ]
        
        for logo_path in posibles_rutas:
            if os.path.exists(logo_path):
                try:
                    with open(logo_path, 'rb') as f:
                        logo_data = f.read()
                        self.logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                        print(f"✅ Logo cargado desde: {logo_path}")
                        return self.logo_base64
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    continue
            else:
                print(f"🔍 Logo no encontrado: {logo_path}")
        
        print("❌ No se encontró el logo")
        return None

    # ============================================================
    # ✅ MÉTODO PRINCIPAL - CORREGIDO (con indentación correcta)
    # ============================================================
    def generar_pdf_universal(self, datos):
        print(f"📄 Generando PDF universal...")
        tipo = datos.get('tipo_documento', '')
        
        if tipo == 'guia_remision' or ('serie' in datos and 'numero' in datos and 'destinatario_nombre' in datos):
            return self._generar_guia_remision(datos)
        elif tipo in ['factura', 'boleta', 'comprobante']:
            return self._generar_comprobante(datos)
        elif tipo == 'cotizacion' or 'numero_cotizacion' in datos or 'cliente_nombre' in datos:
            return self._generar_cotizacion(datos)
        else:
            return self._generar_cotizacion(datos)

    # ============================================================
    # GENERAR GUÍA DE REMISIÓN
    # ============================================================
    def _generar_guia_remision(self, datos_guia):
        try:
            print("📄 Generando PDF de Guía de Remisión...")
            
            datos_mapeados = self._mapear_datos_guia(datos_guia)
            template_content = self._obtener_template_guia()
            filas_productos = self._generar_filas_productos_guia(datos_mapeados.get('items', []))
            datos_mapeados['filas_productos'] = filas_productos
            html_content = self._reemplazar_variables_template_guia(template_content, datos_mapeados)
            
            fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_file = f"guia_{datos_mapeados.get('serie', 'T001')}_{datos_mapeados.get('numero', 'sin_numero')}_{fecha}.pdf"
            
            base_url = f"file://{os.getcwd()}/"
            HTML(string=html_content, base_url=base_url).write_pdf(pdf_file)
            
            print(f"✅ PDF generado: {pdf_file}")
            return pdf_file
        except Exception as e:
            print(f"❌ Error en _generar_guia_remision: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _obtener_template_guia(self):
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Guía de Remisión {{ serie }}-{{ numero }}</title>
    <style>
        @page { size: A4; margin: 1.2cm 1.5cm; }
        body { font-family: 'Helvetica', Arial, sans-serif; font-size: 9.5px; color: #1a1a1a; line-height: 1.8; }
        .header-superior { display: flex; justify-content: space-between; align-items: stretch; margin-bottom: 10px; gap: 15px; }
        .empresa-izquierda { flex: 1; display: flex; align-items: center; gap: 12px; }
        .empresa-izquierda .logo-container { flex-shrink: 0; width: 80px; height: 60px; display: flex; align-items: center; justify-content: center; }
        .empresa-izquierda .logo-container img { max-height: 60px; max-width: 100px; object-fit: contain; }
        .empresa-izquierda .info-texto { font-size: 8px; line-height: 1.4; }
        .empresa-izquierda .info-texto .nombre { font-size: 10px; font-weight: bold; text-transform: uppercase; }
        .recuadro-derecha { flex-shrink: 0; border: 2px solid #000; border-radius: 12px; padding: 10px 20px; text-align: center; min-width: 200px; }
        .recuadro-derecha .ruc { font-size: 10px; font-weight: bold; }
        .recuadro-derecha .titulo { font-size: 11px; font-weight: bold; letter-spacing: 1px; margin: 2px 0; }
        .recuadro-derecha .numero { font-size: 13px; font-weight: bold; }
        .seccion { margin-bottom: 8px; }
        .seccion-titulo { font-weight: bold; font-size: 9.5px; margin-bottom: 3px; text-transform: uppercase; border-bottom: 1px solid #000; padding-bottom: 2px; }
        .info-destinatario, .datos-traslado, .datos-ruta, .datos-transporte, .referencias, .observaciones {
            border: 1px solid #ccc; border-radius: 8px; padding: 6px 12px; margin-bottom: 6px; background: #f9f9f9; }
        .fila { display: flex; padding: 1px 0; align-items: baseline; }
        .fila .label { font-weight: bold; min-width: 200px; flex-shrink: 0; }
        .fila .value { flex: 1; text-align: left; padding-left: 5px; }
        .products-table { width: 100%; border-collapse: collapse; margin: 4px 0; font-size: 8.5px; }
        .products-table th { background: #333; color: white; padding: 4px 5px; text-align: center; border: 1px solid #000; }
        .products-table td { padding: 3px 5px; border: 1px solid #ccc; text-align: center; }
        .products-table td.descripcion { text-align: left; }
        .qr-container { text-align: center; margin: 8px 0 5px 0; padding: 6px; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }
        .qr-container img { width: 90px; height: 90px; }
        .qr-container .qr-text { font-size: 7px; color: #64748B; margin-top: 2px; }
        .footer { margin-top: 12px; text-align: center; font-size: 7.5px; color: #555; border-top: 1px solid #ddd; padding-top: 6px; }
        .referencias-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; padding: 6px 0; }
        .ref-item { text-align: center; }
        .ref-item .ref-label { font-weight: bold; display: block; font-size: 7.5px; color: #555; text-transform: uppercase; letter-spacing: 0.3px; }
        .ref-item .ref-value { font-size: 9px; font-weight: 600; }
    </style>
</head>
<body>
    <div class="header-superior">
        <div class="empresa-izquierda">
            <div class="logo-container"><img src="{{ logo_src }}" alt="Logo" style="max-height:60px;"></div>
            <div class="info-texto">
                <div class="nombre">{{ remitente_nombre }}</div>
                <div class="contacto">
                    <span>Telf: {{ telefono }}</span><br>
                    <span>Email: {{ email }}</span><br>
                    <span>Web: {{ web }}</span>
                </div>
            </div>
        </div>
        <div class="recuadro-derecha">
            <div class="ruc">R.U.C. Nº {{ ruc_remitente }}</div>
            <div class="titulo">GUIA DE REMISIÓN REMITENTE</div>
            <div class="numero">{{ serie }}-{{ numero }}</div>
        </div>
    </div>
    <div class="seccion">
        <div class="seccion-titulo">DESTINATARIO</div>
        <div class="info-destinatario">
            <div class="fila"><span class="label">R.U.C.:</span><span class="value">{{ ruc_destinatario }}</span></div>
            <div class="fila"><span class="label">DENOMINACIÓN:</span><span class="value">{{ destinatario_nombre }}</span></div>
        </div>
    </div>
    <div class="seccion">
        <div class="seccion-titulo">DATOS DEL TRASLADO</div>
        <div class="datos-traslado">
            <div class="fila"><span class="label">FECHA EMISIÓN:</span><span class="value">{{ fecha_emision }}</span></div>
            <div class="fila"><span class="label">FECHA INICIO TRASLADO:</span><span class="value">{{ fecha_inicio_traslado }}</span></div>
            <div class="fila"><span class="label">MOTIVO DE TRASLADO:</span><span class="value">{{ motivo_texto }}</span></div>
            <div class="fila"><span class="label">MODALIDAD DE TRANSPORTE:</span><span class="value">{{ modalidad_texto }}</span></div>
            <div class="fila"><span class="label">PESO BRUTO TOTAL (KGM):</span><span class="value">{{ peso_bruto_total }}</span></div>
            <div class="fila"><span class="label">NÚMERO DE BULTOS:</span><span class="value">{{ numero_bultos }}</span></div>
        </div>
    </div>
   <div class="seccion">
    <div class="seccion-titulo">DATOS DE RUTA</div>
    <div class="datos-ruta">
        <div class="fila">
            <span class="label">PUNTO DE PARTIDA:</span>
            <span class="value" style="white-space: pre-line; line-height: 1.6;">
                {{ remitente_direccion }}
            </span>
        </div>
        <div class="fila">
            <span class="label">PUNTO DE LLEGADA:</span>
            <span class="value" style="white-space: pre-line; line-height: 1.6;">
                {{ destinatario_direccion }}
            </span>
        </div>
    </div>
</div>
    <div class="seccion">
        <div class="seccion-titulo">DATOS DEL TRANSPORTE</div>
        <div class="datos-transporte">
            <div class="fila"><span class="label">TRANSPORTISTA:</span><span class="value">{{ transportista_nombre }}</span></div>
            <div class="fila"><span class="label">CONDUCTOR:</span><span class="value">{{ conductor_nombre }}</span></div>
            <div class="fila"><span class="label">DNI:</span><span class="value">{{ conductor_dni }}</span></div>
            <div class="fila"><span class="label">PLACA:</span><span class="value">{{ placa_vehiculo }}</span></div>
            <div class="fila"><span class="label">LICENCIA:</span><span class="value">{{ licencia_conductor }}</span></div>
        </div>
    </div>
    <div class="seccion">
        <div class="seccion-titulo">PRODUCTOS</div>
        <table class="products-table">
            <thead><tr><th style="width:8%">ITEM</th><th style="width:15%">CODIGO</th><th style="width:40%">PRODUCTO</th><th style="width:15%">UM</th><th style="width:15%">CANTIDAD</th></tr></thead>
            <tbody>{% for item in items %}<tr><td>{{ item.item }}</td><td>{{ item.codigo }}</td><td class="descripcion">{{ item.descripcion }}</td><td>{{ item.unidad }}</td><td>{{ item.cantidad }}</td></tr>{% endfor %}</tbody>
        </table>
    </div>
    <div class="seccion">
        <div class="seccion-titulo">DOCUMENTOS RELACIONADOS</div>
        <div class="referencias">
            <div class="referencias-grid">
                <div class="ref-item"><span class="ref-label">NRO ORDEN DE COMPRA</span><span class="ref-value">{{ orden_compra_cliente or '—' }}</span></div>
                <div class="ref-item"><span class="ref-label">NRO DE FACTURA</span><span class="ref-value">{{ factura or '—' }}</span></div>
                <div class="ref-item"><span class="ref-label">NRO DE COTIZACION</span><span class="ref-value">{{ nro_cotizacion or '—' }}</span></div>
            </div>
        </div>
    </div>
    <div class="observaciones"><div class="fila"><span class="label">OBSERVACIONES:</span><span class="value">{{ observaciones }}</span></div></div>
    <div class="qr-container">
        <img src="{{ qr_base64 }}" alt="QR">
        <div class="qr-text">Representación impresa de la GUIA DE REMISIÓN REMITENTE ELECTRÓNICA, consulte el documento en https://see.conflux.pe
Autorizado mediante resolución N° 214-005-0001193/SUNAT</div>
    </div>
    <div class="footer"><div>Pag. 1 de 1</div><div>Powered by KCF CORPORACION</div></div>
</body>
</html>"""

    def _mapear_datos_guia(self, datos_guia):
        EMPRESA = {
            'ruc': '20602095704',
            'nombre': 'KCF CORPORACION E.I.R.L',
            'direccion': 'JR. LAS ALMENDRAS VERDES NRO. 284 URB. VIRGEN DEL ROSARIO LIMA - LIMA - SAN MARTIN DE PORRES',
            'telefono': '999 932 051',
            'email': 'ventas@kcfcorporacion.com',
            'web': 'https://kcfcorporacion.com/'
        }
        
        logo_base64 = self._obtener_logo_base64()
        logo_src = f"data:image/png;base64,{logo_base64}" if logo_base64 else ""
        
        items = datos_guia.get('items', [])
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except:
                items = []
        
        items_formateados = []
        for idx, item in enumerate(items, 1):
            if isinstance(item, dict):
                items_formateados.append({
                    'item': idx,
                    'codigo': item.get('codigo', ''),
                    'descripcion': item.get('producto', item.get('descripcion', '')),
                    'unidad': item.get('um', 'NIU'),
                    'cantidad': float(item.get('cantidad', 1))
                })
            elif isinstance(item, (list, tuple)):
                items_formateados.append({
                    'item': idx,
                    'codigo': item[0] if len(item) > 0 else '',
                    'descripcion': item[1] if len(item) > 1 else '',
                    'unidad': 'NIU',
                    'cantidad': float(item[2] if len(item) > 2 else 1)
                })
        
        peso_total = float(datos_guia.get('peso_total', 0))
        if peso_total == 0 and items_formateados:
            peso_total = sum(float(item['cantidad']) * 0.5 for item in items_formateados)
        
        return {
            'logo_src': logo_src,
            'ruc_remitente': datos_guia.get('ruc_remitente', EMPRESA['ruc']),
            'remitente_nombre': datos_guia.get('remitente_nombre', EMPRESA['nombre']),
            'remitente_direccion': datos_guia.get('remitente_direccion', EMPRESA['direccion']),
            'remitente_ubigeo': datos_guia.get('remitente_ubigeo', '150101'),
            'telefono': EMPRESA['telefono'],
            'email': EMPRESA['email'],
            'web': EMPRESA.get('web', ''),
            'ruc_destinatario': datos_guia.get('ruc_destinatario', datos_guia.get('ruc', '')),
            'destinatario_nombre': datos_guia.get('destinatario_nombre', datos_guia.get('cliente', '')),
            'destinatario_direccion': datos_guia.get('destinatario_direccion', datos_guia.get('destino', '')),
            'destinatario_ubigeo': datos_guia.get('destinatario_ubigeo', '150101'),
            'serie': datos_guia.get('serie', 'T001'),
            'numero': datos_guia.get('numero', ''),
            'fecha_emision': self._formatear_fecha(datos_guia.get('fecha_emision')),
            'fecha_traslado': self._formatear_fecha(datos_guia.get('fecha_traslado')),
            'fecha_inicio_traslado': self._formatear_fecha(datos_guia.get('fecha_inicio_traslado')),
            'motivo_traslado': datos_guia.get('motivo_traslado', '01'),
            'motivo_texto': self._get_motivo_texto(datos_guia.get('motivo_traslado', '01')),
            'modalidad_transporte': datos_guia.get('modalidad_transporte', 'PRIVADO'),
            'modalidad_texto': 'Transporte privado' if datos_guia.get('modalidad_transporte') == 'PRIVADO' else 'Transporte público',
            'peso_bruto_total': f"{peso_total:.1f}",
            'numero_bultos': datos_guia.get('numero_bultos', 1),
            'unidad_peso_texto': 'KGM',
            'transportista_nombre': datos_guia.get('transportista_nombre', '---'),
            'conductor_nombre': datos_guia.get('conductor_nombre', '---'),
            'conductor_dni': datos_guia.get('conductor_dni', '---'),
            'placa_vehiculo': datos_guia.get('placa_vehiculo', '---'),
            'licencia_conductor': datos_guia.get('licencia_conductor', '---'),
            'orden_compra_cliente': datos_guia.get('orden_compra_cliente', ''),
            'factura': datos_guia.get('factura', ''),
            'nro_cotizacion': datos_guia.get('nro_cotizacion', datos_guia.get('documento_asociado', '')),
            'items': items_formateados,
            'observaciones': datos_guia.get('observaciones', ''),
            'qr_base64': self._generar_qr_guia(datos_guia)
        }

    def _formatear_fecha(self, fecha):
        if not fecha:
            return datetime.now().strftime('%d/%m/%Y')
        try:
            if isinstance(fecha, str):
                if '/' in fecha:
                    return fecha
                dt = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
                return dt.strftime('%d/%m/%Y')
            elif isinstance(fecha, datetime):
                return fecha.strftime('%d/%m/%Y')
            return str(fecha)
        except:
            return str(fecha)

    def _get_motivo_texto(self, codigo):
        motivos = {
            '01': 'Venta', '02': 'Compra', '03': 'Traslado entre establecimientos',
            '04': 'Consignación', '05': 'Devolución', '06': 'Exportación',
            '07': 'Importación', '08': 'Donación', '09': 'Traslado por cuenta de terceros'
        }
        return motivos.get(codigo, codigo or 'Venta')

    def _generar_qr_guia(self, datos_guia):
        try:
            import qrcode
            from io import BytesIO
            qr_data = {
                'serie': datos_guia.get('serie', ''),
                'numero': datos_guia.get('numero', ''),
                'ruc_remitente': datos_guia.get('ruc_remitente', ''),
                'ruc_destinatario': datos_guia.get('ruc_destinatario', ''),
                'fecha_emision': self._formatear_fecha(datos_guia.get('fecha_emision')),
                'total_peso': str(datos_guia.get('peso_total', 0))
            }
            qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=4, border=2)
            qr.add_data(json.dumps(qr_data))
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"
        except:
            return ""

    def _generar_filas_productos_guia(self, productos):
        filas = ""
        for prod in productos:
            filas += f"""<tr><td>{prod.get('item', '')}</td><td>{prod.get('codigo', '')}</td><td class="descripcion">{prod.get('descripcion', '')}</td><td>{prod.get('unidad', 'NIU')}</td><td>{prod.get('cantidad', 0)}</td></tr>"""
        return filas

    def _reemplazar_variables_template_guia(self, template, datos):
        try:
            return Template(template).render(**datos)
        except Exception as e:
            print(f"❌ Error renderizando template Jinja2 de guía: {e}")
            return template
        
    # ============================================================
    # GENERAR FACTURA / BOLETA (COMPROBANTE) - CON QR Y DOCUMENTOS RELACIONADOS
    # ============================================================
    def _generar_comprobante(self, datos_comprobante):
        try:
            print("📄 Generando PDF de comprobante...")
            print(f"📦 Datos recibidos (keys): {list(datos_comprobante.keys())}")
            
            # --- DEBUG: Imprimir TODOS los campos para ver qué está llegando ---
            print("🔍 TODOS LOS CAMPOS RECIBIDOS:")
            for key, value in datos_comprobante.items():
                if key in ['items', 'items_json', 'productos', 'detalle']:
                    print(f"   {key}: (array con {len(value) if value else 0} items)")
                else:
                    print(f"   {key}: {value}")
            print("=" * 60)

            # --- 1. DATOS DE LA EMPRESA (FIJOS) ---
            EMPRESA = {
                'ruc': '20602095704',
                'nombre': 'KCF CORPORACION E.I.R.L',
                'direccion': 'JR. LAS ALMENDRAS VERDES NRO. 284 URB. VIRGEN DEL ROSARIO LIMA - LIMA - SAN MARTIN DE PORRES',
                'telefono': '999 932 051',
                'email': 'ventas@kcfcorporacion.com',
                'web': 'https://kcfcorporacion.com/'
            }

            # --- 2. OBTENER LOGO EN BASE64 ---
            logo_base64 = self._obtener_logo_base64()
            logo_src = f"data:image/png;base64,{logo_base64}" if logo_base64 else ""

            # --- 3. MAPEAR DATOS DEL COMPROBANTE ---
            items = []
            
            if 'items' in datos_comprobante and datos_comprobante['items']:
                items = datos_comprobante['items']
                print(f"📦 Items encontrados en 'items': {len(items)} items")
            
            if not items and 'items_json' in datos_comprobante:
                items_json = datos_comprobante['items_json']
                if isinstance(items_json, str):
                    try:
                        items = json.loads(items_json)
                        print(f"📦 Items parseados desde 'items_json' (string): {len(items)} items")
                    except:
                        print("⚠️ Error parseando items_json")
                        items = []
                elif isinstance(items_json, list):
                    items = items_json
                    print(f"📦 Items desde 'items_json' (list): {len(items)} items")
            
            if not items and 'productos' in datos_comprobante:
                items = datos_comprobante['productos']
                print(f"📦 Items desde 'productos': {len(items)} items")
            
            if not items and 'detalle' in datos_comprobante:
                items = datos_comprobante['detalle']
                print(f"📦 Items desde 'detalle': {len(items)} items")
            
            if not items:
                print("⚠️ No se encontraron productos, usando datos de ejemplo")
                items = [
                    {'codigo': 'PRD-001', 'producto': 'Producto de ejemplo 1', 'cantidad': 2, 'valorVenta': 100.00},
                    {'codigo': 'PRD-002', 'producto': 'Producto de ejemplo 2', 'cantidad': 1, 'valorVenta': 250.00}
                ]

            # --- 4. FORMATEAR ITEMS PARA EL TEMPLATE ---
            items_formateados = []
            for idx, item in enumerate(items, 1):
                try:
                    if isinstance(item, dict):
                        cantidad = float(item.get('cantidad', item.get('cant', item.get('qty', 1))))
                        precio = float(item.get('valorVenta', item.get('precio', item.get('precio_unitario', item.get('price', 0)))))
                        total_item = cantidad * precio
                        
                        descripcion = item.get('producto', item.get('descripcion', item.get('nombre', item.get('name', 'Sin descripción'))))
                        
                        items_formateados.append({
                            'item': idx,
                            'codigo': item.get('codigo', item.get('code', '')),
                            'descripcion': descripcion,
                            'marca': item.get('marca', item.get('brand', '')),
                            'modelo': item.get('modelo', item.get('model', '')),
                            'unidad': item.get('um', item.get('unidad', item.get('unit', 'NIU'))),
                            'cantidad': cantidad,
                            'precio_unitario': precio,
                            'total_item': total_item
                        })
                    elif isinstance(item, (list, tuple)):
                        codigo = item[0] if len(item) > 0 else ''
                        descripcion = item[1] if len(item) > 1 else 'Sin descripción'
                        cantidad = float(item[2] if len(item) > 2 else 1)
                        precio = float(item[3] if len(item) > 3 else 0)
                        total_item = cantidad * precio
                        
                        items_formateados.append({
                            'item': idx,
                            'codigo': codigo,
                            'descripcion': descripcion,
                            'marca': item[4] if len(item) > 4 else '',
                            'modelo': item[5] if len(item) > 5 else '',
                            'unidad': 'NIU',
                            'cantidad': cantidad,
                            'precio_unitario': precio,
                            'total_item': total_item
                        })
                    else:
                        print(f"⚠️ Item {idx} no es ni dict ni list: {type(item)}")
                        
                except Exception as e:
                    print(f"❌ Error procesando item {idx}: {e}")
                    continue
            
            print(f"✅ {len(items_formateados)} items formateados correctamente")

            # --- 5. CALCULAR MONTOS ---
            subtotal = float(datos_comprobante.get('subtotal', 0))
            igv = float(datos_comprobante.get('igv', 0))
            total = float(datos_comprobante.get('total', datos_comprobante.get('monto', 0)))
            
            if subtotal == 0 and items_formateados:
                subtotal = sum(item['total_item'] for item in items_formateados)
                igv = subtotal * 0.18
                total = subtotal + igv
                print(f"💰 Montos calculados: Subtotal={subtotal:.2f}, IGV={igv:.2f}, Total={total:.2f}")

            # --- 6. GENERAR QR PARA EL COMPROBANTE ---
            qr_base64 = self._generar_qr_comprobante(datos_comprobante)
            print(f"📱 QR generado: {'Sí' if qr_base64 else 'No'}")

            # ============================================================
            # --- 7. OBTENER DOCUMENTOS RELACIONADOS - IGUAL QUE EN LA GUÍA ---
            # ============================================================
            # Usamos EXACTAMENTE los mismos nombres de campo que la guía
            orden_compra_cliente = datos_comprobante.get('orden_compra_cliente', '')
            factura = datos_comprobante.get('factura', '')
            nro_cotizacion = datos_comprobante.get('nro_cotizacion', '')

            # Si no viene en 'nro_cotizacion', buscar en otros nombres comunes
            if not nro_cotizacion:
                nro_cotizacion = (
                    datos_comprobante.get('documento_asociado', '') or
                    datos_comprobante.get('cotizacion', '') or
                    datos_comprobante.get('cotizacion_numero', '') or
                    datos_comprobante.get('numero_cotizacion', '')
                )

            print(f"📋 Documentos relacionados - OC: '{orden_compra_cliente}', Factura: '{factura}', Cotización: '{nro_cotizacion}'")

            # --- 8. PREPARAR DATOS PARA EL TEMPLATE ---
            datos_mapeados = {
                # Encabezado
                'logo_src': logo_src,
                'empresa_ruc': EMPRESA['ruc'],
                'empresa_nombre': EMPRESA['nombre'],
                'empresa_direccion': EMPRESA['direccion'],
                'empresa_telefono': EMPRESA['telefono'],
                'empresa_email': EMPRESA['email'],
                'empresa_web': EMPRESA['web'],
                
                # Datos del comprobante
                'tipo': datos_comprobante.get('tipo_comprobante', datos_comprobante.get('tipo', 'Factura')),
                'serie': datos_comprobante.get('serie', 'F001'),
                'numero': datos_comprobante.get('numero', ''),
                'fecha_emision': self._formatear_fecha(datos_comprobante.get('fecha_emision', datos_comprobante.get('fecha'))),
                
                # Datos del cliente
                'cliente_nombre': datos_comprobante.get('cliente_nombre', datos_comprobante.get('cliente', '')),
                'cliente_ruc': datos_comprobante.get('cliente_numero_doc', datos_comprobante.get('ruc', '')),
                'cliente_direccion': datos_comprobante.get('cliente_direccion', datos_comprobante.get('direccion', '')),
                'cliente_email': datos_comprobante.get('cliente_email', datos_comprobante.get('email', '')),
                'cliente_telefono': datos_comprobante.get('cliente_telefono', datos_comprobante.get('telefono', '')),
                
                # Montos
                'moneda': datos_comprobante.get('moneda', 'S/'),
                'subtotal': f"{subtotal:.2f}",
                'igv': f"{igv:.2f}",
                'total': f"{total:.2f}",
                
                # Condiciones
                'condicion_pago': datos_comprobante.get('condicion_pago', datos_comprobante.get('condicion', 'Contado')),
                'estado': datos_comprobante.get('estado_sunat', datos_comprobante.get('estado', 'Borrador')),
                
                # Observaciones
                'observaciones': datos_comprobante.get('observaciones', ''),
                
                # ============================================================
                # DOCUMENTOS RELACIONADOS - MISMO NOMBRE QUE LA GUÍA
                # ============================================================
                'orden_compra_cliente': orden_compra_cliente or '—',
                'factura': factura or '—',  # ← MISMO NOMBRE QUE EN LA GUÍA
                'nro_cotizacion': nro_cotizacion or '—',
                
                # PRODUCTOS
                'items': items_formateados,
                
                # QR
                'qr_base64': qr_base64
            }

            # --- 9. OBTENER Y RENDERIZAR EL TEMPLATE ---
            template_content = self._obtener_template_comprobante()
            html_content = self._reemplazar_variables_template_comprobante(template_content, datos_mapeados)

            # --- 10. GUARDAR HTML PARA DEBUG ---
            try:
                with open('debug_comprobante.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print("💾 HTML de debug guardado en debug_comprobante.html")
            except:
                pass

            # --- 11. GENERAR EL PDF ---
            fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f"{datos_mapeados['tipo']}_{datos_mapeados['serie']}_{datos_mapeados['numero']}_{fecha}.pdf"
            
            base_url = f"file://{os.getcwd()}/"
            HTML(string=html_content, base_url=base_url).write_pdf(nombre_archivo)

            print(f"✅ PDF generado: {nombre_archivo}")
            return nombre_archivo

        except Exception as e:
            print(f"❌ Error en _generar_comprobante: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ============================================================
    # TEMPLATE HTML PARA COMPROBANTE (CON QR Y DOCUMENTOS RELACIONADOS)
    # ============================================================
    def _obtener_template_comprobante(self):
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ tipo }} {{ serie }}-{{ numero }}</title>
    <style>
        @page { size: A4; margin: 1.2cm 1.5cm; }
        body {
            font-family: 'Helvetica', Arial, sans-serif;
            font-size: 9.5px;
            color: #1a1a1a;
            line-height: 1.8;
        }
        .header-superior {
            display: flex;
            justify-content: space-between;
            align-items: stretch;
            margin-bottom: 10px;
            gap: 15px;
        }
        .empresa-izquierda {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .empresa-izquierda .logo-container {
            flex-shrink: 0;
            width: 80px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .empresa-izquierda .logo-container img {
            max-height: 60px;
            max-width: 100px;
            object-fit: contain;
        }
        .empresa-izquierda .info-texto {
            font-size: 8px;
            line-height: 1.4;
        }
        .empresa-izquierda .info-texto .nombre {
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .recuadro-derecha {
            flex-shrink: 0;
            border: 2px solid #000;
            border-radius: 12px;
            padding: 10px 20px;
            text-align: center;
            min-width: 200px;
        }
        .recuadro-derecha .ruc {
            font-size: 10px;
            font-weight: bold;
        }
        .recuadro-derecha .titulo {
            font-size: 13px;
            font-weight: bold;
            letter-spacing: 1px;
            margin: 2px 0;
        }
        .recuadro-derecha .numero {
            font-size: 15px;
            font-weight: bold;
        }
        
        .seccion {
            margin-bottom: 8px;
        }
        .seccion-titulo {
            font-weight: bold;
            font-size: 9.5px;
            margin-bottom: 3px;
            text-transform: uppercase;
            border-bottom: 1px solid #000;
            padding-bottom: 2px;
        }
        .info-cliente {
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 6px 12px;
            margin-bottom: 6px;
            background: #f9f9f9;
        }
        .fila {
            display: flex;
            padding: 1px 0;
            align-items: baseline;
        }
        .fila .label {
            font-weight: bold;
            min-width: 120px;
            flex-shrink: 0;
        }
        .fila .value {
            flex: 1;
            text-align: left;
            padding-left: 5px;
        }
        .products-table {
            width: 100%;
            border-collapse: collapse;
            margin: 4px 0;
            font-size: 8.5px;
        }
        .products-table th {
            background: #333;
            color: white;
            padding: 4px 5px;
            text-align: center;
            border: 1px solid #000;
        }
        .products-table td {
            padding: 3px 5px;
            border: 1px solid #ccc;
            text-align: center;
        }
        .products-table td.descripcion {
            text-align: left;
        }
        .products-table td.total-row {
            font-weight: bold;
            background: #f0f0f0;
        }
        .totales-box {
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 8px 12px;
            background: #f9f9f9;
            margin-top: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }
        .totales-box .linea {
            display: flex;
            justify-content: space-between;
            width: 220px;
            padding: 2px 0;
        }
        .totales-box .linea.total {
            font-weight: bold;
            font-size: 12px;
            border-top: 2px solid #000;
            padding-top: 4px;
            margin-top: 4px;
        }
        .totales-box .linea .label-total {
            font-weight: bold;
        }
        .totales-box .linea .value-total {
            font-weight: bold;
        }
        
        /* ============================================================
           DOCUMENTOS RELACIONADOS - IGUAL QUE EN LA GUÍA
           ============================================================ */
        .referencias {
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 6px 12px;
            margin-bottom: 6px;
            background: #f9f9f9;
        }
        .referencias-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
            padding: 6px 0;
        }
        .ref-item {
            text-align: center;
        }
        .ref-item .ref-label {
            font-weight: bold;
            display: block;
            font-size: 7.5px;
            color: #555;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        .ref-item .ref-value {
            font-size: 9px;
            font-weight: 600;
        }
        
        .qr-container {
            text-align: center;
            margin: 8px 0 5px 0;
            padding: 6px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #fafafa;
        }
        .qr-container img {
            width: 90px;
            height: 90px;
        }
        .qr-container .qr-text {
            font-size: 7px;
            color: #64748B;
            margin-top: 2px;
        }
        .footer {
            margin-top: 12px;
            text-align: center;
            font-size: 7.5px;
            color: #555;
            border-top: 1px solid #ddd;
            padding-top: 6px;
        }
        .footer .condicion-pago {
            margin: 4px 0;
            font-size: 8.5px;
            font-weight: bold;
            color: #0F172A;
        }
        .observaciones {
            margin-top: 6px;
            padding: 6px 10px;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            background: #fafafa;
            font-size: 8.5px;
        }
        .documentos-relacionados {
            display: flex;
            gap: 20px;
            padding: 4px 0;
            font-size: 8px;
            color: #475569;
        }
        .documentos-relacionados .doc-item {
            display: flex;
            gap: 4px;
        }
        .documentos-relacionados .doc-label {
            font-weight: bold;
            color: #334155;
        }
    </style>
</head>
<body>
    <!-- ENCABEZADO -->
    <div class="header-superior">
        <div class="empresa-izquierda">
            <div class="logo-container"><img src="{{ logo_src }}" alt="Logo" style="max-height:60px;"></div>
            <div class="info-texto">
                <div class="nombre">{{ empresa_nombre }}</div>
                <div class="contacto">
                    <span>Telf: {{ empresa_telefono }}</span><br>
                    <span>Email: {{ empresa_email }}</span><br>
                    <span>Web: {{ empresa_web }}</span>
                </div>
            </div>
        </div>
        <div class="recuadro-derecha">
            <div class="ruc">R.U.C. Nº {{ empresa_ruc }}</div>
            <div class="titulo">{{ tipo }}</div>
            <div class="numero">{{ serie }}-{{ numero }}</div>
        </div>
    </div>

    <!-- DATOS DEL CLIENTE -->
    <div class="seccion">
        <div class="seccion-titulo">DATOS DEL CLIENTE</div>
        <div class="info-cliente">
            <div class="fila"><span class="label">R.U.C.:</span><span class="value">{{ cliente_ruc }}</span></div>
            <div class="fila"><span class="label">RAZÓN SOCIAL:</span><span class="value">{{ cliente_nombre }}</span></div>
            <div class="fila"><span class="label">DIRECCIÓN:</span><span class="value">{{ cliente_direccion }}</span></div>
            <div class="fila"><span class="label">EMAIL:</span><span class="value">{{ cliente_email }}</span></div>
            <div class="fila"><span class="label">TELÉFONO:</span><span class="value">{{ cliente_telefono }}</span></div>
        </div>
    </div>

    <!-- ============================================================
         DOCUMENTOS RELACIONADOS - IGUAL QUE EN LA GUÍA
         ============================================================ -->
    <div class="seccion">
        <div class="seccion-titulo">DOCUMENTOS RELACIONADOS</div>
        <div class="referencias">
            <div class="referencias-grid">
                <div class="ref-item">
                    <span class="ref-label">NRO ORDEN DE COMPRA</span>
                    <span class="ref-value">{{ orden_compra_cliente or '—' }}</span>
                </div>
                <div class="ref-item">
                    <span class="ref-label">NRO DE FACTURA</span>
                    <span class="ref-value">{{ factura or '—' }}</span>
                </div>
                <div class="ref-item">
                    <span class="ref-label">NRO DE COTIZACION</span>
                    <span class="ref-value">{{ nro_cotizacion or '—' }}</span>
                </div>
            </div>
        </div>
    </div>

    <!-- DETALLE DE PRODUCTOS -->
    <div class="seccion">
        <div class="seccion-titulo">DETALLE DE PRODUCTOS</div>
        <table class="products-table">
            <thead>
                <tr>
                    <th style="width:6%">Item</th>
                    <th style="width:12%">Código</th>
                    <th style="width:35%">Descripción</th>
                    <th style="width:8%">UM</th>
                    <th style="width:8%">Cant.</th>
                    <th style="width:13%">Precio Unit.</th>
                    <th style="width:18%">Total</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr>
                    <td>{{ item.item }}</td>
                    <td>{{ item.codigo }}</td>
                    <td class="descripcion">{{ item.descripcion }}</td>
                    <td>{{ item.unidad }}</td>
                    <td>{{ item.cantidad }}</td>
                    <td>{{ moneda }} {{ "%.2f"|format(item.precio_unitario) }}</td>
                    <td>{{ moneda }} {{ "%.2f"|format(item.total_item) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- TOTALES -->
    <div class="totales-box">
        <div class="linea"><span>Subtotal:</span><span>{{ moneda }} {{ subtotal }}</span></div>
        <div class="linea"><span>IGV (18%):</span><span>{{ moneda }} {{ igv }}</span></div>
        <div class="linea total">
            <span class="label-total">TOTAL:</span>
            <span class="value-total">{{ moneda }} {{ total }}</span>
        </div>
    </div>

    <!-- CONDICIONES DE PAGO -->
    <div class="seccion">
        <div class="seccion-titulo">CONDICIONES DE PAGO</div>
        <div class="info-cliente" style="background:#f9f9f9; padding:4px 12px;">
            <div class="fila"><span class="label">Condición:</span><span class="value" style="font-weight:bold;">{{ condicion_pago }}</span></div>
            <div class="fila"><span class="label">Estado:</span><span class="value">{{ estado }}</span></div>
            <div class="fila"><span class="label">Fecha Emisión:</span><span class="value">{{ fecha_emision }}</span></div>
        </div>
    </div>

    <!-- OBSERVACIONES -->
    {% if observaciones %}
    <div class="observaciones">
        <strong>Observaciones:</strong> {{ observaciones }}
    </div>
    {% endif %}

    <!-- QR -->
    <div class="qr-container">
        <img src="{{ qr_base64 }}" alt="QR">
        <div class="qr-text">Representación impresa del {{ tipo }}
Autorizado mediante resolución N° 214-005-0001193/SUNAT</div>
    </div>

    <div class="footer">
        <div>Pag. 1 de 1</div>
        <div class="condicion-pago">** {{ condicion_pago }} **</div>
        <div>Powered by KCF CORPORACION</div>
    </div>
</body>
</html>"""

    # ============================================================
    # REEMPLAZAR VARIABLES DEL TEMPLATE DE COMPROBANTE
    # ============================================================
    def _reemplazar_variables_template_comprobante(self, template, datos):
        try:
            return Template(template).render(**datos)
        except Exception as e:
            print(f"❌ Error renderizando template Jinja2 de comprobante: {e}")
            html = template
            
            variables = {
                'logo_src': datos.get('logo_src', ''),
                'empresa_ruc': '20602095704',
                'empresa_nombre': 'KCF CORPORACION E.I.R.L',
                'empresa_direccion': 'JR. LAS ALMENDRAS VERDES NRO. 284 URB. VIRGEN DEL ROSARIO LIMA - LIMA - SAN MARTIN DE PORRES',
                'empresa_telefono': '999 932 051',
                'empresa_email': 'ventas@kcfcorporacion.com',
                'empresa_web': 'https://kcfcorporacion.com/',
                'tipo': datos.get('tipo', 'Factura'),
                'serie': datos.get('serie', 'F001'),
                'numero': datos.get('numero', ''),
                'fecha_emision': datos.get('fecha_emision', ''),
                'cliente_nombre': datos.get('cliente_nombre', ''),
                'cliente_ruc': datos.get('cliente_ruc', ''),
                'cliente_direccion': datos.get('cliente_direccion', ''),
                'cliente_email': datos.get('cliente_email', ''),
                'cliente_telefono': datos.get('cliente_telefono', ''),
                'moneda': datos.get('moneda', 'S/'),
                'subtotal': datos.get('subtotal', '0.00'),
                'igv': datos.get('igv', '0.00'),
                'total': datos.get('total', '0.00'),
                'condicion_pago': datos.get('condicion_pago', 'Contado'),
                'estado': datos.get('estado', 'Borrador'),
                'observaciones': datos.get('observaciones', ''),
                'orden_compra_cliente': datos.get('orden_compra_cliente', '—'),
                'factura': datos.get('factura', '—'),  # ← MISMO NOMBRE QUE LA GUÍA
                'nro_cotizacion': datos.get('nro_cotizacion', '—'),
                'qr_base64': datos.get('qr_base64', ''),
            }
            
            for key, value in variables.items():
                html = html.replace(f"{{{{ {key} }}}}", str(value))
            
            items_html = ""
            for item in datos.get('items', []):
                items_html += f"""
                <tr>
                    <td>{item.get('item', '')}</td>
                    <td>{item.get('codigo', '')}</td>
                    <td class="descripcion">{item.get('descripcion', '')}</td>
                    <td>{item.get('unidad', 'NIU')}</td>
                    <td>{item.get('cantidad', 0)}</td>
                    <td>{item.get('precio_unitario', 0):.2f}</td>
                    <td>{item.get('total_item', 0):.2f}</td>
                </tr>
                """
            html = html.replace("{% for item in items %}", items_html)
            html = html.replace("{% endfor %}", "")
            
            html = re.sub(r'{%.*?%}', '', html, flags=re.DOTALL)
            html = re.sub(r'{{.*?}}', '', html, flags=re.DOTALL)
            
            return html



# ============================================================
# GENERAR COTIZACIÓN - CON LOGO A LA IZQUIERDA (CORREGIDO)
# ============================================================
def _generar_cotizacion(self, datos):
    try:
        print("📄 Generando PDF de cotización...")
        
        # 🔽 OBTENER LOGO - ESTO ES LO QUE FALTABA 🔽
        logo_base64 = self._obtener_logo_base64()
        logo_src = f"data:image/png;base64,{logo_base64}" if logo_base64 else ""
        print(f"📷 Logo cargado: {'Sí' if logo_base64 else 'No'}")
        
        # Datos de la empresa (fijos)
        EMPRESA = {
            'ruc': '20602095704',
            'nombre': 'KCF CORPORACION E.I.R.L',
            'direccion': 'JR. LAS ALMENDRAS VERDES NRO. 284 URB. VIRGEN DEL ROSARIO LIMA - LIMA - SAN MARTIN DE PORRES',
            'telefono': '999 932 051',
            'email': 'ventas@kcfcorporacion.com',
            'web': 'https://kcfcorporacion.com/'
        }
        
        # Obtener items
        items = datos.get('items', [])
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except:
                items = []
        
        # Formatear items para el template
        items_formateados = []
        for idx, item in enumerate(items, 1):
            if isinstance(item, dict):
                items_formateados.append({
                    'item': idx,
                    'codigo': item.get('codigo', ''),
                    'descripcion': item.get('producto', item.get('descripcion', '')),
                    'marca': item.get('marca', ''),
                    'modelo': item.get('modelo', ''),
                    'unidad': item.get('um', 'NIU'),
                    'cantidad': float(item.get('cantidad', 1)),
                    'precio_unitario': float(item.get('valorVenta', item.get('precio', 0))),
                    'total_item': float(item.get('cantidad', 1)) * float(item.get('valorVenta', item.get('precio', 0)))
                })
            elif isinstance(item, (list, tuple)):
                items_formateados.append({
                    'item': idx,
                    'codigo': item[0] if len(item) > 0 else '',
                    'descripcion': item[1] if len(item) > 1 else '',
                    'marca': item[4] if len(item) > 4 else '',
                    'modelo': item[5] if len(item) > 5 else '',
                    'unidad': 'NIU',
                    'cantidad': float(item[2] if len(item) > 2 else 1),
                    'precio_unitario': float(item[3] if len(item) > 3 else 0),
                    'total_item': float(item[2] if len(item) > 2 else 1) * float(item[3] if len(item) > 3 else 0)
                })
        
        # Calcular totales
        subtotal = float(datos.get('subtotal', 0))
        igv = float(datos.get('igv', 0))
        total = float(datos.get('total', datos.get('monto', 0)))
        
        if subtotal == 0 and items_formateados:
            subtotal = sum(item['total_item'] for item in items_formateados)
            igv = subtotal * 0.18
            total = subtotal + igv
        
        # 🔽 VERIFICAR QUE EL LOGO SE PASE AL TEMPLATE 🔽
        datos_template = {
            'logo_src': logo_src,  # ← ESTO ES CRÍTICO
            'empresa_ruc': EMPRESA['ruc'],
            'empresa_nombre': EMPRESA['nombre'],
            'empresa_direccion': EMPRESA['direccion'],
            'empresa_telefono': EMPRESA['telefono'],
            'empresa_email': EMPRESA['email'],
            'empresa_web': EMPRESA['web'],
            'tipo': datos.get('tipo_documento', 'COTIZACIÓN'),
            'serie': datos.get('serie', 'COT'),
            'numero': datos.get('numero', datos.get('numero_cotizacion', '')),
            'fecha_emision': self._formatear_fecha(datos.get('fecha_emision', datos.get('fecha'))),
            'cliente_nombre': datos.get('cliente_nombre', datos.get('razon', datos.get('cliente', ''))),
            'cliente_ruc': datos.get('cliente_ruc', datos.get('ruc', '')),
            'cliente_direccion': datos.get('cliente_direccion', datos.get('direccion', '')),
            'cliente_email': datos.get('cliente_email', datos.get('email', '')),
            'cliente_telefono': datos.get('cliente_telefono', datos.get('telefono', '')),
            'moneda': datos.get('moneda', 'S/'),
            'subtotal': f"{subtotal:.2f}",
            'igv': f"{igv:.2f}",
            'total': f"{total:.2f}",
            'condicion_pago': datos.get('condicion_pago', datos.get('condicion', 'Contado')),
            'tiempo_entrega': datos.get('tiempo_entrega', datos.get('entrega', '')),
            'validez': datos.get('validez', datos.get('validez_oferta', '15 días')),
            'observaciones': datos.get('observaciones', ''),
            'orden_compra_cliente': datos.get('orden_compra_cliente', '—'),
            'nro_cotizacion': datos.get('nro_cotizacion', datos.get('numero_cotizacion', '—')),
            'items': items_formateados,
            'qr_base64': self._generar_qr_cotizacion(datos)
        }
        
        print(f"📷 Logo en datos_template: {'Sí' if datos_template.get('logo_src') else 'No'}")
        
        # Obtener template
        template_content = self._obtener_template_cotizacion()
        
        # Renderizar
        try:
            html_content = Template(template_content).render(**datos_template)
        except Exception as e:
            print(f"❌ Error renderizando template de cotización: {e}")
            html_content = template_content
        
        # Guardar HTML para debug
        try:
            with open('debug_cotizacion.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print("💾 HTML de debug guardado en debug_cotizacion.html")
        except:
            pass
        
        # Generar PDF
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f"cotizacion_{datos_template['serie']}_{datos_template['numero']}_{fecha}.pdf"
        
        base_url = f"file://{os.getcwd()}/"
        HTML(string=html_content, base_url=base_url).write_pdf(nombre_archivo)
        
        print(f"✅ PDF generado: {nombre_archivo}")
        return nombre_archivo
        
    except Exception as e:
        print(f"❌ Error generando cotización: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================
# TEMPLATE PARA COTIZACIÓN - CON LOGO Y RECUADRO (IGUAL QUE GUÍA)
# ============================================================
def _obtener_template_cotizacion(self):
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ tipo }} {{ serie }}-{{ numero }}</title>
    <style>
        @page { size: A4; margin: 1.2cm 1.5cm; }
        body {
            font-family: 'Helvetica', Arial, sans-serif;
            font-size: 9.5px;
            color: #1a1a1a;
            line-height: 1.8;
        }
        
        /* ============================================================
           ENCABEZADO - LOGO IZQUIERDA, RECUADRO DERECHA (IGUAL QUE GUÍA)
           ============================================================ */
        .header-superior {
            display: flex;
            justify-content: space-between;
            align-items: stretch;
            margin-bottom: 10px;
            gap: 15px;
        }
        .empresa-izquierda {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .empresa-izquierda .logo-container {
            flex-shrink: 0;
            width: 80px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .empresa-izquierda .logo-container img {
            max-height: 60px;
            max-width: 100px;
            object-fit: contain;
        }
        .empresa-izquierda .info-texto {
            font-size: 8px;
            line-height: 1.4;
        }
        .empresa-izquierda .info-texto .nombre {
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .recuadro-derecha {
            flex-shrink: 0;
            border: 2px solid #000;
            border-radius: 12px;
            padding: 10px 20px;
            text-align: center;
            min-width: 200px;
        }
        .recuadro-derecha .ruc {
            font-size: 10px;
            font-weight: bold;
        }
        .recuadro-derecha .titulo {
            font-size: 13px;
            font-weight: bold;
            letter-spacing: 1px;
            margin: 2px 0;
        }
        .recuadro-derecha .numero {
            font-size: 15px;
            font-weight: bold;
        }
        
        /* ============================================================
           SECCIONES
           ============================================================ */
        .seccion {
            margin-bottom: 8px;
        }
        .seccion-titulo {
            font-weight: bold;
            font-size: 9.5px;
            margin-bottom: 3px;
            text-transform: uppercase;
            border-bottom: 1px solid #000;
            padding-bottom: 2px;
        }
        .info-cliente {
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 6px 12px;
            margin-bottom: 6px;
            background: #f9f9f9;
        }
        .fila {
            display: flex;
            padding: 1px 0;
            align-items: baseline;
        }
        .fila .label {
            font-weight: bold;
            min-width: 120px;
            flex-shrink: 0;
        }
        .fila .value {
            flex: 1;
            text-align: left;
            padding-left: 5px;
        }
        
        /* ============================================================
           TABLA DE PRODUCTOS
           ============================================================ */
        .products-table {
            width: 100%;
            border-collapse: collapse;
            margin: 4px 0;
            font-size: 8.5px;
        }
        .products-table th {
            background: #333;
            color: white;
            padding: 4px 5px;
            text-align: center;
            border: 1px solid #000;
        }
        .products-table td {
            padding: 3px 5px;
            border: 1px solid #ccc;
            text-align: center;
        }
        .products-table td.descripcion {
            text-align: left;
        }
        .products-table td.total-row {
            font-weight: bold;
            background: #f0f0f0;
        }
        
        /* ============================================================
           TOTALES
           ============================================================ */
        .totales-box {
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 8px 12px;
            background: #f9f9f9;
            margin-top: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }
        .totales-box .linea {
            display: flex;
            justify-content: space-between;
            width: 220px;
            padding: 2px 0;
        }
        .totales-box .linea.total {
            font-weight: bold;
            font-size: 12px;
            border-top: 2px solid #000;
            padding-top: 4px;
            margin-top: 4px;
        }
        .totales-box .linea .label-total {
            font-weight: bold;
        }
        .totales-box .linea .value-total {
            font-weight: bold;
        }
        
        /* ============================================================
           DOCUMENTOS RELACIONADOS (IGUAL QUE GUÍA)
           ============================================================ */
        .referencias {
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 6px 12px;
            margin-bottom: 6px;
            background: #f9f9f9;
        }
        .referencias-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
            padding: 6px 0;
        }
        .ref-item {
            text-align: center;
        }
        .ref-item .ref-label {
            font-weight: bold;
            display: block;
            font-size: 7.5px;
            color: #555;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        .ref-item .ref-value {
            font-size: 9px;
            font-weight: 600;
        }
        
        /* ============================================================
           QR Y FOOTER
           ============================================================ */
        .qr-container {
            text-align: center;
            margin: 8px 0 5px 0;
            padding: 6px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #fafafa;
        }
        .qr-container img {
            width: 90px;
            height: 90px;
        }
        .qr-container .qr-text {
            font-size: 7px;
            color: #64748B;
            margin-top: 2px;
        }
        .footer {
            margin-top: 12px;
            text-align: center;
            font-size: 7.5px;
            color: #555;
            border-top: 1px solid #ddd;
            padding-top: 6px;
        }
        .footer .condicion-pago {
            margin: 4px 0;
            font-size: 8.5px;
            font-weight: bold;
            color: #0F172A;
        }
        .observaciones {
            margin-top: 6px;
            padding: 6px 10px;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            background: #fafafa;
            font-size: 8.5px;
        }
        .condiciones {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px 20px;
            padding: 4px 0;
        }
        .condiciones .cond-item {
            display: flex;
            gap: 4px;
            font-size: 8.5px;
        }
        .condiciones .cond-label {
            font-weight: bold;
            color: #475569;
        }
        .condiciones .cond-value {
            font-weight: 600;
            color: #0F172A;
        }
    </style>
</head>
<body>
    <!-- ============================================================
         ENCABEZADO - LOGO IZQUIERDA, RECUADRO DERECHA
         ============================================================ -->
    <div class="header-superior">
        <div class="empresa-izquierda">
            <div class="logo-container">
                <img src="{{ logo_src }}" alt="Logo" style="max-height:60px;">
            </div>
            <div class="info-texto">
                <div class="nombre">{{ empresa_nombre }}</div>
                <div class="contacto">
                    <span>Telf: {{ empresa_telefono }}</span><br>
                    <span>Email: {{ empresa_email }}</span><br>
                    <span>Web: {{ empresa_web }}</span>
                </div>
            </div>
        </div>
        <div class="recuadro-derecha">
            <div class="ruc">R.U.C. Nº {{ empresa_ruc }}</div>
            <div class="titulo">{{ tipo }}</div>
            <div class="numero">{{ serie }}-{{ numero }}</div>
        </div>
    </div>

    <!-- ============================================================
         DATOS DEL CLIENTE
         ============================================================ -->
    <div class="seccion">
        <div class="seccion-titulo">DATOS DEL CLIENTE</div>
        <div class="info-cliente">
            <div class="fila"><span class="label">R.U.C.:</span><span class="value">{{ cliente_ruc }}</span></div>
            <div class="fila"><span class="label">RAZÓN SOCIAL:</span><span class="value">{{ cliente_nombre }}</span></div>
            <div class="fila"><span class="label">DIRECCIÓN:</span><span class="value">{{ cliente_direccion }}</span></div>
            <div class="fila"><span class="label">EMAIL:</span><span class="value">{{ cliente_email }}</span></div>
            <div class="fila"><span class="label">TELÉFONO:</span><span class="value">{{ cliente_telefono }}</span></div>
        </div>
    </div>

    <!-- ============================================================
         DOCUMENTOS RELACIONADOS (IGUAL QUE GUÍA)
         ============================================================ -->
    <div class="seccion">
        <div class="seccion-titulo">DOCUMENTOS RELACIONADOS</div>
        <div class="referencias">
            <div class="referencias-grid">
                <div class="ref-item">
                    <span class="ref-label">NRO ORDEN DE COMPRA</span>
                    <span class="ref-value">{{ orden_compra_cliente or '—' }}</span>
                </div>
                <div class="ref-item">
                    <span class="ref-label">NRO DE COTIZACION</span>
                    <span class="ref-value">{{ nro_cotizacion or '—' }}</span>
                </div>
                <div class="ref-item">
                    <span class="ref-label">FECHA EMISIÓN</span>
                    <span class="ref-value">{{ fecha_emision or '—' }}</span>
                </div>
            </div>
        </div>
    </div>

    <!-- ============================================================
         DETALLE DE PRODUCTOS
         ============================================================ -->
    <div class="seccion">
        <div class="seccion-titulo">DETALLE DE PRODUCTOS</div>
        <table class="products-table">
            <thead>
                <tr>
                    <th style="width:5%">Item</th>
                    <th style="width:12%">Código</th>
                    <th style="width:33%">Descripción</th>
                    <th style="width:10%">Marca</th>
                    <th style="width:8%">Modelo</th>
                    <th style="width:6%">UM</th>
                    <th style="width:6%">Cant.</th>
                    <th style="width:10%">Precio Unit.</th>
                    <th style="width:10%">Total</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr>
                    <td>{{ item.item }}</td>
                    <td>{{ item.codigo }}</td>
                    <td class="descripcion">{{ item.descripcion }}</td>
                    <td>{{ item.marca }}</td>
                    <td>{{ item.modelo }}</td>
                    <td>{{ item.unidad }}</td>
                    <td>{{ item.cantidad }}</td>
                    <td>{{ moneda }} {{ "%.2f"|format(item.precio_unitario) }}</td>
                    <td>{{ moneda }} {{ "%.2f"|format(item.total_item) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- ============================================================
         TOTALES
         ============================================================ -->
    <div class="totales-box">
        <div class="linea"><span>Subtotal:</span><span>{{ moneda }} {{ subtotal }}</span></div>
        <div class="linea"><span>IGV (18%):</span><span>{{ moneda }} {{ igv }}</span></div>
        <div class="linea total">
            <span class="label-total">TOTAL:</span>
            <span class="value-total">{{ moneda }} {{ total }}</span>
        </div>
    </div>

    <!-- ============================================================
         CONDICIONES COMERCIALES
         ============================================================ -->
    <div class="seccion">
        <div class="seccion-titulo">CONDICIONES COMERCIALES</div>
        <div class="info-cliente" style="background:#f9f9f9; padding:4px 12px;">
            <div class="condiciones">
                <div class="cond-item">
                    <span class="cond-label">Condición de Pago:</span>
                    <span class="cond-value">{{ condicion_pago }}</span>
                </div>
                <div class="cond-item">
                    <span class="cond-label">Tiempo de Entrega:</span>
                    <span class="cond-value">{{ tiempo_entrega or '—' }}</span>
                </div>
                <div class="cond-item">
                    <span class="cond-label">Validez de Oferta:</span>
                    <span class="cond-value">{{ validez or '—' }}</span>
                </div>
                <div class="cond-item">
                    <span class="cond-label">Fecha Emisión:</span>
                    <span class="cond-value">{{ fecha_emision }}</span>
                </div>
            </div>
        </div>
    </div>

    <!-- ============================================================
         OBSERVACIONES
         ============================================================ -->
    {% if observaciones %}
    <div class="observaciones">
        <strong>Observaciones:</strong> {{ observaciones }}
    </div>
    {% endif %}

    <!-- ============================================================
         QR
         ============================================================ -->
    <div class="qr-container">
        <img src="{{ qr_base64 }}" alt="QR">
        <div class="qr-text">Representación impresa de la COTIZACIÓN
Autorizado mediante resolución N° 214-005-0001193/SUNAT</div>
    </div>

    <!-- ============================================================
         FOOTER
         ============================================================ -->
    <div class="footer">
        <div>Pag. 1 de 1</div>
        <div class="condicion-pago">** {{ condicion_pago }} **</div>
        <div>Powered by KCF CORPORACION</div>
    </div>
</body>
</html>"""

# ============================================================
# GENERAR QR PARA COTIZACIÓN
# ============================================================
def _generar_qr_cotizacion(self, datos):
    try:
        import qrcode
        from io import BytesIO
        
        qr_data = {
            'tipo': datos.get('tipo_documento', 'COTIZACIÓN'),
            'serie': datos.get('serie', 'COT'),
            'numero': datos.get('numero', datos.get('numero_cotizacion', '')),
            'ruc_emisor': '20602095704',
            'ruc_cliente': datos.get('cliente_ruc', datos.get('ruc', '')),
            'fecha_emision': self._formatear_fecha(datos.get('fecha_emision', datos.get('fecha'))),
            'total': str(datos.get('total', datos.get('monto', 0)))
        }
        
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4,
            border=2
        )
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    except ImportError:
        print("⚠️ qrcode no instalado, QR no generado")
        return ""
    except Exception as e:
        print(f"⚠️ Error generando QR: {e}")
        return ""
    # ============================================================
    # GENERAR ORDEN DE COMPRA
    # ============================================================
    def _generar_orden_compra(self, datos):
        print("Generando orden de compra...")
        return None


# ============================================================
# INSTANCIA GLOBAL
# ============================================================
pdf_generator = PDFGenerator()