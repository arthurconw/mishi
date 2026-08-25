# pdf_generator.py - VERSIÓN COMPLETA CORREGIDA

import os
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
    # OBTENER LOGO EN BASE64 - CON RUTA templates/pdf/logo-kcf.png
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
    # MÉTODO PRINCIPAL
    # ============================================================
    def generar_pdf_universal(self, datos):
        print(f"📄 Generando PDF universal...")
        tipo = datos.get('tipo_documento', '')
        
        if tipo == 'guia_remision' or ('serie' in datos and 'numero' in datos and 'destinatario_nombre' in datos):
            return self._generar_guia_remision(datos)
        elif tipo in ['factura', 'boleta', 'comprobante']:
            return self._generar_comprobante(datos)
        elif tipo == 'cotizacion' or 'numero_cotizacion' in datos:
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
            print(f"❌ Error: {e}")
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
    <div class="qr-container"><img src="{{ qr_base64 }}" alt="QR"><div class="qr-text">Representación impresa de la GUIA DE REMISIÓN</div></div>
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
        html = template
        logo_src = datos.get('logo_src', '')
        html = html.replace('{{ logo_src }}', logo_src)
        
        variables = [
            'ruc_remitente', 'remitente_nombre', 'remitente_direccion',
            'remitente_ubigeo', 'telefono', 'email', 'web',
            'ruc_destinatario', 'destinatario_nombre', 'destinatario_direccion',
            'destinatario_ubigeo', 'serie', 'numero',
            'fecha_emision', 'fecha_traslado', 'fecha_inicio_traslado',
            'motivo_traslado', 'motivo_texto', 'modalidad_texto',
            'peso_bruto_total', 'numero_bultos', 'unidad_peso_texto', 
            'transportista_nombre', 'conductor_nombre', 'conductor_dni', 
            'placa_vehiculo', 'licencia_conductor', 'nro_cotizacion', 'observaciones'
        ]
        for var in variables:
            value = datos.get(var, '')
            html = html.replace(f"{{{{ {var} }}}}", str(value))
        
        qr = datos.get('qr_base64', '')
        html = html.replace("{{ qr_base64 }}", qr)
        html = html.replace("{% for item in items %}", datos.get('filas_productos', ''))
        html = html.replace("{% endfor %}", "")
        html = re.sub(r'{%.*?%}', '', html, flags=re.DOTALL)
        html = re.sub(r'{{.*?}}', '', html, flags=re.DOTALL)
        return html

    # ============================================================
    # GENERAR FACTURA / BOLETA
    # ============================================================
    def _generar_comprobante(self, datos):
        print("📄 Generando PDF de comprobante...")
        return None

    # ============================================================
    # GENERAR COTIZACIÓN
    # ============================================================
    def _generar_cotizacion(self, datos):
        print("📄 Generando PDF de cotización...")
        return None

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