from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response, send_from_directory
from supabase import create_client
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
import os

import os
# Para Vercel: las carpetas templates y static están al mismo nivel que api/
# Para local: también al mismo nivel
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.environ.get('SECRET_KEY', 'clave-secreta-app-pacientes-2026')

# ============================================
# CONFIGURACION SUPABASE (desde variables de entorno)
# ============================================
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://lbqichqgufkpataypqqs.supabase.co')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

print(f"Conectando a: {SUPABASE_URL}")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) if SUPABASE_ANON_KEY else None
    supabase_service = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if SUPABASE_SERVICE_KEY else None
    print("Conexion exitosa a Supabase (Anon + Service Role)")
except Exception as e:
    print(f"Error de conexion: {e}")
    supabase = None
    supabase_service = None

# ============================================
# SERVIR ARCHIVOS ESTATICOS EN VERCEL
# ============================================

@app.route('/static/img/<path:filename>')
def serve_image(filename):
    return send_from_directory(os.path.join(static_dir, 'img'), filename)

@app.route('/static/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(static_dir, 'css'), filename)

@app.route('/static/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(static_dir, 'js'), filename)

# ============================================
# RUTAS PRINCIPALES
# ============================================

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        response = make_response(render_template('login.html'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    data = request.get_json()
    usuario = data.get('usuario', '').strip().lower()
    contraseña = data.get('contraseña', '')

    if not usuario or not contraseña:
        return jsonify({'error': 'Usuario y contraseña son obligatorios'}), 400

    try:
        response = supabase.table('pac_usuarios').select('*').eq('usuario', usuario).execute()

        if not response.data:
            return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401

        user = response.data[0]

        if user.get('estado') != 'activo':
            return jsonify({'error': 'Usuario inactivo. Contacte al administrador.'}), 403

        password_ok = False
        stored_password = user['contraseña']

        if stored_password.startswith('pbkdf2:') or stored_password.startswith('scrypt:'):
            password_ok = check_password_hash(stored_password, contraseña)
        else:
            password_ok = stored_password == contraseña
            if password_ok:
                new_hash = generate_password_hash(contraseña, method='pbkdf2:sha256')
                supabase_service.table('pac_usuarios').update({'contraseña': new_hash}).eq('id', user['id']).execute()

        if not password_ok:
            return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401

        session['user'] = {
            'id': user['id'],
            'nombres': user['nombres'],
            'apellidos': user['apellidos'],
            'usuario': user['usuario'],
            'rol': user['rol']
        }

        return jsonify({'success': True, 'user': session['user']})

    except Exception as e:
        print(f"Error en login: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    response = make_response(render_template('dashboard.html', user=session['user']))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/logout')
def logout():
    session.clear()
    response = redirect('/login')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ============================================
# API - STATS
# ============================================

@app.route('/api/stats')
def stats():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        pacientes_resp = supabase.table('pac_pacientes').select('id').execute()
        total_pacientes = len(pacientes_resp.data) if pacientes_resp.data else 0

        hoy = date.today().isoformat()
        atenciones_hoy_resp = supabase.table('pac_atenciones').select('id').eq('fecha_atencion', hoy).execute()
        total_hoy = len(atenciones_hoy_resp.data) if atenciones_hoy_resp.data else 0

        mes_actual = date.today().month
        anio_actual = date.today().year
        atenciones_mes_resp = supabase.table('pac_atenciones').select('id').eq('mes', mes_actual).eq('anio', anio_actual).execute()
        total_mes = len(atenciones_mes_resp.data) if atenciones_mes_resp.data else 0

        judicial_resp = supabase.table('pac_pacientes').select('id').eq('origen', 'PODER JUDICIAL').execute()
        total_judicial = len(judicial_resp.data) if judicial_resp.data else 0

        inicio_semana = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        validaciones_resp = supabase.table('pac_validaciones_sis').select('id').gte('fecha_validacion', inicio_semana).execute()
        total_validaciones = len(validaciones_resp.data) if validaciones_resp.data else 0

        citas_pendientes_resp = supabase.table('pac_citas_programadas').select('id').eq('estado', 'PENDIENTE_VALIDACION').execute()
        total_citas_pendientes = len(citas_pendientes_resp.data) if citas_pendientes_resp.data else 0

        return jsonify({
            'pacientes': total_pacientes,
            'hoy': total_hoy,
            'mes': total_mes,
            'judicial': total_judicial,
            'validaciones_semana': total_validaciones,
            'citas_pendientes_validacion': total_citas_pendientes
        })
    except Exception as e:
        print(f"Error en stats: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# API - ATENCIONES POR MES
# ============================================

@app.route('/api/atenciones-por-mes')
def atenciones_por_mes():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        anio = request.args.get('anio', date.today().year, type=int)
        response = supabase.table('pac_atenciones').select('mes').eq('anio', anio).execute()
        datos = [0] * 12
        for atencion in response.data:
            mes = atencion.get('mes')
            if mes and 1 <= mes <= 12:
                datos[mes - 1] += 1
        return jsonify({'data': datos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# API - DATOS PERSONALES POR DNI (RENIEC)
# ============================================

@app.route('/api/pacientes/datos-personales/<dni>')
def get_datos_personales(dni):
    """Busca datos personales en la tabla de referencia RENIEC.

    Usa supabase_service (Service Role Key) para leer la tabla
    pac_datos_personales que tiene RLS activado.

    La tabla se vacía y recarga mensualmente con datos actualizados.
    """
    # Verificar conexión Service Role
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500

    try:
        # Validar que sea DNI numérico de 8 dígitos
        if not dni or not dni.isdigit() or len(dni) != 8:
            return jsonify({'success': False, 'error': 'DNI inválido'}), 400

        # Usar SERVICE ROLE para leer tabla con RLS activado
        response = supabase_service.table('pac_datos_personales')            .select('dni, apellidos_nombres, fecha_nacimiento, sexo')            .eq('dni', dni)            .limit(1)            .execute()

        if response.data and len(response.data) > 0:
            return jsonify({'success': True, 'data': response.data[0]})
        else:
            return jsonify({'success': False, 'message': 'DNI no encontrado'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# API - PROCEDIMIENTOS
# ============================================

@app.route('/api/procedimientos')
def buscar_procedimientos():
    """Busca procedimientos filtrados por diagnósticos seleccionados.

    Reglas:
    - condicion='TODOS': aparece con cualquier diagnóstico
    - condicion='Z133': solo aparece si Z133 está en diagnósticos seleccionados
    - 99402.09 es excepción: está en ambas categorías
    """
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        query = request.args.get('q', '').strip()
        diagnosticos = request.args.get('diagnosticos', '').strip()

        # Construir query base
        db_query = supabase_service.table('pac_procedimientos').select('*')

        if query:
            db_query = db_query.or_(f"cpms.ilike.%{query}%,descripcion.ilike.%{query}%")

        # Filtrar por condición según diagnósticos seleccionados
        diagnosticos_list = [d.strip() for d in diagnosticos.split(',') if d.strip()]
        tiene_z133 = 'Z133' in diagnosticos_list

        if diagnosticos_list:
            # Si tiene Z133, mostrar TODOS + Z133
            # Si NO tiene Z133, mostrar solo TODOS
            if tiene_z133:
                db_query = db_query.in_('condicion', ['TODOS', 'Z133'])
            else:
                db_query = db_query.eq('condicion', 'TODOS')
        else:
            # Sin diagnósticos seleccionados, mostrar solo TODOS
            db_query = db_query.eq('condicion', 'TODOS')

        response = db_query.limit(20).execute()
        return jsonify({'data': response.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# API - VERIFICAR DUPLICADOS (TIEMPO REAL)
# ============================================

@app.route('/api/pacientes/verificar-duplicado', methods=['GET'])
def verificar_duplicado_paciente():
    """Endpoint para verificación en tiempo real de duplicados al registrar pacientes."""
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        tipo = request.args.get('tipo', '').strip().upper()
        numero = request.args.get('numero', '').strip()
        hcl = request.args.get('hcl', '').strip()

        if tipo == 'INDOCUMENTADO':
            if not hcl:
                return jsonify({'existe': False})
            existe = supabase_service.table('pac_pacientes')                .select('id, apellidos_nombres, tipo_documento, hcl, estado, codigo_temporal')                .eq('hcl', hcl).execute()
            if existe.data and len(existe.data) > 0:
                p = existe.data[0]
                return jsonify({'existe': True, 'paciente': {
                    'id': p.get('id'), 'apellidos_nombres': p.get('apellidos_nombres'),
                    'tipo_documento': p.get('tipo_documento'), 'codigo_temporal': p.get('codigo_temporal'),
                    'hcl': p.get('hcl'), 'estado': p.get('estado')
                }})
            return jsonify({'existe': False})
        else:
            if not tipo or not numero:
                return jsonify({'existe': False})
            existe = supabase_service.table('pac_pacientes')                .select('id, apellidos_nombres, tipo_documento, numero_documento, hcl, estado')                .eq('tipo_documento', tipo).eq('numero_documento', numero).execute()
            if existe.data and len(existe.data) > 0:
                p = existe.data[0]
                return jsonify({'existe': True, 'paciente': {
                    'id': p.get('id'), 'apellidos_nombres': p.get('apellidos_nombres'),
                    'tipo_documento': p.get('tipo_documento'), 'numero_documento': p.get('numero_documento'),
                    'hcl': p.get('hcl'), 'estado': p.get('estado')
                }})
            return jsonify({'existe': False})
    except Exception as e:
        return jsonify({'existe': False, 'error': str(e)}), 500

# ============================================
# API - PACIENTES (CRUD)
# ============================================

@app.route('/api/pacientes', methods=['GET'])
def get_pacientes():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        busqueda = request.args.get('q', '')
        query = supabase.table('pac_pacientes').select('*').order('created_at', desc=True)
        if busqueda:
            query = query.or_(f"apellidos_nombres.ilike.%{busqueda}%,numero_documento.ilike.%{busqueda}%,hcl.ilike.%{busqueda}%")
        response = query.execute()
        return jsonify({'data': response.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pacientes', methods=['POST'])
def create_paciente():
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        data = request.get_json()
        tipo_doc = data.get('tipo_documento')

        # ========== VALIDACION ANTI-DUPLICADOS ==========
        if tipo_doc == 'INDOCUMENTADO':
            hcl = data.get('hcl', '').strip()
            if not hcl:
                return jsonify({'error': 'Para pacientes indocumentados, el HCL es obligatorio como identificador unico'}), 400

            existe = supabase_service.table('pac_pacientes')                .select('id, apellidos_nombres, hcl')                .eq('hcl', hcl)                .execute()
            if existe.data and len(existe.data) > 0:
                p = existe.data[0]
                return jsonify({
                    'error': f"Ya existe un paciente indocumentado con HCL {hcl}: {p.get('apellidos_nombres', '')}",
                    'paciente_existente': p
                }), 409
        else:
            num_doc = data.get('numero_documento', '').strip()
            if not num_doc:
                return jsonify({'error': f'El numero de {tipo_doc} es obligatorio'}), 400

            existe = supabase_service.table('pac_pacientes')                .select('id, apellidos_nombres, tipo_documento, numero_documento')                .eq('tipo_documento', tipo_doc)                .eq('numero_documento', num_doc)                .execute()
            if existe.data and len(existe.data) > 0:
                p = existe.data[0]
                return jsonify({
                    'error': f"Ya existe un paciente con {tipo_doc} {num_doc}: {p.get('apellidos_nombres', '')}",
                    'paciente_existente': p
                }), 409
        # ========== FIN VALIDACION ==========

        if data.get('fecha_nacimiento'):
            try:
                fecha_nac = datetime.strptime(data['fecha_nacimiento'], '%Y-%m-%d').date()
                hoy = date.today()
                data['edad'] = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
            except:
                data['edad'] = None
        if data.get('peso') and data.get('talla'):
            try:
                peso = float(data['peso'])
                talla = float(data['talla'])
                if talla > 3:
                    talla = talla / 100
                if talla > 0:
                    data['talla'] = talla
                    data['imc'] = round(peso / (talla * talla), 2)
            except:
                pass
        response = supabase_service.table('pac_pacientes').insert(data).execute()
        return jsonify({'data': response.data, 'message': 'Paciente registrado correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pacientes/<id>', methods=['GET'])
def get_paciente(id):
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        response = supabase.table('pac_pacientes').select('*').eq('id', id).single().execute()
        return jsonify({'data': response.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pacientes/<id>', methods=['PUT'])
def update_paciente(id):
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        data = request.get_json()
        if data.get('fecha_nacimiento'):
            try:
                fecha_nac = datetime.strptime(data['fecha_nacimiento'], '%Y-%m-%d').date()
                hoy = date.today()
                data['edad'] = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
            except:
                pass
        if data.get('peso') and data.get('talla'):
            try:
                peso = float(data['peso'])
                talla = float(data['talla'])
                if talla > 0:
                    data['imc'] = round(peso / (talla * talla), 2)
            except:
                pass
        response = supabase_service.table('pac_pacientes').update(data).eq('id', id).execute()
        return jsonify({'data': response.data, 'message': 'Paciente actualizado correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pacientes/<id>', methods=['DELETE'])
def delete_paciente(id):
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        response = supabase_service.table('pac_pacientes').delete().eq('id', id).execute()
        return jsonify({'message': 'Paciente eliminado correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# API - ATENCIONES
# ============================================

@app.route('/api/atenciones', methods=['GET'])
def get_atenciones():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        paciente_id = request.args.get('paciente_id')
        query = supabase.table('pac_atenciones').select('*').order('fecha_atencion', desc=True)
        if paciente_id:
            query = query.eq('paciente_id', paciente_id)
        response = query.execute()
        return jsonify({'data': response.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/atenciones', methods=['POST'])
def create_atencion():
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        data = request.get_json()
        if data.get('fecha_atencion'):
            try:
                fecha = datetime.strptime(data['fecha_atencion'], '%Y-%m-%d').date()
                data['mes'] = fecha.month
                data['anio'] = fecha.year
            except:
                pass
        if data.get('peso') and data.get('talla'):
            try:
                peso = float(data['peso'])
                talla = float(data['talla'])
                if talla > 0:
                    data['imc'] = round(peso / (talla * talla), 2)
            except:
                pass
        if session.get('user'):
            data['registrado_por'] = session['user']['id']

        response = supabase_service.table('pac_atenciones').insert(data).execute()
        atencion_id = response.data[0]['id'] if response.data else None

        if data.get('proxima_cita') and not data.get('finaliza_proceso'):
            try:
                cita_data = {
                    'paciente_id': data['paciente_id'],
                    'atencion_id': atencion_id,
                    'fecha_cita_sugerida': data['proxima_cita'],
                    'estado': 'PENDIENTE_VALIDACION',
                    'created_at': datetime.now().isoformat()
                }
                supabase_service.table('pac_citas_programadas').insert(cita_data).execute()
            except Exception as e_cita:
                print(f"Error creando cita: {e_cita}")

        if data.get('finaliza_proceso'):
            supabase_service.table('pac_pacientes').update({'estado': 'inactivo'}).eq('id', data['paciente_id']).execute()

        return jsonify({'data': response.data, 'message': 'Atencion registrada correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/atenciones/<id>', methods=['GET'])
def get_atencion(id):
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        response = supabase.table('pac_atenciones').select('*').eq('id', id).single().execute()
        return jsonify({'data': response.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/atenciones/<id>', methods=['PUT'])
def update_atencion(id):
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        data = request.get_json()
        if data.get('fecha_atencion'):
            try:
                fecha = datetime.strptime(data['fecha_atencion'], '%Y-%m-%d').date()
                data['mes'] = fecha.month
                data['anio'] = fecha.year
            except:
                pass
        if data.get('peso') and data.get('talla'):
            try:
                peso = float(data['peso'])
                talla = float(data['talla'])
                if talla > 0:
                    data['imc'] = round(peso / (talla * talla), 2)
            except:
                pass
        response = supabase_service.table('pac_atenciones').update(data).eq('id', id).execute()
        return jsonify({'data': response.data, 'message': 'Atencion actualizada correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/atenciones/<id>', methods=['DELETE'])
def delete_atencion(id):
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        response = supabase_service.table('pac_atenciones').delete().eq('id', id).execute()
        return jsonify({'message': 'Atencion eliminada correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# API - CITAS PROGRAMADAS
# ============================================

@app.route('/api/citas-programadas', methods=['GET'])
def get_citas_programadas():
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        estado = request.args.get('estado', 'PENDIENTE_VALIDACION')
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')

        query = supabase_service.table('pac_citas_programadas').select('*, pac_pacientes(*)').eq('estado', estado)

        if estado == 'VALIDADO':
            if fecha_desde:
                query = query.gte('fecha_cita_confirmada', fecha_desde)
            if fecha_hasta:
                query = query.lte('fecha_cita_confirmada', fecha_hasta)
        else:
            if fecha_desde:
                query = query.gte('fecha_cita_sugerida', fecha_desde)
            if fecha_hasta:
                query = query.lte('fecha_cita_sugerida', fecha_hasta)

        result = query.order('fecha_cita_sugerida', desc=False).execute()
        return jsonify({'success': True, 'data': result.data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/citas-programadas/<cita_id>', methods=['PUT'])
def update_cita_programada(cita_id):
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        data = request.get_json()
        update_data = {}
        if 'fecha_cita_confirmada' in data:
            update_data['fecha_cita_confirmada'] = data['fecha_cita_confirmada']
        if 'estado' in data:
            update_data['estado'] = data['estado']
        if 'observaciones' in data:
            update_data['observaciones'] = data['observaciones']
        if 'validacion_sis_id' in data:
            update_data['validacion_sis_id'] = data['validacion_sis_id']
        update_data['updated_at'] = datetime.now().isoformat()

        result = supabase_service.table('pac_citas_programadas').update(update_data).eq('id', cita_id).execute()
        return jsonify({'success': True, 'data': result.data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# API - VALIDACION SIS
# ============================================

@app.route('/api/validaciones-sis', methods=['GET'])
def get_validaciones_sis():
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        result = supabase_service.table('pac_validaciones_sis').select('*, pac_pacientes(*), pac_citas_programadas(*)').order('fecha_validacion', desc=True).execute()
        return jsonify({'success': True, 'data': result.data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/validaciones-sis', methods=['POST'])
def create_validacion_sis():
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        data = request.get_json()
        usuario_id = session.get('user', {}).get('id')

        validacion_data = {
            'paciente_id': data['paciente_id'],
            'cita_programada_id': data.get('cita_programada_id'),
            'fecha_validacion': data['fecha_validacion'],
            'sis_estado': data['sis_estado'],
            'observacion': data.get('observaciones'),
            'validado_por': str(usuario_id) if usuario_id else None,
            'semana_anio': datetime.strptime(data['fecha_validacion'], '%Y-%m-%d').isocalendar()[1],
            'anio': datetime.strptime(data['fecha_validacion'], '%Y-%m-%d').year
        }

        result = supabase_service.table('pac_validaciones_sis').insert(validacion_data).execute()
        validacion_id = result.data[0]['id']

        if data.get('cita_programada_id'):
            cita_update = {
                'estado': 'VALIDADO',
                'validacion_sis_id': validacion_id,
                'updated_at': datetime.now().isoformat()
            }
            cita = supabase_service.table('pac_citas_programadas').select('fecha_cita_sugerida').eq('id', data['cita_programada_id']).execute()
            if cita.data:
                cita_update['fecha_cita_confirmada'] = cita.data[0]['fecha_cita_sugerida']
            supabase_service.table('pac_citas_programadas').update(cita_update).eq('id', data['cita_programada_id']).execute()

        supabase_service.table('pac_pacientes').update({
            'sis_ultima_validacion': data['fecha_validacion'],
            'sis_estado_actual': data['sis_estado']
        }).eq('id', data['paciente_id']).execute()

        return jsonify({'success': True, 'message': 'Validación registrada', 'data': result.data[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/validaciones-sis/resumen-semanal', methods=['GET'])
def get_resumen_validaciones_sis():
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        hoy = date.today()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)

        result = supabase_service.table('pac_validaciones_sis').select('sis_estado, fua_generado').gte('fecha_validacion', inicio_semana.isoformat()).lte('fecha_validacion', fin_semana.isoformat()).execute()

        data = result.data or []
        resumen = {
            'total': len(data),
            'activo': sum(1 for v in data if v.get('sis_estado') == 'ACTIVO'),
            'inactivo': sum(1 for v in data if v.get('sis_estado') == 'INACTIVO'),
            'no_encontrado': sum(1 for v in data if v.get('sis_estado') == 'NO ENCONTRADO'),
            'con_fua': sum(1 for v in data if v.get('fua_generado')),
            'sin_fua': sum(1 for v in data if not v.get('fua_generado'))
        }
        return jsonify({'success': True, 'data': resumen})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/validaciones-sis/<validacion_id>', methods=['DELETE'])
def delete_validacion_sis(validacion_id):
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        validacion = supabase_service.table('pac_validaciones_sis').select('cita_programada_id').eq('id', validacion_id).execute()
        cita_id = validacion.data[0]['cita_programada_id'] if validacion.data else None

        supabase_service.table('pac_validaciones_sis').delete().eq('id', validacion_id).execute()

        if cita_id:
            supabase_service.table('pac_citas_programadas').update({
                'estado': 'PENDIENTE_VALIDACION',
                'validacion_sis_id': None,
                'fecha_cita_confirmada': None
            }).eq('id', cita_id).execute()

        return jsonify({'success': True, 'message': 'Validación eliminada'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/citas-programadas/<cita_id>/confirmar', methods=['PUT'])
def confirmar_cita_admision(cita_id):
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        data = request.get_json()
        update_data = {'updated_at': datetime.now().isoformat()}
        if 'fecha_cita_confirmada' in data:
            update_data['fecha_cita_confirmada'] = data['fecha_cita_confirmada']
        if 'fua_generado' in data:
            update_data['fua_generado'] = data['fua_generado']
        if 'observaciones_admision' in data:
            update_data['observaciones_admision'] = data['observaciones_admision']

        result = supabase_service.table('pac_citas_programadas').update(update_data).eq('id', cita_id).execute()
        return jsonify({'success': True, 'message': 'Cita confirmada', 'data': result.data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# API - PROGRAMACION ANUAL
# ============================================

@app.route('/api/programacion-anual', methods=['GET'])
def get_programacion_anual():
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        anio = int(request.args.get('anio', datetime.now().year))
        inicio = f"{anio}-01-01"
        fin = f"{anio}-12-31"

        result = supabase_service.table('pac_citas_programadas').select('*, pac_pacientes(origen)').eq('estado', 'VALIDADO').gte('fecha_cita_confirmada', inicio).lte('fecha_cita_confirmada', fin).execute()

        citas = result.data or []
        programacion = {}
        for mes in range(1, 13):
            programacion[mes] = {
                'PODER JUDICIAL': {'pacientes': 0, 'atenciones': 0},
                'CEM': {'pacientes': 0, 'atenciones': 0}
            }

        for cita in citas:
            fecha = datetime.strptime(cita['fecha_cita_confirmada'], '%Y-%m-%d')
            mes = fecha.month
            origen = cita['pac_pacientes']['origen'] if cita.get('pac_pacientes') else 'PODER JUDICIAL'
            if origen not in programacion[mes]:
                origen = 'PODER JUDICIAL'
            programacion[mes][origen]['pacientes'] += 1
            programacion[mes][origen]['atenciones'] += 1

        return jsonify({'success': True, 'data': programacion})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# API - PENDIENTES POR ATENDER
# ============================================

@app.route('/api/pendientes-atender', methods=['GET'])
def get_pendientes_atender():
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        hoy = date.today().isoformat()
        limite = (date.today() + timedelta(days=7)).isoformat()

        result = supabase_service.table('pac_citas_programadas').select('*, pac_pacientes(*)').eq('estado', 'VALIDADO').gte('fecha_cita_confirmada', hoy).lte('fecha_cita_confirmada', limite).order('fecha_cita_confirmada', desc=False).execute()

        return jsonify({'success': True, 'data': result.data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# API - USUARIOS
# ============================================

@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    if session.get('user', {}).get('rol') != 'administrador':
        return jsonify({'error': 'No autorizado'}), 403
    try:
        response = supabase.table('pac_usuarios').select('id, nombres, apellidos, usuario, rol, estado, created_at').execute()
        return jsonify({'data': response.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios', methods=['POST'])
def create_usuario():
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    if session.get('user', {}).get('rol') != 'administrador':
        return jsonify({'error': 'No autorizado'}), 403

    data = request.get_json()
    campos_requeridos = ['nombres', 'apellidos', 'usuario', 'contraseña', 'rol']
    for campo in campos_requeridos:
        if not data.get(campo) or str(data.get(campo)).strip() == '':
            return jsonify({'error': f'El campo "{campo}" es obligatorio'}), 400

    if data['rol'] not in ['administrador', 'usuario']:
        return jsonify({'error': 'Rol no válido'}), 400
    if len(data['contraseña']) < 6:
        return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400

    try:
        existe = supabase.table('pac_usuarios').select('id').eq('usuario', data['usuario'].strip().lower()).execute()
        if existe.data:
            return jsonify({'error': 'El nombre de usuario ya existe'}), 409

        password_hash = generate_password_hash(data['contraseña'], method='pbkdf2:sha256')
        nuevo_usuario = {
            'nombres': data['nombres'].strip(),
            'apellidos': data['apellidos'].strip(),
            'usuario': data['usuario'].strip().lower(),
            'contraseña': password_hash,
            'rol': data['rol'],
            'estado': 'activo'
        }
        response = supabase_service.table('pac_usuarios').insert(nuevo_usuario).execute()
        return jsonify({'data': response.data, 'message': 'Usuario creado correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios/<uuid:id>', methods=['PUT'])
def update_usuario(id):
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    if session.get('user', {}).get('rol') != 'administrador':
        return jsonify({'error': 'No autorizado'}), 403

    data = request.get_json()
    try:
        usuario_actual = supabase.table('pac_usuarios').select('usuario').eq('id', str(id)).execute()
        if usuario_actual.data and usuario_actual.data[0]['usuario'] == 'admin':
            usuario_editor = session.get('user', {}).get('usuario')
            if usuario_editor != 'admin':
                return jsonify({'error': 'No puedes editar al usuario administrador principal'}), 403

        update_data = {}
        for campo in ['nombres', 'apellidos', 'rol', 'estado']:
            if campo in data:
                update_data[campo] = data[campo].strip() if isinstance(data[campo], str) else data[campo]

        if data.get('contraseña'):
            if len(data['contraseña']) < 6:
                return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
            update_data['contraseña'] = generate_password_hash(data['contraseña'], method='pbkdf2:sha256')

        if not update_data:
            return jsonify({'error': 'No hay campos para actualizar'}), 400

        response = supabase_service.table('pac_usuarios').update(update_data).eq('id', str(id)).execute()
        return jsonify({'data': response.data, 'message': 'Usuario actualizado correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios/<uuid:id>', methods=['DELETE'])
def delete_usuario(id):
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    if session.get('user', {}).get('rol') != 'administrador':
        return jsonify({'error': 'No autorizado'}), 403
    try:
        usuario_objetivo = supabase.table('pac_usuarios').select('usuario').eq('id', str(id)).execute()
        if usuario_objetivo.data:
            usuario_target = usuario_objetivo.data[0]['usuario']
            usuario_actual = session.get('user', {}).get('usuario')
            if usuario_target == usuario_actual:
                return jsonify({'error': 'No puedes eliminar tu propio usuario'}), 400
            if usuario_target == 'admin':
                return jsonify({'error': 'No puedes eliminar al usuario administrador principal'}), 400
        supabase_service.table('pac_usuarios').delete().eq('id', str(id)).execute()
        return jsonify({'message': 'Usuario eliminado correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/usuarios/<uuid:id>/toggle', methods=['PATCH'])
def toggle_usuario_estado(id):
    if supabase_service is None:
        return jsonify({'error': 'Sin conexion'}), 500
    if session.get('user', {}).get('rol') != 'administrador':
        return jsonify({'error': 'No autorizado'}), 403
    try:
        usuario = supabase.table('pac_usuarios').select('estado, usuario').eq('id', str(id)).execute()
        if not usuario.data:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        if usuario.data[0]['usuario'] == 'admin':
            return jsonify({'error': 'No puedes desactivar al administrador principal'}), 400
        nuevo_estado = 'inactivo' if usuario.data[0]['estado'] == 'activo' else 'activo'
        response = supabase_service.table('pac_usuarios').update({'estado': nuevo_estado}).eq('id', str(id)).execute()
        return jsonify({'data': response.data, 'estado': nuevo_estado, 'message': f'Usuario {nuevo_estado}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# API - REPORTES
# ============================================

@app.route('/api/reportes/atenciones-por-origen')
def reporte_atenciones_por_origen():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        anio = request.args.get('anio', date.today().year, type=int)
        mes = request.args.get('mes', type=int)
        query = supabase.table('pac_atenciones').select('paciente_id, mes, anio').eq('anio', anio)
        if mes:
            query = query.eq('mes', mes)
        response = query.execute()
        atenciones = response.data or []
        paciente_ids = list(set([a['paciente_id'] for a in atenciones if a.get('paciente_id')]))
        judicial = 0
        cem = 0
        if paciente_ids:
            pacientes_resp = supabase.table('pac_pacientes').select('id, origen').in_('id', paciente_ids).execute()
            pacientes_map = {p['id']: p.get('origen', 'DESCONOCIDO') for p in (pacientes_resp.data or [])}
            for a in atenciones:
                origen = pacientes_map.get(a.get('paciente_id'), 'DESCONOCIDO')
                if origen == 'PODER JUDICIAL':
                    judicial += 1
                elif origen == 'CEM':
                    cem += 1
        return jsonify({'data': {'judicial': judicial, 'cem': cem, 'total': judicial + cem}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reportes/pacientes-por-estado')
def reporte_pacientes_por_estado():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        activos_resp = supabase.table('pac_pacientes').select('id').eq('estado', 'activo').execute()
        inactivos_resp = supabase.table('pac_pacientes').select('id').eq('estado', 'inactivo').execute()
        return jsonify({'data': {'activos': len(activos_resp.data or []), 'inactivos': len(inactivos_resp.data or []), 'total': len(activos_resp.data or []) + len(inactivos_resp.data or [])}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reportes/pacientes-nuevos-por-mes')
def reporte_pacientes_nuevos_por_mes():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        anio = request.args.get('anio', date.today().year, type=int)
        response = supabase.table('pac_pacientes').select('created_at').execute()
        pacientes = response.data or []
        datos = [0] * 12
        for p in pacientes:
            if p.get('created_at'):
                try:
                    fecha = datetime.fromisoformat(p['created_at'].replace('Z', '+00:00'))
                    if fecha.year == anio:
                        datos[fecha.month - 1] += 1
                except:
                    pass
        return jsonify({'data': datos, 'anio': anio})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reportes/top-diagnosticos')
def reporte_top_diagnosticos():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        anio = request.args.get('anio', date.today().year, type=int)
        mes = request.args.get('mes', type=int)
        limite = request.args.get('limite', 10, type=int)
        query = supabase.table('pac_atenciones').select('diagnostico').eq('anio', anio)
        if mes:
            query = query.eq('mes', mes)
        response = query.execute()
        atenciones = response.data or []
        conteo = {}
        for a in atenciones:
            diag = a.get('diagnostico', '')
            if diag:
                diagnosticos = [d.strip() for d in diag.split(';') if d.strip()]
                for d in diagnosticos:
                    codigo = d.split(' - ')[0].strip() if ' - ' in d else d[:10]
                    nombre = d.split(' - ')[1].strip() if ' - ' in d and len(d.split(' - ')) > 1 else d
                    clave = f"{codigo} - {nombre}"
                    conteo[clave] = conteo.get(clave, 0) + 1
        top = sorted(conteo.items(), key=lambda x: x[1], reverse=True)[:limite]
        return jsonify({'data': [{'diagnostico': k, 'cantidad': v} for k, v in top], 'total_atenciones': len(atenciones)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reportes/atenciones-por-usuario')
def reporte_atenciones_por_usuario():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        anio = request.args.get('anio', date.today().year, type=int)
        mes = request.args.get('mes', type=int)
        query = supabase.table('pac_atenciones').select('mes, anio').eq('anio', anio)
        if mes:
            query = query.eq('mes', mes)
        response = query.execute()
        atenciones = response.data or []
        por_mes = [0] * 12
        for a in atenciones:
            m = a.get('mes')
            if m and 1 <= m <= 12:
                por_mes[m - 1] += 1
        return jsonify({'por_mes': por_mes, 'total_atenciones': len(atenciones)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# RUTA - FICHA PACIENTE
# ============================================

@app.route('/paciente/<id>')
def ficha_paciente(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    if supabase is None:
        return "Error de conexion", 500
    try:
        paciente_resp = supabase.table('pac_pacientes').select('*').eq('id', id).single().execute()
        paciente = paciente_resp.data
        if not paciente:
            return "Paciente no encontrado", 404

        # Calcular edad desde fecha_nacimiento
        edad = None
        if paciente.get('fecha_nacimiento'):
            try:
                fecha_nac = datetime.strptime(paciente['fecha_nacimiento'], '%Y-%m-%d').date()
                hoy = date.today()
                edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
            except:
                pass

        atenciones_resp = supabase.table('pac_atenciones').select('*').eq('paciente_id', id).order('fecha_atencion', desc=True).execute()
        es_print = request.args.get('print') == '1'

        return render_template('ficha_paciente.html', 
                               paciente=paciente, 
                               atenciones=atenciones_resp.data or [], 
                               user=session['user'], 
                               es_print=es_print,
                               edad=edad)
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/diagnosticos')
def buscar_diagnosticos():
    if supabase is None:
        return jsonify({'error': 'Sin conexion'}), 500
    try:
        query = request.args.get('q', '').strip()
        response = supabase.table('diagnosticospsico').select('*').or_(f"codigo.ilike.%{query}%,nombre.ilike.%{query}%").limit(20).execute()
        return jsonify({'data': response.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# ENTRY POINT PARA VERCEL
# ============================================

# Vercel necesita una función 'app' exportable
# El handler se crea automáticamente con @vercel/python