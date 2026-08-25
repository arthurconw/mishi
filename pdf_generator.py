# pdf_generator.py - VERSIÓN COMPLETA Y CORREGIDA

import os
from weasyprint import HTML
from datetime import datetime
from flask import render_template_string
import json
import base64
import re

class PDFGenerator:
    def __init__(self):
        self.templates_dir = 'templates/cotizacion_oc/'
        self.logo_base64 = None  # Cache para el logo

    # ============================================================
    # OBTENER LOGO EN BASE64 - CORREGIDO
    # ============================================================
    def _obtener_logo_base64(self):
        """Obtiene el logo en base64 para incrustarlo en el PDF"""
        if self.logo_base64:
            return self.logo_base64 
        
        # ============================================================
        # 🔽 RUTA ESPECÍFICA DONDE ESTÁ EL LOGO (templates/pdf/logo-kcf.png)
        # ============================================================
        posibles_rutas = [
            os.path.join('templates', 'pdf', 'logo-kcf.png'),  # <--- TU RUTA
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
                        print(f"✅ Logo encontrado y cargado desde: {logo_path}")
                        return self.logo_base64
                except Exception as e:
                    print(f"⚠️ Error al leer logo desde {logo_path}: {e}")
                    continue
            else:
                print(f"🔍 Logo no encontrado en: {logo_path}")
        
        print("❌ No se encontró el logo en ninguna de las rutas probadas")
        return None

    # ============================================================
    # MAPEAR DATOS DE GUÍA - CORREGIDO (INDENTACIÓN DENTRO DE LA CLASE)
    # ============================================================
    def _mapear_datos_guia(self, datos_guia):
        """Mapea los datos de la guía al formato esperado"""
        # ============================================================
        # 🔽 DATOS CORRECTOS DE LA EMPRESA (KCF CORPORACION E.I.R.L)
        # ============================================================
        EMPRESA = {
            'ruc': '20602095704',
            'nombre': 'KCF CORPORACION E.I.R.L',
            'direccion': 'JR. LAS ALMENDRAS VERDES NRO. 284 URB. VIRGEN DEL ROSARIO LIMA - LIMA - SAN MARTIN DE PORRES',
            'telefono': '999 932 051',
            'email': 'ventas@kcfcorporacion.com',
            'web': 'https://kcfcorporacion.com/'
        }
        
        print(f"🔍 DATOS RECIBIDOS en _mapear_datos_guia:")
        print(f"  - orden_compra_cliente: {datos_guia.get('orden_compra_cliente', 'NO')}")
        print(f"  - factura: {datos_guia.get('factura', 'NO')}")
        print(f"  - documento_asociado: {datos_guia.get('documento_asociado', 'NO')}")
        
        logo_base64 = self._obtener_logo_base64()
        logo_src = f"data:image/png;base64,{logo_base64}" if logo_base64 else ""
        
        # Procesar items
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
        
        # Calcular peso total si no viene
        peso_total = float(datos_guia.get('peso_total', 0))
        if peso_total == 0 and items_formateados:
            peso_total = sum(float(item['cantidad']) * 0.5 for item in items_formateados)
        
        # ============================================================
        # 🔽 USAR LOS DATOS DEL BACKEND (datos_guia) como PRIORIDAD
        # ============================================================
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


def _obtener_logo_base64(self):
    """Obtiene el logo en base64 para incrustarlo en el PDF"""
    if self.logo_base64:
        return self.logo_base64 
    
    # ============================================================
    # 🔽 MÚLTIPLES RUTAS POSIBLES PARA EL LOGO
    # ============================================================
    posibles_rutas = [
        os.path.join('static', 'img', 'logo-kcf.png'),
        os.path.join('static', 'logo-kcf.png'),
        os.path.join('templates', 'logo-kcf.png'),
        'logo-kcf.png',
        os.path.join('static', 'images', 'logo-kcf.png'),
    ]
    
    for logo_path in posibles_rutas:
        if os.path.exists(logo_path):
            try:
                with open(logo_path, 'rb') as f:
                    logo_data = f.read()
                    self.logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                    print(f"✅ Logo encontrado y cargado desde: {logo_path}")
                    return self.logo_base64
            except Exception as e:
                print(f"⚠️ Error al leer logo desde {logo_path}: {e}")
                continue
        else:
            print(f"🔍 Logo no encontrado en: {logo_path}")
    
    print("❌ No se encontró el logo en ninguna de las rutas probadas")
    print("   Rutas buscadas:")
    for ruta in posibles_rutas:
        print(f"   - {ruta}")
    return None
    # ============================================================
    # 🔽 RUTAS POSIBLES PARA EL LOGO (orden de prioridad)
    # ============================================================
    posibles_rutas = [
        os.path.join('static', 'img', 'logo-kcf.png'),  # Ruta más común en Flask
        os.path.join('static', 'logo-kcf.png'),
        os.path.join('templates', 'logo-kcf.png'),
        'logo-kcf.png',
        os.path.join('static', 'images', 'logo-kcf.png'),
    ]
    
    for logo_path in posibles_rutas:
        if os.path.exists(logo_path):
            try:
                with open(logo_path, 'rb') as f:
                    logo_data = f.read()
                    self.logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                    print(f"✅ Logo encontrado en: {logo_path}")
                    return self.logo_base64
            except Exception as e:
                print(f"Error al leer logo desde {logo_path}: {e}")
                continue
        else:
            print(f"⚠️ Logo no encontrado en: {logo_path}")
    
    print("❌ No se encontró el logo en ninguna de las rutas probadas")
    return None
    # ============================================================
    # MÉTODO PRINCIPAL - GENERAR PDF UNIVERSAL
    # ============================================================
    def generar_pdf_universal(self, datos):
        """Genera PDF basado en el tipo de documento - MÉTODO PRINCIPAL"""
        try:
            tipo_documento = datos.get('tipo_documento', '')
            
            print(f"📄 Generando PDF universal - Tipo detectado: {tipo_documento}")
            
            # GUÍA DE REMISIÓN
            if tipo_documento == 'guia_remision' or ('serie' in datos and 'numero' in datos and 'destinatario_nombre' in datos):
                return self._generar_guia_remision(datos)
            
            # FACTURA / BOLETA (COMPROBANTE)
            elif tipo_documento in ['factura', 'boleta', 'comprobante'] or ('serie' in datos and 'numero' in datos and 'cliente' in datos and 'tipo' in datos):
                return self._generar_comprobante(datos)
            
            # ORDEN DE COMPRA
            elif tipo_documento == 'orden_compra' or 'numero_orden' in datos:
                return self._generar_orden_compra(datos)
            
            # COTIZACIÓN (por defecto)
            elif tipo_documento == 'cotizacion' or 'numero_cotizacion' in datos:
                return self._generar_cotizacion(datos)
            else:
                # Detección automática
                if 'proveedor_razon_social' in datos:
                    return self._generar_orden_compra(datos)
                elif 'destinatario_nombre' in datos and 'serie' in datos:
                    return self._generar_guia_remision(datos)
                elif 'cliente' in datos and 'tipo' in datos:
                    return self._generar_comprobante(datos)
                else:
                    return self._generar_cotizacion(datos)
                    
        except Exception as e:
            print(f"❌ Error en generación universal de PDF: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ============================================================
    # GENERAR GUÍA DE REMISIÓN
    # ============================================================
    def _generar_guia_remision(self, datos_guia):
        """Genera PDF para Guía de Remisión usando template en memoria"""
        try:
            print("📄 Iniciando generación de PDF de Guía de Remisión...")
            
            datos_mapeados = self._mapear_datos_guia(datos_guia)
            
            template_content = self._obtener_template_guia()
            
            filas_productos = self._generar_filas_productos_guia(datos_mapeados.get('items', []))
            datos_mapeados['filas_productos'] = filas_productos
            
            html_content = self._reemplazar_variables_template_guia(template_content, datos_mapeados)
            
            fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_file = f"guia_{datos_mapeados.get('serie', 'T001')}_{datos_mapeados.get('numero', 'sin_numero')}_{fecha}.pdf"
            
            print(f"Generando PDF: {pdf_file}")
            
            base_url = f"file://{os.getcwd()}/"
            HTML(string=html_content, base_url=base_url).write_pdf(pdf_file)
            
            print("✅ PDF de Guía de Remisión generado exitosamente")
            return pdf_file
            
        except Exception as e:
            print(f"❌ Error generando PDF de guía: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _obtener_template_guia(self):
        """Retorna el template HTML de la guía como string (en memoria)"""
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
            border: 1px solid #ccc; border-radius: 8px; padding: 6px 12px; margin-bottom: 6px; background: #f9f9f9;
        }
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
            <div class="logo-container">
                <img src="{{ logo_src }}" alt="Logo" style="max-height:60px;">
            </div>
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
            <div class="fila"><span class="label">PUNTO DE PARTIDA:</span><span class="value">{{ remitente_direccion }}</span></div>
            <div class="fila"><span class="label">PUNTO DE LLEGADA:</span><span class="value">{{ destinatario_direccion }}</span></div>
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
            <thead>
                <tr>
                    <th style="width:8%">ITEM</th>
                    <th style="width:15%">CODIGO</th>
                    <th style="width:40%">PRODUCTO</th>
                    <th style="width:15%">U/M</th>
                    <th style="width:15%">CANTIDAD</th>
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
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <!-- ============================================================ -->
    <!-- SECCIÓN DOCUMENTOS RELACIONADOS - CORREGIDA -->
    <!-- ============================================================ -->
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
    
    <div class="observaciones">
        <div class="fila"><span class="label">OBSERVACIONES:</span><span class="value">{{ observaciones }}</span></div>
    </div>
    
    <div class="qr-container">
        <img src="{{ qr_base64 }}" alt="Código QR">
        <div class="qr-text">Representación impresa de la GUIA DE REMISIÓN</div>
    </div>
    
    <div class="footer">
        <div>Pag. 1 de 1</div>
        <div>Powered by KCF CORPORACION</div>
    </div>
</body>
</html>"""

def _mapear_datos_guia(self, datos_guia):
    """Mapea los datos de la guía al formato esperado"""
    # ============================================================
    # 🔽 DATOS CORRECTOS DE LA EMPRESA (KCF CORPORACION E.I.R.L)
    # ============================================================
    EMPRESA = {
        'ruc': '20602095704',
        'nombre': 'KCF CORPORACION E.I.R.L',
        'direccion': 'JR. LAS ALMENDRAS VERDES NRO. 284 URB. VIRGEN DEL ROSARIO LIMA - LIMA - SAN MARTIN DE PORRES',
        'telefono': '999 932 051',
        'email': 'ventas@kcfcorporacion.com',
        'web': 'https://kcfcorporacion.com/'
    }
    
    print(f"🔍 DATOS RECIBIDOS en _mapear_datos_guia:")
    print(f"  - orden_compra_cliente: {datos_guia.get('orden_compra_cliente', 'NO')}")
    print(f"  - factura: {datos_guia.get('factura', 'NO')}")
    print(f"  - documento_asociado: {datos_guia.get('documento_asociado', 'NO')}")
    
    logo_base64 = self._obtener_logo_base64()
    logo_src = f"data:image/png;base64,{logo_base64}" if logo_base64 else ""
    
    # Procesar items
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
    
    # Calcular peso total si no viene
    peso_total = float(datos_guia.get('peso_total', 0))
    if peso_total == 0 and items_formateados:
        peso_total = sum(float(item['cantidad']) * 0.5 for item in items_formateados)
    
    # ============================================================
    # 🔽 USAR LOS DATOS DEL BACKEND (datos_guia) como PRIORIDAD
    # ============================================================
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
        # 🔽 ESTOS SON LOS IMPORTANTES - VIENEN DEL BACKEND
        'orden_compra_cliente': datos_guia.get('orden_compra_cliente', ''),
        'factura': datos_guia.get('factura', ''),
        'nro_cotizacion': datos_guia.get('nro_cotizacion', datos_guia.get('documento_asociado', '')),
        'items': items_formateados,
        'observaciones': datos_guia.get('observaciones', ''),
        'qr_base64': self._generar_qr_guia(datos_guia)
    }

    # ============================================================
    # FUNCIONES AUXILIARES
    # ============================================================
    def _formatear_fecha(self, fecha):
        """Formatea fecha para mostrar en DD/MM/YYYY"""
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
        """Obtiene el texto del motivo de traslado"""
        motivos = {
            '01': 'Venta', '02': 'Compra', '03': 'Traslado entre establecimientos',
            '04': 'Consignación', '05': 'Devolución', '06': 'Exportación',
            '07': 'Importación', '08': 'Donación', '09': 'Traslado por cuenta de terceros'
        }
        return motivos.get(codigo, codigo or 'Venta')

    def _generar_qr_guia(self, datos_guia):
        """Genera un código QR para la guía"""
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
        """Genera las filas HTML de la tabla de productos para guía"""
        filas = ""
        for prod in productos:
            filas += f"""            <tr>
                <td>{prod.get('item', '')}</td>
                <td>{prod.get('codigo', '')}</td>
                <td class="descripcion">{prod.get('descripcion', '')}</td>
                <td>{prod.get('unidad', 'NIU')}</td>
                <td>{prod.get('cantidad', 0)}</td>
            </tr>
"""
        return filas

    def _reemplazar_variables_template_guia(self, template, datos):
        """Reemplaza variables del template de guía"""
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
        
        inicio_tbody = html.find('<tbody>')
        fin_tbody = html.find('</tbody>')
        if inicio_tbody >= 0 and fin_tbody > inicio_tbody:
            inicio_for = html.find('{% for item in items %}', inicio_tbody)
            fin_for = html.find('{% endfor %}', inicio_for)
            if inicio_for >= 0 and fin_for > inicio_for:
                parte_antes = html[:inicio_for]
                parte_despues = html[fin_for + len('{% endfor %}'):]
                html = parte_antes + datos.get('filas_productos', '') + parte_despues
        
        html = re.sub(r'{%.*?%}', '', html, flags=re.DOTALL)
        html = re.sub(r'{{.*?}}', '', html, flags=re.DOTALL)
        
        return html

    # ============================================================
    # GENERAR FACTURA / BOLETA (COMPROBANTE)
    # ============================================================
    def _generar_comprobante(self, datos_comprobante):
        """Genera PDF para Factura o Boleta usando template en memoria"""
        try:
            print("📄 Iniciando generación de PDF de comprobante...")
            
            datos_mapeados = self._mapear_datos_comprobante(datos_comprobante)
            
            template_content = self._obtener_template_comprobante()
            
            filas_productos = self._generar_filas_productos_comprobante(datos_mapeados.get('items', []))
            datos_mapeados['filas_productos'] = filas_productos
            
            html_content = self._reemplazar_variables_template_comprobante(template_content, datos_mapeados)
            
            fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_file = f"{datos_mapeados.get('tipo', 'factura').lower()}_{datos_mapeados.get('serie', 'F001')}_{datos_mapeados.get('numero', 'sin_numero')}_{fecha}.pdf"
            
            print(f"Generando PDF: {pdf_file}")
            
            base_url = f"file://{os.getcwd()}/"
            HTML(string=html_content, base_url=base_url).write_pdf(pdf_file)
            
            print("✅ PDF de comprobante generado exitosamente")
            return pdf_file
            
        except Exception as e:
            print(f"❌ Error generando PDF de comprobante: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _obtener_template_comprobante(self):
        """Retorna el template HTML del comprobante como string (en memoria)"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ tipo }} {{ serie }}-{{ numero }}</title>
    <style>
        @page { size: A4; margin: 1.2cm 1.5cm; }
        body { font-family: 'Helvetica', Arial, sans-serif; font-size: 9.5px; color: #1a1a1a; line-height: 1.6; }
        .header-superior { display: flex; justify-content: space-between; align-items: stretch; margin-bottom: 10px; gap: 15px; }
        .empresa-izquierda { flex: 1; display: flex; align-items: center; gap: 12px; }
        .empresa-izquierda .logo-container { flex-shrink: 0; width: 80px; height: 60px; display: flex; align-items: center; justify-content: center; }
        .empresa-izquierda .logo-container img { max-height: 60px; max-width: 100px; object-fit: contain; }
        .empresa-izquierda .info-texto { font-size: 8px; line-height: 1.4; }
        .empresa-izquierda .info-texto .nombre { font-size: 10px; font-weight: bold; text-transform: uppercase; }
        .recuadro-derecha { flex-shrink: 0; border: 2px solid #000; border-radius: 12px; padding: 10px 20px; text-align: center; min-width: 200px; }
        .recuadro-derecha .ruc { font-size: 10px; font-weight: bold; }
        .recuadro-derecha .titulo { font-size: 14px; font-weight: bold; letter-spacing: 1px; margin: 2px 0; }
        .recuadro-derecha .numero-doc { font-size: 13px; font-weight: bold; }
        .seccion { margin-bottom: 8px; }
        .seccion-titulo { font-weight: bold; font-size: 9.5px; margin-bottom: 3px; text-transform: uppercase; border-bottom: 1px solid #000; padding-bottom: 2px; }
        .info-cliente { border: 1px solid #ccc; border-radius: 8px; padding: 6px 12px; margin-bottom: 6px; background: #f9f9f9; }
        .fila { display: flex; padding: 1px 0; align-items: baseline; }
        .fila .label { font-weight: bold; min-width: 120px; flex-shrink: 0; }
        .fila .value { flex: 1; text-align: left; padding-left: 5px; }
        .products-table { width: 100%; border-collapse: collapse; margin: 4px 0; font-size: 8.5px; }
        .products-table th { background: #333; color: white; padding: 4px 5px; text-align: center; border: 1px solid #000; }
        .products-table td { padding: 3px 5px; border: 1px solid #ccc; text-align: center; }
        .products-table td.descripcion { text-align: left; }
        .products-table td.numero { text-align: right; }
        .totales { width: 280px; margin-left: auto; margin-top: 8px; border: 1px solid #333; border-radius: 8px; padding: 6px 12px; background: #f9f9f9; }
        .total-line { display: flex; justify-content: space-between; padding: 2px 0; font-size: 9px; }
        .total-final { border-top: 2px solid #000; padding-top: 4px; margin-top: 4px; font-weight: bold; font-size: 11px; }
        .footer { margin-top: 12px; text-align: center; font-size: 7.5px; color: #555; border-top: 1px solid #ddd; padding-top: 6px; }
        .observaciones { border: 1px solid #ccc; border-radius: 8px; padding: 6px 12px; margin-top: 6px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="header-superior">
        <div class="empresa-izquierda">
            <div class="logo-container">
                <img src="{{ logo_src }}" alt="Logo" style="max-height:60px;">
            </div>
            <div class="info-texto">
                <div class="nombre">{{ empresa_nombre }}</div>
                <div class="direccion">{{ empresa_direccion }}</div>
                <div class="contacto">
                    <span>Telf: {{ empresa_telefono }}</span>
                    <span>Email: {{ empresa_email }}</span>
                </div>
            </div>
        </div>
        <div class="recuadro-derecha">
            <div class="ruc">R.U.C. Nº {{ empresa_ruc }}</div>
            <div class="titulo">{{ tipo }}</div>
            <div class="numero-doc">{{ serie }}-{{ numero }}</div>
        </div>
    </div>
    
    <div class="seccion">
        <div class="seccion-titulo">DATOS DEL CLIENTE</div>
        <div class="info-cliente">
            <div class="fila"><span class="label">R.U.C.:</span><span class="value">{{ cliente_ruc }}</span></div>
            <div class="fila"><span class="label">RAZÓN SOCIAL:</span><span class="value">{{ cliente_nombre }}</span></div>
            <div class="fila"><span class="label">DIRECCIÓN:</span><span class="value">{{ cliente_direccion }}</span></div>
            <div class="fila"><span class="label">TELÉFONO:</span><span class="value">{{ cliente_telefono }}</span></div>
            <div class="fila"><span class="label">EMAIL:</span><span class="value">{{ cliente_email }}</span></div>
        </div>
    </div>
    
    <div style="display: flex; gap: 20px; margin-bottom: 6px;">
        <div><span style="font-weight:bold;">FECHA EMISIÓN:</span> {{ fecha_emision }}</div>
        <div><span style="font-weight:bold;">MONEDA:</span> {{ moneda }}</div>
        <div><span style="font-weight:bold;">COND. PAGO:</span> {{ condicion_pago }}</div>
    </div>
    
    <div class="seccion">
        <div class="seccion-titulo">PRODUCTOS</div>
        <table class="products-table">
            <thead>
                <tr>
                    <th style="width:5%">ITEM</th>
                    <th style="width:12%">CÓDIGO</th>
                    <th style="width:40%">DESCRIPCIÓN</th>
                    <th style="width:8%">UM</th>
                    <th style="width:10%">CANT.</th>
                    <th style="width:12%">P. UNIT</th>
                    <th style="width:13%">TOTAL</th>
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
                    <td class="numero">{{ item.precio_unitario }}</td>
                    <td class="numero">{{ item.total }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <div class="totales">
        <div class="total-line"><span>SUBTOTAL:</span><span>S/ {{ subtotal }}</span></div>
        <div class="total-line"><span>IGV (18%):</span><span>S/ {{ igv }}</span></div>
        <div class="total-line total-final"><span>TOTAL A PAGAR:</span><span>S/ {{ total }}</span></div>
    </div>
    
    {% if observaciones %}
    <div class="observaciones">
        <div class="fila"><span class="label">OBSERVACIONES:</span><span class="value">{{ observaciones }}</span></div>
    </div>
    {% endif %}
    
    <div class="footer">
        <div>Pag. 1 de 1</div>
        <div>Powered by KCF CORPORACION</div>
    </div>
</body>
</html>"""

    def _mapear_datos_comprobante(self, datos_comprobante):
        """Mapea los datos del comprobante al formato esperado"""
        EMPRESA = {
            'ruc': '20131369124',
            'nombre': 'KCF CORPORACION S.A.C.',
            'direccion': 'Av. Industrial 123, Lima, Perú',
            'telefono': '999 932 051',
            'email': 'ventas@kcfcorporacion.com'
        }
        
        logo_base64 = self._obtener_logo_base64()
        logo_src = f"data:image/png;base64,{logo_base64}" if logo_base64 else ""
        
        items = datos_comprobante.get('items', [])
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
                    'cantidad': float(item.get('cantidad', 1)),
                    'precio_unitario': f"{float(item.get('precio', 0)):.2f}",
                    'total': f"{float(item.get('cantidad', 1)) * float(item.get('precio', 0)):.2f}"
                })
            elif isinstance(item, (list, tuple)):
                items_formateados.append({
                    'item': idx,
                    'codigo': item[0] if len(item) > 0 else '',
                    'descripcion': item[1] if len(item) > 1 else '',
                    'unidad': 'NIU',
                    'cantidad': float(item[2] if len(item) > 2 else 1),
                    'precio_unitario': f"{float(item[3] if len(item) > 3 else 0):.2f}",
                    'total': f"{float(item[2] if len(item) > 2 else 1) * float(item[3] if len(item) > 3 else 0):.2f}"
                })
        
        subtotal = float(datos_comprobante.get('subtotal', 0))
        igv = float(datos_comprobante.get('igv', 0))
        total = float(datos_comprobante.get('total', 0))
        
        return {
            'logo_src': logo_src,
            'empresa_ruc': EMPRESA['ruc'],
            'empresa_nombre': EMPRESA['nombre'],
            'empresa_direccion': EMPRESA['direccion'],
            'empresa_telefono': EMPRESA['telefono'],
            'empresa_email': EMPRESA['email'],
            'tipo': datos_comprobante.get('tipo', 'FACTURA'),
            'serie': datos_comprobante.get('serie', 'F001'),
            'numero': datos_comprobante.get('numero', ''),
            'fecha_emision': self._formatear_fecha(datos_comprobante.get('fecha_emision')),
            'moneda': datos_comprobante.get('moneda', 'S/'),
            'condicion_pago': datos_comprobante.get('condicion_pago', 'Contado'),
            'cliente_ruc': datos_comprobante.get('ruc', ''),
            'cliente_nombre': datos_comprobante.get('cliente', ''),
            'cliente_direccion': datos_comprobante.get('direccion', ''),
            'cliente_telefono': datos_comprobante.get('telefono', ''),
            'cliente_email': datos_comprobante.get('email', ''),
            'subtotal': f"{subtotal:.2f}",
            'igv': f"{igv:.2f}",
            'total': f"{total:.2f}",
            'observaciones': datos_comprobante.get('observaciones', ''),
            'items': items_formateados
        }

    def _generar_filas_productos_comprobante(self, productos):
        """Genera las filas HTML de la tabla de productos para comprobante"""
        filas = ""
        for prod in productos:
            filas += f"""            <tr>
                <td>{prod.get('item', '')}</td>
                <td>{prod.get('codigo', '')}</td>
                <td class="descripcion">{prod.get('descripcion', '')}</td>
                <td>{prod.get('unidad', 'NIU')}</td>
                <td>{prod.get('cantidad', 0)}</td>
                <td class="numero">{prod.get('precio_unitario', '0.00')}</td>
                <td class="numero">{prod.get('total', '0.00')}</td>
            </tr>
"""
        return filas

    def _reemplazar_variables_template_comprobante(self, template, datos):
        """Reemplaza variables del template de comprobante"""
        html = template
        
        logo_src = datos.get('logo_src', '')
        html = html.replace('{{ logo_src }}', logo_src)
        
        variables = [
            'empresa_ruc', 'empresa_nombre', 'empresa_direccion',
            'empresa_telefono', 'empresa_email',
            'tipo', 'serie', 'numero', 'fecha_emision',
            'moneda', 'condicion_pago', 'cliente_ruc', 'cliente_nombre',
            'cliente_direccion', 'cliente_telefono', 'cliente_email',
            'subtotal', 'igv', 'total', 'observaciones'
        ]
        
        for var in variables:
            value = datos.get(var, '')
            html = html.replace(f"{{{{ {var} }}}}", str(value))
        
        inicio_tbody = html.find('<tbody>')
        fin_tbody = html.find('</tbody>')
        if inicio_tbody >= 0 and fin_tbody > inicio_tbody:
            inicio_for = html.find('{% for item in items %}', inicio_tbody)
            fin_for = html.find('{% endfor %}', inicio_for)
            if inicio_for >= 0 and fin_for > inicio_for:
                parte_antes = html[:inicio_for]
                parte_despues = html[fin_for + len('{% endfor %}'):]
                html = parte_antes + datos.get('filas_productos', '') + parte_despues
        
        html = re.sub(r'{%.*?%}', '', html, flags=re.DOTALL)
        html = re.sub(r'{{.*?}}', '', html, flags=re.DOTALL)
        
        return html

    # ============================================================
    # GENERAR COTIZACIÓN
    # ============================================================
    def _generar_cotizacion(self, datos_cotizacion):
        """Genera PDF para cotización - Usa template en memoria"""
        try:
            print("📄 Iniciando generación de PDF de cotización...")
            
            datos_mapeados = self._mapear_datos_cotizacion(datos_cotizacion)
            
            template_content = self._obtener_template_cotizacion()
            
            filas_productos = self._generar_filas_productos(datos_mapeados.get('productos', []))
            datos_mapeados['filas_productos'] = filas_productos
            
            html_content = self._reemplazar_variables_template(template_content, datos_mapeados)
            
            fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_file = f"cotizacion_{datos_mapeados.get('numero_cotizacion', 'sin_numero')}_{fecha}.pdf"
            
            print(f"Generando PDF: {pdf_file}")
            
            base_url = f"file://{os.getcwd()}/"
            HTML(string=html_content, base_url=base_url).write_pdf(pdf_file)
            
            print("✅ PDF de cotización generado exitosamente")
            return pdf_file
            
        except Exception as e:
            print(f"❌ Error generando PDF de cotización: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _obtener_template_cotizacion(self):
        """Retorna el template HTML de la cotización como string (en memoria)"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cotización - KCF CORPORACION</title>
    <style>
        @page { size: A4; margin: 1.2cm; }
        body { font-family: Arial, sans-serif; font-size: 11px; color: #1a1a1a; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #D32F2F; padding-bottom: 10px; margin-bottom: 15px; }
        .logo-section img { max-height: 60px; }
        .empresa-info { text-align: center; }
        .empresa-info h1 { color: #D32F2F; margin: 0; font-size: 18px; }
        .cotizacion-info { text-align: right; }
        .numero-cotizacion { font-size: 14px; font-weight: bold; color: #D32F2F; }
        .seccion-cliente, .seccion-condiciones { 
            border: 1px solid #D32F2F; border-radius: 8px; padding: 10px; margin-bottom: 12px;
            background: #f8f9fa;
        }
        .seccion-cliente h3, .seccion-condiciones h3 { 
            color: #D32F2F; border-bottom: 1px solid #D32F2F; padding-bottom: 5px; margin-top: 0; 
        }
        .info-line { display: flex; margin-bottom: 3px; font-size: 10px; }
        .info-label { width: 100px; font-weight: bold; }
        .info-value { flex: 1; }
        .tabla-productos { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 9px; }
        .tabla-productos th { background: #D32F2F; color: white; padding: 6px; border: 1px solid #B71C1C; }
        .tabla-productos td { padding: 5px; border: 1px solid #ddd; }
        .tabla-productos td.descripcion { text-align: left; }
        .numero-formateado { text-align: right; }
        .seccion-totales { 
            width: 280px; margin-left: auto; margin-top: 10px; 
            border: 1px solid #D32F2F; padding: 10px; border-radius: 8px;
            background: #f8f9fa;
        }
        .total-line { display: flex; justify-content: space-between; margin-bottom: 3px; font-size: 10px; }
        .total-final { border-top: 2px solid #D32F2F; padding-top: 5px; font-weight: bold; font-size: 13px; }
        .seccion-contacto { margin-top: 15px; border-top: 1px solid #D32F2F; padding-top: 10px; font-size: 9px; }
        .contacto-nombre { font-size: 11px; font-weight: bold; color: #D32F2F; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-section">
            <img src="{{ logo_src }}" alt="Logo">
        </div>
        <div class="empresa-info">
            <h1>KCF CORPORACION</h1>
            <div>Soluciones industriales y comerciales</div>
        </div>
        <div class="cotizacion-info">
            <div class="numero-cotizacion">COTIZACIÓN N°: {{ codigo_cotizacion }}</div>
            <div>Fecha: {{ fecha_actual }}</div>
        </div>
    </div>
    
    <div style="display:flex; gap:15px;">
        <div class="seccion-cliente" style="flex:1;">
            <h3>INFORMACIÓN DEL CLIENTE</h3>
            <div class="info-line"><span class="info-label">Cliente:</span><span class="info-value">{{ cliente_razon_social }}</span></div>
            <div class="info-line"><span class="info-label">RUC:</span><span class="info-value">{{ cliente_ruc }}</span></div>
            <div class="info-line"><span class="info-label">Dirección:</span><span class="info-value">{{ cliente_direccion }}</span></div>
            <div class="info-line"><span class="info-label">Contacto:</span><span class="info-value">{{ cliente_contacto }}</span></div>
        </div>
        <div class="seccion-condiciones" style="flex:1;">
            <h3>CONDICIONES COMERCIALES</h3>
            <div class="info-line"><span class="info-label">Ejecutiva:</span><span class="info-value">{{ asesor_comercial }}</span></div>
            <div class="info-line"><span class="info-label">Condición Pago:</span><span class="info-value">{{ condicion_pago }}</span></div>
            <div class="info-line"><span class="info-label">Tiempo Entrega:</span><span class="info-value">{{ tiempo_entrega }}</span></div>
            <div class="info-line"><span class="info-label">Validez:</span><span class="info-value">{{ validez_oferta }}</span></div>
        </div>
    </div>
    
    <table class="tabla-productos">
        <thead>
            <tr>
                <th>Item</th>
                <th style="text-align:left;">Descripción</th>
                <th>Marca</th>
                <th>Und.</th>
                <th>Cant.</th>
                <th>Valor Unit S/.</th>
                <th>Valor Total S/.</th>
            </tr>
        </thead>
        <tbody>
            {% for producto in productos %}
            <tr>
                <td>{{ producto.item }}</td>
                <td class="descripcion">{{ producto.descripcion }}</td>
                <td>{{ producto.marca }}</td>
                <td>{{ producto.unidad }}</td>
                <td>{{ producto.cantidad }}</td>
                <td class="numero-formateado">{{ "%.2f"|format(producto.precio_venta_unitario|default(0)) }}</td>
                <td class="numero-formateado">{{ "%.2f"|format(producto.subtotal_venta_desc|default(producto.subtotal_venta|default(0))) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div class="seccion-totales">
        <div class="total-line"><span>Subtotal:</span><span>S/ {{ "%.2f"|format(total_subtotal_venta|default(0)) }}</span></div>
        <div class="total-line"><span>IGV (18%):</span><span>S/ {{ "%.2f"|format(summary_igv|default(0)) }}</span></div>
        <div class="total-line total-final"><span>TOTAL A PAGAR:</span><span>S/ {{ "%.2f"|format(summary_total_venta|default(0)) }}</span></div>
    </div>
    
    <div class="seccion-contacto">
        <div class="contacto-nombre">Cordialmente,</div>
        <div class="contacto-nombre">HELLEN BLAS PRINCIPE</div>
        <div>Ejecutiva Comercial - KCF CORPORACIÓN</div>
        <div>📞 (+51) 999932051</div>
        <div>✉ Ventas@kcfcorporacion.com</div>
    </div>
</body>
</html>"""

    def _mapear_datos_cotizacion(self, datos_cotizacion):
        """Mapea los datos de la cotización al formato esperado por el template"""
        cliente = datos_cotizacion.get('cliente', {})
        
        def get_from_notas(prefijo):
            notas = datos_cotizacion.get('notas', '')
            for line in notas.split('\n'):
                if line.startswith(prefijo):
                    return line.replace(prefijo, '').strip()
            return ''
        
        logo_base64 = self._obtener_logo_base64()
        logo_src = f"data:image/png;base64,{logo_base64}" if logo_base64 else ""
        
        datos_mapeados = {
            'numero_cotizacion': datos_cotizacion.get('numero_cotizacion'),
            'fecha_actual': datetime.now().strftime('%d/%m/%Y'),
            'cliente_razon_social': cliente.get('razon_social', '') or get_from_notas('Señor(es):'),
            'cliente_ruc': cliente.get('numero_documento', '') or get_from_notas('Doc:'),
            'cliente_direccion': cliente.get('direccion_fiscal', '') or get_from_notas('Dirección entrega:'),
            'cliente_telefono': get_from_notas('Teléfono:'),
            'cliente_contacto': get_from_notas('Atención:'),
            'numero_requerimiento': get_from_notas('Requerimiento:'),
            'asesor_comercial': get_from_notas('Asesor:'),
            'email_contacto': get_from_notas('Email:'),
            'telefono_contacto': get_from_notas('Teléfono contacto:'),
            'forma_pago': get_from_notas('Forma pago:'),
            'tiempo_entrega': get_from_notas('Tiempo entrega:'),
            'lugar_entrega': get_from_notas('Lugar entrega:'),
            'validez_oferta': get_from_notas('Validez:'),
            'descuento_comercial': get_from_notas('Desc comercial:'),
            'nota_cotizacion': get_from_notas('Nota cotización:'),
            'logo_src': logo_src,
            'productos': [],
            'subtotal': datos_cotizacion.get('subtotal', 0),
            'igv': datos_cotizacion.get('igv', 0),
            'total': datos_cotizacion.get('total', 0)
        }
        
        for i, item in enumerate(datos_cotizacion.get('items', []), 1):
            producto = {
                'item': i,
                'descripcion': item.get('descripcion', ''),
                'marca': item.get('marca', ''),
                'unidad': item.get('unidad', ''),
                'cantidad': item.get('cantidad', 0),
                'precio_venta_unitario': item.get('precio_venta_con_descuento', 0),
                'subtotal_venta_desc': item.get('subtotal_venta_con_descuento', 0),
                'subtotal_venta': item.get('subtotal_venta', 0),
                'porcentaje_descuento': item.get('descuento_porcentaje', 0)
            }
            datos_mapeados['productos'].append(producto)
        
        return datos_mapeados

    def _generar_filas_productos(self, productos):
        """Genera las filas HTML de la tabla de productos"""
        filas = ""
        for prod in productos:
            filas += f"""            <tr>
                <td>{prod.get('item', '')}</td>
                <td class="descripcion">{prod.get('descripcion', '')}</td>
                <td class="marca">{prod.get('marca', '')}</td>
                <td>{prod.get('unidad', '')}</td>
                <td>{prod.get('cantidad', 0)}</td>
                <td class="numero-formateado">S/ {prod.get('precio_venta_unitario', 0):.2f}</td>
                <td class="numero-formateado">S/ {prod.get('subtotal_venta_desc', prod.get('subtotal_venta', 0)):.2f}</td>
            </tr>
"""
        return filas

    def _reemplazar_variables_template(self, template, datos):
        """Reemplaza variables del template sin usar Jinja2"""
        html = template
        
        logo_src = datos.get('logo_src', '')
        html = html.replace('{{ logo_src }}', logo_src)
        
        variables = [
            'numero_cotizacion', 'fecha_actual', 'cliente_razon_social',
            'cliente_ruc', 'cliente_direccion', 'cliente_telefono',
            'cliente_contacto', 'numero_requerimiento', 'asesor_comercial',
            'email_contacto', 'telefono_contacto', 'forma_pago',
            'tiempo_entrega', 'lugar_entrega', 'validez_oferta',
            'descuento_comercial', 'nota_cotizacion', 'total_subtotal_venta',
            'summary_igv', 'summary_total_venta'
        ]
        
        for var in variables:
            value = datos.get(var, '')
            html = html.replace(f"{{{{ {var} }}}}", str(value))
        
        # Reemplazar variables con formato específico
        subtotal = datos.get('subtotal', 0)
        igv = datos.get('igv', 0)
        total = datos.get('total', 0)
        
        html = html.replace("{{ total_subtotal_venta|default(0)|formato_soles }}", f"{subtotal:.2f}")
        html = html.replace("{{ total_subtotal_venta_desc|default(0)|formato_soles }}", f"{subtotal:.2f}")
        html = html.replace("{{ summary_igv|default(0)|formato_soles }}", f"{igv:.2f}")
        html = html.replace("{{ summary_total_venta|default(0)|formato_soles }}", f"{total:.2f}")
        
        inicio_tbody = html.find('<tbody>')
        fin_tbody = html.find('</tbody>')
        if inicio_tbody >= 0 and fin_tbody > inicio_tbody:
            inicio_for = html.find('{% for producto in productos %}', inicio_tbody)
            fin_for = html.find('{% endfor %}', inicio_for)
            if inicio_for >= 0 and fin_for > inicio_for:
                parte_antes = html[:inicio_for]
                parte_despues = html[fin_for + len('{% endfor %}'):]
                html = parte_antes + datos.get('filas_productos', '') + parte_despues
        
        html = re.sub(r'{%.*?%}', '', html, flags=re.DOTALL)
        html = re.sub(r'{{.*?}}', '', html, flags=re.DOTALL)
        
        return html

    # ============================================================
    # GENERAR ORDEN DE COMPRA
    # ============================================================
    def _generar_orden_compra(self, datos_orden_compra):
        """Genera PDF para orden de compra"""
        print("Generando orden de compra...")
        return None


# ============================================================
# INSTANCIA GLOBAL - ¡NECESARIA PARA LA IMPORTACIÓN!
# ============================================================
pdf_generator = PDFGenerator()