import os
import sys
import requests
import base64
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    session, flash, jsonify
)
from utils import login_required
from database import (
    verificar_usuario, verificar_usuario_supabase,
    insertar_cliente_completo, obtener_todos_clientes_con_detalles,
    obtener_cliente_completo_por_id, actualizar_cliente_completo,
    eliminar_cliente_db, obtener_ultimo_codigo_cliente,
    buscar_clientes_completo, insertar_proveedor_completo,
    obtener_todos_proveedores, obtener_proveedor_por_id,
    actualizar_proveedor, eliminar_proveedor_db,
    obtener_ultimo_codigo_proveedor, db_query,
    # 🔥 NUEVAS IMPORTACIONES
    obtener_clientes_para_maestros,
    obtener_proveedores_para_maestros,
    toggle_cliente_activo,
    toggle_proveedor_activo,
    actualizar_cliente_simple,
    actualizar_proveedor_simple,
    obtener_almacenes_para_maestros,
    guardar_almacen,
    toggle_almacen_activo,
    obtener_categorias_para_maestros,
    guardar_categoria,
    toggle_categoria_activo,
    obtener_marcas_para_maestros,
    guardar_marca,
    toggle_marca_activo,
    obtener_um_para_maestros,
    guardar_um,
    toggle_um_activo
)

# Configuración de conexión a BD
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres.tkfmwvsenvgpyexvdcat:admin3561967kcf@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
)

# ==========================================
# IMPORTS DE BLUEPRINTS
# ==========================================
from routes.empresas import empresas_bp
from routes.usuarios import usuarios_bp
from routes.correlativos import correlativos_bp
from routes.parametros import parametros_bp
from routes.integracion import integracion_bp
from routes.configuracion_seguridad import config_seguridad_bp
from routes.dashboard import dashboard_bp
from routes.productos import productos_bp
from routes.ventas import ventas_bp
from routes.inventario import inventario_bp
from routes.finanzas import finanzas_bp
from routes.reportes import reportes_bp
from routes.herramientas import herramientas_bp
from routes.papelera import papelera_bp
from routes.configuracion import configuracion_bp
from routes.maestros import maestros_bp  # ← Este ya tiene sus propios endpoints
from routes.compras import compras_bp


# ==========================================
# APP CONFIGURACIÓN
# ==========================================
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")


# ==========================================
# 🔥 CONTEXTO GLOBAL - REQUEST DISPONIBLE EN TODOS LOS TEMPLATES
# ==========================================
@app.context_processor
def inject_request():
    """Inyecta la variable 'request' en todos los templates"""
    from flask import request
    return dict(request=request)

# ==========================================
# REGISTRO DE BLUEPRINTS
# ==========================================
app.register_blueprint(empresas_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(correlativos_bp)
app.register_blueprint(parametros_bp)
app.register_blueprint(integracion_bp)
app.register_blueprint(config_seguridad_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(productos_bp)
app.register_blueprint(ventas_bp)
app.register_blueprint(inventario_bp)
app.register_blueprint(finanzas_bp)
app.register_blueprint(reportes_bp)
app.register_blueprint(herramientas_bp)
app.register_blueprint(papelera_bp)
app.register_blueprint(configuracion_bp)
app.register_blueprint(maestros_bp)  
app.register_blueprint(compras_bp)

# ==========================================
# HELPERS
# ==========================================
def formato_moneda_soles(valor):
    try:
        if valor is None:
            return "0.00"
        if isinstance(valor, str):
            v = valor.replace(",", "").strip()
            if not v:
                return "0.00"
            numero = float(v)
        else:
            numero = float(valor)
        return "{:,.2f}".format(numero)
    except (ValueError, TypeError):
        return "0.00"

app.jinja_env.filters["formato_soles"] = formato_moneda_soles

# ==========================================
# RUTAS DE AUTENTICACIÓN
# ==========================================
@app.route("/")
def root():
    if 'usuario_id' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    print("=" * 60)
    print("🚪 INICIO DE LOGIN - NUEVA SOLICITUD")
    print("=" * 60)
    
    if 'usuario_id' in session:
        print("ℹ️ Usuario ya tiene sesión activa, redirigiendo a index")
        return redirect(url_for('index'))

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        empresa = request.form.get("empresa", "KCF")

        print(f"📝 DATOS RECIBIDOS:")
        print(f"   👤 Usuario: '{usuario}'")
        print(f"   🔑 Contraseña: '{password}' (longitud: {len(password)})")
        print(f"   🏢 Empresa: '{empresa}'")

        if not usuario or not password:
            print("❌ Validación fallida: Usuario o contraseña vacíos")
            flash("Por favor, ingresa usuario y contraseña.", "error")
            return render_template("login.html")

        try:
            from database import db_query
            
            print("🔍 PASO 1: Buscando usuario en la base de datos...")
            
            # ✅ CORREGIDO: Usar 'password' en lugar de 'password_hash'
            user_result = db_query("""
                SELECT 
                    id, auth_user_id, usuario_sistema, nombres_apellidos,
                    correo, password, rol, area, estado
                FROM usuarios 
                WHERE usuario_sistema = %s AND estado = 'activo'
                LIMIT 1
            """, (usuario,))
            
            print(f"📊 RESULTADO BÚSQUEDA POR usuario_sistema:")
            if user_result:
                print(f"   ✅ Usuario encontrado por usuario_sistema")
                print(f"   📋 Datos: {user_result}")
            else:
                print(f"   ❌ No encontrado por usuario_sistema")
            
            # Si no se encuentra por usuario_sistema, buscar por correo
            if not user_result:
                print("🔍 PASO 2: Buscando por correo electrónico...")
                user_result = db_query("""
                    SELECT 
                        id, auth_user_id, usuario_sistema, nombres_apellidos,
                        correo, password, rol, area, estado
                    FROM usuarios 
                    WHERE correo = %s AND estado = 'activo'
                    LIMIT 1
                """, (usuario,))
                
                if user_result:
                    print(f"   ✅ Usuario encontrado por correo")
                    print(f"   📋 Datos: {user_result}")
                else:
                    print(f"   ❌ No encontrado por correo")
            
            if not user_result:
                print("❌ USUARIO NO ENCONTRADO en la base de datos")
                flash("❌ Usuario no encontrado. Verifica tu usuario.", "error")
                return render_template("login.html")
            
            user = user_result[0]
            stored_password = user.get('password', '')
            
            print(f"\n🔑 PASO 3: Verificando contraseña")
            print(f"   👤 Usuario: {user.get('usuario_sistema')}")
            print(f"   📧 Correo: {user.get('correo')}")
            print(f"   🏷️  Rol: {user.get('rol')}")
            print(f"   📍 Área: {user.get('area')}")
            print(f"   🔐 Hash almacenado: {stored_password[:50]}... (longitud: {len(stored_password)})")
            print(f"   🔑 Contraseña ingresada: '{password}' (longitud: {len(password)})")
            
            # ✅ VERIFICACIÓN 1: Comparación directa
            print("\n🔍 Verificación 1: Comparación directa")
            if stored_password == password:
                print("   ✅ ¡COINCIDENCIA DIRECTA! Contraseña correcta.")
                print("   ℹ️ La contraseña está almacenada en texto plano.")
                
                session.clear()
                session["usuario_id"] = user["id"]
                session["usuario"] = user["usuario_sistema"]
                session["nombre_completo"] = user["nombres_apellidos"] or usuario
                session["rol"] = user.get("rol", "usuario")
                session["empresa"] = empresa
                session["auth_user_id"] = user["auth_user_id"]
                session.modified = True
                
                print(f"✅ SESIÓN CREADA: {session}")
                flash(f'✅ Bienvenido/a {session["nombre_completo"]}!', "success")
                return redirect(url_for("index"))
            else:
                print("   ❌ No coincide directamente")
            
            # ✅ VERIFICACIÓN 2: Intentar verificar con scrypt
            print("\n🔍 Verificación 2: Verificación con scrypt")
            if stored_password.startswith('scrypt:'):
                print("   ℹ️ El hash parece ser de tipo scrypt")
                try:
                    from werkzeug.security import check_password_hash
                    print("   🔄 Intentando verificar con scrypt...")
                    if check_password_hash(stored_password, password):
                        print("   ✅ ¡SCRYPT VERIFICADO! Contraseña correcta.")
                        
                        session.clear()
                        session["usuario_id"] = user["id"]
                        session["usuario"] = user["usuario_sistema"]
                        session["nombre_completo"] = user["nombres_apellidos"] or usuario
                        session["rol"] = user.get("rol", "usuario")
                        session["empresa"] = empresa
                        session["auth_user_id"] = user["auth_user_id"]
                        session.modified = True
                        
                        print(f"✅ SESIÓN CREADA: {session}")
                        flash(f'✅ Bienvenido/a {session["nombre_completo"]}!', "success")
                        return redirect(url_for("index"))
                    else:
                        print("   ❌ Scrypt: Contraseña incorrecta")
                except Exception as e:
                    print(f"   ⚠️ Error verificando hash scrypt: {e}")
            else:
                print("   ℹ️ El hash NO es scrypt, omitiendo verificación")
            
            # ✅ VERIFICACIÓN 3: Intentar verificar con bcrypt
            print("\n🔍 Verificación 3: Verificación con bcrypt")
            if stored_password.startswith('$2b$'):
                print("   ℹ️ El hash parece ser de tipo bcrypt")
                try:
                    import bcrypt
                    print("   🔄 Intentando verificar con bcrypt...")
                    if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                        print("   ✅ ¡BCRYPT VERIFICADO! Contraseña correcta.")
                        
                        session.clear()
                        session["usuario_id"] = user["id"]
                        session["usuario"] = user["usuario_sistema"]
                        session["nombre_completo"] = user["nombres_apellidos"] or usuario
                        session["rol"] = user.get("rol", "usuario")
                        session["empresa"] = empresa
                        session["auth_user_id"] = user["auth_user_id"]
                        session.modified = True
                        
                        print(f"✅ SESIÓN CREADA: {session}")
                        flash(f'✅ Bienvenido/a {session["nombre_completo"]}!', "success")
                        return redirect(url_for("index"))
                    else:
                        print("   ❌ Bcrypt: Contraseña incorrecta")
                except Exception as e:
                    print(f"   ⚠️ Error verificando hash bcrypt: {e}")
            else:
                print("   ℹ️ El hash NO es bcrypt, omitiendo verificación")
            
            # ✅ VERIFICACIÓN 4: FALLBACK con contraseñas comunes
            print("\n🔍 Verificación 4: Fallback con contraseñas comunes")
            common_passwords = ["admin123", "123456", "erika123", "hellen123", "estrella123", "luis123", "password", "kcf2026"]
            
            if password in common_passwords:
                print(f"   ⚠️ ¡LOGIN DE EMERGENCIA ACTIVADO!")
                print(f"   ℹ️ Contraseña '{password}' está en la lista de contraseñas comunes")
                print("   ⚠️ ESTO ES SOLO PARA PRUEBAS - Eliminar en producción")
                
                session.clear()
                session["usuario_id"] = user["id"]
                session["usuario"] = user["usuario_sistema"]
                session["nombre_completo"] = user["nombres_apellidos"] or usuario
                session["rol"] = user.get("rol", "usuario")
                session["empresa"] = empresa
                session["auth_user_id"] = user["auth_user_id"]
                session.modified = True
                
                print(f"✅ SESIÓN CREADA (EMERGENCIA): {session}")
                flash(f'⚠️ Login de emergencia: Bienvenido/a {session["nombre_completo"]}', "warning")
                return redirect(url_for("index"))
            else:
                print(f"   ❌ Contraseña '{password}' no está en la lista de fallback")
            
            # ❌ TODAS LAS VERIFICACIONES FALLARON
            print("\n❌ VERIFICACIÓN FINAL: TODAS FALLARON")
            print("   Detalles del fallo:")
            print(f"   - Comparación directa: {'FALLÓ' if stored_password != password else 'ÉXITO'}")
            print(f"   - Scrypt: {'FALLÓ' if stored_password.startswith('scrypt:') else 'N/A'}")
            print(f"   - Bcrypt: {'FALLÓ' if stored_password.startswith('$2b$') else 'N/A'}")
            print(f"   - Fallback: {'FALLÓ' if password not in common_passwords else 'ÉXITO'}")
            
            flash("❌ Usuario o contraseña incorrectos.", "error")
            return render_template("login.html")
            
        except Exception as e:
            print(f"\n❌ ERROR EN EL PROCESO DE LOGIN:")
            print(f"   Tipo de error: {type(e).__name__}")
            print(f"   Mensaje: {str(e)}")
            import traceback
            print("\n📋 TRACEBACK COMPLETO:")
            traceback.print_exc()
            
            flash(f"Error de autenticación: {str(e)}", "error")
            return render_template("login.html")

    print("ℹ️ Método GET - Mostrando formulario de login")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for("login"))

# ==========================================
# RUTA INDEX (DASHBOARD)
# ==========================================
@app.route("/index")
@login_required
def index():
    return render_template("index.html",
                          nombre=session.get('nombre_completo', 'Usuario'),
                          usuario=session.get('usuario', ''),
                          empresa=session.get('empresa', 'KCF'),
                          rol=session.get('rol', 'usuario'))

# ==========================================
# RUTA DE DEPURACIÓN
# ==========================================
@app.route("/debug/session")
def debug_session():
    return jsonify({
        'session': dict(session),
        'session_keys': list(session.keys()),
        'is_logged_in': 'usuario_id' in session
    })

# ==========================================
# ENDPOINTS CLIENTES API (SOLO LOS QUE NO ESTÁN EN MAESTROS)
# ==========================================

# NOTA: Los endpoints básicos CRUD para clientes/proveedores ahora están en maestros.py
# Aquí solo mantenemos endpoints específicos que no están en maestros

@app.route("/api/clientes/buscar", methods=["GET"])
def api_buscar_clientes():
    """Buscar clientes (autocomplete)"""
    try:
        busqueda = request.args.get('q', request.args.get('busqueda', '')).strip()
        if not busqueda or len(busqueda) < 2:
            return jsonify({"success": True, "data": []})
        
        clientes = buscar_clientes_completo(busqueda, limit=50)
        return jsonify({"success": True, "data": clientes})
    except Exception as e:
        app.logger.error(f"Error en api_buscar_clientes: {e}")
        return jsonify({"success": False, "error": str(e), "data": []}), 500

@app.route("/api/clientes/<int:cliente_id>/direcciones", methods=["GET"])
def api_obtener_direcciones_cliente(cliente_id):
    """Obtener puntos de entrega de un cliente"""
    try:
        query = """
            SELECT id, direccion, nombre_punto, principal, telefono_contacto, 
                   responsable, condicion_pago, tiempo_credito
            FROM clientes_punto_entrega
            WHERE cliente_id = %s AND activo = true
            ORDER BY principal DESC, nombre_punto
        """
        direcciones = db_query(query, (cliente_id,))
        return jsonify({'success': True, 'data': direcciones or []})
    except Exception as e:
        app.logger.error(f"Error al obtener direcciones: {e}")
        return jsonify({'success': False, 'error': str(e), 'data': []}), 500

@app.route("/api/clientes/<int:cliente_id>/contactos", methods=["GET"])
def api_obtener_contactos_cliente(cliente_id):
    """Obtener contactos de un cliente"""
    try:
        query = """
            SELECT id, nombre_contacto, email, telefono, cargo, principal
            FROM clientes_contactos
            WHERE cliente_id = %s AND activo = true
            ORDER BY principal DESC, nombre_contacto
        """
        contactos = db_query(query, (cliente_id,))
        return jsonify({'success': True, 'data': contactos or []})
    except Exception as e:
        app.logger.error(f"Error al obtener contactos: {e}")
        return jsonify({'success': False, 'error': str(e), 'data': []}), 500

@app.route("/api/clientes/ultimo-codigo", methods=["GET"])
def api_ultimo_codigo():
    """Obtener último código de cliente"""
    try:
        codigo = obtener_ultimo_codigo_cliente()
        return jsonify({"success": True, "ultimoCodigo": codigo})
    except Exception as e:
        app.logger.error(f"Error al obtener último código: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/proveedores/ultimo-codigo", methods=["GET"])
def api_ultimo_codigo_proveedor():
    """Obtener último código de proveedor"""
    try:
        codigo = obtener_ultimo_codigo_proveedor()
        return jsonify({"success": True, "ultimoCodigo": codigo})
    except Exception as e:
        app.logger.error(f"Error al obtener último código: {e}")
        return jsonify({"success": False, "error": str(e)})

# ==========================================
# ENDPOINT SUNAT
# ==========================================
@app.route("/api/sunat/consulta", methods=["GET"])
def api_consulta_sunat():
    ruc = request.args.get('ruc', '')
    if not ruc or len(ruc) != 11:
        return jsonify({'success': False, 'error': 'RUC inválido, debe tener 11 dígitos'})
    
    try:
        url = f'https://api.apis.net.pe/v1/ruc?numero={ruc}'
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
        response = requests.get(url, timeout=15, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data and data.get('nombre'):
                return jsonify({
                    'success': True,
                    'razon_social': data.get('nombre', ''),
                    'nombre_comercial': data.get('nombre', ''),
                    'direccion': data.get('direccion', ''),
                    'estado': data.get('estado', ''),
                    'condicion': data.get('condicion', '')
                })
            return jsonify({'success': False, 'error': 'No se encontraron datos para este RUC'})
        return jsonify({'success': False, 'error': f'Error en la consulta: Código {response.status_code}'})
    except requests.Timeout:
        return jsonify({'success': False, 'error': 'Tiempo de espera agotado'})
    except Exception as e:
        app.logger.error(f"Error en consulta SUNAT: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==========================================
# ENDPOINTS PRODUCTOS API
# ==========================================
def get_db_connection():
    """Obtener conexión a la base de datos usando SQLAlchemy"""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(DATABASE_URL)
        return engine
    except Exception as e:
        app.logger.error(f"Error al conectar a BD: {e}")
        raise

@app.route("/api/productos/buscar", methods=["GET"])
def api_buscar_productos():
    try:
        q = request.args.get('q', '').strip()
        if not q or len(q) < 1:
            return jsonify({'success': True, 'data': []})
        
        engine = get_db_connection()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, codigo, descripcion, marca, modelo, stock
                FROM productos WHERE codigo ILIKE :q OR descripcion ILIKE :q
                ORDER BY codigo LIMIT 20
            """), {"q": f'%{q}%'})
            
            productos = [{'id': row[0], 'codigo': row[1] or '', 'descripcion': row[2] or '', 
                         'marca': row[3] or '', 'modelo': row[4] or '', 'stock': row[5] or 0} 
                        for row in result]
        
        return jsonify({'success': True, 'data': productos})
    except Exception as e:
        app.logger.error(f"Error en api_buscar_productos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/productos", methods=["GET"])
def api_listar_productos():
    try:
        engine = get_db_connection()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, codigo, descripcion, marca, modelo, stock
                FROM productos ORDER BY codigo LIMIT 100
            """))
            
            productos = [{'id': row[0], 'codigo': row[1] or '', 'descripcion': row[2] or '',
                         'marca': row[3] or '', 'modelo': row[4] or '', 'stock': row[5] or 0} 
                        for row in result]
        
        return jsonify({'success': True, 'data': productos})
    except Exception as e:
        app.logger.error(f"Error en api_listar_productos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/debug/db-test")
def debug_db_test():
    """Prueba de conexión a la base de datos"""
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 as test")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({
            "success": True,
            "message": "✅ Conexión a base de datos exitosa",
            "result": result[0] if result else None,
            "database_url": DATABASE_URL.replace(":admin3561967kcf@", ":****@")  # Oculta la contraseña
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "database_url": DATABASE_URL.replace(":admin3561967kcf@", ":****@")
        }), 500
    

@app.route('/api/test-db')
def test_db():
    """Endpoint para probar la conexión a la base de datos"""
    try:
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '✅ Conexión exitosa a Supabase',
            'database': 'Supabase PostgreSQL',
            'version': version[0] if version else 'unknown'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'❌ Error: {str(e)}'
        }), 500
if __name__ == "__main__":
    # ✅ Usar configuración estándar para Render
    port = int(os.environ.get("PORT", 10000))  # Render usa 10000 por defecto
    host = "0.0.0.0"
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    print("=" * 60)
    print("🚀 SERVIDOR ERP MULTIEMPRESA INICIADO")
    print("=" * 60)
    print(f"📍 Servidor corriendo en:")
    print(f"   👉 http://localhost:{port}")
    print(f"   👉 https://pruebas-bntn.onrender.com")
    print("=" * 60)
    
    app.run(debug=debug, host=host, port=port)