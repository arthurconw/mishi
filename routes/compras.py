# routes/compras.py - Módulo de Compras

import sys
import os

# Asegurar que la raíz del proyecto esté en el path de Python
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from datetime import datetime
import json

# Importar desde database.py
from database import db_query, db_execute, db_tx, get_connection

# ============================================================
# CREAR EL BLUEPRINT
# ============================================================
compras_bp = Blueprint('compras', __name__)

# ============================================================
# FUNCIÓN LOGIN REQUIRED
# ============================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            if request.path.startswith('/compras/api/'):
                return jsonify({'error': 'Sesión expirada o no autorizada. Inicia sesión.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# FUNCIONES DE AYUDA PARA SOLICITUDES DE COMPRA
# ============================================================

def obtener_solicitudes_db():
    """Obtiene todas las solicitudes de compra"""
    try:
        query = """
            SELECT 
                id, numero_solicitud, fecha, estado,
                producto, cantidad, unidad, area, solicitante,
                urgencia, justificacion,
                created_at, updated_at
            FROM solicitudes_compra
            ORDER BY id DESC
        """
        return db_query(query)
    except Exception as e:
        print(f"❌ Error en obtener_solicitudes_db: {e}")
        return []

def obtener_solicitud_por_id_db(solicitud_id):
    """Obtiene una solicitud de compra por su ID"""
    try:
        query = """
            SELECT 
                id, numero_solicitud, fecha, estado,
                producto, cantidad, unidad, area, solicitante,
                urgencia, justificacion,
                created_at, updated_at
            FROM solicitudes_compra
            WHERE id = %s
        """
        result = db_query(query, (solicitud_id,))
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en obtener_solicitud_por_id_db: {e}")
        return None


def guardar_solicitud_db(data):
    """Guarda una nueva solicitud de compra"""
    try:
        query = """
            INSERT INTO solicitudes_compra (
                numero_solicitud, fecha, estado,
                producto, cantidad, unidad, area, solicitante,
                urgencia, justificacion,
                creado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, numero_solicitud
        """
        params = (
            data.get('numero_solicitud'),
            data.get('fecha') or datetime.now().isoformat(),
            data.get('estado', 'Borrador'),
            data.get('producto'),
            float(data.get('cantidad', 1)),
            data.get('unidad', 'UND'),
            data.get('area'),
            data.get('solicitante'),
            data.get('urgencia', 'Media'),
            data.get('justificacion', ''),
            data.get('creado_por') or session.get('usuario_id', 8)
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_solicitud_db: {e}")
        raise

def actualizar_solicitud_db(solicitud_id, data):
    """Actualiza una solicitud de compra existente"""
    try:
        query = """
            UPDATE solicitudes_compra SET
                producto = %s,
                cantidad = %s,
                unidad = %s,
                area = %s,
                solicitante = %s,
                urgencia = %s,
                justificacion = %s,
                estado = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, numero_solicitud
        """
        params = (
            data.get('producto'),
            float(data.get('cantidad', 1)),
            data.get('unidad', 'UND'),
            data.get('area'),
            data.get('solicitante'),
            data.get('urgencia', 'Media'),
            data.get('justificacion', ''),
            data.get('estado', 'Borrador'),
            solicitud_id
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en actualizar_solicitud_db: {e}")
        raise


# ============================================================
# FUNCIONES DE AYUDA PARA COMPARATIVOS DE PROVEEDORES
# ============================================================

def obtener_comparativos_db():
    """Obtiene todos los comparativos de proveedores"""
    try:
        query = """
            SELECT 
                id, numero_comparativo, fecha, estado,
                producto, proveedores_json,
                created_at, updated_at
            FROM comparativos_proveedores
            ORDER BY id DESC
        """
        results = db_query(query)
        for row in results:
            if row.get('proveedores_json'):
                try:
                    row['proveedores'] = json.loads(row['proveedores_json'])
                except:
                    row['proveedores'] = []
            else:
                row['proveedores'] = []
        return results
    except Exception as e:
        print(f"❌ Error en obtener_comparativos_db: {e}")
        return []

def guardar_comparativo_db(data):
    """Guarda un nuevo comparativo de proveedores"""
    try:
        proveedores_json = json.dumps(data.get('proveedores', []))
        
        query = """
            INSERT INTO comparativos_proveedores (
                numero_comparativo, fecha, estado,
                producto, proveedores_json,
                creado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
            RETURNING id, numero_comparativo
        """
        params = (
            data.get('numero_comparativo'),
            data.get('fecha') or datetime.now().isoformat(),
            data.get('estado', 'Borrador'),
            data.get('producto'),
            proveedores_json,
            data.get('creado_por') or session.get('usuario_id', 8)
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_comparativo_db: {e}")
        raise


# ============================================================
# FUNCIONES DE AYUDA PARA ÓRDENES DE COMPRA
# ============================================================

# ============================================================
# FUNCIONES DE AYUDA PARA ÓRDENES DE COMPRA
# ============================================================

# ============================================================
# FUNCIONES DE AYUDA PARA ÓRDENES DE COMPRA (CORREGIDO)
# ============================================================

def obtener_ordenes_db():
    """Obtiene todas las órdenes de compra usando tu estructura real"""
    try:
        query = """
            SELECT 
                id, numero_orden, codigo_orden, correlativo,
                proveedor_id, usuario_id, fecha_creacion, estado,
                subtotal, igv, total, condicion_pago, tiempo_entrega,
                fecha_requerida, lugar_entrega, num_cotizacion,
                nota_compra, notas,
                descuento_porcentaje, descuento_monto, descuento_tipo,
                contacto_proveedor, telefono_proveedor, email_proveedor,
                created_at, updated_at
            FROM ordenes_compra
            ORDER BY id DESC
        """
        results = db_query(query)
        
        # Obtener items para cada orden
        for row in results:
            row['items'] = []
            if row.get('id'):
                try:
                    items_query = """
                        SELECT producto, cantidad, precio_unitario, total
                        FROM ordenes_compra_items
                        WHERE orden_compra_id = %s
                    """
                    items = db_query(items_query, (row['id'],))
                    row['items'] = items if items else []
                except Exception as e:
                    print(f"⚠️ Error obteniendo items para orden {row['id']}: {e}")
                    row['items'] = []
        
        return results
    except Exception as e:
        print(f"❌ Error en obtener_ordenes_db: {e}")
        import traceback
        traceback.print_exc()
        return []


def guardar_orden_db(data):
    """Guarda una nueva orden de compra (usando tu estructura real)"""
    try:
        from datetime import datetime
        
        # Si es actualización, usar UPDATE
        if data.get('id'):
            query = """
                UPDATE ordenes_compra SET
                    codigo_orden = %s,
                    correlativo = %s,
                    proveedor_id = %s,
                    usuario_id = %s,
                    estado = %s,
                    subtotal = %s,
                    igv = %s,
                    total = %s,
                    condicion_pago = %s,
                    tiempo_entrega = %s,
                    fecha_requerida = %s,
                    lugar_entrega = %s,
                    num_cotizacion = %s,
                    nota_compra = %s,
                    notas = %s,
                    descuento_porcentaje = %s,
                    descuento_monto = %s,
                    descuento_tipo = %s,
                    contacto_proveedor = %s,
                    telefono_proveedor = %s,
                    email_proveedor = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, numero_orden
            """
            params = (
                data.get('codigo_orden') or data.get('numero_orden'),
                data.get('correlativo') or '00001',
                data.get('proveedor_id'),
                data.get('usuario_id') or session.get('usuario_id', 8),
                data.get('estado', 'pendiente'),
                float(data.get('subtotal', 0)),
                float(data.get('igv', 0)),
                float(data.get('total', 0)),
                data.get('condicion_pago', 'Contado'),
                data.get('tiempo_entrega', '5 días hábiles'),
                data.get('fecha_requerida'),
                data.get('lugar_entrega'),
                data.get('num_cotizacion'),
                data.get('nota_compra'),
                data.get('notas'),
                float(data.get('descuento_porcentaje', 0)),
                float(data.get('descuento_monto', 0)),
                data.get('descuento_tipo', 'porcentaje'),
                data.get('contacto_proveedor'),
                data.get('telefono_proveedor'),
                data.get('email_proveedor'),
                data['id']
            )
            result = db_query(query, params)
            return result[0] if result else None
        
        # Si es nuevo, INSERT
        query = """
            INSERT INTO ordenes_compra (
                numero_orden, codigo_orden, correlativo,
                proveedor_id, usuario_id, estado,
                subtotal, igv, total, condicion_pago, tiempo_entrega,
                fecha_requerida, lugar_entrega, num_cotizacion,
                nota_compra, notas,
                descuento_porcentaje, descuento_monto, descuento_tipo,
                contacto_proveedor, telefono_proveedor, email_proveedor
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            RETURNING id, numero_orden
        """
        
        params = (
            data.get('numero_orden'),
            data.get('codigo_orden') or data.get('numero_orden'),
            data.get('correlativo') or '00001',
            data.get('proveedor_id'),
            data.get('usuario_id') or session.get('usuario_id', 8),
            data.get('estado', 'pendiente'),
            float(data.get('subtotal', 0)),
            float(data.get('igv', 0)),
            float(data.get('total', 0)),
            data.get('condicion_pago', 'Contado'),
            data.get('tiempo_entrega', '5 días hábiles'),
            data.get('fecha_requerida'),
            data.get('lugar_entrega'),
            data.get('num_cotizacion'),
            data.get('nota_compra'),
            data.get('notas'),
            float(data.get('descuento_porcentaje', 0)),
            float(data.get('descuento_monto', 0)),
            data.get('descuento_tipo', 'porcentaje'),
            data.get('contacto_proveedor'),
            data.get('telefono_proveedor'),
            data.get('email_proveedor')
        )
        
        result = db_query(query, params)
        orden_id = result[0]['id'] if result else None
        
        # Guardar items si existen
        items = data.get('items', [])
        if items and orden_id:
            for item in items:
                try:
                    item_query = """
                        INSERT INTO ordenes_compra_items (
                            orden_compra_id, producto, cantidad, 
                            precio_unitario, total
                        ) VALUES (%s, %s, %s, %s, %s)
                    """
                    db_query(item_query, (
                        orden_id,
                        item.get('producto'),
                        float(item.get('cantidad', 1)),
                        float(item.get('precio_unitario', 0)),
                        float(item.get('total', 0))
                    ))
                except Exception as e:
                    print(f"⚠️ Error guardando item: {e}")
        
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_orden_db: {e}")
        import traceback
        traceback.print_exc()
        raise


def actualizar_orden_db(orden_id, data):
    """Actualiza una orden de compra existente"""
    try:
        query = """
            UPDATE ordenes_compra SET
                estado = %s,
                condicion_pago = %s,
                tiempo_entrega = %s,
                fecha_requerida = %s,
                lugar_entrega = %s,
                nota_compra = %s,
                notas = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, numero_orden
        """
        params = (
            data.get('estado', 'pendiente'),
            data.get('condicion_pago', 'Contado'),
            data.get('tiempo_entrega', '5 días hábiles'),
            data.get('fecha_requerida'),
            data.get('lugar_entrega'),
            data.get('nota_compra'),
            data.get('notas'),
            orden_id
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en actualizar_orden_db: {e}")
        raise
# ============================================================
# FUNCIONES DE AYUDA PARA COMPROBANTES DE PROVEEDOR
# ============================================================

# ============================================================
# FUNCIONES DE AYUDA PARA COMPROBANTES DE PROVEEDOR
# ============================================================

def obtener_comprobantes_proveedor_db():
    """Obtiene todos los comprobantes de proveedor"""
    try:
        query = """
            SELECT 
                id,
                tipo,
                numero,
                fecha,
                monto,
                ruc_proveedor,
                proveedor_nombre,
                orden_compra_id,
                orden_compra_numero,
                estado,
                observaciones,
                creado_por,
                created_at,
                updated_at
            FROM comprobantes_proveedor
            ORDER BY id DESC
        """
        rows = db_query(query) or []

        normalized = []
        for r in rows:
            normalized.append({
                'id': r.get('id'),
                'tipo': r.get('tipo') or 'Factura',
                'numero': r.get('numero') or '',
                'fecha': r.get('fecha'),
                'monto': float(r.get('monto') or 0),
                'ruc_proveedor': r.get('ruc_proveedor') or '',
                'ruc': r.get('ruc_proveedor') or '',
                'proveedor_nombre': r.get('proveedor_nombre') or '',
                'proveedor': r.get('proveedor_nombre') or '',
                'orden_compra_id': r.get('orden_compra_id'),
                'orden_compra_numero': r.get('orden_compra_numero') or '',
                'orden_compra': r.get('orden_compra_numero') or '',
                'estado': r.get('estado') or 'Pendiente',
                'observaciones': r.get('observaciones') or '',
                'created_at': r.get('created_at'),
                'updated_at': r.get('updated_at'),
            })

        return normalized

    except Exception as e:
        print(f"❌ Error en obtener_comprobantes_proveedor_db: {e}")
        import traceback
        traceback.print_exc()
        return []

def guardar_comprobante_proveedor_db(data):
    """Guarda un nuevo comprobante de proveedor"""
    try:
        query = """
            INSERT INTO comprobantes_proveedor (
                tipo, numero, fecha, monto,
                ruc_proveedor, proveedor_nombre,
                orden_compra_id, orden_compra_numero,
                estado, observaciones,
                creado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, numero
        """
        params = (
            data.get('tipo', 'Factura'),
            data.get('numero'),
            data.get('fecha') or datetime.now().isoformat(),
            float(data.get('monto', 0)),
            data.get('ruc') or data.get('ruc_proveedor') or '',
            data.get('proveedor') or data.get('proveedor_nombre') or '',
            data.get('orden_compra_id'),                  # int o None
            data.get('orden_compra') or data.get('orden_compra_numero') or '',
            data.get('estado', 'Pendiente'),
            data.get('observaciones', ''),
            data.get('creado_por') or session.get('usuario_id', 8)
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_comprobante_proveedor_db: {e}")
        import traceback
        traceback.print_exc()
        raise
# ============================================================
# FUNCIONES DE AYUDA PARA RECEPCIÓN DE MERCADERÍA
# ============================================================

# ============================================================
# FUNCIONES DE AYUDA PARA RECEPCIÓN DE MERCADERÍA
# ============================================================
# ============================================================
# FUNCIONES DE AYUDA PARA RECEPCIÓN DE MERCADERÍA
# ============================================================

def obtener_recepciones_db():
    """Obtiene todas las recepciones de mercadería"""
    try:
        query = """
            SELECT 
                id,
                numero_recepcion,
                fecha,
                estado,
                orden_compra_id,
                orden_compra_numero,
                proveedor_nombre,
                producto,
                cantidad,
                unidad,
                estado_mercaderia,
                observaciones,
                creado_por,
                created_at,
                updated_at
            FROM recepciones_mercaderia
            ORDER BY id DESC
        """
        rows = db_query(query) or []

        normalized = []
        for r in rows:
            normalized.append({
                'id': r.get('id'),
                'numero': r.get('numero_recepcion') or '',
                'numero_recepcion': r.get('numero_recepcion') or '',
                'fecha': r.get('fecha'),
                'estado': r.get('estado') or 'Pendiente',
                'orden_compra_id': r.get('orden_compra_id'),
                'orden_compra': r.get('orden_compra_numero') or '',
                'orden': r.get('orden_compra_numero') or '',
                'orden_compra_numero': r.get('orden_compra_numero') or '',
                'proveedor': r.get('proveedor_nombre') or '',
                'proveedor_nombre': r.get('proveedor_nombre') or '',
                'producto': r.get('producto') or '',
                'cantidad': float(r.get('cantidad') or 0),
                'unidad': r.get('unidad') or 'UND',
                'estado_mercaderia': r.get('estado_mercaderia') or '',
                'observaciones': r.get('observaciones') or '',
                'created_at': r.get('created_at'),
                'updated_at': r.get('updated_at'),
            })

        return normalized

    except Exception as e:
        print(f"❌ Error en obtener_recepciones_db: {e}")
        import traceback
        traceback.print_exc()
        return []


def guardar_recepcion_db(data):
    """Guarda una nueva recepción de mercadería"""
    try:
        query = """
            INSERT INTO recepciones_mercaderia (
                numero_recepcion, fecha, estado,
                orden_compra_id, orden_compra_numero, proveedor_nombre,
                producto, cantidad, unidad,
                estado_mercaderia, observaciones,
                creado_por
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, numero_recepcion
        """
        params = (
            data.get('numero_recepcion'),
            data.get('fecha') or datetime.now().isoformat(),
            data.get('estado', 'Pendiente'),
            data.get('orden_compra_id'),                  # int o None
            data.get('orden_compra') or data.get('orden_compra_numero') or '',
            data.get('proveedor') or data.get('proveedor_nombre') or '',
            data.get('producto'),
            float(data.get('cantidad', 1)),
            data.get('unidad', 'UND'),
            data.get('estado_mercaderia', 'Buen estado'),
            data.get('observaciones', ''),
            data.get('creado_por') or session.get('usuario_id', 8)
        )
        result = db_query(query, params)
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error en guardar_recepcion_db: {e}")
        import traceback
        traceback.print_exc()
        raise

# RUTAS PRINCIPALES
# ============================================================

@compras_bp.route('/compras')
@login_required
def compras():
    """Página principal del módulo de compras"""
    tab = request.args.get('tab', 'solicitud_compra')
    return render_template('compras/index.html',
                         active_tab=tab,
                         usuario=session.get('usuario'),
                         nombre=session.get('nombre_completo'),
                         empresa=session.get('empresa'))


# ============================================================
# API - SOLICITUDES DE COMPRA
# ============================================================

@compras_bp.route('/compras/api/solicitudes/listar', methods=['GET'])
@login_required
def api_solicitudes_listar():
    """Lista todas las solicitudes de compra"""
    try:
        data = obtener_solicitudes_db()
        
        # Formatear para el frontend
        formatted_data = []
        for row in data:
            formatted_data.append({
                'id': row.get('id'),
                'numero': row.get('numero_solicitud'),
                'fecha': row.get('fecha'),
                'estado': row.get('estado'),
                'producto': row.get('producto'),
                'cantidad': float(row.get('cantidad', 0)),
                'unidad': row.get('unidad', 'UND'),
                'area': row.get('area'),
                'solicitante': row.get('solicitante'),
                'urgencia': row.get('urgencia', 'Media'),
                'justificacion': row.get('justificacion', '')
            })
        
        return jsonify({'success': True, 'data': formatted_data})
    except Exception as e:
        print(f"❌ Error en api_solicitudes_listar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@compras_bp.route('/compras/api/solicitudes/guardar', methods=['POST'])
@login_required
def api_solicitudes_guardar():
    """Guarda una solicitud de compra"""
    try:
        data = request.get_json()
        print(f"📦 Guardando solicitud: {data}")
        
        # Generar número si no tiene
        if not data.get('numero_solicitud'):
            count_data = db_query("SELECT COUNT(*) as total FROM solicitudes_compra")
            count = count_data[0]['total'] + 1 if count_data else 1
            data['numero_solicitud'] = f"SOL-{datetime.now().strftime('%Y%m%d')}-{str(count).zfill(4)}"
        
        # Si tiene ID, actualizar
        if data.get('id'):
            print(f"✏️ Actualizando solicitud ID: {data['id']}")
            
            # Verificar que la solicitud existe
            existing = obtener_solicitud_por_id_db(data['id'])
            if not existing:
                return jsonify({'success': False, 'error': 'Solicitud no encontrada'}), 404
            
            # Actualizar solicitud
            query = """
                UPDATE solicitudes_compra SET
                    producto = %s,
                    cantidad = %s,
                    unidad = %s,
                    area = %s,
                    solicitante = %s,
                    urgencia = %s,
                    justificacion = %s,
                    estado = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, numero_solicitud
            """
            params = (
                data.get('producto'),
                float(data.get('cantidad', 1)),
                data.get('unidad', 'UND'),
                data.get('area'),
                data.get('solicitante'),
                data.get('urgencia', 'Media'),
                data.get('justificacion', ''),
                data.get('estado', 'Borrador'),
                data['id']
            )
            result = db_query(query, params)
            
            if result:
                return jsonify({
                    'success': True, 
                    'message': 'Solicitud actualizada', 
                    'data': result[0]
                })
            return jsonify({'success': False, 'error': 'No se pudo actualizar'}), 400
        
        # Si no tiene ID, crear nueva
        print(f"🆕 Creando nueva solicitud")
        result = guardar_solicitud_db(data)
        if result:
            return jsonify({'success': True, 'message': 'Solicitud creada', 'data': result})
        return jsonify({'success': False, 'error': 'No se pudo crear'}), 400
        
    except Exception as e:
        print(f"❌ Error en api_solicitudes_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@compras_bp.route('/compras/api/solicitudes/<int:id>/toggle', methods=['PUT'])
@login_required
def api_solicitudes_toggle(id):
    """Cambia el estado de una solicitud de compra"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        estados_validos = ['Borrador', 'Pendiente', 'Aprobada', 'Rechazada', 'Ordenada']
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido'}), 400
        
        query = """
            UPDATE solicitudes_compra 
            SET estado = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado
        """
        result = db_query(query, (nuevo_estado, id))
        
        if result:
            return jsonify({
                'success': True,
                'message': f'Solicitud actualizada a {nuevo_estado}',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'Solicitud no encontrada'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_solicitudes_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@compras_bp.route('/compras/api/solicitudes/<int:id>', methods=['DELETE'])
@login_required
def api_solicitudes_eliminar(id):
    """Elimina una solicitud de compra"""
    try:
        query = "DELETE FROM solicitudes_compra WHERE id = %s RETURNING id"
        result = db_query(query, (id,))
        
        if result:
            return jsonify({'success': True, 'message': 'Solicitud eliminada'})
        
        return jsonify({'success': False, 'error': 'Solicitud no encontrada'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_solicitudes_eliminar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API - COMPARATIVOS DE PROVEEDORES
# ============================================================

@compras_bp.route('/compras/api/comparativos/listar', methods=['GET'])
@login_required
def api_comparativos_listar():
    """Lista todos los comparativos de proveedores"""
    try:
        data = obtener_comparativos_db()
        
        formatted_data = []
        for row in data:
            # Obtener el mejor precio
            proveedores = row.get('proveedores', [])
            mejor = None
            if proveedores:
                mejor = min(proveedores, key=lambda p: float(p.get('precio', 0))) if proveedores else None
            
            formatted_data.append({
                'id': row.get('id'),
                'numero': row.get('numero_comparativo'),
                'fecha': row.get('fecha'),
                'estado': row.get('estado'),
                'producto': row.get('producto'),
                'proveedores': proveedores,
                'mejor_proveedor': mejor.get('nombre') if mejor else None,
                'mejor_precio': float(mejor.get('precio', 0)) if mejor else 0,
                'mejor_plazo': mejor.get('plazo') if mejor else None
            })
        
        return jsonify({'success': True, 'data': formatted_data})
    except Exception as e:
        print(f"❌ Error en api_comparativos_listar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@compras_bp.route('/compras/api/comparativos/guardar', methods=['POST'])
@login_required
def api_comparativos_guardar():
    """Guarda un comparativo de proveedores"""
    try:
        data = request.get_json()
        print(f"📊 Guardando comparativo: {data}")
        
        if not data.get('numero_comparativo'):
            count_data = db_query("SELECT COUNT(*) as total FROM comparativos_proveedores")
            count = count_data[0]['total'] + 1 if count_data else 1
            data['numero_comparativo'] = f"CMP-{datetime.now().strftime('%Y%m%d')}-{str(count).zfill(4)}"
        
        result = guardar_comparativo_db(data)
        if result:
            return jsonify({'success': True, 'message': 'Comparativo guardado', 'data': result})
        return jsonify({'success': False, 'error': 'No se pudo guardar'}), 400
        
    except Exception as e:
        print(f"❌ Error en api_comparativos_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@compras_bp.route('/compras/api/comparativos/<int:id>/toggle', methods=['PUT'])
@login_required
def api_comparativos_toggle(id):
    """Cambia el estado de un comparativo"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        estados_validos = ['Borrador', 'En evaluación', 'Seleccionado', 'Rechazado']
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido'}), 400
        
        query = """
            UPDATE comparativos_proveedores 
            SET estado = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado
        """
        result = db_query(query, (nuevo_estado, id))
        
        if result:
            return jsonify({
                'success': True,
                'message': f'Comparativo actualizado a {nuevo_estado}',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'Comparativo no encontrado'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_comparativos_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API - ÓRDENES DE COMPRA
# ============================================================

@compras_bp.route('/compras/api/ordenes/listar', methods=['GET'])
@login_required
def api_ordenes_listar():
    """Lista todas las órdenes de compra"""
    try:
        data = obtener_ordenes_db()
        
        formatted_data = []
        for row in data:
            # Obtener nombre del proveedor si existe
            proveedor_nombre = None
            if row.get('proveedor_id'):
                try:
                    prov_query = "SELECT razon_social FROM proveedores WHERE id = %s"
                    prov_result = db_query(prov_query, (row['proveedor_id'],))
                    if prov_result:
                        proveedor_nombre = prov_result[0].get('razon_social')
                except:
                    pass
            
            formatted_data.append({
                'id': row.get('id'),
                'numero': row.get('numero_orden'),
                'fecha': row.get('fecha_creacion'),
                'estado': row.get('estado'),
                'proveedor': proveedor_nombre or row.get('contacto_proveedor') or f"Proveedor ID: {row.get('proveedor_id')}",
                'ruc': row.get('contacto_proveedor') and 'RUC no disponible',
                'condicion_pago': row.get('condicion_pago'),
                'moneda': 'Soles (S/)',
                'subtotal': float(row.get('subtotal', 0)),
                'igv': float(row.get('igv', 0)),
                'total': float(row.get('total', 0)),
                'items': row.get('items', []),
                'nota_compra': row.get('nota_compra', ''),
                'notas': row.get('notas', '')
            })
        
        return jsonify({'success': True, 'data': formatted_data})
    except Exception as e:
        print(f"❌ Error en api_ordenes_listar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@compras_bp.route('/compras/api/ordenes/guardar', methods=['POST'])
@login_required
def api_ordenes_guardar():
    """Guarda una orden de compra"""
    try:
        data = request.get_json()
        print(f"📄 Guardando orden de compra: {data}")
        
        if not data.get('numero_orden'):
            count_data = db_query("SELECT COUNT(*) as total FROM ordenes_compra")
            count = count_data[0]['total'] + 1 if count_data else 1
            data['numero_orden'] = f"OC-{datetime.now().strftime('%Y%m%d')}-{str(count).zfill(4)}"
        
        # Calcular totales si no vienen
        items = data.get('items', [])
        if items and not data.get('subtotal'):
            subtotal = sum(float(i.get('total', float(i.get('cantidad', 0)) * float(i.get('precio_unitario', 0)))) for i in items)
            data['subtotal'] = subtotal
            data['igv'] = subtotal * 0.18
            data['total'] = subtotal * 1.18
        
        result = guardar_orden_db(data)
        if result:
            return jsonify({'success': True, 'message': 'Orden de compra guardada', 'data': result})
        return jsonify({'success': False, 'error': 'No se pudo guardar'}), 400
        
    except Exception as e:
        print(f"❌ Error en api_ordenes_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@compras_bp.route('/compras/api/ordenes/<int:id>/toggle', methods=['PUT'])
@login_required
def api_ordenes_toggle(id):
    """Cambia el estado de una orden de compra"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        estados_validos = ['Borrador', 'Emitida', 'Enviada', 'Confirmada', 'Anulada']
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido'}), 400
        
        query = """
            UPDATE ordenes_compra 
            SET estado = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado
        """
        result = db_query(query, (nuevo_estado, id))
        
        if result:
            return jsonify({
                'success': True,
                'message': f'Orden actualizada a {nuevo_estado}',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'Orden no encontrada'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_ordenes_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@compras_bp.route('/compras/api/ordenes/<int:id>', methods=['DELETE'])
@login_required
def api_ordenes_eliminar(id):
    """Elimina una orden de compra (solo si está en Borrador o Anulada)"""
    try:
        # Verificar estado
        check_query = "SELECT id, estado FROM ordenes_compra WHERE id = %s"
        check_result = db_query(check_query, (id,))
        
        if not check_result:
            return jsonify({'success': False, 'error': 'Orden no encontrada'}), 404
        
        estado = check_result[0].get('estado')
        if estado not in ['Borrador', 'Anulada']:
            return jsonify({
                'success': False,
                'error': f'Solo se pueden eliminar órdenes en estado "Borrador" o "Anulada". Estado actual: {estado}'
            }), 400
        
        query = "DELETE FROM ordenes_compra WHERE id = %s RETURNING id"
        result = db_query(query, (id,))
        
        if result:
            return jsonify({'success': True, 'message': 'Orden eliminada'})
        
        return jsonify({'success': False, 'error': 'No se pudo eliminar'}), 400
        
    except Exception as e:
        print(f"❌ Error en api_ordenes_eliminar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API - COMPROBANTES DE PROVEEDOR
# ============================================================
@compras_bp.route('/compras/api/comprobantes-proveedor/listar', methods=['GET'])
@login_required
def api_comprobantes_proveedor_listar():
    """Lista todos los comprobantes de proveedor"""
    try:
        data = obtener_comprobantes_proveedor_db()

        formatted_data = []
        for row in data:
            formatted_data.append({
                'id': row.get('id'),
                'tipo': row.get('tipo') or 'Factura',
                'numero': row.get('numero') or '',
                'fecha': row.get('fecha'),
                'monto': float(row.get('monto') or 0),
                'ruc': row.get('ruc_proveedor') or '',
                'ruc_proveedor': row.get('ruc_proveedor') or '',
                'proveedor': row.get('proveedor_nombre') or '',
                'proveedor_nombre': row.get('proveedor_nombre') or '',
                'orden_compra': row.get('orden_compra_numero') or '',
                'orden_compra_numero': row.get('orden_compra_numero') or '',
                'estado': row.get('estado') or 'Pendiente',
                'observaciones': row.get('observaciones') or ''
            })

        return jsonify({'success': True, 'data': formatted_data})

    except Exception as e:
        print(f"❌ Error en api_comprobantes_proveedor_listar: {e}")
        import traceback
        traceback.print_exc()
        # Devolver 200 con lista vacía para no romper el frontend
        return jsonify({'success': False, 'error': str(e), 'data': []}), 200


@compras_bp.route('/compras/api/recepciones/listar', methods=['GET'])
@login_required
def api_recepciones_listar():
    """Lista todas las recepciones de mercadería"""
    try:
        data = obtener_recepciones_db()

        formatted_data = []
        for row in data:
            formatted_data.append({
                'id': row.get('id'),
                'numero': row.get('numero_recepcion') or '',
                'numero_recepcion': row.get('numero_recepcion') or '',
                'fecha': row.get('fecha'),
                'estado': row.get('estado') or 'Pendiente',
                'orden_compra': row.get('orden_compra_numero') or '',
                'orden': row.get('orden_compra_numero') or '',
                'proveedor': row.get('proveedor_nombre') or '',
                'producto': row.get('producto') or '',
                'cantidad': float(row.get('cantidad') or 0),
                'unidad': row.get('unidad') or 'UND',
                'estado_mercaderia': row.get('estado_mercaderia') or '',
                'observaciones': row.get('observaciones') or ''
            })

        return jsonify({'success': True, 'data': formatted_data})

    except Exception as e:
        print(f"❌ Error en api_recepciones_listar: {e}")
        import traceback
        traceback.print_exc()
        # Devolver 200 con lista vacía para no romper el frontend
        return jsonify({'success': False, 'error': str(e), 'data': []}), 200


@compras_bp.route('/compras/api/comprobantes-proveedor/guardar', methods=['POST'])
@login_required
def api_comprobantes_proveedor_guardar():
    """Guarda un comprobante de proveedor"""
    try:
        data = request.get_json()
        print(f"🧾 Guardando comprobante de proveedor: {data}")

        result = guardar_comprobante_proveedor_db(data)
        if result:
            return jsonify({'success': True, 'message': 'Comprobante registrado', 'data': result})
        return jsonify({'success': False, 'error': 'No se pudo guardar'}), 200

    except Exception as e:
        print(f"❌ Error en api_comprobantes_proveedor_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 200


@compras_bp.route('/compras/api/recepciones/guardar', methods=['POST'])
@login_required
def api_recepciones_guardar():
    """Guarda una recepción de mercadería"""
    try:
        data = request.get_json()
        print(f"📦 Guardando recepción: {data}")

        if not data.get('numero_recepcion'):
            count_data = db_query("SELECT COUNT(*) as total FROM recepciones_mercaderia")
            count = count_data[0]['total'] + 1 if count_data else 1
            data['numero_recepcion'] = f"REC-{datetime.now().strftime('%Y%m%d')}-{str(count).zfill(4)}"

        result = guardar_recepcion_db(data)
        if result:
            # Si la recepción se aprueba o almacena, actualizar stock
            if data.get('estado') in ('Aprobada', 'Almacenada'):
                try:
                    update_stock_query = """
                        UPDATE productos 
                        SET stock = stock + %s
                        WHERE descripcion ILIKE %s OR codigo ILIKE %s
                    """
                    db_query(update_stock_query, (
                        float(data.get('cantidad', 0)),
                        f"%{data.get('producto', '')}%",
                        f"%{data.get('producto', '')}%"
                    ))
                    print(f"✅ Stock actualizado para: {data.get('producto')}")
                except Exception as e:
                    print(f"⚠️ Error actualizando stock: {e}")

            return jsonify({'success': True, 'message': 'Recepción guardada', 'data': result})
        return jsonify({'success': False, 'error': 'No se pudo guardar'}), 200

    except Exception as e:
        print(f"❌ Error en api_recepciones_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 200


@compras_bp.route('/compras/api/comprobantes-proveedor/<int:id>/toggle', methods=['PUT'])
@login_required
def api_comprobantes_proveedor_toggle(id):
    """Cambia el estado de un comprobante de proveedor"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        estados_validos = ['Pendiente', 'Registrado', 'Pagado', 'Anulado']
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido'}), 400
        
        query = """
            UPDATE comprobantes_proveedor 
            SET estado = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado
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
        print(f"❌ Error en api_comprobantes_proveedor_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API - RECEPCIÓN DE MERCADERÍA
# ============================================================

@compras_bp.route('/compras/api/recepciones/listar', methods=['GET'])
@login_required
def api_recepciones_listar():
    """Lista todas las recepciones de mercadería"""
    try:
        data = obtener_recepciones_db()
        
        formatted_data = []
        for row in data:
            formatted_data.append({
                'id': row.get('id'),
                'numero': row.get('numero_recepcion'),
                'fecha': row.get('fecha'),
                'estado': row.get('estado'),
                'orden_compra': row.get('orden_compra'),
                'proveedor': row.get('proveedor'),
                'producto': row.get('producto'),
                'cantidad': float(row.get('cantidad', 0)),
                'unidad': row.get('unidad', 'UND'),
                'estado_mercaderia': row.get('estado_mercaderia'),
                'observaciones': row.get('observaciones', '')
            })
        
        return jsonify({'success': True, 'data': formatted_data})
    except Exception as e:
        print(f"❌ Error en api_recepciones_listar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@compras_bp.route('/compras/api/recepciones/guardar', methods=['POST'])
@login_required
def api_recepciones_guardar():
    """Guarda una recepción de mercadería"""
    try:
        data = request.get_json()
        print(f"📦 Guardando recepción: {data}")
        
        if not data.get('numero_recepcion'):
            count_data = db_query("SELECT COUNT(*) as total FROM recepciones_mercaderia")
            count = count_data[0]['total'] + 1 if count_data else 1
            data['numero_recepcion'] = f"REC-{datetime.now().strftime('%Y%m%d')}-{str(count).zfill(4)}"
        
        result = guardar_recepcion_db(data)
        if result:
            # Si la recepción fue aprobada, actualizar stock de productos
            if data.get('estado') == 'Aprobada' or data.get('estado') == 'Almacenada':
                try:
                    # Actualizar stock del producto
                    update_stock_query = """
                        UPDATE productos 
                        SET stock = stock + %s
                        WHERE descripcion ILIKE %s OR codigo ILIKE %s
                    """
                    db_query(update_stock_query, (
                        float(data.get('cantidad', 0)),
                        f'%{data.get("producto", "")}%',
                        f'%{data.get("producto", "")}%'
                    ))
                    print(f"✅ Stock actualizado para producto: {data.get('producto')}")
                except Exception as e:
                    print(f"⚠️ Error actualizando stock: {e}")
            
            return jsonify({'success': True, 'message': 'Recepción guardada', 'data': result})
        return jsonify({'success': False, 'error': 'No se pudo guardar'}), 400
        
    except Exception as e:
        print(f"❌ Error en api_recepciones_guardar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@compras_bp.route('/compras/api/recepciones/<int:id>/toggle', methods=['PUT'])
@login_required
def api_recepciones_toggle(id):
    """Cambia el estado de una recepción"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        estados_validos = ['Pendiente', 'En inspección', 'Aprobada', 'Rechazada', 'Almacenada']
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': f'Estado inválido'}), 400
        
        query = """
            UPDATE recepciones_mercaderia 
            SET estado = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, estado
        """
        result = db_query(query, (nuevo_estado, id))
        
        if result:
            # Si se aprueba, actualizar stock
            if nuevo_estado in ['Aprobada', 'Almacenada']:
                try:
                    # Obtener datos de la recepción
                    get_query = """
                        SELECT producto, cantidad 
                        FROM recepciones_mercaderia 
                        WHERE id = %s
                    """
                    recepcion = db_query(get_query, (id,))
                    if recepcion:
                        update_stock_query = """
                            UPDATE productos 
                            SET stock = stock + %s
                            WHERE descripcion ILIKE %s OR codigo ILIKE %s
                        """
                        db_query(update_stock_query, (
                            float(recepcion[0].get('cantidad', 0)),
                            f'%{recepcion[0].get("producto", "")}%',
                            f'%{recepcion[0].get("producto", "")}%'
                        ))
                        print(f"✅ Stock actualizado para recepción ID: {id}")
                except Exception as e:
                    print(f"⚠️ Error actualizando stock: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Recepción actualizada a {nuevo_estado}',
                'data': result[0]
            })
        
        return jsonify({'success': False, 'error': 'Recepción no encontrada'}), 404
        
    except Exception as e:
        print(f"❌ Error en api_recepciones_toggle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API - EXPORTACIÓN DE DATOS
# ============================================================

@compras_bp.route('/compras/api/exportar/<tipo>', methods=['GET'])
@login_required
def api_exportar(tipo):
    """Exporta datos en formato JSON"""
    try:
        data = []
        filename = f"compras_{tipo}_{datetime.now().strftime('%Y%m%d')}.json"
        
        if tipo == 'solicitud_compra':
            data = obtener_solicitudes_db()
        elif tipo == 'comparativo':
            data = obtener_comparativos_db()
        elif tipo == 'orden_compra':
            data = obtener_ordenes_db()
        elif tipo == 'comprobante_proveedor':
            data = obtener_comprobantes_proveedor_db()
        elif tipo == 'recepcion':
            data = obtener_recepciones_db()
        else:
            return jsonify({'success': False, 'error': 'Tipo no válido'}), 400
        
        # Crear respuesta JSON
        from flask import Response
        import json
        
        json_data = json.dumps(data, default=str, indent=2)
        
        return Response(
            json_data,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
        
    except Exception as e:
        print(f"❌ Error en api_exportar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# API - BUSCAR PROVEEDOR POR RUC / NOMBRE (VERSIÓN FINAL AJUSTADA)
# ============================================================

@compras_bp.route('/compras/api/proveedores/buscar', methods=['GET'])
@login_required
def api_proveedores_buscar():
    """
    Busca proveedores por RUC exacto, o por razón social/contacto.
    Devuelve TODOS los campos útiles para autocompletar formularios.
    """
    try:
        q = (request.args.get('q') or '').strip()

        if not q or len(q) < 2:
            return jsonify({'success': True, 'data': [], 'source': 'empty'})

        es_ruc = q.isdigit() and len(q) == 11

        # ------------------------------------------------------------
        # Query base (usa las columnas REALES de tu tabla)
        # ------------------------------------------------------------
        select_str = """
            id,
            ruc,
            razon_social,
            razon_comercial,
            codigo_proveedor,
            direccion,
            telefono,
            contacto,
            email,
            condicion_pago,
            tiempo_credito,
            moneda,
            descuento,
            banco,
            numero_cuenta,
            cci,
            tipo_cuenta,
            lugar_recojo,
            ambito,
            estado,
            activo
        """

        if es_ruc:
            # Búsqueda exacta por RUC (más rápida y precisa)
            query = f"""
                SELECT {select_str}
                FROM proveedores
                WHERE ruc = %s
                LIMIT 5
            """
            params = (q,)
        else:
            # Búsqueda amplia por razón social, comercial, contacto o RUC parcial
            pattern = f"%{q}%"
            query = f"""
                SELECT {select_str}
                FROM proveedores
                WHERE ruc ILIKE %s
                   OR razon_social ILIKE %s
                   OR COALESCE(razon_comercial, '') ILIKE %s
                   OR COALESCE(contacto, '') ILIKE %s
                ORDER BY razon_social
                LIMIT 20
            """
            params = (pattern, pattern, pattern, pattern)

        # ------------------------------------------------------------
        # Ejecutar y normalizar
        # ------------------------------------------------------------
        try:
            rows = db_query(query, params) or []
        except Exception as e:
            print(f"⚠️ Error consultando proveedores: {e}")
            return _fallback_sunat_compras(q)

        # Si buscó por RUC exacto y no encontró, fallback SUNAT
        if not rows and es_ruc:
            return _fallback_sunat_compras(q)

        data = []
        for r in rows:
            data.append({
                'id': r.get('id'),
                'ruc': r.get('ruc') or '',
                'razon_social': r.get('razon_social') or '',
                'razon_comercial': r.get('razon_comercial') or '',
                'codigo_proveedor': r.get('codigo_proveedor') or '',
                'direccion': r.get('direccion') or '',
                'telefono': r.get('telefono') or '',
                'contacto': r.get('contacto') or '',
                'email': r.get('email') or '',
                'condicion_pago': r.get('condicion_pago') or '',
                'tiempo_credito': r.get('tiempo_credito') or '',
                'moneda': r.get('moneda') or '',
                'descuento': r.get('descuento') or '',
                'banco': r.get('banco') or '',
                'numero_cuenta': r.get('numero_cuenta') or '',
                'cci': r.get('cci') or '',
                'tipo_cuenta': r.get('tipo_cuenta') or '',
                'lugar_recojo': r.get('lugar_recojo') or '',
                'ambito': r.get('ambito') or '',
                'estado': r.get('estado') or '',
                'activo': bool(r.get('activo')) if r.get('activo') is not None else True
            })

        return jsonify({'success': True, 'data': data, 'source': 'bd'})

    except Exception as e:
        print(f"❌ Error CRÍTICO en api_proveedores_buscar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': True, 'data': [], 'source': 'error', 'warning': str(e)})


def _fallback_sunat_compras(ruc):
    """Fallback: consulta SUNAT y devuelve formato compatible."""
    try:
        if not ruc.isdigit() or len(ruc) != 11:
            return jsonify({'success': True, 'data': [], 'source': 'invalid_ruc'})

        import urllib.request, json as _json, ssl

        url = f"https://api.apis.net.pe/v1/ruc?numero={ruc}"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
            raw = resp.read().decode('utf-8')
            data_sunat = _json.loads(raw)

        razon = data_sunat.get('razonSocial') or data_sunat.get('nombre') or ''
        direccion = data_sunat.get('direccion') or ''

        if razon:
            return jsonify({
                'success': True,
                'source': 'sunat',
                'data': [{
                    'id': None,
                    'ruc': ruc,
                    'razon_social': razon,
                    'razon_comercial': '',
                    'codigo_proveedor': '',
                    'direccion': direccion,
                    'telefono': '',
                    'contacto': '',
                    'email': '',
                    'condicion_pago': '',
                    'tiempo_credito': '',
                    'moneda': 'Soles (S/)',
                    'descuento': '',
                    'banco': '',
                    'numero_cuenta': '',
                    'cci': '',
                    'tipo_cuenta': '',
                    'lugar_recojo': '',
                    'ambito': '',
                    'estado': 'Activo',
                    'activo': True
                }]
            })

        return jsonify({'success': True, 'data': [], 'source': 'sunat_empty'})

    except Exception as e:
        print(f"❌ Error en _fallback_sunat_compras: {e}")
        return jsonify({'success': True, 'data': [], 'source': 'error'})

def _fallback_sunat(ruc):
    """Fallback: consulta SUNAT y devuelve formato compatible."""
    try:
        import urllib.request
        import json as _json
        import ssl

        # Validar RUC
        if not ruc.isdigit() or len(ruc) != 11:
            return jsonify({'success': True, 'data': [], 'source': 'sunat_invalid'})

        # Intentar consultar SUNAT vía API externa
        # Opción 1: API interna si existe
        try:
            url = f"https://api.apis.net.pe/v1/ruc?numero={ruc}"
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                raw = resp.read().decode('utf-8')
                data_sunat = _json.loads(raw)

            razon = data_sunat.get('razonSocial') or data_sunat.get('nombre') or ''
            direccion = data_sunat.get('direccion') or ''

            if razon:
                return jsonify({
                    'success': True,
                    'source': 'sunat',
                    'data': [{
                        'id': None,
                        'ruc': ruc,
                        'razon_social': razon,
                        'direccion': direccion,
                        'telefono': '',
                        'email': '',
                        'contacto': ''
                    }]
                })
        except Exception as e:
            print(f"⚠️ Error consultando SUNAT externa: {e}")

        return jsonify({'success': True, 'data': [], 'source': 'sunat_empty'})

    except Exception as e:
        print(f"❌ Error en _fallback_sunat: {e}")
        return jsonify({'success': True, 'data': [], 'source': 'error'})

# ============================================================
# API - BUSCAR ÓRDENES DE COMPRA (autocomplete)
# ============================================================

@compras_bp.route('/compras/api/ordenes/buscar', methods=['GET'])
@login_required
def api_ordenes_buscar():
    """Busca órdenes de compra para autocomplete"""
    try:
        q = request.args.get('q', '').strip()
        
        if not q or len(q) < 2:
            return jsonify({'success': True, 'data': []})
        
        query = """
            SELECT id, numero_orden, proveedor, ruc, total, estado
            FROM ordenes_compra
            WHERE numero_orden ILIKE %s
               OR proveedor ILIKE %s
               OR ruc ILIKE %s
            ORDER BY fecha DESC
            LIMIT 20
        """
        search_pattern = f'%{q}%'
        results = db_query(query, (search_pattern, search_pattern, search_pattern))
        
        return jsonify({'success': True, 'data': results})
        
    except Exception as e:
        print(f"❌ Error en api_ordenes_buscar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# RUTA PARA VISTA PREVIA DE ORDEN DE COMPRA
# ============================================================

@compras_bp.route('/compras/orden/<int:id>/preview', methods=['GET'])
@login_required
def orden_preview(id):
    """Vista previa de una orden de compra"""
    try:
        query = """
            SELECT 
                id, numero_orden, fecha, estado,
                proveedor, ruc, condicion_pago, moneda,
                subtotal, igv, total,
                items_json, observaciones,
                created_at, updated_at
            FROM ordenes_compra
            WHERE id = %s
        """
        result = db_query(query, (id,))
        
        if not result:
            return "Orden de compra no encontrada", 404
        
        orden = result[0]
        
        # Parsear items
        if orden.get('items_json'):
            try:
                orden['items'] = json.loads(orden['items_json'])
            except:
                orden['items'] = []
        else:
            orden['items'] = []
        
        return render_template('compras/orden_preview.html', orden=orden)
        
    except Exception as e:
        print(f"❌ Error en orden_preview: {e}")
        return f"Error: {e}", 500