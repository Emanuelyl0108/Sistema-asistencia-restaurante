"""
Sistema de Asistencia con QR Dinámico
Backend API - Flask
VERSIÓN COMPLETA con Panel Admin + Registro de Empleados
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import jwt
import datetime
import sqlite3
import pandas as pd
import os
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__, static_folder='build', static_url_path='')

# Configuración CORS para producción
CORS(app, 
    resources={r"/api/*": {
        "origins": [
            "https://asistencia-restaurante.netlify.app",
            "http://localhost:3000",
            "http://localhost:5000"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }}
)

# ==================== CONFIGURACIÓN ====================
SECRET_KEY = os.environ.get('SECRET_KEY', 'prueba123')
QR_EXPIRATION_MINUTES = int(os.environ.get('QR_EXPIRATION_MINUTES', 5))
GPS_RADIUS_METERS = int(os.environ.get('GPS_RADIUS_METERS', 50))

# Coordenadas del restaurante
RESTAURANT_LAT = float(os.environ.get('RESTAURANT_LAT', 5.618553712703385))
RESTAURANT_LON = float(os.environ.get('RESTAURANT_LON', -73.81627418830061))

# Configuración de Email (Gmail)
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', 'tu-email@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'tu-app-password')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@enruanadosgourmet.com')

# Horarios permitidos
HORARIOS = {
    "cocina": {
        "lunes_viernes": {"inicio": "11:00", "cierre": "21:00"},
        "fin_semana": {"inicio": "11:00", "cierre": "21:30"}
    },
    "general": {
        "lunes_viernes": {"inicio": "11:30", "cierre": "21:00"},
        "fin_semana": {"inicio": "11:30", "cierre": "21:30"}
    }
}
TOLERANCIA_SALIDA_MINUTOS = 40

DB_PATH = os.environ.get('DB_PATH', 'asistencia.db')

# ==================== BASE DE DATOS ====================

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializar base de datos SQLite"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabla de marcajes
    c.execute('''
        CREATE TABLE IF NOT EXISTS marcajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_nombre TEXT NOT NULL,
            tipo TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            latitud REAL,
            longitud REAL,
            distancia_metros REAL,
            dispositivo TEXT,
            validado BOOLEAN DEFAULT 1,
            sincronizado BOOLEAN DEFAULT 0
        )
    ''')
    
    # Tabla de empleados
    c.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cedula TEXT UNIQUE NOT NULL,
            email TEXT,
            telefono TEXT,
            rol TEXT NOT NULL,
            estado TEXT DEFAULT 'PENDIENTE',
            usuario_fudo TEXT,
            password_fudo TEXT,
            fecha_registro TEXT NOT NULL,
            fecha_aprobacion TEXT,
            aprobado_por TEXT
        )
    ''')
    
    # Tabla de QR tokens
    c.execute('''
        CREATE TABLE IF NOT EXISTS qr_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            usado BOOLEAN DEFAULT 0
        )
    ''')
    
    # Tabla de intentos fallidos
    c.execute('''
        CREATE TABLE IF NOT EXISTS intentos_fallidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_nombre TEXT,
            motivo TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            latitud REAL,
            longitud REAL,
            dispositivo TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# ==================== FUNCIONES AUXILIARES ====================

def calcular_distancia_gps(lat1, lon1, lat2, lon2):
    """Calcular distancia entre dos puntos GPS usando fórmula Haversine"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km * 1000  # convertir a metros

def generar_credenciales_fudo(nombre):
    """Generar usuario y contraseña temporal para FUDO"""
    import re
    
    # Limpiar nombre y crear usuario
    nombre_limpio = re.sub(r'[^a-zA-Z\s]', '', nombre.lower())
    nombre_usuario = nombre_limpio.replace(' ', '.')
    
    usuario = f"{nombre_usuario}@enruanadosgourmet.com"
    password = f"Temp{datetime.datetime.now().year}!"
    
    return usuario, password

def enviar_email_admin(empleado_data):
    """Enviar email al administrador con credenciales FUDO del nuevo empleado"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🆕 Nuevo Empleado Registrado: {empleado_data['nombre']}"
        msg['From'] = EMAIL_SENDER
        msg['To'] = ADMIN_EMAIL
        
        # HTML del email
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px;">
              <h2 style="color: #6B46C1;">🆕 Nuevo Empleado Registrado</h2>
              
              <div style="background-color: #F3F4F6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Datos del Empleado:</h3>
                <p><strong>Nombre:</strong> {empleado_data['nombre']}</p>
                <p><strong>Cédula:</strong> {empleado_data['cedula']}</p>
                <p><strong>Email:</strong> {empleado_data['email']}</p>
                <p><strong>Teléfono:</strong> {empleado_data['telefono']}</p>
                <p><strong>Rol:</strong> {empleado_data['rol'].upper()}</p>
              </div>
        """
        
        if empleado_data['rol'] == 'mesero':
            html += f"""
              <div style="background-color: #EDE9FE; border-left: 4px solid #6B46C1; padding: 20px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #6B46C1;">🔑 Credenciales FUDO Generadas:</h3>
                <p><strong>Usuario:</strong> <code style="background-color: #F3F4F6; padding: 2px 6px; border-radius: 4px;">{empleado_data['usuario_fudo']}</code></p>
                <p><strong>Contraseña Temporal:</strong> <code style="background-color: #F3F4F6; padding: 2px 6px; border-radius: 4px;">{empleado_data['password_fudo']}</code></p>
                <p style="color: #DC2626; font-size: 14px;"><strong>⚠️ Acción Requerida:</strong> Crear esta cuenta manualmente en el sistema FUDO.</p>
              </div>
            """
        
        html += """
              <p style="color: #6B7280; font-size: 14px; margin-top: 30px;">
                Accede al panel de administración para aprobar o rechazar este registro.
              </p>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, 'html')
        msg.attach(part)
        
        # Enviar email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, ADMIN_EMAIL, msg.as_string())
        
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False

def verificar_horario_permitido(empleado_nombre, hora_actual):
    """Verificar si el empleado puede marcar en este horario"""
    try:
        conn = get_db_connection()
        empleado = conn.execute(
            "SELECT * FROM empleados WHERE nombre = ? AND estado = 'ACTIVO'",
            (empleado_nombre,)
        ).fetchone()
        conn.close()
        
        if not empleado:
            return False, "Empleado no encontrado o no activo"
    except:
        return False, "Error al verificar empleado"
    
    # Determinar si es fin de semana
    dia_semana = datetime.datetime.now().weekday()
    es_fin_semana = dia_semana >= 5
    
    tipo_horario = "general"
    horario_key = "fin_semana" if es_fin_semana else "lunes_viernes"
    horario = HORARIOS[tipo_horario][horario_key]
    
    hora_inicio = datetime.datetime.strptime(horario["inicio"], "%H:%M").time()
    hora_cierre = datetime.datetime.strptime(horario["cierre"], "%H:%M").time()
    
    cierre_con_tolerancia = (
        datetime.datetime.combine(datetime.date.today(), hora_cierre) + 
        datetime.timedelta(minutes=TOLERANCIA_SALIDA_MINUTOS)
    ).time()
    
    if hora_actual < hora_inicio:
        return False, f"Fuera de horario. Inicio: {horario['inicio']}"
    
    if hora_actual > cierre_con_tolerancia:
        return False, f"Fuera de horario. Cierre: {horario['cierre']} (+ {TOLERANCIA_SALIDA_MINUTOS} min)"
    
    return True, "Horario válido"

# ==================== ENDPOINTS API ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de salud"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'version': '2.0.0'
    })

# ==================== AUTENTICACIÓN ADMIN ====================

@app.route('/api/admin/login', methods=['POST', 'OPTIONS'])
def admin_login():
    if request.method == 'OPTIONS':
        return '', 204
    
    data = request.json
    usuario = data.get('usuario')
    password = data.get('password')
    
    # Credenciales hardcodeadas (cambiar en producción por BD)
    if usuario == 'admin' and password == 'admin2025':
        token = jwt.encode({
            'usuario': usuario,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        }, SECRET_KEY, algorithm='HS256')
        
        return jsonify({'success': True, 'token': token})
    
    return jsonify({'success': False, 'error': 'Credenciales inválidas'}), 401

# ==================== REGISTRO DE EMPLEADOS ====================

@app.route('/api/empleados/registrar', methods=['POST', 'OPTIONS'])
def registrar_empleado():
    if request.method == 'OPTIONS':
        return '', 204
    
    data = request.json
    nombre = data.get('nombre')
    cedula = data.get('cedula')
    email = data.get('email')
    telefono = data.get('telefono')
    rol = data.get('rol')
    
    # Validar campos requeridos
    if not all([nombre, cedula, email, telefono, rol]):
        return jsonify({'error': 'Todos los campos son requeridos'}), 400
    
    # Generar credenciales FUDO si es mesero
    usuario_fudo = None
    password_fudo = None
    
    if rol == 'mesero':
        usuario_fudo, password_fudo = generar_credenciales_fudo(nombre)
    
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO empleados 
            (nombre, cedula, email, telefono, rol, estado, usuario_fudo, password_fudo, fecha_registro)
            VALUES (?, ?, ?, ?, ?, 'PENDIENTE', ?, ?, ?)
        ''', (nombre, cedula, email, telefono, rol, usuario_fudo, password_fudo, 
              datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        # Enviar email al admin
        empleado_data = {
            'nombre': nombre,
            'cedula': cedula,
            'email': email,
            'telefono': telefono,
            'rol': rol,
            'usuario_fudo': usuario_fudo,
            'password_fudo': password_fudo
        }
        
        enviar_email_admin(empleado_data)
        
        response = {
            'success': True,
            'mensaje': 'Registro enviado correctamente'
        }
        
        if rol == 'mesero':
            response['credenciales'] = {
                'usuario': usuario_fudo,
                'password': password_fudo
            }
        
        return jsonify(response)
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Ya existe un empleado con esta cédula'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== PANEL ADMIN - GESTIÓN ====================

@app.route('/api/admin/empleados/pendientes', methods=['GET', 'OPTIONS'])
def empleados_pendientes():
    if request.method == 'OPTIONS':
        return '', 204
    
    conn = get_db_connection()
    empleados = conn.execute(
        "SELECT * FROM empleados WHERE estado = 'PENDIENTE' ORDER BY fecha_registro DESC"
    ).fetchall()
    conn.close()
    
    return jsonify([dict(emp) for emp in empleados])

@app.route('/api/admin/empleados/aprobar/<int:id>', methods=['POST', 'OPTIONS'])
def aprobar_empleado(id):
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE empleados 
            SET estado = 'ACTIVO', 
                fecha_aprobacion = ?,
                aprobado_por = 'admin'
            WHERE id = ?
        ''', (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'mensaje': 'Empleado aprobado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/empleados/rechazar/<int:id>', methods=['DELETE', 'OPTIONS'])
def rechazar_empleado(id):
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM empleados WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'mensaje': 'Empleado rechazado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/marcajes', methods=['GET', 'OPTIONS'])
def admin_marcajes():
    if request.method == 'OPTIONS':
        return '', 204
    
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    conn = get_db_connection()
    
    if fecha_inicio and fecha_fin:
        marcajes = conn.execute(
            "SELECT * FROM marcajes WHERE fecha BETWEEN ? AND ? ORDER BY timestamp DESC",
            (fecha_inicio, fecha_fin)
        ).fetchall()
    else:
        # Por defecto últimos 30 días
        hace_30 = (datetime.date.today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        marcajes = conn.execute(
            "SELECT * FROM marcajes WHERE fecha >= ? ORDER BY timestamp DESC",
            (hace_30,)
        ).fetchall()
    
    conn.close()
    
    return jsonify([dict(m) for m in marcajes])

@app.route('/api/admin/estadisticas', methods=['GET', 'OPTIONS'])
def admin_estadisticas():
    if request.method == 'OPTIONS':
        return '', 204
    
    conn = get_db_connection()
    
    # Empleados activos
    empleados_activos = conn.execute(
        "SELECT COUNT(*) as total FROM empleados WHERE estado = 'ACTIVO'"
    ).fetchone()['total']
    
    # Marcajes hoy
    hoy = datetime.date.today().strftime('%Y-%m-%d')
    marcajes_hoy = conn.execute(
        "SELECT COUNT(*) as total FROM marcajes WHERE fecha = ?",
        (hoy,)
    ).fetchone()['total']
    
    # Horas trabajadas (aproximado)
    marcajes_mes = conn.execute(
        "SELECT * FROM marcajes WHERE fecha >= ?",
        ((datetime.date.today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'),)
    ).fetchall()
    
    conn.close()
    
    # Calcular horas
    horas_totales = 0
    for m in marcajes_mes:
        if m['tipo'] == 'salida':
            # Buscar entrada correspondiente (simplificado)
            horas_totales += 8  # Aproximado
    
    return jsonify({
        'empleados_activos': empleados_activos,
        'marcajes_hoy': marcajes_hoy,
        'horas_trabajadas_mes': round(horas_totales, 1)
    })

# ==================== ENDPOINTS ORIGINALES (MANTENIDOS) ====================

@app.route('/api/generar-qr', methods=['GET', 'OPTIONS'])
def generar_qr():
    if request.method == 'OPTIONS':
        return '', 204
    
    now = datetime.datetime.utcnow()
    expires = now + datetime.timedelta(minutes=QR_EXPIRATION_MINUTES)
    
    payload = {
        'exp': expires,
        'iat': now,
        'token_id': hashlib.sha256(str(now.timestamp()).encode()).hexdigest()[:16]
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO qr_tokens (token, created_at, expires_at)
        VALUES (?, ?, ?)
    ''', (token, int(now.timestamp()), int(expires.timestamp())))
    conn.commit()
    conn.close()
    
    return jsonify({
        'token': token,
        'expires_at': expires.isoformat(),
        'valid_for_seconds': QR_EXPIRATION_MINUTES * 60
    })

@app.route('/api/empleados', methods=['GET', 'OPTIONS'])
def listar_empleados():
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        conn = get_db_connection()
        empleados = conn.execute(
            "SELECT nombre FROM empleados WHERE estado = 'ACTIVO' ORDER BY nombre"
        ).fetchall()
        conn.close()
        
        return jsonify({
            'empleados': [emp['nombre'] for emp in empleados]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/marcar', methods=['POST', 'OPTIONS'])
def marcar_asistencia():
    if request.method == 'OPTIONS':
        return '', 204
    
    data = request.json
    
    required = ['token', 'empleado_nombre', 'tipo', 'latitud', 'longitud']
    if not all(k in data for k in required):
        return jsonify({'error': 'Datos incompletos'}), 400
    
    token = data['token']
    empleado_nombre = data['empleado_nombre']
    tipo = data['tipo']
    lat = float(data['latitud'])
    lon = float(data['longitud'])
    dispositivo = data.get('dispositivo', 'unknown')
    
    # Validar QR
    try:
        jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except:
        return jsonify({'error': 'QR inválido o expirado'}), 400
    
    # Validar GPS
    distancia = calcular_distancia_gps(lat, lon, RESTAURANT_LAT, RESTAURANT_LON)
    
    if distancia > GPS_RADIUS_METERS:
        return jsonify({
            'error': f'Debes estar en el restaurante. Distancia: {distancia:.0f}m'
        }), 400
    
    # Validar horario
    hora_actual = datetime.datetime.now().time()
    horario_valido, mensaje_horario = verificar_horario_permitido(empleado_nombre, hora_actual)
    
    if not horario_valido:
        return jsonify({'error': mensaje_horario}), 400
    
    # Registrar marcaje
    now = datetime.datetime.now()
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO marcajes 
        (empleado_nombre, tipo, fecha, hora, timestamp, latitud, longitud, distancia_metros, dispositivo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        empleado_nombre,
        tipo,
        now.strftime('%Y-%m-%d'),
        now.strftime('%H:%M:%S'),
        int(now.timestamp()),
        lat,
        lon,
        round(distancia, 2),
        dispositivo
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'mensaje': f'✅ {empleado_nombre} — {tipo.capitalize()} registrada',
        'hora': now.strftime('%I:%M %p'),
        'distancia': f'{distancia:.0f}m'
    })

# ==================== ENDPOINT INTEGRACIÓN NÓMINA ====================

@app.route('/api/turnos/quincena', methods=['GET', 'OPTIONS'])
def calcular_turnos_quincena():
    """Calcular turnos trabajados en una quincena - Compatible con Gestor de Nómina"""
    if request.method == 'OPTIONS':
        return '', 204
    
    empleado = request.args.get('empleado')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    if not all([empleado, fecha_inicio, fecha_fin]):
        return jsonify({'error': 'Faltan parámetros'}), 400
    
    conn = get_db_connection()
    marcajes = conn.execute('''
        SELECT fecha, tipo, hora, timestamp
        FROM marcajes 
        WHERE empleado_nombre = ? AND fecha BETWEEN ? AND ?
        ORDER BY timestamp
    ''', (empleado, fecha_inicio, fecha_fin)).fetchall()
    conn.close()
    
    if not marcajes:
        return jsonify({
            'empleado': empleado,
            'periodo': f"{fecha_inicio} a {fecha_fin}",
            'dias_completos': 0,
            'medios_turnos': 0,
            'medios_adicionales': 0,
            'dias_extras': 0,
            'faltas': 15,
            'detalle': []
        })
    
    # Agrupar por día y calcular horas
    dias_trabajados = {}
    
    for fecha in set(m['fecha'] for m in marcajes):
        marcajes_dia = [m for m in marcajes if m['fecha'] == fecha]
        
        entradas = [m for m in marcajes_dia if m['tipo'] == 'entrada']
        salidas = [m for m in marcajes_dia if m['tipo'] == 'salida']
        
        if entradas and salidas:
            ts_entrada = entradas[0]['timestamp']
            ts_salida = salidas[-1]['timestamp']
            horas = (ts_salida - ts_entrada) / 3600
            
            # Clasificar turno
            if horas >= 6:
                tipo_turno = 'completo'
            elif horas >= 3:
                tipo_turno = 'medio'
            else:
                tipo_turno = 'incompleto'
            
            dias_trabajados[fecha] = {
                'entrada': entradas[0]['hora'],
                'salida': salidas[-1]['hora'],
                'horas': round(horas, 2),
                'tipo': tipo_turno
            }
    
    # Calcular totales
    dias_completos = sum(1 for d in dias_trabajados.values() if d['tipo'] == 'completo')
    medios_turnos = sum(1 for d in dias_trabajados.values() if d['tipo'] == 'medio')
    
    dias_totales = len(dias_trabajados)
    faltas = max(0, 15 - dias_totales - 2)  # 2 descansos permitidos
    
    return jsonify({
        'empleado': empleado,
        'periodo': f"{fecha_inicio} a {fecha_fin}",
        'dias_completos': dias_completos,
        'medios_turnos': medios_turnos,
        'medios_adicionales': 0,
        'dias_extras': 0,
        'faltas': faltas,
        'detalle': dias_trabajados
    })

# ==================== MIGRACIÓN DE EMPLEADOS ====================

@app.route('/api/admin/migrar-empleados', methods=['POST', 'OPTIONS'])
def migrar_empleados_csv():
    """Migrar empleados desde empleados.csv a SQLite"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Leer CSV
        df = pd.read_csv('empleados.csv')
        
        conn = get_db_connection()
        migrados = 0
        errores = []
        
        for _, row in df.iterrows():
            nombre = str(row['nombre']).strip()
            
            # Generar cédula si no existe
            cedula_raw = row.get('id', '')
            if pd.isna(cedula_raw) or str(cedula_raw).strip() == '':
                cedula = f"CED-{nombre.replace(' ', '')[:10]}"
            else:
                cedula = str(cedula_raw).strip()
            
            estado = str(row['estado']).strip().upper()
            
            # Solo migrar empleados ACTIVOS
            if estado == 'ACTIVO':
                try:
                    conn.execute('''
                        INSERT INTO empleados 
                        (nombre, cedula, email, telefono, rol, estado, fecha_registro, fecha_aprobacion, aprobado_por)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        nombre,
                        cedula,
                        f"{nombre.lower().replace(' ', '.')}@temp.com",
                        "300-000-0000",
                        "general",
                        "ACTIVO",
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "migracion_csv"
                    ))
                    migrados += 1
                    print(f"✅ Migrado: {nombre}")
                except sqlite3.IntegrityError as e:
                    errores.append(f"{nombre}: Ya existe (cédula duplicada)")
                    print(f"⚠️  Ya existe: {nombre}")
                except Exception as e:
                    errores.append(f"{nombre}: {str(e)}")
                    print(f"❌ Error con {nombre}: {e}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'migrados': migrados,
            'total_activos': len(df[df['estado'].str.upper() == 'ACTIVO']),
            'errores': errores
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== SERVIR FRONTEND ====================

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# ==================== INICIALIZACIÓN ====================

if __name__ == '__main__':
    init_db()
    print("✅ Base de datos inicializada")
    print(f"📍 Ubicación del restaurante: {RESTAURANT_LAT}, {RESTAURANT_LON}")
    print(f"🔒 Radio de validación: {GPS_RADIUS_METERS}m")
    print(f"⏱️  Expiración de QR: {QR_EXPIRATION_MINUTES} minutos")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
