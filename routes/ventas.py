# routes/ventas.py - INICIO CORREGIDO

import sys
import os

# Asegurar que la raíz del proyecto esté en el path de Python
# Esto permite importar módulos desde la carpeta principal
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from datetime import datetime
import json

# Importar el generador de PDF desde la raíz del proyecto
from pdf_generator import pdf_generator

# Importar desde database.py
from database import db_query, db_execute, db_tx, get_connection, buscar_cliente_por_ruc

ventas_bp = Blueprint('ventas', __name__)

# ============================================================
# FUNCIÓN LOGIN REQUIRED
# ============================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            if request.path.startswith('/ventas/api/'):
                return jsonify({'error': 'Sesión expirada o no autorizado. Inicia sesión.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# FUNCIONES DE AYUDA PARA COTIZACIONES - VERSIÓN CORREGIDA
# ============================================================

def crear_tabla_cotizaciones_eliminadas_si_no_existe():
    """Crea la tabla de respaldo de cotizaciones eliminadas si no existe"""
    try:
        query = """
            CREATE TABLE IF NOT EXISTS cotizaciones_eliminadas (
                id SERIAL PRIMARY KEY,
                cotizacion_id_original INTEGER,
                numero_cotizacion VARCHAR(50),
                codigo_cotizacion VARCHAR(50),
                cliente_id INTEGER,
                cliente_razon_social VARCHAR(255),
                cliente_ruc VARCHAR(20),
                fecha_creacion TIMESTAMP,
                estado_anterior VARCHAR(50),
                subtotal NUMERIC(12,2),
                igv NUMERIC(12,2),
                total NUMERIC(12,2),
                condicion_pago VARCHAR(100),
                tiempo_entrega VARCHAR(100),
                direccion_entrega TEXT,
                vendedor VARCHAR(150),
                contacto_cliente VARCHAR(150),
                telefono_cliente VARCHAR(50),
                email_cliente VARCHAR(150),
                nota_cotizacion TEXT,
                requerimiento TEXT,
                productos_json JSONB,
                datos_completos_json JSONB,
                motivo_eliminacion TEXT NOT NULL,
                eliminado_por INTEGER,
                eliminado_en TIMESTAMP DEFAULT NOW()
            )
        """
        db_execute(query)
    except Exception as e:
        print(f"❌ Error creando tabla cotizaciones_eliminadas: {e}")
        raise

def obtener_cotizaciones_db():
    """Obtiene todas las cotizaciones con datos del cliente"""
    try:
        query = """
            SELECT 
                c.id, 
                c.numero_cotizacion, 
                c.cliente_id, 
                c.fecha_creacion, 
                c.estado,
                c.subtotal, 
                c.igv, 
                c.total, 
                c.usuario_id, 
                c.notas,
                c.forma_pago, 
                c.tiempo_entrega, 
                c.almacen, 
                c.validez_oferta,
                c.codigo_cotizacion, 
                c.correlativo, 
                c.condicion_pago,
                c.direccion_entrega,
                c.requerimiento, 
                c.nota_cotizacion,
                c.descuento_porcentaje, 
                c.descuento_monto, 
                c.descuento_tipo,
                c.contacto_cliente, 
                c.telefono_cliente, 
                c.email_cliente,
                c.seguimiento,
                c.motivo,
                c.transporte,
                c.parihuela,
                c.nota_interna,
                c.vendedor,
                cl.id as cliente_id,
                cl.razon_social as cliente_razon_social,
                cl.numero_documento as cliente_ruc,
                cl.nombre_comercial as cliente_nombre_comercial,
                cl.direccion_fiscal as cliente_direccion,
                cl.telefono_contacto as cliente_telefono,
                cl.nombre_contacto as cliente_contacto,
                cl.email_contacto as cliente_email,
                cl.codigo_cliente as cod_cliente,
                (
                    SELECT p.descripcion
                    FROM cotizacion_detalle d
                    LEFT JOIN productos p ON p.id = d.producto_id
                    WHERE d.cotizacion_id = c.id
                    ORDER BY d.id ASC
                    LIMIT 1
                ) AS primer_producto_descripcion
            FROM cotizaciones c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id::integer
            WHERE c.estado != 'Anulada'
            ORDER BY c.id DESC
        """
        results = db_query(query)
        print(f"✅ Cotizaciones encontradas: {len(results)}")
        return results
    except Exception as e:
        print(f"❌ Error en obtener_cotizaciones_db: {e}")
        import traceback
        traceback.print_exc()
        return []

def obtener_cotizacion_por_id_db(cotizacion_id):
    """Obtiene una cotización por su ID"""
    try:
        query = """
            SELECT 
                id, numero_cotizacion, cliente_id, fecha_creacion, estado,
                subtotal, igv, total, usuario_id, notas,
                forma_pago, tiempo_entrega, almacen, validez_oferta,
                codigo_cotizacion, correlativo, condicion_pago,
                direccion_entrega, requerimiento, nota_cotizacion,
                descuento_porcentaje, descuento_monto, descuento_tipo,
                contacto_cliente, telefono_cliente, email_cliente
            FROM cotizaciones
            WHERE id = %s
        """
        result = db_query(query, (cotizacion_id,))
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en obtener_cotizacion_por_id_db: {e}")
        return None

def guardar_cotizacion_db(data):
    """Guarda una nueva cotización"""
    try:
        query = """
            INSERT INTO cotizaciones (
                numero_cotizacion, cliente_id, fecha_creacion, estado,
                subtotal, igv, total, usuario_id, notas,
                forma_pago, tiempo_entrega, almacen, validez_oferta,
                codigo_cotizacion, correlativo, condicion_pago,
                direccion_entrega, requerimiento, nota_cotizacion,
                descuento_porcentaje, descuento_monto, descuento_tipo,
                contacto_cliente, telefono_cliente, email_cliente,
                -- 🔽 NUEVOS CAMPOS DE INFORMACIÓN ADICIONAL
                seguimiento, motivo, transporte, parihuela, nota_interna,
                vendedor
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            RETURNING id, numero_cotizacion
        """
        params = (
            data.get('numero_cotizacion'),
            data.get('cliente_id'),
            data.get('fecha_creacion') or datetime.now().isoformat(),
            data.get('estado', 'Borrador'),
            float(data.get('subtotal', 0)),
            float(data.get('igv', 0)),
            float(data.get('total', 0)),
            data.get('usuario_id'),
            data.get('notas', ''),
            data.get('forma_pago'),
            data.get('tiempo_entrega'),
            data.get('almacen'),
            data.get('validez_oferta'),
            data.get('codigo_cotizacion'),
            data.get('correlativo'),
            data.get('condicion_pago'),
            data.get('direccion_entrega'),
            data.get('requerimiento'),
            data.get('nota_cotizacion', ''),
            float(data.get('descuento_porcentaje', 0)),
            float(data.get('descuento_monto', 0)),
            data.get('descuento_tipo', 'porcentaje'),
            data.get('contacto_cliente'),
            data.get('telefono_cliente'),
            data.get('email_cliente'),
            # 🔽 NUEVOS CAMPOS
            data.get('seguimiento', 'Asesor'),
            data.get('motivo', 'Proyecto nuevo'),
            data.get('transporte', 'Seleccione'),
            data.get('parihuela', 'Seleccione'),
            data.get('nota_interna', ''),
            data.get('vendedor', 'Helen Blas Príncipe')
        )
        
        print(f"📝 INSERT params: {params}")
        result = db_query(query, params)
        print(f"📦 INSERT result: {result}")
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_cotizacion_db: {e}")
        raise

def actualizar_cotizacion_db(cotizacion_id, data):
    """Actualiza una cotización existente"""
    try:
        query = """
            UPDATE cotizaciones SET
                cliente_id = %s,
                estado = %s,
                subtotal = %s,
                igv = %s,
                total = %s,
                usuario_id = %s,
                notas = %s,
                forma_pago = %s,
                tiempo_entrega = %s,
                almacen = %s,
                validez_oferta = %s,
                condicion_pago = %s,
                direccion_entrega = %s,
                requerimiento = %s,
                nota_cotizacion = %s,
                descuento_porcentaje = %s,
                descuento_monto = %s,
                descuento_tipo = %s,
                contacto_cliente = %s,
                telefono_cliente = %s,
                email_cliente = %s,
                -- 🔽 NUEVOS CAMPOS
                seguimiento = %s,
                motivo = %s,
                transporte = %s,
                parihuela = %s,
                nota_interna = %s,
                vendedor = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, numero_cotizacion
        """
        params = (
            data.get('cliente_id'),
            data.get('estado', 'Borrador'),
            float(data.get('subtotal', 0)),
            float(data.get('igv', 0)),
            float(data.get('total', 0)),
            data.get('usuario_id'),
            data.get('notas', ''),
            data.get('forma_pago'),
            data.get('tiempo_entrega'),
            data.get('almacen'),
            data.get('validez_oferta'),
            data.get('condicion_pago'),
            data.get('direccion_entrega'),
            data.get('requerimiento'),
            data.get('nota_cotizacion', ''),
            float(data.get('descuento_porcentaje', 0)),
            float(data.get('descuento_monto', 0)),
            data.get('descuento_tipo', 'porcentaje'),
            data.get('contacto_cliente'),
            data.get('telefono_cliente'),
            data.get('email_cliente'),
            # 🔽 NUEVOS CAMPOS
            data.get('seguimiento', 'Asesor'),
            data.get('motivo', 'Proyecto nuevo'),
            data.get('transporte', 'Seleccione'),
            data.get('parihuela', 'Seleccione'),
            data.get('nota_interna', ''),
            data.get('vendedor', 'Helen Blas Príncipe'),
            cotizacion_id
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en actualizar_cotizacion_db: {e}")
        raise


def actualizar_estado_cotizacion_db(cotizacion_id, nuevo_estado):
    """Actualiza el estado de una cotización"""
    try:
        query = """
            UPDATE cotizaciones 
            SET estado = %s
            WHERE id = %s
            RETURNING id, estado
        """
        result = db_query(query, (nuevo_estado, cotizacion_id))
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en actualizar_estado_cotizacion_db: {e}")
        raise


# ============================================================
# FUNCIONES DE AYUDA PARA GUÍAS
# ============================================================

def obtener_guias_db():
    """Obtiene todas las guías"""
    try:
        query = """
            SELECT 
                id, serie, numero, fecha_emision, fecha_traslado,
                ruc_remitente, remitente_nombre, remitente_direccion,
                remitente_ubigeo, ruc_destinatario, destinatario_nombre,
                destinatario_direccion, destinatario_ubigeo,
                modalidad_transporte, placa_vehiculo, conductor_dni,
                conductor_nombre, licencia_conductor, transportista_ruc,
                transportista_nombre, motivo_traslado, documento_asociado,
                orden_compra_cliente, factura,
                peso_total, items_json, observaciones, estado_sunat,
                cdr_response, sunat_response, creado_por, created_at, updated_at
            FROM guias_remision
            ORDER BY id DESC
        """
        return db_query(query)
    except Exception as e:
        print(f"❌ Error en obtener_guias_db: {e}")
        return []

def obtener_guia_por_id_db(guia_id):
    """Obtiene una guía por su ID"""
    try:
        query = """
            SELECT 
                id, serie, numero, fecha_emision, fecha_traslado,
                ruc_remitente, remitente_nombre, remitente_direccion,
                remitente_ubigeo, ruc_destinatario, destinatario_nombre,
                destinatario_direccion, destinatario_ubigeo,
                modalidad_transporte, placa_vehiculo, conductor_dni,
                conductor_nombre, licencia_conductor, transportista_ruc,
                transportista_nombre, motivo_traslado, documento_asociado,
                orden_compra_cliente, factura,
                peso_total, items_json, observaciones, estado_sunat,
                cdr_response, sunat_response, creado_por
            FROM guias_remision
            WHERE id = %s
        """
        result = db_query(query, (guia_id,))
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en obtener_guia_por_id_db: {e}")
        return None

def guardar_guia_db(data):
    """Guarda una nueva guía con fecha y hora correcta"""
    try:
        from datetime import datetime
        
        # Asegurar que fecha_emision tenga hora correcta
        fecha_emision = data.get('fecha_emision')
        if fecha_emision:
            # Si viene sin hora (solo fecha), agregar hora actual
            if isinstance(fecha_emision, str) and 'T' not in fecha_emision and ' ' not in fecha_emision:
                ahora = datetime.now()
                fecha_emision = f"{fecha_emision}T{ahora.strftime('%H:%M:%S')}"
        else:
            # Si no viene, usar ahora mismo
            fecha_emision = datetime.now().isoformat()
        
        # Fecha traslado (puede ser solo fecha)
        fecha_traslado = data.get('fecha_traslado') or datetime.now().date().isoformat()
        
        print(f"📅 Fecha emisión guardando: {fecha_emision}")
        print(f"📅 Fecha traslado guardando: {fecha_traslado}")
        
        query = """
            INSERT INTO guias_remision (
                serie, numero, fecha_emision, fecha_traslado,
                ruc_remitente, remitente_nombre, remitente_direccion,
                remitente_ubigeo, ruc_destinatario, destinatario_nombre,
                destinatario_direccion, destinatario_ubigeo,
                modalidad_transporte, placa_vehiculo, conductor_dni,
                conductor_nombre, licencia_conductor, transportista_ruc,
                transportista_nombre, motivo_traslado, documento_asociado,
                orden_compra_cliente, factura,
                peso_total, items_json, observaciones, estado_sunat,
                creado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s
            )
            RETURNING id, numero
        """
        params = (
            data.get('serie', 'T001'),
            data.get('numero'),
            fecha_emision,  # ← CON HORA CORRECTA
            fecha_traslado,
            data.get('ruc_remitente'),
            data.get('remitente_nombre'),
            data.get('remitente_direccion'),
            data.get('remitente_ubigeo'),
            data.get('ruc_destinatario'),
            data.get('destinatario_nombre'),
            data.get('destinatario_direccion'),
            data.get('destinatario_ubigeo'),
            data.get('modalidad_transporte', 'PRIVADO'),
            data.get('placa_vehiculo'),
            data.get('conductor_dni'),
            data.get('conductor_nombre'),
            data.get('licencia_conductor'),
            data.get('transportista_ruc'),
            data.get('transportista_nombre'),
            data.get('motivo_traslado', 'VENTA'),
            data.get('documento_asociado'),
            data.get('orden_compra_cliente'),
            data.get('factura'),
            float(data.get('peso_total', 0)),
            data.get('items_json'),
            data.get('observaciones'),
            data.get('estado_sunat', 'BORRADOR'),
            data.get('creado_por')
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_guia_db: {e}")
        raise



def actualizar_guia_db(guia_id, data):
    """Actualiza una guía existente"""
    try:
        query = """
            UPDATE guias_remision SET
                fecha_traslado = %s,
                ruc_destinatario = %s,
                destinatario_nombre = %s,
                destinatario_direccion = %s,
                destinatario_ubigeo = %s,
                placa_vehiculo = %s,
                conductor_dni = %s,
                conductor_nombre = %s,
                licencia_conductor = %s,
                transportista_ruc = %s,
                transportista_nombre = %s,
                motivo_traslado = %s,
                documento_asociado = %s,
                orden_compra_cliente = %s,
                factura = %s,
                peso_total = %s,
                items_json = %s,
                observaciones = %s,
                estado_sunat = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, numero
        """
        params = (
            data.get('fecha_traslado'),
            data.get('ruc_destinatario'),
            data.get('destinatario_nombre'),
            data.get('destinatario_direccion'),
            data.get('destinatario_ubigeo'),
            data.get('placa_vehiculo'),
            data.get('conductor_dni'),
            data.get('conductor_nombre'),
            data.get('licencia_conductor'),
            data.get('transportista_ruc'),
            data.get('transportista_nombre'),
            data.get('motivo_traslado', 'VENTA'),
            data.get('documento_asociado'),
            data.get('orden_compra_cliente'),
            data.get('factura'),
            float(data.get('peso_total', 0)),
            data.get('items_json'),
            data.get('observaciones'),
            data.get('estado_sunat', 'BORRADOR'),
            guia_id
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en actualizar_guia_db: {e}")
        raise

# ============================================================
# FUNCIONES DE AYUDA PARA COMPROBANTES
# ============================================================

def obtener_comprobantes_db():
    """Obtiene todos los comprobantes con los campos de retención"""
    try:
        query = """
            SELECT 
                id, tipo_comprobante, serie, numero, fecha_emision,
                moneda, cliente_tipo_doc, cliente_numero_doc,
                cliente_nombre, cliente_direccion, cliente_email,
                cliente_telefono, subtotal, igv, total,
                items_json, observaciones, estado_sunat, 
                documento_asociado, condicion_pago,
                guia_vinculada, pc_vinculado,
                -- 🔽 NUEVOS CAMPOS DE RETENCIÓN
                es_credito, estado_credito, fecha_aprobacion,
                fecha_vencimiento, dias_credito, monto_retenido,
                obs_retencion,
                sunat_response, cdr_response, creado_por,
                created_at, updated_at
            FROM comprobantes
            ORDER BY id DESC
        """
        return db_query(query)
    except Exception as e:
        print(f"❌ Error en obtener_comprobantes_db: {e}")
        return []

def guardar_comprobante_db(data):
    """Guarda un nuevo comprobante con fecha y hora correcta"""
    try:
        from datetime import datetime
        
        # ✅ OBTENER FECHA Y HORA COMPLETA (mantiene la hora del frontend)
        fecha_emision = data.get('fecha_emision')
        if not fecha_emision:
            fecha_emision = datetime.now().isoformat()
        
        print(f"📅 Fecha emisión guardando: {fecha_emision}")  # Para depuración
        
        query = """
            INSERT INTO comprobantes (
                tipo_comprobante, serie, numero, fecha_emision,
                moneda, cliente_tipo_doc, cliente_numero_doc,
                cliente_nombre, cliente_direccion, cliente_email,
                cliente_telefono, subtotal, igv, total,
                items_json, observaciones, estado_sunat,
                condicion_pago, documento_asociado, guia_vinculada,
                pc_vinculado, creado_por,
                -- 🔽 CAMPOS DE RETENCIÓN
                tiene_retencion, es_credito, estado_credito,
                fecha_aprobacion, fecha_vencimiento, dias_credito,
                porcentaje_retencion, monto_retenido, monto_a_pagar,
                obs_retencion
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, serie, numero
        """
        
        params = (
            data.get('tipo_comprobante', 'FACTURA'),
            data.get('serie', 'F001'),
            data.get('numero'),
            fecha_emision,  # ✅ CON FECHA Y HORA COMPLETA
            data.get('moneda', 'PEN'),
            data.get('cliente_tipo_doc', 'RUC'),
            data.get('cliente_numero_doc'),
            data.get('cliente_nombre'),
            data.get('cliente_direccion'),
            data.get('cliente_email'),
            data.get('cliente_telefono'),
            float(data.get('subtotal', 0)),
            float(data.get('igv', 0)),
            float(data.get('total', 0)),
            data.get('items_json'),
            data.get('observaciones'),
            data.get('estado_sunat', 'BORRADOR'),
            data.get('condicion_pago', 'Contado'),
            data.get('documento_asociado'),
            data.get('guia_vinculada'),
            data.get('pc_vinculado'),
            data.get('creado_por'),
            # 🔽 CAMPOS DE RETENCIÓN
            data.get('tiene_retencion', False),
            data.get('es_credito', False),
            data.get('estado_credito'),
            data.get('fecha_aprobacion'),
            data.get('fecha_vencimiento'),
            data.get('dias_credito'),
            data.get('porcentaje_retencion', 3.00),
            data.get('monto_retenido', 0),
            data.get('monto_a_pagar', 0),
            data.get('obs_retencion')
        )
        
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_comprobante_db: {e}")
        raise


def actualizar_estado_comprobante_db(comp_id, nuevo_estado):
    """Actualiza el estado de un comprobante"""
    try:
        query = """
            UPDATE comprobantes 
            SET estado_sunat = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado_sunat
        """
        result = db_query(query, (nuevo_estado, comp_id))
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en actualizar_estado_comprobante_db: {e}")
        raise


# ============================================================
# FUNCIONES DE AYUDA PARA NOTAS DE CRÉDITO
# ============================================================

def obtener_notas_credito_db():
    """Obtiene todas las notas de crédito"""
    try:
        query = """
            SELECT 
                id, serie, numero, fecha_emision, fecha_vencimiento,
                cliente_tipo_doc, cliente_numero_doc, cliente_nombre,
                cliente_direccion, cliente_email, cliente_telefono,
                comprobante_asociado, motivo, monto, observaciones,
                estado, creado_por, created_at, updated_at
            FROM notas_credito
            ORDER BY id DESC
        """
        return db_query(query)
    except Exception as e:
        print(f"❌ Error en obtener_notas_credito_db: {e}")
        return []

def guardar_nota_credito_db(data):
    """Guarda una nueva nota de crédito"""
    try:
        query = """
            INSERT INTO notas_credito (
                serie, numero, fecha_emision, fecha_vencimiento,
                cliente_tipo_doc, cliente_numero_doc, cliente_nombre,
                cliente_direccion, cliente_email, cliente_telefono,
                comprobante_asociado, motivo, monto, observaciones,
                estado, creado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            RETURNING id, serie, numero
        """
        params = (
            data.get('serie', 'FC01'),
            data.get('numero'),
            data.get('fecha_emision') or datetime.now().date().isoformat(),
            data.get('fecha_vencimiento'),
            data.get('cliente_tipo_doc', 'RUC'),
            data.get('cliente_numero_doc'),
            data.get('cliente_nombre'),
            data.get('cliente_direccion'),
            data.get('cliente_email'),
            data.get('cliente_telefono'),
            data.get('comprobante_asociado'),
            data.get('motivo'),
            float(data.get('monto', 0)),
            data.get('observaciones'),
            data.get('estado', 'Borrador'),
            data.get('creado_por')
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_nota_credito_db: {e}")
        raise
# ============================================================
# FUNCIONES DE AYUDA PARA PEDIDO COMPRA (PC)
# ============================================================

def obtener_pc_db():
    """Obtiene todos los pedidos de compra"""
    try:
        query = """
            SELECT 
                id, numero, fecha, estado, cliente, ruc, monto,
                cotizacion_id, cotizacion_numero, correo_origen,
                fecha_recepcion, fecha_despacho, archivo_oc,
                observaciones, valida_precios, valida_cantidades,
                valida_stock, valida_entrega, valida_montos,
                responsable, lugar_entrega, condicion_atencion,
                medio, entrega, req_compra, guia, factura,
                condicion_pago, vendedor,
                created_at, updated_at,
                items_json
            FROM pedido_compra_pc
            ORDER BY id DESC
        """
        results = db_query(query)
        for row in results:
            if row.get('items_json'):
                try:
                    row['items'] = json.loads(row['items_json'])
                except:
                    row['items'] = []
            else:
                row['items'] = []
            
            if not row.get('medio') and row.get('correo_origen'):
                row['medio'] = 'Correo'
            elif not row.get('medio'):
                row['medio'] = 'No especificado'
            
            if not row.get('entrega') and row.get('lugar_entrega'):
                row['entrega'] = row['lugar_entrega']
            
            if not row.get('condicion_pago') and row.get('condicion_atencion'):
                row['condicion_pago'] = row['condicion_atencion']
            
            if not row.get('req_compra'):
                if row.get('estado') == 'PC observado':
                    row['req_compra'] = 'Bloqueado'
                elif row.get('estado') in ['Listo para despacho', 'PC atendido']:
                    row['req_compra'] = 'No'
                else:
                    row['req_compra'] = 'Sí'
        return results
    except Exception as e:
        print(f"❌ Error en obtener_pc_db: {e}")
        return []

def guardar_pc_db(data):
    """Guarda o actualiza un pedido de compra"""
    try:
        print("📝 Guardando PC en BD...")
        
        items_json = json.dumps(data.get('items', []))
        
        # Validaciones
        valida_precios = data.get('valida_precios', False)
        valida_cantidades = data.get('valida_cantidades', False)
        valida_stock = data.get('valida_stock', False)
        valida_entrega = data.get('valida_entrega', False)
        valida_montos = data.get('valida_montos', False)
        valida_transporte = data.get('valida_transporte', False)
        valida_margen = data.get('valida_margen', False)
        valida_vigencia = data.get('valida_vigencia', False)
        
        # NO BLOQUEAR POR STOCK
        validacion_ok = all([
            valida_precios,
            valida_cantidades,
            valida_entrega,
            valida_montos,
            valida_transporte,
            valida_margen,
            valida_vigencia
        ])
        
        if not validacion_ok:
            estado = 'PC observado'
            req_compra = 'Bloqueado'
        else:
            estado = data.get('estado', 'PC conforme')
            req_compra = data.get('req_compra', 'Sí')
        
        pc_id = data.get('id')
        
        # ============================================================
        # SI HAY ID, ACTUALIZAR
        # ============================================================
        if pc_id:
            print(f"🔄 Actualizando PC ID: {pc_id}")
            
            query = """
                UPDATE pedido_compra_pc SET
                    numero = %s,
                    fecha = %s,
                    estado = %s,
                    cliente = %s,
                    ruc = %s,
                    monto = %s,
                    cotizacion_id = %s,
                    cotizacion_numero = %s,
                    correo_origen = %s,
                    fecha_recepcion = %s,
                    fecha_despacho = %s,
                    archivo_oc = %s,
                    observaciones = %s,
                    valida_precios = %s,
                    valida_cantidades = %s,
                    valida_stock = %s,
                    valida_entrega = %s,
                    valida_montos = %s,
                    valida_transporte = %s,
                    valida_margen = %s,
                    valida_vigencia = %s,
                    responsable = %s,
                    lugar_entrega = %s,
                    condicion_atencion = %s,
                    items_json = %s,
                    medio = %s,
                    entrega = %s,
                    condicion_pago = %s,
                    vendedor = %s,
                    req_compra = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, numero
            """
            
            params = (
                data.get('numero'),
                data.get('fecha') or datetime.now().isoformat(),
                estado,
                data.get('cliente') or '',
                data.get('ruc') or '',
                float(data.get('monto', 0)),
                data.get('cotizacion_id'),  # Puede ser None
                data.get('cotizacion_numero') or '',
                data.get('correo_origen') or data.get('medio') or '',
                data.get('fecha_recepcion') or data.get('fecha'),
                data.get('fecha_despacho'),
                data.get('archivo_oc'),
                data.get('observaciones') or '',
                valida_precios,
                valida_cantidades,
                valida_stock,
                valida_entrega,
                valida_montos,
                valida_transporte,
                valida_margen,
                valida_vigencia,
                data.get('responsable') or data.get('vendedor') or 'Hellen',
                data.get('lugar_entrega') or data.get('entrega') or '',
                data.get('condicion_atencion') or data.get('condicion_pago') or '',
                items_json,
                data.get('medio') or data.get('correo_origen') or 'Correo',
                data.get('entrega') or data.get('lugar_entrega') or '',
                data.get('condicion_pago') or data.get('condicion_atencion') or '',
                data.get('vendedor') or data.get('responsable') or 'Helen Blas Príncipe',
                req_compra,
                pc_id
            )
            
            result = db_query(query, params)
            print(f"✅ Resultado UPDATE: {result}")
            return result[0] if result else None
        
        # ============================================================
        # SI NO HAY ID, INSERTAR
        # ============================================================
        print("➕ Insertando nuevo PC...")
        
        # Asegurar que todos los valores sean válidos (no None)
        cotizacion_id = data.get('cotizacion_id')
        if cotizacion_id is None or cotizacion_id == '':
            cotizacion_id = None
        
        query = """
            INSERT INTO pedido_compra_pc (
                numero, fecha, estado, cliente, ruc, monto,
                cotizacion_id, cotizacion_numero, correo_origen,
                fecha_recepcion, fecha_despacho, archivo_oc,
                observaciones, 
                valida_precios, valida_cantidades, valida_stock, 
                valida_entrega, valida_montos, valida_transporte,
                valida_margen, valida_vigencia,
                responsable, lugar_entrega, condicion_atencion,
                creado_por, items_json, medio, entrega,
                condicion_pago, vendedor, req_compra
            ) VALUES (
                %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id, numero
        """
        
        params = (
            data.get('numero'),
            data.get('fecha') or datetime.now().isoformat(),
            estado,
            data.get('cliente') or '',
            data.get('ruc') or '',
            float(data.get('monto', 0)),
            cotizacion_id,  # Puede ser None
            data.get('cotizacion_numero') or '',
            data.get('correo_origen') or data.get('medio') or '',
            data.get('fecha_recepcion') or data.get('fecha'),
            data.get('fecha_despacho'),
            data.get('archivo_oc'),
            data.get('observaciones') or '',
            valida_precios,
            valida_cantidades,
            valida_stock,
            valida_entrega,
            valida_montos,
            valida_transporte,
            valida_margen,
            valida_vigencia,
            data.get('responsable') or data.get('vendedor') or 'Hellen',
            data.get('lugar_entrega') or data.get('entrega') or '',
            data.get('condicion_atencion') or data.get('condicion_pago') or '',
            data.get('creado_por') or 8,
            items_json,
            data.get('medio') or data.get('correo_origen') or 'Correo',
            data.get('entrega') or data.get('lugar_entrega') or '',
            data.get('condicion_pago') or data.get('condicion_atencion') or '',
            data.get('vendedor') or data.get('responsable') or 'Helen Blas Príncipe',
            req_compra
        )
        
        result = db_query(query, params)
        print(f"✅ Resultado INSERT: {result}")
        return result[0] if result else None
        
    except Exception as e:
        print(f"❌ Error en guardar_pc_db: {e}")
        import traceback
        traceback.print_exc()
        raise


def obtener_despachos_db():
    """Obtiene todos los despachos con sus items"""
    try:
        query = """
            SELECT 
                id, numero, fecha, fecha_despacho, estado,
                pc_id, pc_numero, cotizacion_id, cotizacion_numero,
                cliente, ruc, comprobante, guia, origen, destino,
                transportista, observaciones, responsable,
                items_json, created_at, updated_at
            FROM despachos
            ORDER BY id DESC
        """
        results = db_query(query)
        
        # Parsear items_json para cada despacho
        for row in results:
            if row.get('items_json'):
                try:
                    row['items'] = json.loads(row['items_json'])
                except:
                    row['items'] = []
            else:
                row['items'] = []
        
        return results
    except Exception as e:
        print(f"❌ Error en obtener_despachos_db: {e}")
        return []


def guardar_despacho_db(data):
    """Guarda un nuevo despacho"""
    try:
        query = """
            INSERT INTO despachos (
                numero, fecha, fecha_despacho, estado,
                pc_id, pc_numero, cotizacion_id, cotizacion_numero,
                cliente, ruc, comprobante, guia, origen, destino,
                transportista, observaciones, responsable,
                creado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            RETURNING id, numero
        """
        params = (
            data.get('numero'),
            data.get('fecha') or datetime.now().isoformat(),
            data.get('fecha_despacho'),
            data.get('estado', 'Pendiente despacho'),
            data.get('pc_id'),
            data.get('pc_numero'),
            data.get('cotizacion_id'),
            data.get('cotizacion_numero'),
            data.get('cliente'),
            data.get('ruc'),
            data.get('comprobante'),
            data.get('guia'),
            data.get('origen', 'ALM-SMP'),
            data.get('destino'),
            data.get('transportista'),
            data.get('observaciones'),
            data.get('responsable'),
            data.get('creado_por')
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_despacho_db: {e}")
        raise

# ============================================================
# FUNCIONES DE AYUDA PARA DEVOLUCIONES
# ============================================================

def obtener_devoluciones_db():
    """Obtiene todas las devoluciones"""
    try:
        query = """
            SELECT 
                id, numero, fecha, estado, ruc, cliente,
                comprobante_id, comprobante_numero, guia, motivo,
                monto, observaciones, creado_por, created_at, updated_at
            FROM devoluciones
            ORDER BY id DESC
        """
        return db_query(query)
    except Exception as e:
        print(f"❌ Error en obtener_devoluciones_db: {e}")
        return []

def guardar_devolucion_db(data):
    """Guarda una nueva devolución"""
    try:
        query = """
            INSERT INTO devoluciones (
                numero, fecha, estado, ruc, cliente,
                comprobante_id, comprobante_numero, guia, motivo,
                monto, observaciones, creado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, numero
        """
        params = (
            data.get('numero'),
            data.get('fecha') or datetime.now().isoformat(),
            data.get('estado', 'Pendiente'),
            data.get('ruc'),
            data.get('cliente'),
            data.get('comprobante_id'),
            data.get('comprobante_numero'),
            data.get('guia'),
            data.get('motivo'),
            float(data.get('monto', 0)),
            data.get('observaciones'),
            data.get('creado_por')
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_devolucion_db: {e}")
        raise

# ============================================================
# RUTAS PRINCIPALES
# ============================================================

@ventas_bp.route('/ventas')
@login_required
def ventas():
    tab = request.args.get('tab', 'cotizaciones')
    return render_template('ventas/index.html', 
                         active_tab=tab,
                         usuario=session.get('usuario'),
                         nombre=session.get('nombre'),
                         empresa=session.get('empresa'))
@ventas_bp.route('/ventas/api/cotizaciones/listar', methods=['GET'])
@login_required
def api_cotizaciones_listar():
    try:
        print("🔍 API COTIZACIONES LLAMADA")
        
        data = obtener_cotizaciones_db()
        print(f"📊 Cotizaciones encontradas: {len(data)}")
        
        formatted_data = []
        for row in data:
            formatted_data.append({
                'id': row.get('id'),
                'numero': row.get('numero_cotizacion') or row.get('codigo_cotizacion'),
                'fecha': row.get('fecha_creacion'),
                'estado': row.get('estado'),
                'ruc': row.get('cliente_ruc') or str(row.get('cliente_id', '')),
                'razon': row.get('cliente_razon_social') or row.get('cliente_nombre_comercial') or f"Cliente {row.get('cliente_id', '')}",
                'descripcion': row.get('nota_cotizacion') or row.get('notas') or '',
                'primer_producto': row.get('primer_producto_descripcion') or '',
                'monto': float(row.get('total', 0)),
                'subtotal': float(row.get('subtotal', 0)),
                'igv': float(row.get('igv', 0)),
                'condicion': row.get('condicion_pago') or row.get('forma_pago'),
                'vendedor': row.get('vendedor') or str(row.get('usuario_id', '')),
                'vencimiento': row.get('validez_oferta'),
                'cod_cliente': str(row.get('cliente_id', '')),
                'direccion_entrega': row.get('direccion_entrega'),
                'requerimiento': row.get('requerimiento'),
                'nota': row.get('nota_cotizacion'),
                'descuento_porcentaje': float(row.get('descuento_porcentaje', 0)),
                'descuento_monto': float(row.get('descuento_monto', 0)),
                'descuento_tipo': row.get('descuento_tipo'),
                'contacto': row.get('contacto_cliente'),
                'telefono': row.get('telefono_cliente'),
                'email': row.get('email_cliente'),
                'tiempo_entrega': row.get('tiempo_entrega'),
                'validez_oferta': row.get('validez_oferta'),
                'nota_comercial': row.get('nota_cotizacion'),
                'seguimiento': row.get('seguimiento', 'Helen Blas Príncipe'),
                'motivo': row.get('motivo', 'Proyecto nuevo'),
                'transporte': row.get('transporte', 'Seleccione'),
                'parihuela': row.get('parihuela', 'Seleccione'),
                'nota_interna': row.get('nota_interna', '')
            })
        
        print(f"✅ Datos formateados: {len(formatted_data)} cotizaciones")
        return jsonify({'success': True, 'data': formatted_data})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/cotizaciones/guardar', methods=['POST'])
@login_required
def api_cotizaciones_guardar():
    try:
        data = request.get_json()
        usuario_id = session.get('usuario_id', 8) or data.get('usuario_id', 8)
        
        print("=" * 80)
        print("📦 API COTIZACIONES GUARDAR")
        print(f"  - id: {data.get('id')}")
        print(f"  - cliente_id: {data.get('cliente_id')}")
        print(f"  - usuario_id: {usuario_id}")
        print(f"  - estado: {data.get('estado')}")
        print(f"  - total: {data.get('total')}")
        print(f"  - productos: {len(data.get('productos', []))}")
        print("=" * 80)
        
        # ============================================================
        # DETERMINAR SI ES EDICIÓN O NUEVA
        # ============================================================
        cotizacion_id = data.get('id')
        es_edicion = cotizacion_id is not None and cotizacion_id > 0
        
        # Obtener cliente_id
        cliente_id = data.get('cliente_id')
        if isinstance(cliente_id, str):
            try:
                cliente_id = int(cliente_id)
            except ValueError:
                return jsonify({'success': False, 'error': 'cliente_id debe ser un número'}), 400
        
        if not cliente_id:
            return jsonify({'success': False, 'error': 'cliente_id es requerido'}), 400
        
        # Verificar que el cliente existe
        cliente = db_query("SELECT id, razon_social FROM clientes WHERE id = %s", (cliente_id,))
        if not cliente:
            return jsonify({'success': False, 'error': f'Cliente con ID {cliente_id} no encontrado'}), 400
        
        print(f"✅ Cliente encontrado: {cliente[0]['razon_social']}")
        
        # Calcular totales
        subtotal = float(data.get('subtotal', 0))
        igv = float(data.get('igv', 0))
        total = float(data.get('total', 0))
        
        print(f"📊 Totales: subtotal={subtotal}, igv={igv}, total={total}")
        
        # ============================================================
        # OBTENER NÚMERO DE COTIZACIÓN (RESPETAR EXISTENTE)
        # ============================================================
        numero = None
        codigo = None
        correlativo = None
        
        if es_edicion:
            # SI ES EDICIÓN, OBTENER EL NÚMERO EXISTENTE DE LA BD
            query_existente = """
                SELECT numero_cotizacion, codigo_cotizacion, correlativo
                FROM cotizaciones 
                WHERE id = %s
            """
            existente = db_query(query_existente, (cotizacion_id,))
            
            if existente:
                numero = existente[0].get('numero_cotizacion')
                codigo = existente[0].get('codigo_cotizacion')
                correlativo = existente[0].get('correlativo')
                print(f"📋 Edición - Manteniendo número: {numero}, correlativo: {correlativo}")
            else:
                # Fallback: si no se encuentra, generar uno nuevo
                count_data = db_query("SELECT COUNT(*) as total FROM cotizaciones")
                count = count_data[0]['total'] + 1 if count_data else 1
                numero = f"COT-{str(count).zfill(6)}"
                codigo = f"COT-{datetime.now().strftime('%Y%m%d')}-{str(count).zfill(4)}"
                correlativo = count
                print(f"📋 Fallback - Generando nuevo número: {numero}")
        else:
            # NUEVA COTIZACIÓN - Generar número
            count_data = db_query("SELECT COUNT(*) as total FROM cotizaciones")
            count = count_data[0]['total'] + 1 if count_data else 1
            numero = f"COT-{str(count).zfill(6)}"
            codigo = f"COT-{datetime.now().strftime('%Y%m%d')}-{str(count).zfill(4)}"
            correlativo = count
            print(f"📋 Nueva cotización - Generando número: {numero}")
        
        print(f"📋 Número final: {numero}, Código: {codigo}, Correlativo: {correlativo}")
        
        # ============================================================
        # GUARDAR O ACTUALIZAR
        # ============================================================
        
        if es_edicion:
            # ============================================================
            # ACTUALIZAR COTIZACIÓN EXISTENTE (MANTENIENDO NÚMERO)
            # ============================================================
            print(f"🔄 Actualizando cotización ID: {cotizacion_id}")
            
            query_update = """
                UPDATE cotizaciones SET
                    cliente_id = %s,
                    estado = %s,
                    subtotal = %s,
                    igv = %s,
                    total = %s,
                    usuario_id = %s,
                    notas = %s,
                    forma_pago = %s,
                    tiempo_entrega = %s,
                    validez_oferta = %s,
                    condicion_pago = %s,
                    direccion_entrega = %s,
                    requerimiento = %s,
                    nota_cotizacion = %s,
                    descuento_porcentaje = %s,
                    descuento_monto = %s,
                    descuento_tipo = %s,
                    contacto_cliente = %s,
                    telefono_cliente = %s,
                    email_cliente = %s
                WHERE id = %s
                RETURNING id, numero_cotizacion
            """
            
            params_update = (
                cliente_id,
                data.get('estado', 'Borrador'),
                subtotal,
                igv,
                total,
                usuario_id,
                data.get('notas', ''),
                data.get('condicion_pago'),
                data.get('tiempo_entrega'),
                data.get('validez'),
                data.get('condicion_pago'),
                data.get('direccion_entrega'),
                data.get('requerimiento'),
                data.get('nota_comercial', ''),
                float(data.get('descuento_porcentaje', 0)),
                float(data.get('descuento_monto', 0)),
                data.get('descuento_tipo', 'porcentaje'),
                data.get('contacto'),
                data.get('telefono'),
                data.get('email'),
                cotizacion_id
            )
            
            result_update = db_query(query_update, params_update)
            
            if result_update:
                # ELIMINAR DETALLES ANTIGUOS Y VOLVER A INSERTAR
                with db_tx() as conn:
                    from psycopg2.extras import RealDictCursor
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    
                    # Eliminar detalles antiguos
                    cur.execute("DELETE FROM cotizacion_detalle WHERE cotizacion_id = %s", (cotizacion_id,))
                    
                    # Insertar nuevos productos
                    productos = data.get('productos', [])
                    productos_guardados = 0
                    productos_fallidos = 0
                    
                    for idx, producto in enumerate(productos):
                        try:
                            codigo_producto = producto.get('codigo', '').strip()
                            producto_id = producto.get('producto_id')
                            
                            # Buscar producto
                            if producto_id:
                                cur.execute(
                                    "SELECT id, codigo, descripcion, precio_unitario, costo_unitario FROM productos WHERE id = %s",
                                    (producto_id,)
                                )
                                producto_bd = cur.fetchone()
                            else:
                                cur.execute(
                                    "SELECT id, codigo, descripcion, precio_unitario, costo_unitario FROM productos WHERE codigo = %s",
                                    (codigo_producto,)
                                )
                                producto_bd = cur.fetchone()
                                
                                if not producto_bd:
                                    cur.execute(
                                        "SELECT id, codigo, descripcion, precio_unitario, costo_unitario FROM productos WHERE TRIM(codigo) = TRIM(%s)",
                                        (codigo_producto,)
                                    )
                                    producto_bd = cur.fetchone()
                            
                            if not producto_bd:
                                print(f"  ❌ Producto '{codigo_producto}' NO ENCONTRADO")
                                productos_fallidos += 1
                                continue
                            
                            producto_id_bd = producto_bd['id']
                            cantidad = float(producto.get('cantidad', 1))
                            precio_venta = float(producto.get('valorVenta', producto_bd.get('precio_unitario', 0)))
                            costo_unitario = float(producto_bd.get('costo_unitario', 0))
                            
                            subtotal_costo = cantidad * costo_unitario
                            subtotal_venta = cantidad * precio_venta
                            
                            if costo_unitario > 0:
                                margen_porcentaje = ((precio_venta - costo_unitario) / costo_unitario * 100)
                            else:
                                margen_porcentaje = 0
                            
                            cur.execute("""
                                INSERT INTO cotizacion_detalle (
                                    cotizacion_id, producto_id, cantidad,
                                    costo_unitario, subtotal_costo, margen_porcentaje,
                                    precio_venta_unitario, subtotal_venta,
                                    descuento_porcentaje, precio_venta_con_descuento,
                                    subtotal_venta_con_descuento, descuento_total, margen_final
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """, (
                                cotizacion_id, producto_id_bd, cantidad,
                                costo_unitario, subtotal_costo, margen_porcentaje,
                                precio_venta, subtotal_venta,
                                0, precio_venta, subtotal_venta, 0, margen_porcentaje
                            ))
                            
                            productos_guardados += 1
                            print(f"  ✅ Producto {idx+1}: {producto_bd['codigo']} - Cant: {cantidad}")
                            
                        except Exception as e:
                            print(f"  ❌ Error guardando producto: {e}")
                            productos_fallidos += 1
                            raise
                
                return jsonify({
                    'success': True,
                    'message': f'Cotización actualizada correctamente con {productos_guardados} productos',
                    'data': {
                        'id': cotizacion_id,
                        'numero': numero,
                        'productos_guardados': productos_guardados,
                        'productos_fallidos': productos_fallidos
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'No se pudo actualizar la cotización'}), 400
        
        else:
            # ============================================================
            # INSERTAR NUEVA COTIZACIÓN
            # ============================================================
            print("➕ Insertando nueva cotización...")
            
            # Preparar parámetros para la cotización
            params = (
                numero,
                cliente_id,
                datetime.now().isoformat(),
                data.get('estado', 'Borrador'),
                subtotal,
                igv,
                total,
                usuario_id,
                data.get('notas', ''),
                data.get('condicion_pago'),
                data.get('tiempo_entrega'),
                data.get('validez'),
                codigo,
                correlativo,
                data.get('condicion_pago'),
                data.get('direccion_entrega'),
                data.get('requerimiento'),
                data.get('nota_comercial', ''),
                float(data.get('descuento_porcentaje', 0)),
                float(data.get('descuento_monto', 0)),
                data.get('descuento_tipo', 'porcentaje'),
                data.get('contacto'),
                data.get('telefono'),
                data.get('email')
            )
            
            try:
                with db_tx() as conn:
                    from psycopg2.extras import RealDictCursor
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    
                    # 1. Insertar cotización
                    cur.execute("""
                        INSERT INTO cotizaciones (
                            numero_cotizacion, cliente_id, fecha_creacion, estado,
                            subtotal, igv, total, usuario_id, notas,
                            forma_pago, tiempo_entrega, validez_oferta,
                            codigo_cotizacion, correlativo, condicion_pago,
                            direccion_entrega, requerimiento, nota_cotizacion,
                            descuento_porcentaje, descuento_monto, descuento_tipo,
                            contacto_cliente, telefono_cliente, email_cliente
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        RETURNING id, numero_cotizacion
                    """, params)
                    
                    result = cur.fetchone()
                    cotizacion_id = result['id']
                    numero = result['numero_cotizacion']
                    print(f"✅ Cotización creada con ID: {cotizacion_id}")
                    
                    # 2. Insertar productos en cotizacion_detalle
                    productos = data.get('productos', [])
                    print(f"📦 Guardando {len(productos)} productos...")
                    
                    productos_guardados = 0
                    productos_fallidos = 0
                    
                    for idx, producto in enumerate(productos):
                        try:
                            codigo_producto = producto.get('codigo', '').strip()
                            producto_id = producto.get('producto_id')
                            
                            # Buscar producto
                            if producto_id:
                                cur.execute(
                                    "SELECT id, codigo, descripcion, precio_unitario, costo_unitario FROM productos WHERE id = %s",
                                    (producto_id,)
                                )
                                producto_bd = cur.fetchone()
                            else:
                                cur.execute(
                                    "SELECT id, codigo, descripcion, precio_unitario, costo_unitario FROM productos WHERE codigo = %s",
                                    (codigo_producto,)
                                )
                                producto_bd = cur.fetchone()
                                
                                if not producto_bd:
                                    cur.execute(
                                        "SELECT id, codigo, descripcion, precio_unitario, costo_unitario FROM productos WHERE TRIM(codigo) = TRIM(%s)",
                                        (codigo_producto,)
                                    )
                                    producto_bd = cur.fetchone()
                            
                            if not producto_bd:
                                print(f"  ❌ Producto '{codigo_producto}' NO ENCONTRADO")
                                productos_fallidos += 1
                                continue
                            
                            producto_id_bd = producto_bd['id']
                            cantidad = float(producto.get('cantidad', 1))
                            precio_venta = float(producto.get('valorVenta', producto_bd.get('precio_unitario', 0)))
                            costo_unitario = float(producto_bd.get('costo_unitario', 0))
                            
                            subtotal_costo = cantidad * costo_unitario
                            subtotal_venta = cantidad * precio_venta
                            
                            if costo_unitario > 0:
                                margen_porcentaje = ((precio_venta - costo_unitario) / costo_unitario * 100)
                            else:
                                margen_porcentaje = 0
                            
                            cur.execute("""
                                INSERT INTO cotizacion_detalle (
                                    cotizacion_id, producto_id, cantidad,
                                    costo_unitario, subtotal_costo, margen_porcentaje,
                                    precio_venta_unitario, subtotal_venta,
                                    descuento_porcentaje, precio_venta_con_descuento,
                                    subtotal_venta_con_descuento, descuento_total, margen_final
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """, (
                                cotizacion_id, producto_id_bd, cantidad,
                                costo_unitario, subtotal_costo, margen_porcentaje,
                                precio_venta, subtotal_venta,
                                0, precio_venta, subtotal_venta, 0, margen_porcentaje
                            ))
                            
                            productos_guardados += 1
                            print(f"  ✅ Producto {idx+1}: {producto_bd['codigo']} - Cant: {cantidad}")
                            
                        except Exception as e:
                            print(f"  ❌ Error guardando producto: {e}")
                            productos_fallidos += 1
                            raise
                    
                    return jsonify({
                        'success': True,
                        'message': f'Cotización creada correctamente con {productos_guardados} productos',
                        'data': {
                            'id': cotizacion_id,
                            'numero': numero,
                            'productos_guardados': productos_guardados,
                            'productos_fallidos': productos_fallidos
                        }
                    })
                    
            except Exception as e:
                print(f"❌ Error en transacción: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'error': str(e)}), 500
            
    except Exception as e:
        print(f"❌ Error general en api_cotizaciones_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/cotizaciones/<int:id>', methods=['GET'])
@login_required
def api_cotizaciones_obtener(id):
    try:
        data = obtener_cotizacion_por_id_db(id)
        if data:
            return jsonify({'success': True, 'data': data})
        return jsonify({'success': False, 'error': 'Cotización no encontrada'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/cotizaciones/<int:id>/toggle', methods=['PUT'])
@login_required
def api_cotizaciones_toggle(id):
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        result = actualizar_estado_cotizacion_db(id, nuevo_estado)
        if result:
            return jsonify({'success': True, 'message': f'Estado actualizado a {nuevo_estado}'})
        return jsonify({'success': False, 'error': 'No se pudo actualizar'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@ventas_bp.route('/ventas/api/cotizaciones/<int:id>', methods=['DELETE'])
@login_required
def api_cotizaciones_eliminar(id):
    """Elimina (anula) una cotización - guarda respaldo con motivo y cambia estado a Anulada"""
    try:
        print(f"🗑️ Eliminando cotización ID: {id}")

        data = request.get_json(silent=True) or {}
        motivo = (data.get('motivo') or '').strip()

        if not motivo:
            return jsonify({'success': False, 'error': 'El motivo de eliminación es obligatorio'}), 400

        # 1. Obtener datos completos de la cotización + cliente
        query_cabecera = """
            SELECT 
                c.*, 
                cl.razon_social as cliente_razon_social,
                cl.numero_documento as cliente_ruc
            FROM cotizaciones c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id::integer
            WHERE c.id = %s
        """
        result_check = db_query(query_cabecera, (id,))

        if not result_check:
            return jsonify({'success': False, 'error': 'Cotización no encontrada'}), 404

        cot = result_check[0]
        estado_actual = cot.get('estado')
        print(f"📊 Estado actual de la cotización: {estado_actual}")

        if estado_actual == 'Anulada':
            return jsonify({
                'success': True,
                'message': 'La cotización ya estaba anulada',
                'data': {'id': id, 'estado': 'Anulada'}
            })

        # 2. Obtener productos de la cotización
        query_productos = """
            SELECT 
                d.id, d.producto_id, d.cantidad,
                d.costo_unitario, d.subtotal_costo, d.margen_porcentaje,
                d.precio_venta_unitario, d.subtotal_venta,
                d.descuento_porcentaje, d.precio_venta_con_descuento,
                d.subtotal_venta_con_descuento, d.descuento_total, d.margen_final,
                p.codigo, p.descripcion, p.modelo, p.marca, p.unidad
            FROM cotizacion_detalle d
            LEFT JOIN productos p ON p.id = d.producto_id
            WHERE d.cotizacion_id = %s
        """
        productos = db_query(query_productos, (id,))

        # 3. Asegurar que la tabla de respaldo exista
        crear_tabla_cotizaciones_eliminadas_si_no_existe()

        usuario_id = session.get('usuario_id', 8)

        # 4. Serializar valores no compatibles con JSON (fechas, Decimal)
        from decimal import Decimal

        def _serializar(v):
            if isinstance(v, datetime):
                return v.isoformat()
            if isinstance(v, Decimal):
                return float(v)
            return v

        datos_completos = {k: _serializar(v) for k, v in cot.items()}
        productos_snapshot = [{k: _serializar(v) for k, v in p.items()} for p in (productos or [])]

        # 5. Guardar el respaldo ANTES de anular
        query_insert = """
            INSERT INTO cotizaciones_eliminadas (
                cotizacion_id_original, numero_cotizacion, codigo_cotizacion,
                cliente_id, cliente_razon_social, cliente_ruc,
                fecha_creacion, estado_anterior, subtotal, igv, total,
                condicion_pago, tiempo_entrega, direccion_entrega, vendedor,
                contacto_cliente, telefono_cliente, email_cliente,
                nota_cotizacion, requerimiento,
                productos_json, datos_completos_json,
                motivo_eliminacion, eliminado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """
        params_insert = (
            id,
            cot.get('numero_cotizacion'),
            cot.get('codigo_cotizacion'),
            cot.get('cliente_id'),
            cot.get('cliente_razon_social'),
            cot.get('cliente_ruc'),
            cot.get('fecha_creacion'),
            estado_actual,
            cot.get('subtotal'),
            cot.get('igv'),
            cot.get('total'),
            cot.get('condicion_pago'),
            cot.get('tiempo_entrega'),
            cot.get('direccion_entrega'),
            cot.get('vendedor'),
            cot.get('contacto_cliente'),
            cot.get('telefono_cliente'),
            cot.get('email_cliente'),
            cot.get('nota_cotizacion'),
            cot.get('requerimiento'),
            json.dumps(productos_snapshot),
            json.dumps(datos_completos),
            motivo,
            usuario_id
        )
        db_execute(query_insert, params_insert)
        print(f"✅ Respaldo guardado en cotizaciones_eliminadas para cotización {id}")

        # 6. Cambiar estado a 'Anulada' (igual que antes)
        query_update = """
            UPDATE cotizaciones 
            SET estado = 'Anulada'
            WHERE id = %s
            RETURNING id, estado
        """
        result_update = db_query(query_update, (id,))

        if result_update:
            return jsonify({
                'success': True,
                'message': 'Cotización anulada y respaldada correctamente',
                'data': result_update[0]
            })

        return jsonify({'success': False, 'error': 'No se pudo anular la cotización'}), 400

    except Exception as e:
        print(f"❌ Error en api_cotizaciones_eliminar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# GUÍAS - API
# ============================================================

@ventas_bp.route('/ventas/api/guias/listar', methods=['GET'])
@login_required
def api_guias_listar():
    try:
        data = obtener_guias_db()
        formatted_data = []
        for row in data:
            items = []
            try:
                if row.get('items_json'):
                    items = json.loads(row.get('items_json'))
            except:
                pass
            
            # 🔽 OBTENER FECHA COMO STRING SIN MODIFICAR ZONA HORARIA
            fecha_emision = row.get('fecha_emision')
            if fecha_emision:
                # Si es datetime, convertir a string ISO sin zona horaria
                if isinstance(fecha_emision, datetime):
                    fecha_emision = fecha_emision.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(fecha_emision, date):
                    fecha_emision = fecha_emision.strftime('%Y-%m-%d')
            
            formatted_data.append({
                'id': row.get('id'),
                'serie': row.get('serie'),
                'numero': row.get('numero'),
                'fecha': fecha_emision,  # ← ENVIAR COMO STRING SIN ZONA
                'fecha_traslado': row.get('fecha_traslado'),
                'estado': row.get('estado_sunat') or row.get('estado'),
                'ruc': row.get('ruc_destinatario'),
                'cliente': row.get('destinatario_nombre'),
                'cotizacion': row.get('documento_asociado'),
                'comprobante': row.get('documento_asociado'),
                'origen': row.get('remitente_direccion'),
                'destino': row.get('destinatario_direccion'),
                'motivo': row.get('motivo_traslado'),
                'observaciones': row.get('observaciones'),
                'items': items,
                'placa': row.get('placa_vehiculo'),
                'conductor': row.get('conductor_nombre'),
                'transportista': row.get('transportista_nombre')
            })
        return jsonify({'success': True, 'data': formatted_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/guias/guardar', methods=['POST'])
@login_required
def api_guias_guardar():
    try:
        data = request.get_json()
        usuario_id = session.get('usuario_id', 8)
        
        print("=" * 80)
        print("📦 API GUIAS GUARDAR - INICIO")
        print(f"  - Usuario ID: {usuario_id}")
        print("=" * 80)
        
        from datetime import datetime
        
        # ============================================================
        # ORIGEN FIJO - DATOS DEL REMITENTE
        # ============================================================
        ORIGEN_FIJO = {
            'ruc': '20602095704',
             'nombre': 'KCF CORPORACION E.I.R.L',
            'direccion': 'JR. LAS ALMENDRAS VERDES NRO. 284 URB. VIRGEN DEL ROSARIO LIMA - LIMA - SAN MARTIN DE PORRES',
            'ubigeo': '150139'
        }
        
        # ============================================================
        # OBTENER FECHA CON HORA CORRECTA
        # ============================================================
        ahora = datetime.now()
        
        # Fecha de emisión
        fecha_emision_raw = data.get('fecha_emision')
        if fecha_emision_raw:
            if isinstance(fecha_emision_raw, str) and 'T' not in fecha_emision_raw and ' ' not in fecha_emision_raw:
                fecha_emision = f"{fecha_emision_raw}T{ahora.strftime('%H:%M:%S')}"
            else:
                fecha_emision = fecha_emision_raw
        else:
            fecha_emision = ahora.isoformat()
        
        # Fecha de traslado
        fecha_traslado = data.get('fecha_traslado') or data.get('fecha_emision') or ahora.date().isoformat()
        
        # ============================================================
        # CONSULTA CON SOLO LAS COLUMNAS QUE EXISTEN EN LA TABLA
        # ============================================================
        query = """
            INSERT INTO guias_remision (
                serie, numero, fecha_emision, fecha_traslado,
                ruc_remitente, remitente_nombre, remitente_direccion,
                remitente_ubigeo, ruc_destinatario, destinatario_nombre,
                destinatario_direccion, destinatario_ubigeo,
                modalidad_transporte, placa_vehiculo, conductor_dni,
                conductor_nombre, licencia_conductor, transportista_ruc,
                transportista_nombre, motivo_traslado, documento_asociado,
                orden_compra_cliente, factura,
                peso_total, items_json, observaciones, estado_sunat,
                creado_por, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, NOW()
            )
            RETURNING id, numero
        """
        
        items_json = json.dumps(data.get('items', []))
        
        # ============================================================
        # 27 VALORES QUE COINCIDEN CON LOS 27 PLACEHOLDERS
        # ============================================================
        params = (
            data.get('serie', 'T001'),
            data.get('numero'),
            fecha_emision,
            fecha_traslado,
            data.get('ruc_remitente') or ORIGEN_FIJO['ruc'],
            data.get('remitente_nombre') or ORIGEN_FIJO['nombre'],
            data.get('remitente_direccion') or ORIGEN_FIJO['direccion'],
            data.get('remitente_ubigeo') or ORIGEN_FIJO['ubigeo'],
            data.get('ruc_destinatario', ''),
            data.get('destinatario_nombre', ''),
            data.get('destinatario_direccion', ''),
            data.get('destinatario_ubigeo', ''),
            data.get('modalidad_transporte', 'PRIVADO'),
            data.get('placa_vehiculo', ''),
            data.get('conductor_dni', ''),
            data.get('conductor_nombre', ''),
            data.get('licencia_conductor', ''),
            data.get('transportista_ruc', ''),
            data.get('transportista_nombre', ''),
            data.get('motivo_traslado', '01'),
            data.get('documento_asociado', ''),
            data.get('orden_compra_cliente',''),
            data.get('factura',''),
            float(data.get('peso_total', 0)),
            items_json,
            data.get('observaciones', ''),
            data.get('estado', 'BORRADOR'),
            usuario_id
        )
        
        print(f"📊 Número de parámetros: {len(params)}")
        print(f"📊 Items: {len(data.get('items', []))} productos")
        
        # ============================================================
        # 🔽 CORRECCIÓN: db_query devuelve una lista de tuplas/diccionarios
        # ============================================================
        result = db_query(query, params)
        
        # Verificar que result no esté vacío
        if result and len(result) > 0:
            # result[0] es el primer registro (diccionario o tupla)
            row = result[0]
            
            # Si es un diccionario, acceder por clave
            if isinstance(row, dict):
                guia_id = row.get('id')
                guia_numero = row.get('numero')
            else:
                # Si es una tupla, acceder por índice
                guia_id = row[0] if len(row) > 0 else None
                guia_numero = row[1] if len(row) > 1 else None
            
            if guia_id:
                return jsonify({
                    'success': True,
                    'message': 'Guía creada correctamente',
                    'data': {
                        'id': guia_id,
                        'numero': guia_numero
                    }
                })
        
        return jsonify({'success': False, 'error': 'No se pudo crear la guía'}), 400
            
    except Exception as e:
        print(f"❌ Error en api_guias_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/ventas/api/guias/<int:id>', methods=['GET'])
@login_required
def api_guias_obtener(id):
    try:
        data = obtener_guia_por_id_db(id)
        if data:
            return jsonify({'success': True, 'data': data})
        return jsonify({'success': False, 'error': 'Guía no encontrada'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/guias/<int:id>', methods=['DELETE'])
@login_required
def api_guias_eliminar(id):
    try:
        result = actualizar_guia_db(id, {'estado_sunat': 'ANULADA'})
        if result:
            return jsonify({'success': True, 'message': 'Guía anulada'})
        return jsonify({'success': False, 'error': 'No se pudo anular'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# GUÍAS - ELIMINACIÓN FÍSICA
# ============================================================

@ventas_bp.route('/ventas/api/guias/<int:id>/permanente', methods=['DELETE'])
@login_required
def api_guias_eliminar_permanente(id):
    """Elimina físicamente una guía de la base de datos (solo si ya está anulada)"""
    try:
        print(f"🗑️ Eliminando físicamente guía ID: {id}")

        query_check = "SELECT id, numero, estado_sunat FROM guias_remision WHERE id = %s"
        result_check = db_query(query_check, (id,))

        if not result_check:
            return jsonify({'success': False, 'error': 'Guía no encontrada'}), 404

        estado = (result_check[0].get('estado_sunat') or '').upper()
        if estado not in ('ANULADA', 'ANULADO'):
            return jsonify({
                'success': False,
                'error': f'Solo se pueden eliminar guías en estado "Anulada". Estado actual: {result_check[0].get("estado_sunat")}'
            }), 400

        query_delete = "DELETE FROM guias_remision WHERE id = %s RETURNING id"
        result_delete = db_query(query_delete, (id,))

        if result_delete:
            return jsonify({'success': True, 'message': 'Guía eliminada correctamente', 'data': {'id': id}})

        return jsonify({'success': False, 'error': 'No se pudo eliminar la guía'}), 400

    except Exception as e:
        print(f"❌ Error en api_guias_eliminar_permanente: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# COMPROBANTES - API
# ============================================================

@ventas_bp.route('/ventas/api/comprobantes/listar', methods=['GET'])
@login_required
def api_comprobantes_listar():
    try:
        data = obtener_comprobantes_db()
        formatted_data = []
        for row in data:
            items = []
            try:
                if row.get('items_json'):
                    items = json.loads(row.get('items_json'))
            except:
                pass
            formatted_data.append({
                'id': row.get('id'),
                'tipo': row.get('tipo_comprobante'),
                'serie': row.get('serie'),
                'numero': row.get('numero'),
                'fecha': row.get('fecha_emision'),
                'estado': row.get('estado_sunat') or 'Borrador',
                'ruc': row.get('cliente_numero_doc'),
                'cliente': row.get('cliente_nombre'),
                'cotizacion': row.get('documento_asociado'),
                'monto': float(row.get('total', 0)),
                'subtotal': float(row.get('subtotal', 0)),
                'igv': float(row.get('igv', 0)),
                'condicion': 'Contado',
                'observaciones': row.get('observaciones'),
                'items': items
            })
        return jsonify({'success': True, 'data': formatted_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/ventas/api/comprobantes/guardar', methods=['POST'])
@login_required
def api_comprobantes_guardar():
    try:
        data = request.get_json()
        usuario_id = session.get('usuario_id', 8)
        
        items_json = data.get('items', [])
        
        # ============================================================
        # 🔽 OBTENER DATOS DE RETENCIÓN DEL IGV (3%)
        # ============================================================
        tiene_retencion = data.get('tiene_retencion', False)
        es_credito = data.get('es_credito', False)
        estado_credito = data.get('estado_credito')
        fecha_aprobacion = data.get('fecha_aprobacion')
        fecha_vencimiento = data.get('fecha_vencimiento')
        dias_credito = data.get('dias_credito')
        porcentaje_retencion = float(data.get('porcentaje_retencion', 3.00))
        monto_retenido = float(data.get('monto_retenido', 0))
        monto_a_pagar = float(data.get('monto_a_pagar', 0))
        obs_retencion = data.get('obs_retencion')
        condicion_pago = data.get('condicion', 'Contado')
        
        # Calcular totales
        monto_total = float(data.get('total', 0))
        subtotal = float(data.get('subtotal', 0))
        igv = float(data.get('igv', 0))
        
        # ============================================================
        # 🔽 OBTENER FECHA Y HORA ACTUAL CORRECTA
        # ============================================================
        from datetime import datetime
        fecha_emision = datetime.now().isoformat()  # ✅ CON HORA COMPLETA
        print(f"📅 Fecha emisión guardando: {fecha_emision}")
        
        # ============================================================
        # 🔽 VALIDAR Y RECALCULAR LA RETENCIÓN
        # ============================================================
        if tiene_retencion:
            if monto_total > 700:
                if monto_retenido == 0:
                    monto_retenido = (monto_total * porcentaje_retencion) / 100
                monto_a_pagar = monto_total - monto_retenido
                if not estado_credito:
                    estado_credito = 'Pendiente de aprobación'
                if not fecha_aprobacion:
                    fecha_aprobacion = datetime.now().date().isoformat()
                if not dias_credito:
                    dias_credito = 30
                if not fecha_vencimiento and dias_credito:
                    from datetime import timedelta
                    fecha_aprobacion_dt = datetime.strptime(fecha_aprobacion, '%Y-%m-%d')
                    fecha_vencimiento_dt = fecha_aprobacion_dt + timedelta(days=int(dias_credito))
                    fecha_vencimiento = fecha_vencimiento_dt.isoformat()
                if not obs_retencion:
                    obs_retencion = f'Retención del {porcentaje_retencion}% por IGV según normativa peruana. Monto: S/ {monto_total:.2f} > S/ 700. Se retiene S/ {monto_retenido:.2f} para la SUNAT.'
            else:
                tiene_retencion = False
                monto_retenido = 0
                monto_a_pagar = monto_total
                estado_credito = 'No aplica (monto < S/ 700)'
        
        # Preparar datos para guardar
        comprobante_data = {
            'tipo_comprobante': data.get('tipo', 'FACTURA'),
            'serie': data.get('serie', 'F001'),
            'numero': data.get('numero'),
            'fecha_emision': data.get('fecha_emision') or datetime.now().isoformat(), 
            'moneda': data.get('moneda', 'PEN'),
            'cliente_tipo_doc': data.get('cliente_tipo_doc', 'RUC'),
            'cliente_numero_doc': data.get('ruc'),
            'cliente_nombre': data.get('cliente'),
            'cliente_direccion': data.get('direccion') or '',
            'cliente_email': data.get('email') or '',
            'cliente_telefono': data.get('telefono') or '',
            'subtotal': subtotal,
            'igv': igv,
            'total': monto_total,
            'items_json': json.dumps(items_json),
            'observaciones': data.get('observaciones', ''),
            'estado_sunat': data.get('estado', 'BORRADOR'),
            'condicion_pago': condicion_pago,
            'documento_asociado': data.get('cotizacion') or data.get('cotizacion_numero') or '',
            'guia_vinculada': data.get('guia') or '',
            'pc_vinculado': data.get('pc') or '',
            # 🔽 CAMPOS DE RETENCIÓN
            'tiene_retencion': tiene_retencion,
            'es_credito': es_credito,
            'estado_credito': estado_credito,
            'fecha_aprobacion': fecha_aprobacion,
            'fecha_vencimiento': fecha_vencimiento,
            'dias_credito': dias_credito,
            'porcentaje_retencion': porcentaje_retencion,
            'monto_retenido': monto_retenido,
            'monto_a_pagar': monto_a_pagar,
            'obs_retencion': obs_retencion,
            'creado_por': usuario_id
        }
        
        # ============================================================
        # SI TIENE ID, ACTUALIZAR
        # ============================================================
        if data.get('id'):
            query = """
                UPDATE comprobantes SET
                    tipo_comprobante = %s, serie = %s, numero = %s,
                    fecha_emision = %s, moneda = %s,
                    cliente_tipo_doc = %s, cliente_numero_doc = %s,
                    cliente_nombre = %s, cliente_direccion = %s,
                    cliente_email = %s, cliente_telefono = %s,
                    subtotal = %s, igv = %s, total = %s,
                    items_json = %s, observaciones = %s,
                    estado_sunat = %s, condicion_pago = %s,
                    documento_asociado = %s, guia_vinculada = %s,
                    pc_vinculado = %s,
                    tiene_retencion = %s, es_credito = %s,
                    estado_credito = %s, fecha_aprobacion = %s,
                    fecha_vencimiento = %s, dias_credito = %s,
                    porcentaje_retencion = %s, monto_retenido = %s,
                    monto_a_pagar = %s, obs_retencion = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, serie, numero
            """
            params = (
                comprobante_data['tipo_comprobante'],
                comprobante_data['serie'],
                comprobante_data['numero'],
                comprobante_data['fecha_emision'],
                comprobante_data['moneda'],
                comprobante_data['cliente_tipo_doc'],
                comprobante_data['cliente_numero_doc'],
                comprobante_data['cliente_nombre'],
                comprobante_data['cliente_direccion'],
                comprobante_data['cliente_email'],
                comprobante_data['cliente_telefono'],
                comprobante_data['subtotal'],
                comprobante_data['igv'],
                comprobante_data['total'],
                comprobante_data['items_json'],
                comprobante_data['observaciones'],
                comprobante_data['estado_sunat'],
                comprobante_data['condicion_pago'],
                comprobante_data['documento_asociado'],
                comprobante_data['guia_vinculada'],
                comprobante_data['pc_vinculado'],
                comprobante_data['tiene_retencion'],
                comprobante_data['es_credito'],
                comprobante_data['estado_credito'],
                comprobante_data['fecha_aprobacion'],
                comprobante_data['fecha_vencimiento'],
                comprobante_data['dias_credito'],
                comprobante_data['porcentaje_retencion'],
                comprobante_data['monto_retenido'],
                comprobante_data['monto_a_pagar'],
                comprobante_data['obs_retencion'],
                data['id']
            )
            result = db_query(query, params)
            
            if result:
                return jsonify({'success': True, 'message': 'Comprobante actualizado', 'data': result[0]})
            return jsonify({'success': False, 'error': 'No se pudo actualizar'}), 400
        
        # ============================================================
        # CREAR NUEVO COMPROBANTE
        # ============================================================
        if not comprobante_data['numero']:
            count_data = db_query("SELECT COUNT(*) as total FROM comprobantes")
            count = count_data[0]['total'] + 1 if count_data else 1
            comprobante_data['numero'] = str(count).zfill(8)
        
        query_insert = """
            INSERT INTO comprobantes (
                tipo_comprobante, serie, numero, fecha_emision,
                moneda, cliente_tipo_doc, cliente_numero_doc,
                cliente_nombre, cliente_direccion, cliente_email,
                cliente_telefono, subtotal, igv, total,
                items_json, observaciones, estado_sunat,
                condicion_pago, documento_asociado, guia_vinculada,
                pc_vinculado, creado_por,
                tiene_retencion, es_credito, estado_credito,
                fecha_aprobacion, fecha_vencimiento, dias_credito,
                porcentaje_retencion, monto_retenido, monto_a_pagar,
                obs_retencion
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, serie, numero
        """
        params_insert = (
            comprobante_data['tipo_comprobante'],
            comprobante_data['serie'],
            comprobante_data['numero'],
            comprobante_data['fecha_emision'],
            comprobante_data['moneda'],
            comprobante_data['cliente_tipo_doc'],
            comprobante_data['cliente_numero_doc'],
            comprobante_data['cliente_nombre'],
            comprobante_data['cliente_direccion'],
            comprobante_data['cliente_email'],
            comprobante_data['cliente_telefono'],
            comprobante_data['subtotal'],
            comprobante_data['igv'],
            comprobante_data['total'],
            comprobante_data['items_json'],
            comprobante_data['observaciones'],
            comprobante_data['estado_sunat'],
            comprobante_data['condicion_pago'],
            comprobante_data['documento_asociado'],
            comprobante_data['guia_vinculada'],
            comprobante_data['pc_vinculado'],
            comprobante_data['creado_por'],
            comprobante_data['tiene_retencion'],
            comprobante_data['es_credito'],
            comprobante_data['estado_credito'],
            comprobante_data['fecha_aprobacion'],
            comprobante_data['fecha_vencimiento'],
            comprobante_data['dias_credito'],
            comprobante_data['porcentaje_retencion'],
            comprobante_data['monto_retenido'],
            comprobante_data['monto_a_pagar'],
            comprobante_data['obs_retencion']
        )
        
        result = db_query(query_insert, params_insert)
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Comprobante creado correctamente',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'No se pudo crear'}), 400
        
    except Exception as e:
        print(f"❌ Error en api_comprobantes_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/ventas/api/comprobantes/<int:id>', methods=['GET'])
@login_required
def api_comprobantes_obtener(id):
    """Obtiene un comprobante específico por su ID"""
    try:
        print(f"🔍 Buscando comprobante ID: {id}")
        
        query = """
            SELECT 
                id, tipo_comprobante, serie, numero, fecha_emision,
                moneda, cliente_tipo_doc, cliente_numero_doc,
                cliente_nombre, cliente_direccion, cliente_email,
                cliente_telefono, subtotal, igv, total,
                items_json, observaciones, estado_sunat,
                condicion_pago, documento_asociado, guia_vinculada,
                pc_vinculado, 
                tiene_retencion, 
                es_credito, estado_credito, fecha_aprobacion,
                fecha_vencimiento, dias_credito, 
                porcentaje_retencion, monto_retenido, monto_a_pagar,
                obs_retencion,
                sunat_response, cdr_response, creado_por,
                created_at, updated_at
            FROM comprobantes
            WHERE id = %s
        """
        result = db_query(query, (id,))
        
        print(f"📊 Resultado de consulta: {result}")
        
        # 🔽 VERIFICAR QUE HAYA RESULTADOS
        if not result:
            print(f"❌ No se encontró comprobante con ID: {id}")
            return jsonify({'success': False, 'error': 'Comprobante no encontrado'}), 404
        
        # Verificar que result sea una lista y tenga elementos
        if not isinstance(result, list) or len(result) == 0:
            print(f"❌ Resultado vacío o no es lista: {type(result)}")
            return jsonify({'success': False, 'error': 'Comprobante no encontrado'}), 404
        
        # Tomar el primer resultado
        comp = result[0]
        
        # Verificar que comp sea un diccionario
        if not isinstance(comp, dict):
            print(f"⚠️ Resultado no es un diccionario: {type(comp)}")
            # Si es una tupla, convertir a diccionario
            if isinstance(comp, (tuple, list)):
                # Obtener los nombres de las columnas
                columns = [
                    'id', 'tipo_comprobante', 'serie', 'numero', 'fecha_emision',
                    'moneda', 'cliente_tipo_doc', 'cliente_numero_doc',
                    'cliente_nombre', 'cliente_direccion', 'cliente_email',
                    'cliente_telefono', 'subtotal', 'igv', 'total',
                    'items_json', 'observaciones', 'estado_sunat',
                    'condicion_pago', 'documento_asociado', 'guia_vinculada',
                    'pc_vinculado', 'tiene_retencion', 'es_credito',
                    'estado_credito', 'fecha_aprobacion', 'fecha_vencimiento',
                    'dias_credito', 'porcentaje_retencion', 'monto_retenido',
                    'monto_a_pagar', 'obs_retencion', 'sunat_response',
                    'cdr_response', 'creado_por', 'created_at', 'updated_at'
                ]
                comp = dict(zip(columns, comp))

        # Parsear items_json de forma segura
        try:
            raw_val = comp.get('items_json')
            if raw_val:
                if isinstance(raw_val, str):
                    comp['items_json'] = json.loads(raw_val)
                else:
                    comp['items_json'] = raw_val
            else:
                comp['items_json'] = []
        except Exception as e:
            print(f"⚠️ Error parseando items_json de comprobante: {e}")
            comp['items_json'] = []

        print(f"✅ Comprobante encontrado: ID {comp.get('id')}, Serie {comp.get('serie')}-{comp.get('numero')}")
        return jsonify({'success': True, 'data': comp})
        
    except Exception as e:
        print(f"❌ Error en api_comprobantes_obtener: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/comprobantes/<int:id>', methods=['DELETE'])
@login_required
def api_comprobantes_eliminar(id):
    try:
        result = actualizar_estado_comprobante_db(id, 'ANULADO')
        if result:
            return jsonify({'success': True, 'message': 'Comprobante anulado'})
        return jsonify({'success': False, 'error': 'No se pudo anular'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================
# COMPROBANTES - ELIMINACIÓN FÍSICA
# ============================================================

@ventas_bp.route('/ventas/api/comprobantes/<int:id>/permanente', methods=['DELETE'])
@login_required
def api_comprobantes_eliminar_permanente(id):
    """Elimina físicamente un comprobante de la base de datos (solo si ya está anulado)"""
    try:
        print(f"🗑️ Eliminando físicamente comprobante ID: {id}")

        query_check = "SELECT id, numero, estado_sunat FROM comprobantes WHERE id = %s"
        result_check = db_query(query_check, (id,))

        if not result_check:
            return jsonify({'success': False, 'error': 'Comprobante no encontrado'}), 404

        estado = (result_check[0].get('estado_sunat') or '').upper()
        if estado not in ('ANULADO', 'ANULADA'):
            return jsonify({
                'success': False,
                'error': f'Solo se pueden eliminar comprobantes en estado "Anulado". Estado actual: {result_check[0].get("estado_sunat")}'
            }), 400

        query_delete = "DELETE FROM comprobantes WHERE id = %s RETURNING id"
        result_delete = db_query(query_delete, (id,))

        if result_delete:
            return jsonify({'success': True, 'message': 'Comprobante eliminado correctamente', 'data': {'id': id}})

        return jsonify({'success': False, 'error': 'No se pudo eliminar el comprobante'}), 400

    except Exception as e:
        print(f"❌ Error en api_comprobantes_eliminar_permanente: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# NOTAS DE CRÉDITO - API
# ============================================================

@ventas_bp.route('/ventas/api/notas-credito/listar', methods=['GET'])
@login_required
def api_notas_credito_listar():
    try:
        data = obtener_notas_credito_db()
        formatted_data = []
        for row in data:
            formatted_data.append({
                'id': row.get('id'),
                'serie': row.get('serie'),
                'numero': row.get('numero'),
                'fecha': row.get('fecha_emision'),
                'estado': row.get('estado'),
                'ruc': row.get('cliente_numero_doc'),
                'cliente': row.get('cliente_nombre'),
                'comprobante': row.get('comprobante_asociado'),
                'motivo': row.get('motivo'),
                'monto': float(row.get('monto', 0)),
                'observaciones': row.get('observaciones')
            })
        return jsonify({'success': True, 'data': formatted_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/notas-credito/guardar', methods=['POST'])
@login_required
def api_notas_credito_guardar():
    try:
        data = request.get_json()
        usuario_id = session.get('usuario_id', 8)
        data['creado_por'] = usuario_id
        
        if not data.get('numero'):
            count_data = db_query("SELECT COUNT(*) as total FROM notas_credito")
            count = count_data[0]['total'] + 1 if count_data else 1
            data['numero'] = str(count)
        
        result = guardar_nota_credito_db(data)
        if result:
            return jsonify({'success': True, 'message': 'Nota de crédito creada', 'data': result})
        return jsonify({'success': False, 'error': 'No se pudo crear'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# NOTAS DE CRÉDITO - ELIMINACIÓN FÍSICA
# ============================================================

@ventas_bp.route('/ventas/api/notas-credito/<int:id>/permanente', methods=['DELETE'])
@login_required
def api_notas_credito_eliminar_permanente(id):
    """Elimina físicamente una nota de crédito de la base de datos (solo si ya está anulada)"""
    try:
        print(f"🗑️ Eliminando físicamente nota de crédito ID: {id}")

        query_check = "SELECT id, numero, estado FROM notas_credito WHERE id = %s"
        result_check = db_query(query_check, (id,))

        if not result_check:
            return jsonify({'success': False, 'error': 'Nota de crédito no encontrada'}), 404

        estado = (result_check[0].get('estado') or '').lower()
        if estado != 'anulada':
            return jsonify({
                'success': False,
                'error': f'Solo se pueden eliminar notas de crédito en estado "Anulada". Estado actual: {result_check[0].get("estado")}'
            }), 400

        query_delete = "DELETE FROM notas_credito WHERE id = %s RETURNING id"
        result_delete = db_query(query_delete, (id,))

        if result_delete:
            return jsonify({'success': True, 'message': 'Nota de crédito eliminada correctamente', 'data': {'id': id}})

        return jsonify({'success': False, 'error': 'No se pudo eliminar la nota de crédito'}), 400

    except Exception as e:
        print(f"❌ Error en api_notas_credito_eliminar_permanente: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# PEDIDO COMPRA (PC) - API
# ============================================================

@ventas_bp.route('/ventas/api/pedido-compra/listar', methods=['GET'])
@login_required
def api_pedido_compra_listar():
    try:
        data = obtener_pc_db()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/pedido-compra/guardar', methods=['POST'])
@login_required
def api_pedido_compra_guardar():
    try:
        data = request.get_json()
        usuario_id = session.get('usuario_id', 8)
        data['creado_por'] = usuario_id
        
        print("=" * 80)
        print("📦 API PEDIDO COMPRA GUARDAR")
        print(f"  - ID: {data.get('id')}")
        print(f"  - Número: {data.get('numero')}")
        print(f"  - Cliente: {data.get('cliente')}")
        print(f"  - Estado: {data.get('estado')}")
        print(f"  - Items: {len(data.get('items', []))}")
        print(f"  - Cotización ID: {data.get('cotizacion_id')}")
        print("=" * 80)
        
        # ============================================================
        # SI HAY ID, ES EDICIÓN - VERIFICAR QUE EXISTA
        # ============================================================
        pc_id = data.get('id')
        if pc_id:
            check_query = "SELECT id, numero FROM pedido_compra_pc WHERE id = %s"
            check_result = db_query(check_query, (pc_id,))
            
            if not check_result:
                return jsonify({'success': False, 'error': f'PC con ID {pc_id} no encontrado'}), 404
            
            print(f"✅ PC existente encontrado: {check_result[0]['numero']}")
        
        # ============================================================
        # SI VIENE DE UNA COTIZACIÓN, OBTENER DATOS ADICIONALES
        # ============================================================
        cotizacion_id = data.get('cotizacion_id')
        cotizacion_numero = data.get('cotizacion_numero')
        
        # Si no hay cotizacion_id pero hay cotizacion_numero, buscar el ID
        if not cotizacion_id and cotizacion_numero and cotizacion_numero != 'SIN COTIZACIÓN':
            try:
                cot_query = """
                    SELECT id FROM cotizaciones 
                    WHERE numero_cotizacion = %s OR codigo_cotizacion = %s
                    LIMIT 1
                """
                cot_result = db_query(cot_query, (cotizacion_numero, cotizacion_numero))
                if cot_result:
                    cotizacion_id = cot_result[0]['id']
                    data['cotizacion_id'] = cotizacion_id
                    print(f"✅ Cotización encontrada por número: {cotizacion_numero} -> ID: {cotizacion_id}")
            except Exception as e:
                print(f"⚠️ Error buscando cotización por número: {e}")
        
        if cotizacion_id and not pc_id:  # Solo si es nuevo
            cot_query = """
                SELECT 
                    c.id, c.numero_cotizacion, c.fecha_creacion,
                    c.condicion_pago, c.direccion_entrega, c.tiempo_entrega,
                    c.vendedor, c.total,
                    cl.razon_social as cliente_razon_social,
                    cl.numero_documento as cliente_ruc,
                    cl.nombre_contacto as cliente_contacto
                FROM cotizaciones c
                LEFT JOIN clientes cl ON cl.id = c.cliente_id::integer
                WHERE c.id = %s
            """
            cot_data = db_query(cot_query, (cotizacion_id,))
            if cot_data:
                cot = cot_data[0]
                if not data.get('cliente'):
                    data['cliente'] = cot.get('cliente_razon_social')
                if not data.get('ruc'):
                    data['ruc'] = cot.get('cliente_ruc')
                if not data.get('cotizacion_numero'):
                    data['cotizacion_numero'] = cot.get('numero_cotizacion')
                if not data.get('monto') or data.get('monto') == 0:
                    data['monto'] = float(cot.get('total', 0))
                if not data.get('lugar_entrega'):
                    data['lugar_entrega'] = cot.get('direccion_entrega')
                if not data.get('condicion_pago'):
                    data['condicion_pago'] = cot.get('condicion_pago')
        
        # ============================================================
        # GENERAR NÚMERO SI ES NUEVO Y NO TIENE
        # ============================================================
        if not pc_id and not data.get('numero'):
            from datetime import datetime
            data['numero'] = f"PC-{datetime.now().strftime('%Y%m%d')}-{str(datetime.now().timestamp()).split('.')[0][-4:]}"
        
        # Fecha si no tiene
        if not data.get('fecha'):
            from datetime import datetime
            data['fecha'] = datetime.now().isoformat()
        
        # ============================================================
        # GUARDAR EL PC (INSERT O UPDATE)
        # ============================================================
        result = guardar_pc_db(data)
        
        if result:
            # Si tiene cotizacion_id y es NUEVO, actualizar estado de la cotización
            if cotizacion_id and not pc_id:
                try:
                    update_cot = """
                        UPDATE cotizaciones 
                        SET estado = 'Aceptada por Cliente', 
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING id
                    """
                    db_query(update_cot, (cotizacion_id,))
                except Exception as e:
                    print(f"⚠️ No se pudo actualizar estado de cotización: {e}")
            
            return jsonify({
                'success': True, 
                'message': 'PC guardado correctamente', 
                'data': result
            })
        
        return jsonify({'success': False, 'error': 'No se pudo guardar'}), 400
            
    except Exception as e:
        print(f"❌ Error en api_pedido_compra_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/despachos/listar', methods=['GET'])
@login_required
def api_despachos_listar():
    try:
        print("🚚 API DESPACHOS LISTAR - INICIO")
        
        query = """
            SELECT 
                d.id, d.numero, d.fecha, d.fecha_despacho, d.estado,
                d.pc_id, d.pc_numero, d.cotizacion_id, d.cotizacion_numero,
                d.cliente, d.ruc, d.comprobante, d.guia, d.origen, d.destino,
                d.transportista, d.observaciones, d.responsable,
                d.items_json, d.created_at, d.updated_at
            FROM despachos d
            ORDER BY d.id DESC
        """
        data = db_query(query)
        print(f"📊 Despachos encontrados: {len(data) if data else 0}")

        # ============================================================
        # 🔽 BUSCAR GUÍAS Y FACTURAS VINCULADAS POR "cotizacion_numero"
        #     (NO por RUC ni por ID) - últimos 4 registros de cada una
        # ============================================================
        cotizacion_numeros = list({
            row.get('cotizacion_numero') for row in data if row.get('cotizacion_numero')
        })

        guias_por_cotizacion = {}
        comprobantes_por_cotizacion = {}

        if cotizacion_numeros:
            try:
                guias_query = """
                    SELECT documento_asociado, numero
                    FROM guias_remision
                    WHERE documento_asociado = ANY(%s)
                    ORDER BY id DESC
                """
                guias_rows = db_query(guias_query, (cotizacion_numeros,))
                for g in guias_rows:
                    key = g.get('documento_asociado')
                    guias_por_cotizacion.setdefault(key, [])
                    if len(guias_por_cotizacion[key]) < 4:
                        guias_por_cotizacion[key].append(g.get('numero'))
            except Exception as e:
                print(f"⚠️ Error buscando guías vinculadas por cotizacion_numero: {e}")

            try:
                comprobantes_query = """
                    SELECT documento_asociado, serie, numero
                    FROM comprobantes
                    WHERE documento_asociado = ANY(%s)
                    ORDER BY id DESC
                """
                comp_rows = db_query(comprobantes_query, (cotizacion_numeros,))
                for c in comp_rows:
                    key = c.get('documento_asociado')
                    comprobantes_por_cotizacion.setdefault(key, [])
                    if len(comprobantes_por_cotizacion[key]) < 4:
                        comprobantes_por_cotizacion[key].append(f"{c.get('serie')}-{c.get('numero')}")
            except Exception as e:
                print(f"⚠️ Error buscando comprobantes vinculados por cotizacion_numero: {e}")

        # ============================================================
        # 🔽 FORMATEAR FECHAS CON HORA
        # ============================================================
        formatted_data = []
        for row in data:
            try:
                # Formatear fecha_despacho
                fecha_despacho = row.get('fecha_despacho')
                fecha_despacho_formateada = None

                if fecha_despacho:
                    try:
                        from datetime import datetime

                        if isinstance(fecha_despacho, str):
                            if 'T' in fecha_despacho:
                                dt = datetime.fromisoformat(fecha_despacho.replace('Z', '+00:00'))
                                fecha_despacho_formateada = dt.strftime('%d/%m/%Y %H:%M')
                            elif '-' in fecha_despacho and len(fecha_despacho) == 10:
                                dt = datetime.strptime(fecha_despacho, '%Y-%m-%d')
                                fecha_despacho_formateada = dt.strftime('%d/%m/%Y')
                            elif '/' in fecha_despacho:
                                fecha_despacho_formateada = fecha_despacho
                            else:
                                fecha_despacho_formateada = fecha_despacho
                        elif isinstance(fecha_despacho, datetime):
                            fecha_despacho_formateada = fecha_despacho.strftime('%d/%m/%Y %H:%M')
                        else:
                            fecha_despacho_formateada = str(fecha_despacho)
                    except Exception as e:
                        print(f"⚠️ Error formateando fecha: {e}")
                        fecha_despacho_formateada = str(fecha_despacho)

                created_at = row.get('created_at')
                created_at_formateada = None
                if created_at:
                    try:
                        from datetime import datetime
                        if isinstance(created_at, str) and 'T' in created_at:
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            created_at_formateada = dt.strftime('%d/%m/%Y %H:%M')
                        else:
                            created_at_formateada = str(created_at)
                    except:
                        created_at_formateada = str(created_at)

                # 🔽 Resolver guía(s) y comprobante(s) vinculados por cotizacion_numero
                cot_num = row.get('cotizacion_numero')
                guias_vinculadas = guias_por_cotizacion.get(cot_num, [])
                comprobantes_vinculados = comprobantes_por_cotizacion.get(cot_num, [])

                guia_display = ', '.join(guias_vinculadas) if guias_vinculadas else row.get('guia')
                comprobante_display = ', '.join(comprobantes_vinculados) if comprobantes_vinculados else row.get('comprobante')

                # 🔽 Manejar items_json de forma segura
                items = []
                items_json_raw = row.get('items_json')
                if items_json_raw:
                    try:
                        if isinstance(items_json_raw, str):
                            items = json.loads(items_json_raw)
                        elif isinstance(items_json_raw, (list, dict)):
                            items = items_json_raw
                        else:
                            items = []
                    except Exception as e:
                        print(f"⚠️ Error parseando items_json: {e}")
                        items = []

                formatted_data.append({
                    'id': row.get('id'),
                    'numero': row.get('numero'),
                    'fecha': row.get('fecha'),
                    'fecha_despacho': fecha_despacho_formateada or row.get('fecha_despacho'),
                    'estado': row.get('estado'),
                    'pc_id': row.get('pc_id'),
                    'pc_numero': row.get('pc_numero'),
                    'cotizacion_id': row.get('cotizacion_id'),
                    'cotizacion_numero': row.get('cotizacion_numero'),
                    'cliente': row.get('cliente'),
                    'ruc': row.get('ruc'),
                    'comprobante': comprobante_display,
                    'guia': guia_display,
                    'origen': row.get('origen'),
                    'destino': row.get('destino'),
                    'transportista': row.get('transportista'),
                    'observaciones': row.get('observaciones'),
                    'responsable': row.get('responsable'),
                    'items': items,  # ← Agregar items al objeto
                    'created_at': created_at_formateada,
                    'updated_at': row.get('updated_at')
                })
            except Exception as e:
                print(f"❌ Error procesando fila de despacho: {e}")
                import traceback
                traceback.print_exc()
                # Continuar con la siguiente fila en lugar de fallar todo
                continue

        print(f"✅ Despachos formateados: {len(formatted_data)}")
        return jsonify({'success': True, 'data': formatted_data})
        
    except Exception as e:
        print(f"❌ Error en api_despachos_listar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

    
@ventas_bp.route('/ventas/api/despachos/guardar', methods=['POST'])
@login_required
def api_despachos_guardar():
    try:
        data = request.get_json()
        usuario_id = session.get('usuario_id', 8)
        
        print("=" * 80)
        print("🚚 API DESPACHOS GUARDAR")
        print(f"  - PC ID: {data.get('pc_id')}")
        print(f"  - PC Número: {data.get('pc_numero')}")
        print(f"  - Items recibidos: {len(data.get('items', []))}")
        print("=" * 80)
        
        # Generar número si no tiene
        if not data.get('numero'):
            from datetime import datetime
            now = datetime.now()
            data['numero'] = f"DESP-{now.strftime('%Y%m%d')}-{str(now.timestamp()).split('.')[0][-4:]}"
        
        # Fecha si no tiene
        if not data.get('fecha'):
            from datetime import datetime
            data['fecha'] = datetime.now().isoformat()
        
        # ============================================================
        # PROCESAR FECHA DESPACHO CON HORA
        # ============================================================
        from datetime import datetime
        fecha_despacho = data.get('fecha_despacho')
        
        if fecha_despacho:
            try:
                if isinstance(fecha_despacho, str) and ' ' in fecha_despacho:
                    dt = datetime.strptime(fecha_despacho, '%Y-%m-%d %H:%M:%S')
                    fecha_despacho = dt.isoformat()
                elif isinstance(fecha_despacho, str) and 'T' in fecha_despacho:
                    pass
                elif isinstance(fecha_despacho, str) and '-' in fecha_despacho and len(fecha_despacho) == 10:
                    ahora = datetime.now()
                    dt = datetime(
                        int(fecha_despacho.split('-')[0]),
                        int(fecha_despacho.split('-')[1]),
                        int(fecha_despacho.split('-')[2]),
                        ahora.hour,
                        ahora.minute,
                        ahora.second
                    )
                    fecha_despacho = dt.isoformat()
                else:
                    fecha_despacho = datetime.now().isoformat()
            except Exception as e:
                print(f"⚠️ Error procesando fecha: {e}")
                fecha_despacho = datetime.now().isoformat()
        else:
            fecha_despacho = datetime.now().isoformat()
        
        print(f"📅 Fecha despacho FINAL: {fecha_despacho}")
        
        # ============================================================
        # GUARDAR ITEMS COMO JSON
        # ============================================================
        items_json = json.dumps(data.get('items', []))
        
        # ============================================================
        # GUARDAR DESPACHO CON ITEMS
        # ============================================================
        query = """
            INSERT INTO despachos (
                numero, fecha, fecha_despacho, estado,
                pc_id, pc_numero, cotizacion_id, cotizacion_numero,
                cliente, ruc, comprobante, guia, origen, destino,
                transportista, observaciones, responsable,
                items_json, creado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id, numero
        """
        
        params = (
            data.get('numero'),
            data.get('fecha'),
            fecha_despacho,
            data.get('estado', 'Pendiente despacho'),
            data.get('pc_id'),
            data.get('pc_numero'),
            data.get('cotizacion_id'),
            data.get('cotizacion_numero'),
            data.get('cliente') or '',
            data.get('ruc') or '',
            data.get('comprobante'),
            data.get('guia'),
            data.get('origen', 'ALM-SMP'),
            data.get('destino') or '',
            data.get('transportista'),
            data.get('observaciones') or '',
            data.get('responsable') or 'Hellen',
            items_json,  # 🔽 GUARDAR ITEMS
            data.get('creado_por') or 8
        )
        
        result = db_query(query, params)
        print(f"✅ Resultado: {result}")
        
        if result:
            return jsonify({'success': True, 'message': 'Despacho guardado', 'data': result})
        
        return jsonify({'success': False, 'error': 'No se pudo guardar'}), 400
            
    except Exception as e:
        print(f"❌ Error en api_despachos_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# DEVOLUCIONES - API
# ============================================================

@ventas_bp.route('/ventas/api/devoluciones/listar', methods=['GET'])
@login_required
def api_devoluciones_listar():
    try:
        data = obtener_devoluciones_db()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/devoluciones/guardar', methods=['POST'])
@login_required
def api_devoluciones_guardar():
    try:
        data = request.get_json()
        usuario_id = session.get('usuario_id', 8)
        data['creado_por'] = usuario_id
        
        if not data.get('numero'):
            data['numero'] = f"DEV-{datetime.now().strftime('%Y%m%d')}-{str(datetime.now().timestamp()).split('.')[0][-4:]}"
        
        result = guardar_devolucion_db(data)
        if result:
            return jsonify({'success': True, 'message': 'Devolución guardada', 'data': result})
        return jsonify({'success': False, 'error': 'No se pudo guardar'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# EXPORTAR DATOS
# ============================================================

@ventas_bp.route('/ventas/api/exportar/<tipo>', methods=['GET'])
@login_required
def api_exportar(tipo):
    try:
        return jsonify({'success': True, 'message': f'Exportación de {tipo} preparada'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# CONSULTAR SUNAT
# ============================================================

@ventas_bp.route('/ventas/api/sunat/consulta', methods=['GET'])
@login_required
def api_sunat_consulta():
    """Consultar RUC en SUNAT"""
    try:
        ruc = request.args.get('ruc', '').strip()
        
        if not ruc or len(ruc) != 11:
            return jsonify({'success': False, 'error': 'RUC inválido, debe tener 11 dígitos'}), 400
        
        # Primero, buscar en la base de datos
        cliente = buscar_cliente_por_ruc(ruc)
        
        if cliente:
            # Cliente encontrado en la base de datos
            return jsonify({
                'success': True,
                'encontrado': True,
                'origen': 'base_datos',
                'mensaje': '✅ Cliente encontrado en sistema',
                'data': {
                    'ruc': cliente.get('numero_documento'),
                    'razon_social': cliente.get('razon_social'),
                    'nombre_comercial': cliente.get('nombre_comercial'),
                    'direccion': cliente.get('direccion_fiscal'),
                    'telefono': cliente.get('telefono_contacto'),
                    'contacto': cliente.get('nombre_contacto'),
                    'email': cliente.get('email_contacto'),
                    'codigo_cliente': cliente.get('codigo_cliente'),
                    'tipo_documento': cliente.get('tipo_documento', 'RUC'),
                    'estado': cliente.get('estado', 'Activo')
                }
            })
        
        # Si no existe en BD, consultar SUNAT (simulado por ahora)
        # En producción, aquí iría la llamada a la API de SUNAT
        datos_sunat = {
            'ruc': ruc,
            'razon_social': f'EMPRESA CON RUC {ruc}',
            'nombre_comercial': f'EMPRESA {ruc[-4:]}',
            'direccion': 'Dirección fiscal consultada en SUNAT',
            'telefono': '',
            'contacto': '',
            'email': '',
            'estado': 'ACTIVO'
        }
        
        return jsonify({
            'success': True,
            'encontrado': False,
            'origen': 'sunat',
            'mensaje': '🌞 Cliente consultado en SUNAT - datos cargados',
            'data': datos_sunat
        })
        
    except Exception as e:
        print(f"❌ Error en api_sunat_consulta: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# DESPACHOS - ENDPOINTS ADICIONALES
# ============================================================

@ventas_bp.route('/ventas/api/despachos/<int:id>/toggle', methods=['PUT'])
@login_required
def api_despachos_toggle(id):
    """Cambia el estado de un despacho (ej: Pendiente -> Despachado)"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        # Validar que el estado sea válido
        estados_validos = ['Pendiente despacho', 'En preparación', 'Despachado', 'Entregado']
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido. Permitidos: {", ".join(estados_validos)}'}), 400
        
        query = """
            UPDATE despachos 
            SET estado = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado
        """
        result = db_query(query, (nuevo_estado, id))
        
        if result:
            return jsonify({
                'success': True, 
                'message': f'Despacho actualizado a {nuevo_estado}',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'Despacho no encontrado'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_despachos_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/ventas/api/despachos/<int:id>', methods=['DELETE'])
@login_required
def api_despachos_eliminar(id):
    """Elimina (anula) un despacho"""
    try:
        query = """
            UPDATE despachos 
            SET estado = 'Anulado', updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado
        """
        result = db_query(query, (id,))
        
        if result:
            return jsonify({'success': True, 'message': 'Despacho anulado', 'data': result[0]})
        
        return jsonify({'success': False, 'error': 'Despacho no encontrado'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_despachos_eliminar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/ventas/api/despachos/<int:id>', methods=['GET'])
@login_required
def api_despachos_obtener(id):
    """Obtiene un despacho por su ID"""
    try:
        query = """
            SELECT 
                id, numero, fecha, fecha_despacho, estado,
                pc_id, pc_numero, cotizacion_id, cotizacion_numero,
                cliente, ruc, comprobante, guia, origen, destino,
                transportista, observaciones, responsable,
                created_at, updated_at
            FROM despachos
            WHERE id = %s
        """
        result = db_query(query, (id,))
        
        if result:
            return jsonify({'success': True, 'data': result[0]})
        
        return jsonify({'success': False, 'error': 'Despacho no encontrado'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_despachos_obtener: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# PEDIDO COMPRA - ENDPOINTS ADICIONALES
# ============================================================

@ventas_bp.route('/ventas/api/pedido-compra/<int:id>/toggle', methods=['PUT'])
@login_required
def api_pedido_compra_toggle(id):
    """Cambia el estado de un pedido de compra"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        # 🔽 Actualizar la lista de estados válidos
        estados_validos = [
            'Pendiente', 
            'Recibido por correo', 
            'En revisión interna', 
            'Validado por Hellen', 
            'Listo para despacho', 
            'Anulado',
            'PC observado',        # ← Agregar este
            'PC conforme',          # ← Agregar este
            'Bloqueado'             # ← Agregar este
        ]
        
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido. Permitidos: {", ".join(estados_validos)}'}), 400
        
        query = """
            UPDATE pedido_compra_pc 
            SET estado = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado
        """
        result = db_query(query, (nuevo_estado, id))
        
        if result:
            return jsonify({
                'success': True, 
                'message': f'PC actualizado a {nuevo_estado}',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'PC no encontrado'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_pedido_compra_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# GUÍAS - ENDPOINTS ADICIONALES
# ============================================================

@ventas_bp.route('/ventas/api/guias/<int:id>/toggle', methods=['PUT'])
@login_required
def api_guias_toggle(id):
    """Cambia el estado de una guía"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        estados_validos = ['Borrador', 'Pendiente despacho', 'Emitida', 'Entregada', 'Anulada']
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido'}), 400
        
        query = """
            UPDATE guias_remision 
            SET estado_sunat = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado_sunat as estado
        """
        result = db_query(query, (nuevo_estado, id))
        
        if result:
            return jsonify({
                'success': True, 
                'message': f'Guía actualizada a {nuevo_estado}',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'Guía no encontrada'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_guias_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# COMPROBANTES - ENDPOINTS ADICIONALES
# ============================================================

@ventas_bp.route('/ventas/api/comprobantes/<int:id>/toggle', methods=['PUT'])
@login_required
def api_comprobantes_toggle(id):
    """Cambia el estado de un comprobante"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        estados_validos = ['Borrador', 'Emitido', 'Enviado', 'Pagado', 'Anulado']
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido'}), 400
        
        query = """
            UPDATE comprobantes 
            SET estado_sunat = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado_sunat as estado
        """
        result = db_query(query, (nuevo_estado, id))
        
        if result:
            return jsonify({
                'success': True, 
                'message': f'Comprobante actualizado a {nuevo_estado}',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'Comprobante no encontrado'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_comprobantes_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# NOTAS DE CRÉDITO - ENDPOINTS ADICIONALES
# ============================================================

@ventas_bp.route('/ventas/api/notas-credito/<int:id>/toggle', methods=['PUT'])
@login_required
def api_notas_credito_toggle(id):
    """Cambia el estado de una nota de crédito"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        estados_validos = ['Borrador', 'Emitida', 'Enviada', 'Aplicada', 'Anulada']
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido'}), 400
        
        query = """
            UPDATE notas_credito 
            SET estado = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado
        """
        result = db_query(query, (nuevo_estado, id))
        
        if result:
            return jsonify({
                'success': True, 
                'message': f'Nota de crédito actualizada a {nuevo_estado}',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'Nota de crédito no encontrada'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_notas_credito_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/ventas/api/notas-credito/<int:id>', methods=['GET'])
@login_required
def api_notas_credito_obtener(id):
    """Obtiene una nota de crédito específica por su ID"""
    try:
        query = """
            SELECT 
                id, serie, numero, fecha_emision, fecha_vencimiento,
                cliente_tipo_doc, cliente_numero_doc, cliente_nombre,
                cliente_direccion, cliente_email, cliente_telefono,
                comprobante_asociado, motivo, monto, observaciones,
                estado, creado_por, created_at, updated_at
            FROM notas_credito
            WHERE id = %s
        """
        result = db_query(query, (id,))
        if not result:
            return jsonify({'success': False, 'error': 'Nota de crédito no encontrada'}), 404

        return jsonify({'success': True, 'data': result[0]})
    except Exception as e:
        print(f"❌ Error en api_notas_credito_obtener: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# DEVOLUCIONES - ENDPOINTS ADICIONALES
# ============================================================

@ventas_bp.route('/ventas/api/devoluciones/<int:id>/toggle', methods=['PUT'])
@login_required
def api_devoluciones_toggle(id):
    """Cambia el estado de una devolución"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        estados_validos = ['Pendiente', 'En revisión', 'Aprobada', 'Rechazada', 'Procesada']
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido'}), 400
        
        query = """
            UPDATE devoluciones 
            SET estado = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado
        """
        result = db_query(query, (nuevo_estado, id))
        
        if result:
            return jsonify({
                'success': True, 
                'message': f'Devolución actualizada a {nuevo_estado}',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'Devolución no encontrada'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_devoluciones_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================

@ventas_bp.route('/ventas/api/cotizaciones/<int:id>/completa', methods=['GET'])
@login_required
def api_cotizaciones_obtener_completa(id):
    """Obtiene una cotización con sus productos para edición o para crear PC"""
    try:
        # Obtener cabecera
        query_cabecera = """
            SELECT 
                c.id, c.numero_cotizacion, c.fecha_creacion, c.estado,
                c.subtotal, c.igv, c.total, c.usuario_id, c.notas,
                c.forma_pago, c.tiempo_entrega, c.almacen, c.validez_oferta,
                c.codigo_cotizacion, c.correlativo, c.condicion_pago,
                c.direccion_entrega, c.requerimiento, c.nota_cotizacion,
                c.descuento_porcentaje, c.descuento_monto, c.descuento_tipo,
                c.contacto_cliente, c.telefono_cliente, c.email_cliente,
                c.seguimiento, c.motivo, c.transporte, c.parihuela, c.nota_interna,
                c.vendedor,
                cl.id as cliente_id,
                cl.razon_social as cliente_razon_social,
                cl.numero_documento as cliente_ruc,
                cl.nombre_comercial as cliente_nombre_comercial,
                cl.codigo_cliente as cod_cliente,
                cl.direccion_fiscal as cliente_direccion,
                cl.telefono_contacto as cliente_telefono,
                cl.nombre_contacto as cliente_contacto,
                cl.email_contacto as cliente_email
            FROM cotizaciones c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id::integer
            WHERE c.id = %s
        """
        cabecera = db_query(query_cabecera, (id,))
        
        if not cabecera:
            return jsonify({'success': False, 'error': 'Cotización no encontrada'}), 404
        
        # 🔽 OBTENER PRODUCTOS - VERIFICAR QUE ESTE QUERY FUNCIONE
        query_productos = """
            SELECT 
                d.id, d.producto_id, d.cantidad,
                d.precio_venta_unitario as valorVenta,
                d.subtotal_venta,
                d.descuento_porcentaje,
                d.precio_venta_con_descuento,
                d.subtotal_venta_con_descuento,
                d.costo_unitario,
                d.margen_porcentaje,
                p.codigo, 
                p.descripcion as producto, 
                p.descripcion_larga,
                p.modelo, 
                p.marca, 
                p.unidad as um, 
                p.stock,
                p.precio_unitario,
                p.costo_unitario as costo
            FROM cotizacion_detalle d
            LEFT JOIN productos p ON p.id = d.producto_id
            WHERE d.cotizacion_id = %s
        """
        productos = db_query(query_productos, (id,))
        
        print(f"📦 Productos encontrados: {len(productos) if productos else 0}")
        
        # Combinar datos
        result = dict(cabecera[0])
        
        # Asegurar nombres consistentes para el frontend
        result['cliente_razon_social'] = result.get('cliente_razon_social') or result.get('cliente_nombre_comercial') or f"Cliente {result.get('cliente_id', '')}"
        result['cliente_ruc'] = result.get('cliente_ruc') or str(result.get('cliente_id', ''))
        result['cod_cliente'] = result.get('cod_cliente') or f"CLI-{str(result.get('cliente_id', '')).zfill(6)}"
        result['cliente_direccion'] = result.get('cliente_direccion') or result.get('direccion_entrega', '')
        result['cliente_email'] = result.get('cliente_email') or result.get('email_cliente', '')
        result['cliente_telefono'] = result.get('cliente_telefono') or result.get('telefono_cliente', '')
        
        # 🔽 ASEGURAR QUE PRODUCTOS SE DEVUELVAN CORRECTAMENTE
        result['productos'] = []
        for p in (productos or []):
            result['productos'].append({
                'id': p.get('producto_id'),
                'codigo': p.get('codigo') or '',
                'producto': p.get('producto') or p.get('descripcion_larga') or 'Producto sin nombre',
                'descripcion': p.get('descripcion_larga') or p.get('producto') or '',
                'modelo': p.get('modelo') or '',
                'marca': p.get('marca') or '',
                'um': p.get('um') or 'NIU',
                'cantidad': float(p.get('cantidad') or 1),
                'valorVenta': float(p.get('valorVenta') or p.get('precio_unitario') or 0),
                'stock': int(p.get('stock') or 0),
                'costo_unitario': float(p.get('costo_unitario') or p.get('costo') or 0),
                'subtotal_venta': float(p.get('subtotal_venta') or 0),
                'descuento_porcentaje': float(p.get('descuento_porcentaje') or 0)
            })
        
        print(f"📦 Productos en respuesta: {len(result['productos'])}")
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f"❌ Error en api_cotizaciones_obtener_completa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/ventas/api/cotizaciones/<int:id>/duplicar', methods=['POST'])
@login_required
def api_cotizaciones_duplicar(id):
    """Duplica una cotización existente con nuevo número"""
    try:
        print(f"📋 Duplicando cotización ID: {id}")
        
        # 1. Obtener la cotización original con sus productos
        query_cabecera = """
            SELECT 
                c.cliente_id, c.estado, c.subtotal, c.igv, c.total,
                c.notas, c.forma_pago, c.tiempo_entrega, c.almacen, 
                c.validez_oferta, c.condicion_pago, c.direccion_entrega,
                c.requerimiento, c.nota_cotizacion, c.descuento_porcentaje,
                c.descuento_monto, c.descuento_tipo, c.contacto_cliente,
                c.telefono_cliente, c.email_cliente,
                cl.razon_social as cliente_razon_social,
                cl.numero_documento as cliente_ruc
            FROM cotizaciones c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id::integer
            WHERE c.id = %s
        """
        cabecera = db_query(query_cabecera, (id,))
        
        if not cabecera:
            return jsonify({'success': False, 'error': 'Cotización original no encontrada'}), 404
        
        # 2. Obtener los productos de la cotización original
        query_productos = """
            SELECT 
                d.producto_id, d.cantidad, d.costo_unitario,
                d.subtotal_costo, d.margen_porcentaje,
                d.precio_venta_unitario, d.subtotal_venta,
                d.descuento_porcentaje, d.precio_venta_con_descuento,
                d.subtotal_venta_con_descuento, d.descuento_total, d.margen_final,
                p.codigo, p.descripcion, p.marca, p.modelo, p.unidad,
                p.precio_unitario as valorVenta, p.stock
            FROM cotizacion_detalle d
            LEFT JOIN productos p ON p.id = d.producto_id
            WHERE d.cotizacion_id = %s
        """
        productos = db_query(query_productos, (id,))
        
        if not productos:
            return jsonify({'success': False, 'error': 'La cotización original no tiene productos'}), 400
        
        print(f"📦 Productos a duplicar: {len(productos)}")
        
        # 3. Generar nuevo número de cotización
        from datetime import datetime
        count_data = db_query("SELECT COUNT(*) as total FROM cotizaciones")
        count = count_data[0]['total'] + 1 if count_data else 1
        nuevo_numero = f"COT-{str(count).zfill(6)}"
        codigo = f"COT-{datetime.now().strftime('%Y%m%d')}-{str(count).zfill(4)}"
        
        usuario_id = session.get('usuario_id', 8)
        cliente_id = cabecera[0].get('cliente_id')
        
        print(f"📋 Nuevo número: {nuevo_numero}")
        print(f"👤 Usuario: {usuario_id}")
        print(f"🏢 Cliente ID: {cliente_id}")
        
        # 4. Insertar nueva cotización
        with db_tx() as conn:
            from psycopg2.extras import RealDictCursor
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Insertar cabecera
            cur.execute("""
                INSERT INTO cotizaciones (
                    numero_cotizacion, cliente_id, fecha_creacion, estado,
                    subtotal, igv, total, usuario_id, notas,
                    forma_pago, tiempo_entrega, almacen, validez_oferta,
                    codigo_cotizacion, correlativo, condicion_pago,
                    direccion_entrega, requerimiento, nota_cotizacion,
                    descuento_porcentaje, descuento_monto, descuento_tipo,
                    contacto_cliente, telefono_cliente, email_cliente
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id, numero_cotizacion
            """, (
                nuevo_numero,
                cliente_id,
                datetime.now().isoformat(),
                'Borrador',  # Siempre empieza como borrador
                float(cabecera[0].get('subtotal', 0)),
                float(cabecera[0].get('igv', 0)),
                float(cabecera[0].get('total', 0)),
                usuario_id,
                cabecera[0].get('notas', '') + ' (Duplicado)',
                cabecera[0].get('forma_pago'),
                cabecera[0].get('tiempo_entrega'),
                cabecera[0].get('almacen'),
                cabecera[0].get('validez_oferta'),
                codigo,
                count,
                cabecera[0].get('condicion_pago'),
                cabecera[0].get('direccion_entrega'),
                cabecera[0].get('requerimiento'),
                cabecera[0].get('nota_cotizacion', '') + ' (Duplicado)',
                float(cabecera[0].get('descuento_porcentaje', 0)),
                float(cabecera[0].get('descuento_monto', 0)),
                cabecera[0].get('descuento_tipo', 'porcentaje'),
                cabecera[0].get('contacto_cliente'),
                cabecera[0].get('telefono_cliente'),
                cabecera[0].get('email_cliente')
            ))
            
            result = cur.fetchone()
            nueva_cotizacion_id = result['id']
            nuevo_numero = result['numero_cotizacion']
            
            print(f"✅ Nueva cotización creada con ID: {nueva_cotizacion_id}")
            
            # 5. Insertar productos duplicados
            productos_guardados = 0
            for producto in productos:
                try:
                    producto_id = producto.get('producto_id')
                    if not producto_id:
                        continue
                    
                    cantidad = float(producto.get('cantidad', 1))
                    precio_venta = float(producto.get('precio_venta_unitario') or producto.get('valorVenta', 0))
                    costo_unitario = float(producto.get('costo_unitario', 0))
                    
                    cur.execute("""
                        INSERT INTO cotizacion_detalle (
                            cotizacion_id, producto_id, cantidad,
                            costo_unitario, subtotal_costo, margen_porcentaje,
                            precio_venta_unitario, subtotal_venta,
                            descuento_porcentaje, precio_venta_con_descuento,
                            subtotal_venta_con_descuento, descuento_total, margen_final
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        nueva_cotizacion_id,
                        producto_id,
                        cantidad,
                        costo_unitario,
                        cantidad * costo_unitario,
                        float(producto.get('margen_porcentaje', 0)),
                        precio_venta,
                        cantidad * precio_venta,
                        float(producto.get('descuento_porcentaje', 0)),
                        precio_venta,
                        cantidad * precio_venta,
                        0,
                        float(producto.get('margen_final', 0))
                    ))
                    productos_guardados += 1
                    
                except Exception as e:
                    print(f"⚠️ Error guardando producto {producto.get('codigo')}: {e}")
                    continue
            
            print(f"📊 Productos duplicados: {productos_guardados}")
            
            return jsonify({
                'success': True,
                'message': f'Cotización duplicada correctamente con {productos_guardados} productos',
                'data': {
                    'id': nueva_cotizacion_id,
                    'numero': nuevo_numero,
                    'productos_guardados': productos_guardados,
                    'estado': 'Borrador'
                }
            })
            
    except Exception as e:
        print(f"❌ Error en api_cotizaciones_duplicar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    


# ============================================================
# GENERAR PDF DE COTIZACIÓN
# ============================================================
@ventas_bp.route('/ventas/api/cotizaciones/<int:id>/pdf', methods=['GET'])
@login_required
def api_cotizaciones_generar_pdf(id):
    """Genera el PDF de una cotización"""
    try:
        print(f"📄 Generando PDF para cotización ID: {id}")
        
        # Obtener la cotización completa con sus productos
        from datetime import datetime
        
        # 1. Obtener cabecera de la cotización
        query_cabecera = """
            SELECT 
                c.id, c.numero_cotizacion, c.codigo_cotizacion,
                c.cliente_id, c.fecha_creacion, c.estado,
                c.subtotal, c.igv, c.total, c.notas,
                c.forma_pago, c.tiempo_entrega, c.almacen, c.validez_oferta,
                c.codigo_cotizacion, c.correlativo, c.condicion_pago,
                c.direccion_entrega, c.requerimiento, c.nota_cotizacion,
                c.descuento_porcentaje, c.descuento_monto, c.descuento_tipo,
                c.contacto_cliente, c.telefono_cliente, c.email_cliente,
                cl.id as cliente_id,
                cl.razon_social as cliente_razon_social,
                cl.numero_documento as cliente_ruc,
                cl.nombre_comercial as cliente_nombre_comercial,
                cl.codigo_cliente as cod_cliente,
                cl.direccion_fiscal as cliente_direccion,
                cl.telefono_contacto as cliente_telefono,
                cl.nombre_contacto as cliente_contacto,
                cl.email_contacto as cliente_email
            FROM cotizaciones c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id::integer
            WHERE c.id = %s
        """
        cabecera = db_query(query_cabecera, (id,))
        
        if not cabecera:
            return jsonify({'success': False, 'error': 'Cotización no encontrada'}), 404
        
        c = cabecera[0]
        
        # 2. Obtener productos de la cotización
        query_productos = """
            SELECT 
                d.id, d.producto_id, d.cantidad,
                d.precio_venta_unitario, d.subtotal_venta,
                d.descuento_porcentaje, d.precio_venta_con_descuento,
                d.subtotal_venta_con_descuento,
                p.codigo, p.descripcion, p.descripcion_larga,
                p.modelo, p.marca, p.unidad as um
            FROM cotizacion_detalle d
            LEFT JOIN productos p ON p.id = d.producto_id
            WHERE d.cotizacion_id = %s
        """
        productos = db_query(query_productos, (id,))
        
        # 3. Preparar datos para el PDF
        from decimal import Decimal
        
        # Datos del cliente
        cliente_razon_social = c.get('cliente_razon_social') or c.get('cliente_nombre_comercial') or 'Cliente'
        cliente_ruc = c.get('cliente_ruc') or '---'
        cliente_direccion = c.get('cliente_direccion') or c.get('direccion_entrega') or '---'
        
        # Calcular totales
        subtotal = float(c.get('subtotal', 0))
        igv = float(c.get('igv', 0))
        total = float(c.get('total', 0))
        descuento_monto = float(c.get('descuento_monto', 0))
        
        # Preparar productos
        productos_list = []
        for idx, p in enumerate(productos or [], 1):
            precio_unitario = float(p.get('precio_venta_unitario', 0))
            cantidad = float(p.get('cantidad', 1))
            subtotal_producto = float(p.get('subtotal_venta', 0))
            descuento_pct = float(p.get('descuento_porcentaje', 0))
            subtotal_desc = float(p.get('subtotal_venta_con_descuento', subtotal_producto))
            
            productos_list.append({
                'item': idx,
                'codigo': p.get('codigo', '---'),
                'descripcion': p.get('descripcion') or p.get('descripcion_larga') or 'Producto sin descripción',
                'modelo': p.get('modelo', ''),
                'marca': p.get('marca', ''),
                'unidad': p.get('um', 'NIU'),
                'cantidad': cantidad,
                'precio_venta_unitario': precio_unitario,
                'subtotal_venta': subtotal_producto,
                'descuento_porcentaje': descuento_pct,
                'subtotal_venta_desc': subtotal_desc
            })
        
        # Calcular si hay descuentos
        hay_descuentos = any(p.get('descuento_porcentaje', 0) > 0 for p in productos_list) or descuento_monto > 0
        
        # Fechas
        fecha_actual = datetime.now().strftime('%d/%m/%Y')
        hora_actual = datetime.now().strftime('%H:%M')
        
        # Obtener logo en base64
        import base64
        import os
        logo_base64 = None
        logo_path = 'logo-kcf.png'
        if os.path.exists(logo_path):
            try:
                with open(logo_path, 'rb') as f:
                    logo_base64 = base64.b64encode(f.read()).decode('utf-8')
            except:
                pass
        
        # 4. Preparar datos para el template
        datos_pdf = {
            'codigo_cotizacion': c.get('codigo_cotizacion') or c.get('numero_cotizacion', 'COT-000001'),
            'fecha_actual': fecha_actual,
            'hora_actual': hora_actual,
            'logo_base64': logo_base64,
            'cliente_razon_social': cliente_razon_social,
            'cliente_ruc': cliente_ruc,
            'cliente_direccion': cliente_direccion,
            'cliente_contacto': c.get('cliente_contacto') or c.get('contacto_cliente') or '---',
            'email_contacto_cliente': c.get('cliente_email') or c.get('email_cliente') or '---',
            'telefono_contacto': c.get('cliente_telefono') or c.get('telefono_cliente') or '---',
            'numero_requerimiento': c.get('requerimiento') or '---',
            'asesor_comercial': 'Helen Blas Príncipe',
            'email_contacto': 'ventas@kcfcorporacion.com',
            'telefono_contacto_user': '999932051',
            'condicion_pago': c.get('condicion_pago') or c.get('forma_pago') or 'Contado',
            'tiempo_entrega': c.get('tiempo_entrega') or '5 días hábiles',
            'direccion_entrega': c.get('direccion_entrega') or cliente_direccion,
            'validez_oferta': c.get('validez_oferta') or '15 días',
            'productos': productos_list,
            'total_subtotal_venta': subtotal,
            'total_descuento_subtotal': descuento_monto,
            'total_subtotal_venta_desc': subtotal - descuento_monto,
            'summary_igv': igv,
            'summary_total_venta': total,
            'hay_descuentos': hay_descuentos
        }
        
        print(f"📊 Datos preparados: {len(productos_list)} productos, Total: {total}")
        
        # 5. Generar PDF usando el template
        from flask import render_template_string
        
        # Cargar el template HTML (lo tienes en el archivo)
        template_html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cotización - KCF CORPORACION</title>
    <style>
        @page {
            size: A4;
            margin: 1.2cm;
        }
        * { text-rendering: optimizeLegibility; margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Cambria', Cochin, Georgia, Times, 'Times New Roman', serif; font-size: 10px; color: #1a1a1a; line-height: 1.3; background: white; }
        .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; border-bottom: 2px solid #D32F2F; padding-bottom: 10px; }
        .logo-section { flex: 1; }
        .logo { max-width: 140px; }
        .logo img { width: 100%; display: block; }
        .empresa-info { flex: 2; text-align: center; }
        .empresa-info h1 { color: #D32F2F; margin: 0 0 3px 0; font-size: 18px; font-weight: bold; }
        .empresa-info .slogan { font-size: 9px; color: #666; letter-spacing: 1px; }
        .cotizacion-info { flex: 1; text-align: right; background: #f8f9fa; padding: 6px 10px; border-radius: 6px; }
        .numero-cotizacion { font-size: 11px; font-weight: bold; color: #D32F2F; }
        .fecha, .hora { font-size: 8px; margin-top: 2px; color: #666; }
        .layout-principal { display: flex; gap: 15px; margin-bottom: 12px; }
        .seccion-cliente, .seccion-condiciones { flex: 1; background: #f8f9fa; padding: 8px 12px; border-radius: 6px; border: 1px solid #D32F2F; }
        .seccion-cliente h3, .seccion-condiciones h3 { color: #D32F2F; border-bottom: 1px solid #D32F2F; padding-bottom: 3px; font-size: 10px; margin-top: 0; margin-bottom: 6px; font-weight: bold; }
        .info-line, .condicion-line { display: flex; margin-bottom: 3px; font-size: 8.5px; }
        .info-label, .condicion-label { width: 90px; font-weight: bold; }
        .info-value, .condicion-value { flex: 1; }
        .texto-introductorio { margin: 10px 0; padding: 8px 15px; background: #FFF8E1; border-left: 4px solid #D32F2F; font-size: 9px; line-height: 1.4; text-align: justify; }
        .texto-introductorio .saludo { font-size: 10px; font-weight: bold; margin-bottom: 5px; }
        .tabla-productos { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 8.2px; }
        .tabla-productos th { background: #D32F2F; color: white; padding: 6px 4px; border: 1px solid #B71C1C; font-weight: bold; text-align: center; vertical-align: middle; }
        .tabla-productos td { padding: 5px 4px; border: 1px solid #ddd; vertical-align: middle; }
        .col-item { text-align: center; width: 35px; }
        .col-codigo { text-align: left; width: 70px; }
        .col-descripcion { text-align: left; }
        .col-modelo { text-align: left; width: 60px; }
        .col-marca { text-align: left; width: 65px; }
        .col-unidad-medida { text-align: center; width: 55px; }
        .col-cantidad { text-align: center; width: 45px; }
        .col-valor-unitario { text-align: right; width: 85px; }
        .col-valor-total { text-align: right; width: 90px; background: #FFF8E1; font-weight: bold; }
        .numero-formateado { text-align: right; font-family: 'Courier New', monospace; font-weight: 500; }
        .text-center { text-align: center; }
        .seccion-totales { width: 280px; margin-left: auto; margin-right: 0; margin-top: 8px; margin-bottom: 12px; border: 1px solid #D32F2F; padding: 8px 12px; border-radius: 6px; background: #f8f9fa; }
        .total-line { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; font-size: 9px; gap: 8px; }
        .total-line span:first-child { white-space: nowrap; }
        .total-line .numero-formateado { font-weight: 500; white-space: nowrap; }
        .total-final { border-top: 2px solid #D32F2F; padding-top: 5px; margin-top: 5px; font-weight: bold; font-size: 11px; color: #D32F2F; }
      .seccion-importante { 
    margin: 8px 0; 
    padding: 5px 10px; 
    background: transparent;   /* ← FONDO TRANSPARENTE */
    border: none;              /* ← SIN BORDE */
    border-radius: 4px; 
    font-size: 7.5px; 
    color: #333;               /* ← TEXTO MÁS OSCURO */
}
        .seccion-importante strong { color: #D32F2F; }
        .cuentas-bancarias { margin-top: 10px; padding: 8px 12px; background: #f8f9fa; border: 1px solid #D32F2F; border-radius: 6px; font-size: 7.5px; }
        .cuentas-bancarias h3 { color: #D32F2F; border-bottom: 1px solid #D32F2F; padding-bottom: 3px; font-size: 9px; margin-top: 0; margin-bottom: 6px; }
        .cuenta-line { margin-bottom: 2px; }
        .seccion-aclaratoria { margin-top: 12px; padding: 8px 16px; background: #eef2f5; border-radius: 8px; font-size: 8.5px; text-align: left; border-left: 4px solid #D32F2F; border-right: 1px solid #ccc; font-style: normal; line-height: 1.4; }
        .seccion-aclaratoria .titulo { font-weight: bold; font-size: 9px; margin-bottom: 4px; font-style: normal; color: #b85c00; text-align: left; }
        .seccion-aclaratoria .web-link { color: #D32F2F; text-decoration: none; font-weight: bold; }
        .seccion-contacto { margin-top: 14px; border-top: 2px solid #D32F2F; padding-top: 12px; text-align: left; font-size: 8.5px; }
        .contacto-nombre { font-size: 10.5px; font-weight: bold; color: #D32F2F; margin-bottom: 4px; }
        .contacto-line { margin-bottom: 2px; }
        .web-link { color: #D32F2F; text-decoration: none; }
        .fw-bold { font-weight: bold; }
        .bg-warning { background: #FFF8E1; }
        .seccion-totales, .cuentas-bancarias, .seccion-aclaratoria, .seccion-contacto { page-break-inside: avoid; break-inside: avoid; }
        .tabla-productos { page-break-inside: avoid; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-section">
            {% if logo_base64 %}
            <div class="logo">
                <img src="data:image/png;base64,{{ logo_base64 }}" alt="KCF Logo">
            </div>
            {% endif %}
        </div>
        <div class="empresa-info">
            <h1>KCF CORPORACION</h1>
            <div class="slogan">Soluciones industriales y comerciales</div>
        </div>
        <div class="cotizacion-info">
            <div class="numero-cotizacion"><strong>COTIZACIÓN N°:</strong> {{ codigo_cotizacion }}</div>
            <div class="fecha"><strong>Fecha:</strong> {{ fecha_actual }}</div>
            <div class="hora"><strong>Hora:</strong> {{ hora_actual|default('00:00') }}</div>
        </div>
    </div>
    <div class="layout-principal">
        <div class="seccion-cliente">
            <h3>INFORMACIÓN DEL CLIENTE</h3>
            <div class="info-line"><span class="info-label">Cliente:</span><span class="info-value">{{ cliente_razon_social }}</span></div>
            <div class="info-line"><span class="info-label">RUC / DNI:</span><span class="info-value">{{ cliente_ruc }}</span></div>
            <div class="info-line"><span class="info-label">Dirección:</span><span class="info-value">{{ cliente_direccion }}</span></div>
            <div class="info-line"><span class="info-label">Teléfono:</span><span class="info-value">{{ telefono_contacto|default('-') }}</span></div>
            <div class="info-line"><span class="info-label">Atención:</span><span class="info-value">{{ cliente_contacto|default('-') }}</span></div>
            <div class="info-line"><span class="info-label">Correo:</span><span class="info-value">{{ email_contacto_cliente|default('-') }}</span></div>
            <div class="info-line"><span class="info-label">N° Requerimiento:</span><span class="info-value">{{ numero_requerimiento|default('-') }}</span></div>
        </div>
        <div class="seccion-condiciones">
            <h3>CONDICIONES COMERCIALES</h3>
            <div class="condicion-line"><span class="condicion-label">Ejecutiva:</span><span class="condicion-value">{{ asesor_comercial }}</span></div>
            <div class="condicion-line"><span class="condicion-label">E-mail:</span><span class="condicion-value">{{ email_contacto }}</span></div>
            <div class="condicion-line"><span class="condicion-label">Teléfono:</span><span class="condicion-value">{{ telefono_contacto_user }}</span></div>
            <div class="condicion-line"><span class="condicion-label">Condición Pago:</span><span class="condicion-value">{{ condicion_pago }}</span></div>
            <div class="condicion-line"><span class="condicion-label">Tiempo Entrega:</span><span class="condicion-value">{{ tiempo_entrega }}</span></div>
            <div class="condicion-line"><span class="condicion-label">Dirección Entrega:</span><span class="condicion-value">{{ direccion_entrega }}</span></div>
            <div class="condicion-line"><span class="condicion-label">Validez Oferta:</span><span class="condicion-value">{{ validez_oferta }}</span></div>
        </div>
    </div>
    <div class="texto-introductorio">
        <div class="saludo">Estimado Cliente,</div>
        La presente tiene como objeto poner a su consideración nuestra oferta detallada según su requerimiento, agradecemos por confiar en nuestros productos:
    </div>
    <table class="tabla-productos">
        <thead>
            <tr>
                <th class="col-item">Item</th>
                <th class="col-codigo">Código Producto</th>
                <th class="col-descripcion">Descripción</th>
                <th class="col-modelo">Modelo</th>
                <th class="col-marca">Marca</th>
                <th class="col-unidad-medida">Unidad Medida</th>
                <th class="col-cantidad">Cantidad</th>
                <th class="col-valor-unitario">Valor Venta Unit S/.</th>
                <th class="col-valor-total">Valor Venta Total S/.</th>
            </tr>
        </thead>
        <tbody>
            {% if productos %}
                {% for producto in productos %}
                <tr>
                    <td class="text-center">{{ producto.item }}</td>
                    <td>{{ producto.codigo|default('-') }}</td>
                    <td class="descripcion">{{ producto.descripcion }}</td>
                    <td>{{ producto.modelo|default('-') }}</td>
                    <td>{{ producto.marca|default('-') }}</td>
                    <td class="text-center">{{ producto.unidad|default('Unid') }}</td>
                    <td class="text-center">{{ "%.0f"|format(producto.cantidad|default(0)) }}</td>
                    <td class="numero-formateado">{{ "%.2f"|format(producto.precio_venta_unitario|default(0)) }}</td>
                    <td class="numero-formateado fw-bold bg-warning">{{ "%.2f"|format(producto.subtotal_venta_desc|default(producto.subtotal_venta|default(0))) }}</td>
                </tr>
                {% endfor %}
            {% else %}
                <tr><td colspan="9" class="text-center" style="padding: 15px;">No hay productos registrados en esta cotización</td></tr>
            {% endif %}
        </tbody>
    </table>
    <div class="seccion-importante">
        <strong>Importante:</strong> Las imágenes son referenciales, colores, acabados o especificaciones técnicas deben ser verificadas en la descripción del producto.
    </div>
    <div class="seccion-totales">
        <div class="total-line"><span>Subtotal (S/):</span><span class="numero-formateado">S/ {{ "%.2f"|format(total_subtotal_venta|default(0)) }}</span></div>
        {% if hay_descuentos %}
        <div class="total-line"><span>Descuentos aplicados (S/):</span><span class="numero-formateado">- S/ {{ "%.2f"|format(total_descuento_subtotal|default(0)) }}</span></div>
        {% endif %}
        <div class="total-line"><span>Subtotal con descuento (S/):</span><span class="numero-formateado">S/ {{ "%.2f"|format(total_subtotal_venta_desc|default(0)) }}</span></div>
        <div class="total-line"><span>IGV (18%):</span><span class="numero-formateado">S/ {{ "%.2f"|format(summary_igv|default(0)) }}</span></div>
        <div class="total-line total-final"><span><strong>TOTAL A PAGAR:</strong></span><span class="numero-formateado"><strong>S/ {{ "%.2f"|format(summary_total_venta|default(0)) }}</strong></span></div>
    </div>
    <div class="cuentas-bancarias">
        <h3>CUENTAS BANCARIAS</h3>
        <div class="cuenta-line"><strong>BCP SOLES:</strong> 191-1889375-0-94 | N. 1911889375094</div>
        <div class="cuenta-line"><strong>BCP DÓLARES:</strong> 191-1881449-1-53 | N. 1911881449153</div>
        <div class="cuenta-line"><strong>BBVA SOLES:</strong> 0011-0335-01-00019126 | N. 00110335100019126</div>
        <div class="cuenta-line"><strong>BBVA DÓLARES:</strong> 0011-0335-01-00019134 | N. 00110335100019134</div>
    </div>
    <div class="seccion-aclaratoria">
        <div class="titulo">📌 Nota Aclaratoria</div>
        La validez de esta oferta está sujeta a la disponibilidad de inventario.<br>
        <strong>Este producto cuenta con el 10% de descuento aplicado directamente en el valor de venta.</strong><br>
        Para más información visítanos en 
        <a href="https://kcfcorporacion.com" class="web-link">www.kcfcorporacion.com</a>
    </div>
    <div class="seccion-contacto">
        <div class="contacto-nombre">Cordialmente,</div>
        <div class="contacto-nombre">HELLEN BLAS PRINCIPE</div>
        <div class="contacto-line">Ejecutiva Comercial</div>
        <div class="contacto-line">KCF CORPORACIÓN</div>
        <div class="contacto-line">📞 (+51) 999932051</div>
        <div class="contacto-line">✉ Ventas@kcfcorporacion.com</div>
        <div class="contacto-line">🌐 www.kcfcorporacion.com</div>
    </div>
</body>
</html>'''
        
        # Renderizar el HTML con los datos
        html_content = render_template_string(template_html, **datos_pdf)
        
        # 6. Generar el PDF con WeasyPrint
        from weasyprint import HTML
        import tempfile
        
        # Crear un archivo temporal para el PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name
        
        # Generar el PDF
        HTML(string=html_content).write_pdf(pdf_path)
        
        print(f"✅ PDF generado: {pdf_path}")
        
        # 7. Devolver el PDF como descarga
        from flask import send_file
        
        nombre_archivo = f"cotizacion_{c.get('codigo_cotizacion', 'sin_numero')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# routes.py - Agregar esta función al final

# ============================================================
# GENERAR PDF DE GUÍA CON PDFGenerator
# ============================================================

# ventas.py - Reemplazar la función generar_pdf_guia_endpoint

@ventas_bp.route('/ventas/api/guias/<int:guia_id>/pdf', methods=['GET'])
@login_required
def generar_pdf_guia_endpoint(guia_id):
    """Genera el PDF de una Guía de Remisión usando PDFGenerator"""
    try:
        print(f"📄 Generando PDF para guía ID: {guia_id}")
        
        # 1. Obtener la guía con TODOS los campos
        query = """
            SELECT 
                id, serie, numero, fecha_emision, fecha_traslado,
                ruc_remitente, remitente_nombre, remitente_direccion,
                remitente_ubigeo, ruc_destinatario, destinatario_nombre,
                destinatario_direccion, destinatario_ubigeo,
                modalidad_transporte, placa_vehiculo, conductor_dni,
                conductor_nombre, licencia_conductor, transportista_ruc,
                transportista_nombre, motivo_traslado, documento_asociado,
                orden_compra_cliente, factura,
                peso_total, items_json, observaciones, estado_sunat,
                creado_por, created_at, updated_at
            FROM guias_remision
            WHERE id = %s
        """
        guia_result = db_query(query, (guia_id,))
        
        if not guia_result:
            return jsonify({'error': 'Guía no encontrada'}), 404
        
        guia = guia_result[0]
        print(f"✅ Guía encontrada: {guia.get('serie')}-{guia.get('numero')}")
        
        # 2. Parsear items_json correctamente
        items = []
        items_json = guia.get('items_json')
        if items_json:
            try:
                if isinstance(items_json, str):
                    items = json.loads(items_json)
                elif isinstance(items_json, (list, dict)):
                    items = items_json
                else:
                    items = []
            except Exception as e:
                print(f"⚠️ Error parseando items_json: {e}")
                items = []
        
        print(f"📦 Items encontrados: {len(items)}")
        
        # 3. Obtener datos del cliente desde la base de datos (si es necesario)
        cliente_data = {}
        ruc_destinatario = guia.get('ruc_destinatario')
        if ruc_destinatario:
            try:
                query_cliente = """
                    SELECT razon_social, direccion_fiscal, telefono_contacto, 
                           nombre_contacto, email_contacto
                    FROM clientes 
                    WHERE numero_documento = %s
                    LIMIT 1
                """
                cliente_result = db_query(query_cliente, (ruc_destinatario,))
                if cliente_result:
                    cliente_data = cliente_result[0]
            except Exception as e:
                print(f"⚠️ Error obteniendo datos del cliente: {e}")
        
        # 4. Preparar datos para el PDFGenerator
        from pdf_generator import pdf_generator
        
        # Fechas
        fecha_emision = guia.get('fecha_emision')
        if fecha_emision and isinstance(fecha_emision, datetime):
            fecha_emision = fecha_emision.strftime('%d/%m/%Y %H:%M')
        elif fecha_emision and isinstance(fecha_emision, str):
            try:
                dt = datetime.fromisoformat(fecha_emision.replace('Z', '+00:00'))
                fecha_emision = dt.strftime('%d/%m/%Y %H:%M')
            except:
                pass
        
        fecha_traslado = guia.get('fecha_traslado')
        if fecha_traslado and isinstance(fecha_traslado, datetime):
            fecha_traslado = fecha_traslado.strftime('%d/%m/%Y')
        elif fecha_traslado and isinstance(fecha_traslado, str):
            try:
                dt = datetime.fromisoformat(fecha_traslado.replace('Z', '+00:00'))
                fecha_traslado = dt.strftime('%d/%m/%Y')
            except:
                pass
        
        # Formatear items para el PDF
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
                    'peso': float(item.get('peso_unitario', 0))
                })
            elif isinstance(item, list):
                # Si es un array [codigo, descripcion, marca, modelo, cantidad, um, peso]
                items_formateados.append({
                    'item': idx,
                    'codigo': item[0] if len(item) > 0 else '',
                    'descripcion': item[1] if len(item) > 1 else '',
                    'marca': item[2] if len(item) > 2 else '',
                    'modelo': item[3] if len(item) > 3 else '',
                    'unidad': item[4] if len(item) > 4 else 'NIU',
                    'cantidad': float(item[5]) if len(item) > 5 else 1,
                    'peso': float(item[6]) if len(item) > 6 else 0
                })
        
        # Datos completos para el PDF
        datos_guia = {
            'tipo_documento': 'guia_remision',
            'serie': guia.get('serie', 'T001'),
            'numero': guia.get('numero', ''),
            'orden_compra_cliente': guia.get('orden_compra_cliente', ''),  # <--- IMPORTANTE
    'factura': guia.get('factura', ''),                            # <--- IMPORTANTE
    'nro_cotizacion': guia.get('documento_asociado', guia.get('cotizacion_numero', '')), 
            # ============================================================
            # REMITENTE (DATOS FIJOS)
            # ============================================================
            'ruc_remitente': guia.get('ruc_remitente', '20602095704'),
            'remitente_nombre': guia.get('remitente_nombre', 'KCF CORPORACION E.I.R.L'),
            'remitente_direccion': guia.get('remitente_direccion', 'JR. LAS ALMENDRAS VERDES NRO. 284 URB. VIRGEN DEL ROSARIO LIMA - LIMA - SAN MARTIN DE PORRES'),
            'remitente_ubigeo': guia.get('remitente_ubigeo', '150139'),
            'remitente_departamento': 'LIMA',
            'remitente_provincia': 'LIMA',
            'remitente_distrito': 'SAN MARTIN DE PORRES',
            
            # ============================================================
            # DESTINATARIO (DATOS DEL CLIENTE)
            # ============================================================
            'ruc_destinatario': guia.get('ruc_destinatario', ''),
            'destinatario_nombre': guia.get('destinatario_nombre', ''),
            'destinatario_direccion': guia.get('destinatario_direccion', ''),
            'destinatario_ubigeo': guia.get('destinatario_ubigeo', ''),
            'destinatario_departamento': guia.get('destinatario_departamento', ''),
            'destinatario_provincia': guia.get('destinatario_provincia', ''),
            'destinatario_distrito': guia.get('destinatario_distrito', ''),
            
            # ============================================================
            # DATOS DE TRANSPORTE
            # ============================================================
            'modalidad_transporte': guia.get('modalidad_transporte', 'PRIVADO'),
            'transportista_nombre': guia.get('transportista_nombre', ''),
            'transportista_ruc': guia.get('transportista_ruc', ''),
            'transportista_direccion': guia.get('transportista_direccion', ''),
            
            # ============================================================
            # DATOS DEL VEHÍCULO Y CONDUCTOR
            # ============================================================
            'placa_vehiculo': guia.get('placa_vehiculo', ''),
            'conductor_nombre': guia.get('conductor_nombre', ''),
            'conductor_dni': guia.get('conductor_dni', ''),
            'licencia_conductor': guia.get('licencia_conductor', ''),
            'telefono_conductor': guia.get('telefono_conductor', ''),
            
            # ============================================================
            # DATOS DEL TRASLADO
            # ============================================================
            'fecha_emision': fecha_emision,
            'fecha_traslado': fecha_traslado,
            'fecha_inicio_traslado': fecha_traslado,
            'motivo_traslado': guia.get('motivo_traslado', '01'),
            'motivo_descripcion': obtener_descripcion_motivo(guia.get('motivo_traslado', '01')),
            'peso_total': float(guia.get('peso_total', 0)),
            'numero_bultos': int(guia.get('numero_bultos', 1)),
            'unidad_peso': guia.get('unidad_peso_bruto', 'KGM'),
            'orden_compra_cliente': guia.get('orden_compra_cliente', ''),
            'documento_asociado': guia.get('documento_asociado', ''),
            'orden_compra_cliente': guia.get('orden_compra_cliente',''),
            'factura': guia.get('factura',''),
            'observaciones': guia.get('observaciones', ''),
            
            # ============================================================
            # PRODUCTOS
            # ============================================================
            'items': items_formateados
        }
        
        # 5. Generar el PDF
        pdf_path = pdf_generator.generar_pdf_universal(datos_guia)
        
        if not pdf_path:
            return jsonify({'error': 'Error al generar el PDF'}), 500
        
        # 6. Retornar el PDF
        from flask import send_file
        filename = f"Guia_{guia.get('serie', 'T001')}_{guia.get('numero', '0001')}.pdf"
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error generando PDF de guía: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def obtener_descripcion_motivo(codigo):
    """Obtiene la descripción del motivo de traslado según el código SUNAT"""
    motivos = {
        '01': 'VENTA',
        '02': 'COMPRA',
        '03': 'TRASLADO ENTRE ESTABLECIMIENTOS',
        '04': 'CONSIGNACIÓN',
        '05': 'DEVOLUCIÓN',
        '06': 'EXPORTACIÓN',
        '07': 'IMPORTACIÓN',
        '08': 'DONACIÓN',
        '09': 'TRASLADO POR CUENTA DE TERCEROS',
        '10': 'TRASLADO PARA TRANSFORMACIÓN',
        '11': 'TRASLADO POR REPARACIÓN',
        '12': 'TRASLADO POR GARANTÍA',
        '13': 'TRASLADO POR CONSIGNACIÓN PARA VENTA',
        '14': 'TRASLADO POR CONSIGNACIÓN PARA TRANSFORMACIÓN',
        '15': 'TRASLADO POR CONSIGNACIÓN PARA REPARACIÓN',
        '16': 'TRASLADO POR DEVOLUCIÓN DE CONSIGNACIÓN',
        '17': 'TRASLADO POR PERMUTA',
        '18': 'TRASLADO POR COMODATO',
        '19': 'TRASLADO POR ARRENDAMIENTO',
        '20': 'TRASLADO POR ANTICIPO DE VENTA',
        '21': 'TRASLADO POR ANTICIPO DE COMPRA',
        '22': 'TRASLADO POR MAQUILA',
        '23': 'TRASLADO POR CONSIGNACIÓN PARA MAQUILA',
        '24': 'TRASLADO POR DEVOLUCIÓN DE MAQUILA'
    }
    return motivos.get(codigo, codigo)



@ventas_bp.route('/ventas/api/guias/<int:guia_id>/pdf/preview', methods=['GET'])
@login_required
def preview_pdf_guia(guia_id):
    """Vista previa del PDF de guía"""
    try:
        print(f"👁️ Vista previa PDF para guía ID: {guia_id}")
        
        # Usar la misma lógica que generar_pdf_guia_endpoint pero sin forzar descarga
        # Reutilizar la función de generación
        from flask import send_file
        from pdf_generator import pdf_generator
        
        query = """
            SELECT 
                id, serie, numero, fecha_emision, fecha_traslado,
                ruc_remitente, remitente_nombre, remitente_direccion,
                remitente_ubigeo, ruc_destinatario, destinatario_nombre,
                destinatario_direccion, destinatario_ubigeo,
                modalidad_transporte, placa_vehiculo, conductor_dni,
                conductor_nombre, licencia_conductor, transportista_ruc,
                transportista_nombre, motivo_traslado, documento_asociado,
                orden_compra_cliente, factura,
                peso_total, items_json, observaciones, estado_sunat,
                creado_por, created_at, updated_at
            FROM guias_remision
            WHERE id = %s
        """
        guia_result = db_query(query, (guia_id,))
        
        if not guia_result:
            return jsonify({'error': 'Guía no encontrada'}), 404
        
        guia = guia_result[0]
        
        # Preparar datos (misma lógica que la función principal)
        # ... (código para preparar datos_guia igual que arriba)
        
        # Generar PDF
        from pdf_generator import pdf_generator
        datos_guia = preparar_datos_guia_pdf(guia)  # Función auxiliar
        
        pdf_path = pdf_generator.generar_pdf_universal(datos_guia)
        
        if not pdf_path:
            return jsonify({'error': 'Error al generar el PDF'}), 500
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=False  # Vista previa
        )
        
    except Exception as e:
        print(f"❌ Error generando vista previa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def preparar_datos_guia_pdf(guia):
    """Prepara los datos de la guía para el PDFGenerator"""
    from datetime import datetime
    
    # Parsear items
    items = []
    items_json = guia.get('items_json')
    if items_json:
        try:
            if isinstance(items_json, str):
                items = json.loads(items_json)
            elif isinstance(items_json, (list, dict)):
                items = items_json
        except:
            items = []
    
    # Formatear items
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
                'peso': float(item.get('peso_unitario', 0))
            })
        elif isinstance(item, list):
            items_formateados.append({
                'item': idx,
                'codigo': item[0] if len(item) > 0 else '',
                'descripcion': item[1] if len(item) > 1 else '',
                'marca': item[2] if len(item) > 2 else '',
                'modelo': item[3] if len(item) > 3 else '',
                'unidad': item[4] if len(item) > 4 else 'NIU',
                'cantidad': float(item[5]) if len(item) > 5 else 1,
                'peso': float(item[6]) if len(item) > 6 else 0
            })
    
    # Fechas
    fecha_emision = guia.get('fecha_emision')
    if fecha_emision and isinstance(fecha_emision, datetime):
        fecha_emision = fecha_emision.strftime('%d/%m/%Y %H:%M')
    elif fecha_emision and isinstance(fecha_emision, str):
        try:
            dt = datetime.fromisoformat(fecha_emision.replace('Z', '+00:00'))
            fecha_emision = dt.strftime('%d/%m/%Y %H:%M')
        except:
            pass
    
    return {
        'tipo_documento': 'guia_remision',
        'serie': guia.get('serie', 'T001'),
        'numero': guia.get('numero', ''),
        'ruc_remitente': guia.get('ruc_remitente', '20602095704'),
        'remitente_nombre': guia.get('remitente_nombre', 'KCF CORPORACION E.I.R.L'),
        'remitente_direccion': guia.get('remitente_direccion', 'JR. LAS ALMENDRAS VERDES NRO. 284 URB. VIRGEN DEL ROSARIO LIMA - LIMA - SAN MARTIN DE PORRES'),
        'remitente_ubigeo': guia.get('remitente_ubigeo', '150139'),
        'ruc_destinatario': guia.get('ruc_destinatario', ''),
        'destinatario_nombre': guia.get('destinatario_nombre', ''),
        'destinatario_direccion': guia.get('destinatario_direccion', ''),
        'destinatario_ubigeo': guia.get('destinatario_ubigeo', ''),
        'modalidad_transporte': guia.get('modalidad_transporte', 'PRIVADO'),
        'transportista_nombre': guia.get('transportista_nombre', ''),
        'transportista_ruc': guia.get('transportista_ruc', ''),
        'placa_vehiculo': guia.get('placa_vehiculo', ''),
        'conductor_nombre': guia.get('conductor_nombre', ''),
        'conductor_dni': guia.get('conductor_dni', ''),
        'licencia_conductor': guia.get('licencia_conductor', ''),
        'fecha_emision': fecha_emision,
        'fecha_traslado': guia.get('fecha_traslado'),
        'motivo_traslado': guia.get('motivo_traslado', '01'),
        'peso_total': float(guia.get('peso_total', 0)),
        'numero_bultos': int(guia.get('numero_bultos', 1)),
        'unidad_peso': guia.get('unidad_peso_bruto', 'KGM'),
        'documento_asociado': guia.get('documento_asociado', ''),
        'orden_compra_cliente' : guia.get('orden_compra_cliente',''),
        'factura' : guia.get('factura',''),
        'observaciones': guia.get('observaciones', ''),
        'items': items_formateados
    }
# ============================================================
# CLIENTES - BUSCAR POR RUC (para ventas)
# ============================================================

@ventas_bp.route('/ventas/api/clientes/buscar', methods=['GET'])
@login_required
def api_clientes_buscar_por_ruc():
    """Busca un cliente por su RUC en la base de datos"""
    try:
        ruc = request.args.get('ruc', '').strip()
        
        if not ruc or len(ruc) != 11:
            return jsonify({'success': False, 'error': 'RUC inválido, debe tener 11 dígitos'}), 400
        
        # Usar la función de database.py
        from database import buscar_cliente_por_ruc
        
        cliente = buscar_cliente_por_ruc(ruc)
        
        if cliente:
            # Obtener contactos adicionales si es necesario
            contactos = db_query("""
                SELECT nombre_contacto, email, telefono, cargo, principal
                FROM clientes_contactos 
                WHERE cliente_id = %s
                ORDER BY principal DESC
            """, (cliente['id'],))
            
            # Obtener puntos de entrega
            puntos = db_query("""
                SELECT nombre_punto, direccion, condicion_pago, responsable, telefono_contacto, principal
                FROM clientes_puntos_entrega 
                WHERE cliente_id = %s
            """, (cliente['id'],))
            
            return jsonify({
                'success': True,
                'data': {
                    'id': cliente['id'],
                    'tipo_documento': cliente.get('tipo_documento', 'RUC'),
                    'numero_documento': cliente.get('numero_documento'),
                    'razon_social': cliente.get('razon_social'),
                    'nombre_comercial': cliente.get('nombre_comercial'),
                    'direccion_fiscal': cliente.get('direccion_fiscal'),
                    'codigo_cliente': cliente.get('codigo_cliente'),
                    'nombre_contacto': cliente.get('nombre_contacto'),
                    'telefono_contacto': cliente.get('telefono_contacto'),
                    'email_contacto': cliente.get('email_contacto'),
                    'estado': cliente.get('estado', 'Activo'),
                    'contactos': contactos,
                    'puntos_entrega': puntos
                }
            })
        
        return jsonify({'success': False, 'error': 'Cliente no encontrado'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_clientes_buscar_por_ruc: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 
        
@ventas_bp.route('/ventas/api/cotizaciones/buscar', methods=['GET'])
@login_required
def api_cotizaciones_buscar():
    """Busca cotizaciones por texto (N° cotización, RUC, razón social) para el buscador del modal PC"""
    try:
        q = request.args.get('q', '').strip()
        if not q or len(q) < 2:
            return jsonify({'success': True, 'data': []})
        
        # Buscar en la base de datos
        query = """
            SELECT 
                c.id, c.numero_cotizacion, c.fecha_creacion, c.estado,
                c.total, c.subtotal, c.igv, c.condicion_pago,
                c.direccion_entrega, c.tiempo_entrega, c.validez_oferta,
                c.vendedor,
                cl.id as cliente_id,
                cl.razon_social as cliente_razon_social,
                cl.numero_documento as cliente_ruc,
                cl.nombre_comercial as cliente_nombre_comercial,
                cl.codigo_cliente as cod_cliente,
                cl.direccion_fiscal as cliente_direccion,
                cl.telefono_contacto as cliente_telefono,
                cl.nombre_contacto as cliente_contacto,
                cl.email_contacto as cliente_email
            FROM cotizaciones c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id::integer
            WHERE c.estado != 'Anulada'
            AND (
                LOWER(c.numero_cotizacion) LIKE LOWER(%s) OR
                LOWER(cl.razon_social) LIKE LOWER(%s) OR
                LOWER(cl.numero_documento) LIKE LOWER(%s) OR
                LOWER(cl.nombre_comercial) LIKE LOWER(%s) OR
                LOWER(c.codigo_cotizacion) LIKE LOWER(%s)
            )
            ORDER BY c.fecha_creacion DESC
            LIMIT 20
        """
        search_pattern = f'%{q}%'
        results = db_query(query, (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern))
        
        # Formatear respuesta
        formatted_data = []
        for row in results:
            formatted_data.append({
                'id': row.get('id'),
                'numero': row.get('numero_cotizacion'),
                'fecha': row.get('fecha_creacion'),
                'estado': row.get('estado'),
                'total': float(row.get('total', 0)),
                'subtotal': float(row.get('subtotal', 0)),
                'igv': float(row.get('igv', 0)),
                'ruc': row.get('cliente_ruc'),
                'razon': row.get('cliente_razon_social') or row.get('cliente_nombre_comercial'),
                'cod_cliente': row.get('cod_cliente'),
                'direccion': row.get('cliente_direccion'),
                'telefono': row.get('cliente_telefono'),
                'contacto': row.get('cliente_contacto'),
                'email': row.get('cliente_email'),
                'condicion_pago': row.get('condicion_pago'),
                'direccion_entrega': row.get('direccion_entrega'),
                'tiempo_entrega': row.get('tiempo_entrega'),
                'validez_oferta': row.get('validez_oferta'),
                'vendedor': row.get('vendedor')
            })
        
        return jsonify({'success': True, 'data': formatted_data})
        
    except Exception as e:
        print(f"❌ Error en api_cotizaciones_buscar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ventas.py - Agregar al final del archivo

# ============================================================
# VALIDACIÓN DE PC - ENDPOINT
# ============================================================

@ventas_bp.route('/ventas/api/pedido-compra/<int:id>/validar', methods=['POST'])
@login_required
def api_pedido_compra_validar(id):
    """
    Valida un PC contra su cotización asociada.
    ⚠️ EL STOCK NO BLOQUEA - SOLO INFORMATIVO
    """
    try:
        data = request.get_json()
        print(f"🔍 Validando PC ID: {id}")
        
        # 1. Obtener el PC
        query_pc = """
            SELECT 
                id, numero, cliente, ruc, monto,
                cotizacion_id, cotizacion_numero,
                valida_precios, valida_cantidades, valida_stock,
                valida_entrega, valida_montos,
                valida_transporte, valida_margen, valida_vigencia,
                items_json, estado, req_compra
            FROM pedido_compra_pc
            WHERE id = %s
        """
        pc_result = db_query(query_pc, (id,))
        
        if not pc_result:
            return jsonify({'success': False, 'error': 'PC no encontrado'}), 404
        
        pc = pc_result[0]
        
        # 2. Obtener la cotización asociada
        cotizacion_id = pc.get('cotizacion_id')
        if not cotizacion_id:
            return jsonify({'success': False, 'error': 'PC no tiene cotización asociada'}), 400
        
        query_cot = """
            SELECT 
                c.id, c.numero_cotizacion, c.subtotal, c.total,
                c.condicion_pago, c.direccion_entrega, c.tiempo_entrega,
                c.transporte, c.margen, c.validez_oferta,
                cl.razon_social as cliente_razon_social,
                cl.numero_documento as cliente_ruc
            FROM cotizaciones c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id::integer
            WHERE c.id = %s
        """
        cot_result = db_query(query_cot, (cotizacion_id,))
        
        if not cot_result:
            return jsonify({'success': False, 'error': 'Cotización no encontrada'}), 404
        
        cotizacion = cot_result[0]
        
        # 3. Obtener items del PC
        pc_items = []
        if pc.get('items_json'):
            try:
                pc_items = json.loads(pc['items_json'])
            except:
                pc_items = []
        
        # 4. Obtener items de la cotización
        query_items_cot = """
            SELECT 
                d.producto_id, d.cantidad, d.precio_venta_unitario,
                p.codigo, p.descripcion, p.unidad,
                p.stock, p.precio_unitario
            FROM cotizacion_detalle d
            LEFT JOIN productos p ON p.id = d.producto_id
            WHERE d.cotizacion_id = %s
        """
        cot_items = db_query(query_items_cot, (cotizacion_id,))
        
        # 5. Realizar validaciones
        # ⚠️ STOCK NO BLOQUEA - solo informativo
        validaciones = {
            'precios': True,
            'cantidades': True,
            'stock': True,  # ← Se guarda pero NO bloquea
            'entrega': True,
            'moneda': True,
            'transporte': True,
            'margen': True,
            'vigencia': True
        }
        
        detalles_validacion = []
        stock_insuficiente = False
        productos_faltantes = []
        
        # Validar cada item
        for pc_item in pc_items:
            # Soporte para formato de lista o diccionario
            if isinstance(pc_item, dict):
                codigo = pc_item.get('codigo', '')
                cantidad_pc = float(pc_item.get('cantidad_pc', pc_item.get('cantidad', 0)))
                precio_pc = float(pc_item.get('precio_pc', pc_item.get('precio', 0)))
            else:
                codigo = pc_item[0] if len(pc_item) > 0 else ''
                cantidad_pc = float(pc_item[3]) if len(pc_item) > 3 else 0
                precio_pc = float(pc_item[5]) if len(pc_item) > 5 else 0
            
            # Buscar item correspondiente en cotización
            cot_item = next(
                (i for i in cot_items if i.get('codigo') == codigo),
                None
            )
            
            if cot_item:
                cantidad_cot = float(cot_item.get('cantidad', 0))
                precio_cot = float(cot_item.get('precio_venta_unitario', 0))
                stock = float(cot_item.get('stock', 0))
                
                # Validar cantidad
                if cantidad_pc != cantidad_cot:
                    validaciones['cantidades'] = False
                
                # Validar precio (tolerancia 5%)
                if precio_pc != 0 and precio_cot != 0:
                    diff_pct = abs(precio_pc - precio_cot) / precio_cot * 100
                    if diff_pct > 5:
                        validaciones['precios'] = False
                
                # ⚠️ STOCK: solo informativo, NO BLOQUEA
                if cantidad_pc > stock:
                    stock_insuficiente = True
                    productos_faltantes.append({
                        'codigo': codigo,
                        'producto': cot_item.get('descripcion', ''),
                        'stock': stock,
                        'requerido': cantidad_pc,
                        'faltante': cantidad_pc - stock
                    })
                    validaciones['stock'] = False
                
                detalles_validacion.append({
                    'codigo': codigo,
                    'producto': cot_item.get('descripcion', ''),
                    'cantidad_cot': cantidad_cot,
                    'cantidad_pc': cantidad_pc,
                    'precio_cot': precio_cot,
                    'precio_pc': precio_pc,
                    'stock': stock,
                    'faltante': max(cantidad_pc - stock, 0),
                    'validaciones': {
                        'cantidad': cantidad_pc == cantidad_cot,
                        'precio': abs(precio_pc - precio_cot) / precio_cot * 100 <= 5 if precio_cot != 0 else True,
                        'stock': cantidad_pc <= stock  # ← SOLO INFORMATIVO
                    }
                })
        
        # Validar entrega
        pc_entrega = pc.get('lugar_entrega') or pc.get('entrega') or ''
        cot_entrega = cotizacion.get('direccion_entrega') or ''
        if pc_entrega.strip().lower() != cot_entrega.strip().lower():
            validaciones['entrega'] = False
        
        # Validar transporte
        pc_transporte = pc.get('transporte') or ''
        cot_transporte = cotizacion.get('transporte') or ''
        if pc_transporte.strip().lower() != cot_transporte.strip().lower():
            validaciones['transporte'] = False
        
        # Validar moneda (si hay campo)
        pc_moneda = pc.get('moneda') or ''
        cot_moneda = cotizacion.get('moneda') or 'Soles (S/)'
        if pc_moneda and cot_moneda and pc_moneda.strip().lower() != cot_moneda.strip().lower():
            validaciones['moneda'] = False
        
        # Validar vigencia
        pc_vigencia = pc.get('vigencia') or ''
        cot_vigencia = cotizacion.get('validez_oferta') or ''
        if pc_vigencia and cot_vigencia and pc_vigencia.strip().lower() != cot_vigencia.strip().lower():
            validaciones['vigencia'] = False
        
        # 6. Determinar resultado final
        # ⚠️ STOCK NO BLOQUEA - solo informativo
        validaciones_para_estado = {
            'precios': validaciones['precios'],
            'cantidades': validaciones['cantidades'],
            'entrega': validaciones['entrega'],
            'moneda': validaciones['moneda'],
            'transporte': validaciones['transporte'],
            'margen': validaciones['margen'],
            'vigencia': validaciones['vigencia']
            # 'stock' NO incluido para bloqueo
        }
        
        todas_validas = all(validaciones_para_estado.values())
        
        if not todas_validas:
            estado = 'PC observado'
            req_compra = 'Bloqueado'
            mensaje = 'PC con observaciones - requiere corrección'
        else:
            # ✅ Todas las validaciones OK (excepto stock)
            estado = 'PC conforme'
            if stock_insuficiente:
                req_compra = 'Sí'  # Requiere compra por falta de stock
                mensaje = 'PC conforme - requiere compra por falta de stock'
            else:
                req_compra = 'No'
                mensaje = 'PC conforme - listo para despacho'
        
        # 7. Actualizar PC
        query_update = """
            UPDATE pedido_compra_pc 
            SET 
                estado = %s,
                req_compra = %s,
                valida_precios = %s,
                valida_cantidades = %s,
                valida_stock = %s,
                valida_entrega = %s,
                valida_montos = %s,
                valida_transporte = %s,
                valida_margen = %s,
                valida_vigencia = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado, req_compra
        """
        
        result = db_query(query_update, (
            estado,
            req_compra,
            validaciones['precios'],
            validaciones['cantidades'],
            validaciones['stock'],  # ← Se guarda para referencia
            validaciones['entrega'],
            validaciones['moneda'],
            validaciones['transporte'],
            validaciones['margen'],
            validaciones['vigencia'],
            id
        ))
        
        if result:
            return jsonify({
                'success': True,
                'message': mensaje,
                'data': {
                    'id': result[0]['id'],
                    'estado': estado,
                    'req_compra': req_compra,
                    'validaciones': validaciones,
                    'stock_insuficiente': stock_insuficiente,
                    'productos_faltantes': productos_faltantes,
                    'detalles': detalles_validacion,
                    'resumen': {
                        'total_items': len(detalles_validacion),
                        'ok': todas_validas,
                        'observaciones': [k for k, v in validaciones_para_estado.items() if not v],
                        'stock_ok': not stock_insuficiente
                    }
                }
            })
        
        return jsonify({'success': False, 'error': 'No se pudo actualizar'}), 400
        
    except Exception as e:
        print(f"❌ Error en api_pedido_compra_validar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/ventas/api/pedido-compra/<int:id>', methods=['GET'])
@login_required
def api_pedido_compra_obtener(id):
    """Obtiene un pedido de compra por su ID con items formateados"""
    try:
        query = """
            SELECT 
                id, numero, fecha, estado, cliente, ruc, monto,
                cotizacion_id, cotizacion_numero, correo_origen,
                fecha_recepcion, fecha_despacho, archivo_oc,
                observaciones, valida_precios, valida_cantidades,
                valida_stock, valida_entrega, valida_montos,
                valida_transporte, valida_margen, valida_vigencia,
                responsable, lugar_entrega, condicion_atencion,
                medio, entrega, req_compra, guia, factura,
                condicion_pago, vendedor, items_json,
                created_at, updated_at
            FROM pedido_compra_pc
            WHERE id = %s
        """
        result = db_query(query, (id,))
        
        if not result:
            return jsonify({'success': False, 'error': 'PC no encontrado'}), 404
        
        pc = result[0]
        
        # Parsear items_json correctamente
        items = []
        if pc.get('items_json'):
            try:
                raw_val = pc['items_json']
                # 🔧 CAMBIO: psycopg2 puede devolver jsonb ya parseado (lista/dict) o como string, según el driver
                raw_items = json.loads(raw_val) if isinstance(raw_val, str) else raw_val
                
                # Si es una lista de listas (formato antiguo), convertir a objetos
                if isinstance(raw_items, list) and len(raw_items) > 0:
                    if isinstance(raw_items[0], list):
                        # Formato: [[codigo, descripcion, marca, modelo, cant_cot, cant_pc, precio_cot, precio_pc, stock], ...]
                        for item in raw_items:
                            if len(item) >= 9:
                                items.append({
                                    'codigo': item[0] or '',
                                    'producto': item[1] or '',
                                    'marca': item[2] or '',
                                    'modelo': item[3] or '',
                                    'cantidad_cotizada': float(item[4] or 0),
                                    'cantidad_pc': float(item[5] or 1),
                                    'precio_cotizado': float(item[6] or 0),
                                    'precio_pc': float(item[7] or 0),
                                    'stock': float(item[8] or 0)
                                })
                            elif len(item) >= 7:
                                # Formato sin marca y modelo: [codigo, descripcion, cant_cot, cant_pc, precio_cot, precio_pc, stock]
                                items.append({
                                    'codigo': item[0] or '',
                                    'producto': item[1] or '',
                                    'marca': '',
                                    'modelo': '',
                                    'cantidad_cotizada': float(item[2] or 0),
                                    'cantidad_pc': float(item[3] or 1),
                                    'precio_cotizado': float(item[4] or 0),
                                    'precio_pc': float(item[5] or 0),
                                    'stock': float(item[6] or 0)
                                })
                            else:
                                # Mínimo: codigo y descripcion
                                items.append({
                                    'codigo': item[0] or '',
                                    'producto': item[1] or '',
                                    'marca': '',
                                    'modelo': '',
                                    'cantidad_cotizada': 0,
                                    'cantidad_pc': 1,
                                    'precio_cotizado': 0,
                                    'precio_pc': 0,
                                    'stock': 0
                                })
                    else:
                        # Ya es una lista de objetos
                        for item in raw_items:
                            if isinstance(item, dict):
                                items.append({
                                    'codigo': item.get('codigo', ''),
                                    'producto': item.get('producto', item.get('descripcion', '')),
                                    'marca': item.get('marca', ''),
                                    'modelo': item.get('modelo', ''),
                                    'cantidad_cotizada': float(item.get('cantidad_cotizada', item.get('cantidad_cot', 0))),
                                    'cantidad_pc': float(item.get('cantidad_pc', item.get('cantidad', 1))),
                                    'precio_cotizado': float(item.get('precio_cotizado', item.get('precio_cot', 0))),
                                    'precio_pc': float(item.get('precio_pc', item.get('precio', 0))),
                                    'stock': float(item.get('stock', 0))
                                })
            except Exception as e:
                print(f"⚠️ Error parseando items_json: {e}")
                items = []
        
        pc['items'] = items
        pc['items_json'] = None  # No devolver el JSON crudo
        
        return jsonify({'success': True, 'data': pc})
        
    except Exception as e:
        print(f"❌ Error en api_pedido_compra_obtener: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# Agregar esta función después de api_cotizaciones_generar_pdf

@ventas_bp.route('/ventas/api/cotizaciones/<int:id>/pdf/preview', methods=['GET'])
@login_required
def api_cotizaciones_preview_pdf(id):
    """Genera y muestra el PDF de una cotización en el navegador (vista previa)"""
    try:
        print(f"📄 Generando vista previa PDF para cotización ID: {id}")
        
        from datetime import datetime
        from flask import send_file, render_template_string
        from weasyprint import HTML
        
        # ============================================================
        # FUNCIÓN PARA OBTENER LOGO EN BASE64
        # ============================================================
        def obtener_logo_base64_para_pdf():
            import base64
            import os
            
            posibles_rutas = [
                os.path.join('templates', 'pdf', 'logo-kcf.png'),
                os.path.join('templates', 'logo-kcf.png'),
                os.path.join('static', 'img', 'logo-kcf.png'),
                os.path.join('static', 'logo-kcf.png'),
                'logo-kcf.png',
                os.path.join('app', 'static', 'img', 'logo-kcf.png'),
                os.path.join('app', 'static', 'logo-kcf.png'),
                os.path.join('static', 'images', 'logo-kcf.png'),
                os.path.join('templates', 'cotizacion_oc', 'logo-kcf.png'),
                os.path.join('..', 'static', 'img', 'logo-kcf.png'),
                os.path.join('..', 'static', 'logo-kcf.png'),
            ]
            
            for logo_path in posibles_rutas:
                if os.path.exists(logo_path):
                    try:
                        with open(logo_path, 'rb') as f:
                            logo_data = f.read()
                            logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                            print(f"✅ Logo cargado desde: {logo_path}")
                            return logo_base64
                    except Exception as e:
                        print(f"⚠️ Error leyendo {logo_path}: {e}")
                        continue
                else:
                    print(f"🔍 Logo no encontrado: {logo_path}")
            
            print("❌ No se encontró el logo en ninguna ruta")
            return None
        
        # 1. Obtener cabecera
        query_cabecera = """
            SELECT 
                c.id, c.numero_cotizacion, c.codigo_cotizacion,
                c.cliente_id, c.fecha_creacion, c.estado,
                c.subtotal, c.igv, c.total, c.notas,
                c.forma_pago, c.tiempo_entrega, c.almacen, c.validez_oferta,
                c.codigo_cotizacion, c.correlativo, c.condicion_pago,
                c.direccion_entrega, c.requerimiento, c.nota_cotizacion,
                c.descuento_porcentaje, c.descuento_monto, c.descuento_tipo,
                c.contacto_cliente, c.telefono_cliente, c.email_cliente,
                cl.id as cliente_id,
                cl.razon_social as cliente_razon_social,
                cl.numero_documento as cliente_ruc,
                cl.nombre_comercial as cliente_nombre_comercial,
                cl.codigo_cliente as cod_cliente,
                cl.direccion_fiscal as cliente_direccion,
                cl.telefono_contacto as cliente_telefono,
                cl.nombre_contacto as cliente_contacto,
                cl.email_contacto as cliente_email
            FROM cotizaciones c
            LEFT JOIN clientes cl ON cl.id = c.cliente_id::integer
            WHERE c.id = %s
        """
        cabecera = db_query(query_cabecera, (id,))
        
        if not cabecera:
            return jsonify({'success': False, 'error': 'Cotización no encontrada'}), 404
        
        c = cabecera[0]
        
        # 2. Obtener productos
        query_productos = """
            SELECT 
                d.id, d.producto_id, d.cantidad,
                d.precio_venta_unitario, d.subtotal_venta,
                d.descuento_porcentaje, d.precio_venta_con_descuento,
                d.subtotal_venta_con_descuento,
                p.codigo, p.descripcion, p.descripcion_larga,
                p.modelo, p.marca, p.unidad as um
            FROM cotizacion_detalle d
            LEFT JOIN productos p ON p.id = d.producto_id
            WHERE d.cotizacion_id = %s
        """
        productos = db_query(query_productos, (id,))
        
        # 3. Preparar datos
        cliente_razon_social = c.get('cliente_razon_social') or c.get('cliente_nombre_comercial') or 'Cliente'
        cliente_ruc = c.get('cliente_ruc') or '---'
        cliente_direccion = c.get('cliente_direccion') or c.get('direccion_entrega') or '---'
        
        subtotal = float(c.get('subtotal', 0))
        igv = float(c.get('igv', 0))
        total = float(c.get('total', 0))
        descuento_monto = float(c.get('descuento_monto', 0))
        
        productos_list = []
        for idx, p in enumerate(productos or [], 1):
            precio_unitario = float(p.get('precio_venta_unitario', 0))
            cantidad = float(p.get('cantidad', 1))
            subtotal_producto = float(p.get('subtotal_venta', 0))
            descuento_pct = float(p.get('descuento_porcentaje', 0))
            subtotal_desc = float(p.get('subtotal_venta_con_descuento', subtotal_producto))
            
            productos_list.append({
                'item': idx,
                'codigo': p.get('codigo', '---'),
                'descripcion': p.get('descripcion') or p.get('descripcion_larga') or 'Producto sin descripción',
                'modelo': p.get('modelo', ''),
                'marca': p.get('marca', ''),
                'unidad': p.get('um', 'NIU'),
                'cantidad': cantidad,
                'precio_venta_unitario': precio_unitario,
                'subtotal_venta': subtotal_producto,
                'descuento_porcentaje': descuento_pct,
                'subtotal_venta_desc': subtotal_desc
            })
        
        hay_descuentos = any(p.get('descuento_porcentaje', 0) > 0 for p in productos_list) or descuento_monto > 0
        
        fecha_actual = datetime.now().strftime('%d/%m/%Y')
        hora_actual = datetime.now().strftime('%H:%M')
        
        logo_base64 = obtener_logo_base64_para_pdf()
        print(f"📷 Logo cargado: {'Sí' if logo_base64 else 'No'}")
        
        datos_pdf = {
            'codigo_cotizacion': c.get('codigo_cotizacion') or c.get('numero_cotizacion', 'COT-000001'),
            'fecha_actual': fecha_actual,
            'hora_actual': hora_actual,
            'logo_base64': logo_base64,
            'cliente_razon_social': cliente_razon_social,
            'cliente_ruc': cliente_ruc,
            'cliente_direccion': cliente_direccion,
            'cliente_contacto': c.get('cliente_contacto') or c.get('contacto_cliente') or '---',
            'email_contacto_cliente': c.get('cliente_email') or c.get('email_cliente') or '---',
            'telefono_contacto': c.get('cliente_telefono') or c.get('telefono_cliente') or '---',
            'numero_requerimiento': c.get('requerimiento') or '---',
            'asesor_comercial': 'Helen Blas Príncipe',
            'email_contacto': 'ventas@kcfcorporacion.com',
            'telefono_contacto_user': '999932051',
            'condicion_pago': c.get('condicion_pago') or c.get('forma_pago') or 'Contado',
            'tiempo_entrega': c.get('tiempo_entrega') or '5 días hábiles',
            'direccion_entrega': c.get('direccion_entrega') or cliente_direccion,
            'validez_oferta': c.get('validez_oferta') or '15 días',
            'productos': productos_list,
            'total_subtotal_venta': subtotal,
            'total_descuento_subtotal': descuento_monto,
            'total_subtotal_venta_desc': subtotal - descuento_monto,
            'summary_igv': igv,
            'summary_total_venta': total,
            'hay_descuentos': hay_descuentos
        }
        
        # 4. Template HTML CON TONOS ROJOS MÁS SUAVES
        template_html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cotización - KCF CORPORACION E.I.R.L</title>
    <style>
        @page {
            size: A4;
            margin: 1.2cm;
        }
        * { text-rendering: optimizeLegibility; margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Cambria', Cochin, Georgia, Times, 'Times New Roman', serif; 
            font-size: 10px; 
            color: #1a1a1a; 
            line-height: 1.3; 
            background: white; 
        }
        
        /* ============================================================
           COLORES SUAVES
           ============================================================ */
        .color-rojo { color: #C62828; }
        .color-rojo-claro { color: #E57373; }
        .bg-rojo-claro { background: #FFF5F5; }
        .border-rojo-claro { border-color: #E57373; }
        .border-rojo { border-color: #C62828; }
        
        /* ============================================================
           HEADER
           ============================================================ */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
            border-bottom: 2px solid #C62828;
            padding-bottom: 10px;
        }
        .logo-section { flex: 1; }
        .logo { max-width: 140px; }
        .logo img { width: 100%; display: block; }
        .empresa-info { flex: 2; text-align: center; }
        .empresa-info h1 { 
            color: #C62828; 
            margin: 0 0 3px 0; 
            font-size: 18px; 
            font-weight: bold; 
        }
        .empresa-info .slogan { 
            font-size: 9px; 
            color: #666; 
            letter-spacing: 1px; 
        }
        .empresa-info .ruc-text { 
            font-size: 8px; 
            color: #888; 
            font-weight: bold; 
            margin-top: 2px; 
        }
        
        /* ============================================================
           COTIZACIÓN INFO
           ============================================================ */
        .cotizacion-info {
            flex: 1;
            text-align: right;
            background: #FFF5F5;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid #E57373;
        }
        .cotizacion-info .numero-linea {
            font-size: 11px;
            font-weight: bold;
            color: #C62828;
            white-space: nowrap;
        }
        .cotizacion-info .fecha, 
        .cotizacion-info .hora {
            font-size: 8px;
            margin-top: 2px;
            color: #666;
        }
        
        /* ============================================================
           SECCIONES CLIENTE Y CONDICIONES
           ============================================================ */
        .layout-principal { display: flex; gap: 15px; margin-bottom: 12px; }
        .seccion-cliente, .seccion-condiciones { 
            flex: 1; 
            background: #FFF5F5; 
            padding: 8px 12px; 
            border-radius: 6px; 
            border: 1px solid #E57373; 
        }
        .seccion-cliente h3, .seccion-condiciones h3 { 
            color: #C62828; 
            border-bottom: 1px solid #E57373; 
            padding-bottom: 3px; 
            font-size: 10px; 
            margin-top: 0; 
            margin-bottom: 6px; 
            font-weight: bold; 
        }
        .info-line, .condicion-line { 
            display: flex; 
            margin-bottom: 3px; 
            font-size: 8.5px; 
        }
        .info-label, .condicion-label { 
            width: 90px; 
            font-weight: bold; 
            color: #555;
        }
        .info-value, .condicion-value { flex: 1; }
        
        /* ============================================================
           TEXTO INTRODUCTORIO
           ============================================================ */
        .texto-introductorio { 
            margin: 10px 0; 
            padding: 8px 15px; 
            background: #FFF8F0; 
            border-left: 4px solid #C62828; 
            font-size: 9px; 
            line-height: 1.4; 
            text-align: justify; 
        }
        .texto-introductorio .saludo { 
            font-size: 10px; 
            font-weight: bold; 
            margin-bottom: 5px; 
            color: #C62828;
        }
        
        /* ============================================================
           TABLA DE PRODUCTOS
           ============================================================ */
        .tabla-productos { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 10px 0; 
            font-size: 8.2px; 
        }
        .tabla-productos th { 
            background: #C62828; 
            color: white; 
            padding: 6px 4px; 
            border: 1px solid #A52A2A; 
            font-weight: bold; 
            text-align: center; 
            vertical-align: middle; 
        }
        .tabla-productos td { 
            padding: 5px 4px; 
            border: 1px solid #ddd; 
            vertical-align: middle; 
        }
        .tabla-productos tr:nth-child(even) td {
            background: #FFF9F9;
        }
        
        .col-item { text-align: center; width: 35px; }
        .col-codigo { text-align: left; width: 70px; }
        .col-descripcion { text-align: left; }
        .col-modelo { text-align: left; width: 60px; }
        .col-marca { text-align: left; width: 65px; }
        .col-unidad-medida { text-align: center; width: 55px; }
        .col-cantidad { text-align: center; width: 45px; }
        .col-valor-unitario { text-align: right; width: 85px; }
        .col-valor-total { 
            text-align: right; 
            width: 90px; 
            background: #FFF0E0; 
            font-weight: bold; 
            color: #C62828;
        }
        
        .numero-formateado { 
            text-align: right; 
            font-family: 'Courier New', monospace; 
            font-weight: 500; 
        }
        .text-center { text-align: center; }
        
        /* ============================================================
           TOTALES
           ============================================================ */
        .seccion-totales { 
            width: 280px; 
            margin-left: auto; 
            margin-right: 0; 
            margin-top: 8px; 
            margin-bottom: 12px; 
            border: 1px solid #E57373; 
            padding: 8px 12px; 
            border-radius: 6px; 
            background: #FFF5F5; 
        }
        .total-line { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 5px; 
            font-size: 9px; 
            gap: 8px; 
        }
        .total-line span:first-child { white-space: nowrap; color: #555; }
        .total-line .numero-formateado { 
            font-weight: 500; 
            white-space: nowrap; 
        }
        .total-final { 
            border-top: 2px solid #C62828; 
            padding-top: 5px; 
            margin-top: 5px; 
            font-weight: bold; 
            font-size: 11px; 
            color: #C62828; 
        }
        
        /* ============================================================
           IMPORTANTE
           ============================================================ */
        .seccion-importante { 
            margin: 8px 0; 
            padding: 5px 10px; 
            background: transparent;
            border: none;
            border-radius: 4px; 
            font-size: 7.5px; 
            color: #555; 
        }
        .seccion-importante strong { color: #C62828; }
        
        /* ============================================================
           CUENTAS BANCARIAS
           ============================================================ */
        .cuentas-bancarias { 
            margin-top: 10px; 
            padding: 8px 12px; 
            background: #FFF5F5; 
            border: 1px solid #E57373; 
            border-radius: 6px; 
            font-size: 7.5px; 
        }
        .cuentas-bancarias h3 { 
            color: #C62828; 
            border-bottom: 1px solid #E57373; 
            padding-bottom: 3px; 
            font-size: 9px; 
            margin-top: 0; 
            margin-bottom: 6px; 
        }
        .cuenta-line { margin-bottom: 2px; }
        
        /* ============================================================
           NOTA ACLARATORIA
           ============================================================ */
        .seccion-aclaratoria { 
            margin-top: 12px; 
            padding: 8px 16px; 
            background: #FFF8F0; 
            border-radius: 8px; 
            font-size: 8.5px; 
            text-align: left; 
            border-left: 4px solid #C62828; 
            border-right: 1px solid #F0E0D0; 
            font-style: normal; 
            line-height: 1.4; 
        }
        .seccion-aclaratoria .titulo { 
            font-weight: bold; 
            font-size: 9px; 
            margin-bottom: 4px; 
            font-style: normal; 
            color: #A0522D; 
            text-align: left; 
        }
        .seccion-aclaratoria .web-link { 
            color: #C62828; 
            text-decoration: none; 
            font-weight: bold; 
        }
        
        /* ============================================================
           CONTACTO
           ============================================================ */
        .seccion-contacto { 
            margin-top: 14px; 
            border-top: 2px solid #C62828; 
            padding-top: 12px; 
            text-align: left; 
            font-size: 8.5px; 
        }
        .contacto-nombre { 
            font-size: 10.5px; 
            font-weight: bold; 
            color: #C62828; 
            margin-bottom: 4px; 
        }
        .contacto-line { margin-bottom: 2px; }
        .web-link { color: #C62828; text-decoration: none; }
        .fw-bold { font-weight: bold; }
        .bg-warning { background: #FFF0E0; }
        
        /* Evitar saltos de página */
        .seccion-totales, .cuentas-bancarias, .seccion-aclaratoria, .seccion-contacto { 
            page-break-inside: avoid; 
            break-inside: avoid; 
        }
        .tabla-productos { page-break-inside: avoid; }
    </style>
</head>
<body>
    <!-- HEADER -->
    <div class="header">
        <div class="logo-section">
            {% if logo_base64 %}
            <div class="logo">
                <img src="data:image/png;base64,{{ logo_base64 }}" alt="KCF Logo">
            </div>
            {% endif %}
        </div>
        <div class="empresa-info">
            <h1>KCF CORPORACION E.I.R.L</h1>
            <div class="slogan">Soluciones integrales en abastecimientos</div>
            <div class="ruc-text">RUC: 20602095704</div>
        </div>
        <div class="cotizacion-info">
            <div class="numero-linea"><strong>COTIZACIÓN N°:</strong> {{ codigo_cotizacion }}</div>
            <div class="fecha"><strong>Fecha:</strong> {{ fecha_actual }}</div>
            <div class="hora"><strong>Hora:</strong> {{ hora_actual|default('00:00') }}</div>
        </div>
    </div>

    <!-- CLIENTE Y CONDICIONES -->
    <div class="layout-principal">
        <div class="seccion-cliente">
            <h3>INFORMACIÓN DEL CLIENTE</h3>
            <div class="info-line"><span class="info-label">Cliente:</span><span class="info-value">{{ cliente_razon_social }}</span></div>
            <div class="info-line"><span class="info-label">RUC / DNI:</span><span class="info-value">{{ cliente_ruc }}</span></div>
            <div class="info-line"><span class="info-label">Dirección:</span><span class="info-value">{{ cliente_direccion }}</span></div>
            <div class="info-line"><span class="info-label">Teléfono:</span><span class="info-value">{{ telefono_contacto|default('-') }}</span></div>
            <div class="info-line"><span class="info-label">Atención:</span><span class="info-value">{{ cliente_contacto|default('-') }}</span></div>
            <div class="info-line"><span class="info-label">Correo:</span><span class="info-value">{{ email_contacto_cliente|default('-') }}</span></div>
            <div class="info-line"><span class="info-label">N° Requerimiento:</span><span class="info-value">{{ numero_requerimiento|default('-') }}</span></div>
        </div>
        <div class="seccion-condiciones">
            <h3>CONDICIONES COMERCIALES</h3>
            <div class="condicion-line"><span class="condicion-label">Ejecutiva:</span><span class="condicion-value">{{ asesor_comercial }}</span></div>
            <div class="condicion-line"><span class="condicion-label">E-mail:</span><span class="condicion-value">{{ email_contacto }}</span></div>
            <div class="condicion-line"><span class="condicion-label">Teléfono:</span><span class="condicion-value">{{ telefono_contacto_user }}</span></div>
            <div class="condicion-line"><span class="condicion-label">Condición Pago:</span><span class="condicion-value">{{ condicion_pago }}</span></div>
            <div class="condicion-line"><span class="condicion-label">Tiempo Entrega:</span><span class="condicion-value">{{ tiempo_entrega }}</span></div>
            <div class="condicion-line"><span class="condicion-label">Dirección Entrega:</span><span class="condicion-value">{{ direccion_entrega }}</span></div>
            <div class="condicion-line"><span class="condicion-label">Validez Oferta:</span><span class="condicion-value">{{ validez_oferta }}</span></div>
        </div>
    </div>

    <!-- TEXTO INTRODUCTORIO -->
    <div class="texto-introductorio">
        <div class="saludo">Estimado Cliente,</div>
        La presente tiene como objeto poner a su consideración nuestra oferta detallada según su requerimiento, agradecemos por confiar en nuestros productos:
    </div>

    <!-- TABLA DE PRODUCTOS -->
    <table class="tabla-productos">
        <thead>
            <tr>
                <th class="col-item">Item</th>
                <th class="col-codigo">Código Producto</th>
                <th class="col-descripcion">Descripción</th>
                <th class="col-modelo">Modelo</th>
                <th class="col-marca">Marca</th>
                <th class="col-unidad-medida">Unidad Medida</th>
                <th class="col-cantidad">Cantidad</th>
                <th class="col-valor-unitario">Valor Venta Unit S/.</th>
                <th class="col-valor-total">Valor Venta Total S/.</th>
            </tr>
        </thead>
        <tbody>
            {% if productos %}
                {% for producto in productos %}
                <tr>
                    <td class="text-center">{{ producto.item }}</td>
                    <td>{{ producto.codigo|default('-') }}</td>
                    <td class="descripcion">{{ producto.descripcion }}</td>
                    <td>{{ producto.modelo|default('-') }}</td>
                    <td>{{ producto.marca|default('-') }}</td>
                    <td class="text-center">{{ producto.unidad|default('Unid') }}</td>
                    <td class="text-center">{{ "%.0f"|format(producto.cantidad|default(0)) }}</td>
                    <td class="numero-formateado">{{ "%.2f"|format(producto.precio_venta_unitario|default(0)) }}</td>
                    <td class="numero-formateado fw-bold bg-warning">{{ "%.2f"|format(producto.subtotal_venta_desc|default(producto.subtotal_venta|default(0))) }}</td>
                </tr>
                {% endfor %}
            {% else %}
                <tr><td colspan="9" class="text-center" style="padding: 15px;">No hay productos registrados en esta cotización</td></tr>
            {% endif %}
        </tbody>
    </table>

    <!-- IMPORTANTE -->
    <div class="seccion-importante">
        <strong>Importante:</strong> Las imágenes son referenciales, colores, acabados o especificaciones técnicas deben ser verificadas en la descripción del producto.
    </div>

    <!-- TOTALES -->
    <div class="seccion-totales">
        <div class="total-line"><span>Subtotal (S/):</span><span class="numero-formateado">S/ {{ "%.2f"|format(total_subtotal_venta|default(0)) }}</span></div>
        {% if hay_descuentos %}
        <div class="total-line"><span>Descuentos aplicados (S/):</span><span class="numero-formateado">- S/ {{ "%.2f"|format(total_descuento_subtotal|default(0)) }}</span></div>
        {% endif %}
        <div class="total-line"><span>Subtotal con descuento (S/):</span><span class="numero-formateado">S/ {{ "%.2f"|format(total_subtotal_venta_desc|default(0)) }}</span></div>
        <div class="total-line"><span>IGV (18%):</span><span class="numero-formateado">S/ {{ "%.2f"|format(summary_igv|default(0)) }}</span></div>
        <div class="total-line total-final"><span><strong>TOTAL A PAGAR:</strong></span><span class="numero-formateado"><strong>S/ {{ "%.2f"|format(summary_total_venta|default(0)) }}</strong></span></div>
    </div>

    <!-- CUENTAS BANCARIAS -->
    <div class="cuentas-bancarias">
        <h3>CUENTAS BANCARIAS</h3>
        <div class="cuenta-line"><strong>BCP SOLES:</strong> 191-1889375-0-94 | N. 1911889375094</div>
        <div class="cuenta-line"><strong>BCP DÓLARES:</strong> 191-1881449-1-53 | N. 1911881449153</div>
        <div class="cuenta-line"><strong>BBVA SOLES:</strong> 0011-0335-01-00019126 | N. 00110335100019126</div>
        <div class="cuenta-line"><strong>BBVA DÓLARES:</strong> 0011-0335-01-00019134 | N. 00110335100019134</div>
    </div>

    <!-- NOTA ACLARATORIA -->
    <div class="seccion-aclaratoria">
        <div class="titulo">📌 Nota Aclaratoria</div>
        La validez de esta oferta está sujeta a la disponibilidad de inventario.<br>
        <strong>Este producto cuenta con el 10% de descuento aplicado directamente en el valor de venta.</strong><br>
        Para más información visítanos en 
        <a href="https://kcfcorporacion.com" class="web-link">www.kcfcorporacion.com</a>
    </div>

    <!-- CONTACTO -->
    <div class="seccion-contacto">
        <div class="contacto-nombre">Cordialmente,</div>
        <div class="contacto-nombre">HELLEN BLAS PRINCIPE</div>
        <div class="contacto-line">Ejecutiva Comercial</div>
        <div class="contacto-line">KCF CORPORACIÓN</div>
        <div class="contacto-line">📞 (+51) 999932051</div>
        <div class="contacto-line">✉ Ventas@kcfcorporacion.com</div>
        <div class="contacto-line">🌐 www.kcfcorporacion.com</div>
    </div>

</body>
</html>'''
        
        html_content = render_template_string(template_html, **datos_pdf)
        
        # 5. Generar PDF en memoria
        import io
        pdf_buffer = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)
        
        nombre_archivo = f"cotizacion_{c.get('codigo_cotizacion', 'sin_numero')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=False,
            download_name=nombre_archivo,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"❌ Error generando vista previa PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/pedido-compra/<int:id>', methods=['DELETE'])
@login_required
def api_pedido_compra_eliminar(id):
    """Elimina físicamente un pedido de compra de la base de datos"""
    try:
        print(f"🗑️ Eliminando físicamente PC ID: {id}")
        
        # Verificar que el PC existe
        query_check = "SELECT id, numero, estado FROM pedido_compra_pc WHERE id = %s"
        result_check = db_query(query_check, (id,))
        
        if not result_check:
            return jsonify({'success': False, 'error': 'PC no encontrado'}), 404
        
        pc = result_check[0]
        estado = pc.get('estado')
        
        # Opcional: Permitir eliminar solo si está anulado
        # Si quieres permitir eliminar cualquier PC, comenta esta validación
        if estado != 'Anulado':
            return jsonify({
                'success': False, 
                'error': f'Solo se pueden eliminar PCs en estado "Anulado". Estado actual: {estado}'
            }), 400
        
        # Eliminar el PC
        query_delete = "DELETE FROM pedido_compra_pc WHERE id = %s RETURNING id"
        result_delete = db_query(query_delete, (id,))
        
        if result_delete:
            return jsonify({
                'success': True, 
                'message': f'PC eliminado correctamente',
                'data': {'id': id}
            })
        
        return jsonify({'success': False, 'error': 'No se pudo eliminar el PC'}), 400
        
    except Exception as e:
        print(f"❌ Error en api_pedido_compra_eliminar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

def obtener_despacho_por_id_db(despacho_id):
    """Obtiene un despacho con sus items desde el PC asociado"""
    try:
        query = """
            SELECT 
                d.id, d.numero, d.fecha, d.fecha_despacho, d.estado,
                d.pc_id, d.pc_numero, d.cotizacion_id, d.cotizacion_numero,
                d.cliente, d.ruc, d.comprobante, d.guia, d.origen, d.destino,
                d.transportista, d.observaciones, d.responsable,
                p.items_json as pc_items
            FROM despachos d
            LEFT JOIN pedido_compra_pc p ON p.id = d.pc_id
            WHERE d.id = %s
        """
        result = db_query(query, (despacho_id,))
        
        if result:
            despacho = result[0]
            # Obtener items del PC si existen
            if despacho.get('pc_items'):
                try:
                    despacho['items'] = json.loads(despacho['pc_items'])
                except:
                    despacho['items'] = []
            else:
                despacho['items'] = []
            return despacho
        
        return None
    except Exception as e:
        print(f"❌ Error en obtener_despacho_por_id_db: {e}")
        return None


# ============================================================
# GENERAR PDF DE COMPROBANTE (FACTURA / BOLETA)
# ============================================================

@ventas_bp.route('/ventas/api/comprobantes/<int:comp_id>/pdf', methods=['GET'])
@login_required
def generar_pdf_comprobante(comp_id):
    """Genera el PDF de un comprobante (Factura o Boleta)"""
    try:
        print(f"📄 Generando PDF para comprobante ID: {comp_id}")
        
        # Obtener el comprobante
        query = """
            SELECT 
                id, tipo_comprobante, serie, numero, fecha_emision,
                moneda, cliente_tipo_doc, cliente_numero_doc,
                cliente_nombre, cliente_direccion, cliente_email,
                cliente_telefono, subtotal, igv, total,
                items_json, observaciones, estado_sunat,
                creado_por
            FROM comprobantes
            WHERE id = %s
        """
        comp_result = db_query(query, (comp_id,))
        
        if not comp_result:
            return jsonify({'error': 'Comprobante no encontrado'}), 404
        
        comp = comp_result[0]
        print(f"✅ Comprobante encontrado: {comp.get('serie')}-{comp.get('numero')}")
        
        # Preparar datos para el PDFGenerator
        from pdf_generator import pdf_generator
        
        items = []
        try:
            if comp.get('items_json'):
                items = json.loads(comp.get('items_json'))
        except:
            items = []
        
        datos_comprobante = {
            'tipo_documento': 'comprobante',
            'tipo': comp.get('tipo_comprobante', 'FACTURA'),
            'serie': comp.get('serie', 'F001'),
            'numero': comp.get('numero', ''),
            'fecha_emision': comp.get('fecha_emision'),
            'moneda': comp.get('moneda', 'S/'),
            'condicion_pago': 'Contado',
            'ruc': comp.get('cliente_numero_doc', ''),
            'cliente': comp.get('cliente_nombre', ''),
            'direccion': comp.get('cliente_direccion', ''),
            'telefono': comp.get('cliente_telefono', ''),
            'email': comp.get('cliente_email', ''),
            'subtotal': float(comp.get('subtotal', 0)),
            'igv': float(comp.get('igv', 0)),
            'total': float(comp.get('total', 0)),
            'observaciones': comp.get('observaciones', ''),
            'items': items
        }
        
        # Generar el PDF
        pdf_path = pdf_generator.generar_pdf_universal(datos_comprobante)
        
        if not pdf_path:
            return jsonify({'error': 'Error al generar el PDF'}), 500
        
        # Retornar el PDF
        from flask import send_file
        filename = f"{comp.get('tipo_comprobante', 'FACTURA')}_{comp.get('serie', 'F001')}_{comp.get('numero', '0001')}.pdf"
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error generando PDF de comprobante: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@ventas_bp.route('/ventas/api/comprobantes/<int:comp_id>/pdf/preview', methods=['GET'])
@login_required
def preview_pdf_comprobante(comp_id):
    """Vista previa del PDF de comprobante"""
    try:
        print(f"👁️ Vista previa PDF para comprobante ID: {comp_id}")
        
        query = """
            SELECT 
                id, tipo_comprobante, serie, numero, fecha_emision,
                moneda, cliente_tipo_doc, cliente_numero_doc,
                cliente_nombre, cliente_direccion, cliente_email,
                cliente_telefono, subtotal, igv, total,
                items_json, observaciones, estado_sunat
            FROM comprobantes
            WHERE id = %s
        """
        comp_result = db_query(query, (comp_id,))
        
        if not comp_result:
            return jsonify({'error': 'Comprobante no encontrado'}), 404
        
        comp = comp_result[0]
        
        from pdf_generator import pdf_generator
        
        items = []
        try:
            if comp.get('items_json'):
                items = json.loads(comp.get('items_json'))
        except:
            items = []
        
        datos_comprobante = {
            'tipo_documento': 'comprobante',
            'tipo': comp.get('tipo_comprobante', 'FACTURA'),
            'serie': comp.get('serie', 'F001'),
            'numero': comp.get('numero', ''),
            'fecha_emision': comp.get('fecha_emision'),
            'moneda': comp.get('moneda', 'S/'),
            'condicion_pago': 'Contado',
            'ruc': comp.get('cliente_numero_doc', ''),
            'cliente': comp.get('cliente_nombre', ''),
            'direccion': comp.get('cliente_direccion', ''),
            'telefono': comp.get('cliente_telefono', ''),
            'email': comp.get('cliente_email', ''),
            'subtotal': float(comp.get('subtotal', 0)),
            'igv': float(comp.get('igv', 0)),
            'total': float(comp.get('total', 0)),
            'observaciones': comp.get('observaciones', ''),
            'items': items
        }
        
        pdf_path = pdf_generator.generar_pdf_universal(datos_comprobante)
        
        if not pdf_path:
            return jsonify({'error': 'Error al generar el PDF'}), 500
        
        from flask import send_file
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=False
        )
        
    except Exception as e:
        print(f"❌ Error generando vista previa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================================
# TRANSPORTISTAS - API (integrado en ventas)
# ============================================================

@ventas_bp.route('/ventas/api/transportistas/listar', methods=['GET'])
@login_required
def api_transportistas_listar():
    """Listar todos los transportistas para usar en ventas"""
    try:
        print("🔍 Listando transportistas...")
        
        query = """
            SELECT 
                id, nombre_completo, dni, placa, 
                medidas, licencia, telefono, peso_carga, tipo,
                activo, created_at, updated_at
            FROM transportistas
            WHERE activo = true
            ORDER BY nombre_completo
        """
        result = db_query(query)
        print(f"✅ {len(result)} transportistas encontrados")
        
        # Formatear los datos para el frontend
        formatted_data = []
        for row in result:
            formatted_data.append({
                'id': row.get('id'),
                'nombre_completo': row.get('nombre_completo') or '',
                'dni': row.get('dni') or '',
                'placa': row.get('placa') or '',
                'medidas': row.get('medidas') or '',
                'licencia': row.get('licencia') or '',
                'telefono': row.get('telefono') or '',
                'peso_carga': row.get('peso_carga') or '',
                'tipo': row.get('tipo') or 'conductor',
                'activo': row.get('activo', True)
            })
        
        return jsonify({'success': True, 'data': formatted_data})
        
    except Exception as e:
        print(f"❌ Error en api_transportistas_listar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/ventas/api/transportistas/<int:id>', methods=['GET'])
@login_required
def api_transportistas_obtener(id):
    """Obtener un transportista por ID"""
    try:
        query = """
            SELECT 
                id, nombre_completo, dni, placa, 
                medidas, licencia, telefono, peso_carga, tipo,
                activo
            FROM transportistas
            WHERE id = %s AND activo = true
        """
        result = db_query(query, (id,))
        if result:
            row = result[0]
            return jsonify({
                'success': True, 
                'data': {
                    'id': row.get('id'),
                    'nombre_completo': row.get('nombre_completo') or '',
                    'dni': row.get('dni') or '',
                    'placa': row.get('placa') or '',
                    'medidas': row.get('medidas') or '',
                    'licencia': row.get('licencia') or '',
                    'telefono': row.get('telefono') or '',
                    'peso_carga': row.get('peso_carga') or '',
                    'tipo': row.get('tipo') or 'conductor'
                }
            })
        return jsonify({'success': False, 'error': 'Transportista no encontrado'}), 404
    except Exception as e:
        print(f"❌ Error en api_transportistas_obtener: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/ventas/api/transportistas/guardar', methods=['POST'])
@login_required
def api_transportistas_guardar():
    """Guardar un nuevo transportista desde ventas"""
    try:
        data = request.get_json()
        usuario_id = session.get('usuario_id', 8)
        
        print(f"📦 Guardando transportista desde ventas: {data}")
        
        query = """
            INSERT INTO transportistas (
                nombre_completo, dni, placa, 
                medidas, licencia, telefono, peso_carga, tipo,
                activo, creado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """
        params = (
            data.get('nombre_completo', '').strip(),
            data.get('dni', '').strip(),
            data.get('placa', '').strip().upper(),
            data.get('medidas', '').strip(),
            data.get('licencia', '').strip(),
            data.get('telefono', '').strip(),
            data.get('peso_carga', '').strip(),
            data.get('tipo', 'conductor'),
            True,
            usuario_id
        )
        
        result = db_query(query, params)
        print(f"✅ Resultado: {result}")
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Transportista guardado correctamente',
                'data': {'id': result[0]['id']}
            })
        return jsonify({'success': False, 'error': 'No se pudo guardar'}), 400
        
    except Exception as e:
        print(f"❌ Error en api_transportistas_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



@ventas_bp.route('/api/cotizaciones/eliminadas', methods=['GET'])
@login_required
def api_cotizaciones_eliminadas():
    """Obtiene el historial de cotizaciones eliminadas/anuladas"""
    try:
        print("🔍 Consultando cotizaciones eliminadas...")
        
        # ✅ CON JOIN CON LA COLUMNA CORRECTA
        query = """
            SELECT 
                ce.id,
                ce.cotizacion_id_original,
                ce.numero_cotizacion as numero,
                ce.cliente_razon_social as cliente,
                ce.cliente_ruc as ruc,
                ce.motivo_eliminacion as motivo,
                ce.eliminado_en as fecha_eliminacion,
                ce.eliminado_por,
                ce.total,
                ce.estado_anterior as estado,
                u.nombre_completo as usuario_elimino
            FROM cotizaciones_eliminadas ce
            LEFT JOIN usuarios u ON u.id = ce.eliminado_por
            ORDER BY ce.eliminado_en DESC
        """
        
        eliminadas = db_query(query)
        
        print(f"📊 {len(eliminadas)} cotizaciones eliminadas encontradas")
        
        # Formatear fechas
        for item in eliminadas:
            if item.get('fecha_eliminacion'):
                if hasattr(item['fecha_eliminacion'], 'strftime'):
                    item['fecha_eliminacion'] = item['fecha_eliminacion'].strftime('%d/%m/%Y %H:%M')
            
            # Si no tiene usuario, poner 'Sistema'
            if not item.get('usuario_elimino'):
                item['usuario_elimino'] = 'Sistema'
        
        return jsonify({
            'success': True,
            'data': eliminadas,
            'total': len(eliminadas)
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo cotizaciones eliminadas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@ventas_bp.route('/ventas/api/transportistas/buscar', methods=['GET'])
@login_required
def api_transportistas_buscar():
    """Buscar transportistas por texto (nombre, dni, placa)"""
    try:
        q = request.args.get('q', '').strip()
        if not q or len(q) < 2:
            return jsonify({'success': True, 'data': []})
        
        search_pattern = f'%{q}%'
        query = """
            SELECT 
                id, nombre_completo, dni, placa, 
                medidas, licencia, telefono, peso_carga, tipo
            FROM transportistas
            WHERE activo = true
            AND (
                LOWER(nombre_completo) LIKE LOWER(%s) OR
                LOWER(dni) LIKE LOWER(%s) OR
                LOWER(placa) LIKE LOWER(%s) OR
                LOWER(telefono) LIKE LOWER(%s)
            )
            ORDER BY nombre_completo
            LIMIT 20
        """
        result = db_query(query, (search_pattern, search_pattern, search_pattern, search_pattern))
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f"❌ Error en api_transportistas_buscar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ventas_bp.route('/api/cotizaciones/eliminadas/<int:id>', methods=['GET'])
@login_required
def api_ver_eliminada(id):
    """Obtiene el detalle de una cotización eliminada"""
    try:
        query = """
            SELECT 
                c.id,
                c.numero_cotizacion as numero,
                c.fecha_creacion as fecha,
                c.estado,
                c.motivo_eliminacion as motivo,
                c.fecha_eliminacion,
                c.eliminado_por,
                c.cliente_razon_social as cliente,
                c.cliente_ruc as ruc,
                c.cliente_direccion as direccion,
                c.cliente_contacto as contacto,
                c.cliente_telefono as telefono,
                c.cliente_email as email,
                c.condicion_pago,
                c.tiempo_entrega,
                c.validez_oferta,
                c.subtotal,
                c.igv,
                c.total,
                u.nombre_usuario as usuario_elimino
            FROM cotizaciones c
            LEFT JOIN usuarios u ON u.id = c.eliminado_por
            WHERE c.id = %s AND c.estado = 'Anulada'
        """
        
        registro = db_query(query, (id,))
        
        if not registro:
            return jsonify({'success': False, 'error': 'Registro no encontrado'}), 404
        
        return jsonify({
            'success': True,
            'data': registro[0]
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500