"""
Sistema de Asistencia con QR Dinámico
Backend API - Flask
Optimizado para Render.com
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import jwt
import datetime
import sqlite3
import pandas as pd
import os
import hashlib
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__, static_folder='build', static_url_path='')

# Configuración CORS para producción
CORS(app, 
    resources={r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }}
)
# ==================== CONFIGURACIÓN ====================
# Variables de entorno (Render las inyecta automáticamente)
SECRET_KEY = os.environ.get('SECRET_KEY', 'prueba123')
QR_EXPIRATION_MINUTES = int(os.environ.get('QR_EXPIRATION_MINUTES', 5))
GPS_RADIUS_METERS = int(os.environ.get('GPS_RADIUS_METERS', 50))

# Coordenadas del restaurante (desde variables de entorno)
RESTAURANT_LAT = float(os.environ.get('RESTAURANT_LAT', 5.618553712703385))
RESTAURANT_LON = float(os.environ.get('RESTAURANT_LON', -73.81627418830061))
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

# Ruta de base de datos (persistente en Render con disco)
DB_PATH = os.environ.get('DB_PATH', 'asistencia.db')

# ==================== BASE DE DATOS ====================

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect(DB_PATH)  # ← Usa DB_PATH en vez de 'asistencia.db'
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializar base de datos SQLite"""
    conn = get_db_connection()  # ← SOLO CAMBIA ESTA LÍNEA (antes era sqlite3.connect('asistencia.db'))
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
    
    # Tabla de QR tokens (para invalidar si es necesario)
    c.execute('''
        CREATE TABLE IF NOT EXISTS qr_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            usado BOOLEAN DEFAULT 0
        )
    ''')
    
    # Tabla de intentos fallidos (para alertas)
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
    """
    Calcular distancia entre dos puntos GPS usando fórmula Haversine
    Retorna distancia en metros
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km * 1000  # convertir a metros

def verificar_horario_permitido(empleado_nombre, hora_actual):
    """
    Verificar si el empleado puede marcar en este horario
    """
    # Cargar empleados
    try:
        empleados_df = pd.read_csv('empleados.csv')
        empleado = empleados_df[empleados_df['nombre'] == empleado_nombre]
        
        if empleado.empty:
            return False, "Empleado no encontrado"
        
        if empleado.iloc[0]['estado'] != 'ACTIVO':
            return False, "Empleado no está activo"
    except:
        return False, "Error al verificar empleado"
    
    # Determinar si es fin de semana
    dia_semana = datetime.datetime.now().weekday()  # 0=lunes, 6=domingo
    es_fin_semana = dia_semana >= 5
    
    # Determinar tipo de horario (por ahora todos general, puedes agregar campo en empleados.csv)
    tipo_horario = "general"  # o "cocina" según el rol del empleado
    
    horario_key = "fin_semana" if es_fin_semana else "lunes_viernes"
    horario = HORARIOS[tipo_horario][horario_key]
    
    hora_inicio = datetime.datetime.strptime(horario["inicio"], "%H:%M").time()
    hora_cierre = datetime.datetime.strptime(horario["cierre"], "%H:%M").time()
    
    # Agregar tolerancia de salida
    cierre_con_tolerancia = (
        datetime.datetime.combine(datetime.date.today(), hora_cierre) + 
        datetime.timedelta(minutes=TOLERANCIA_SALIDA_MINUTOS)
    ).time()
    
    if hora_actual < hora_inicio:
        return False, f"Fuera de horario. Inicio: {horario['inicio']}"
    
    if hora_actual > cierre_con_tolerancia:
        return False, f"Fuera de horario. Cierre: {horario['cierre']} (+ {TOLERANCIA_SALIDA_MINUTOS} min)"
    
    return True, "Horario válido"

def registrar_intento_fallido(empleado_nombre, motivo, lat, lon, dispositivo):
    """Registrar intento fallido para análisis y alertas"""
    conn = sqlite3.connect('asistencia.db')
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO intentos_fallidos 
        (empleado_nombre, motivo, timestamp, latitud, longitud, dispositivo)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (empleado_nombre, motivo, int(datetime.datetime.now().timestamp()), lat, lon, dispositivo))
    
    conn.commit()
    conn.close()

# ==================== ENDPOINTS API ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de salud para Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'config': {
            'qr_expiration': QR_EXPIRATION_MINUTES,
            'gps_radius': GPS_RADIUS_METERS,
            'restaurant_location': f"{RESTAURANT_LAT}, {RESTAURANT_LON}"
        }
    })

@app.route('/api/generar-qr', methods=['GET', 'OPTIONS'])
def generar_qr():
    if request.method == 'OPTIONS':
        return '', 204
    """
    Generar nuevo token QR dinámico
    Expira en QR_EXPIRATION_MINUTES minutos
    """
    now = datetime.datetime.utcnow()
    expires = now + datetime.timedelta(minutes=QR_EXPIRATION_MINUTES)
    
    payload = {
        'exp': expires,
        'iat': now,
        'token_id': hashlib.sha256(str(now.timestamp()).encode()).hexdigest()[:16]
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    # Guardar en BD para tracking
    conn = sqlite3.connect('asistencia.db')
    c = conn.cursor()
    c.execute('''
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

@app.route('/api/validar-qr', methods=['POST', 'OPTIONS'])
def validar_qr():
    if request.method == 'OPTIONS':
        return '', 204
    """
    Validar QR escaneado por empleado
    """
    data = request.json
    token = data.get('token')
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return jsonify({'valid': True, 'token_id': payload.get('token_id')})
    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'error': 'QR expirado'}), 400
    except jwt.InvalidTokenError:
        return jsonify({'valid': False, 'error': 'QR inválido'}), 400

@app.route('/api/marcar', methods=['POST', 'OPTIONS'])
def marcar_asistencia():
    if request.method == 'OPTIONS':
        return '', 204
    """
    Registrar marcaje de entrada/salida
    Valida: QR, GPS, horario, duplicados
    """
    data = request.json
    
    # Validar campos requeridos
    required = ['token', 'empleado_nombre', 'tipo', 'latitud', 'longitud']
    if not all(k in data for k in required):
        return jsonify({'error': 'Datos incompletos'}), 400
    
    token = data['token']
    empleado_nombre = data['empleado_nombre']
    tipo = data['tipo']  # 'entrada' o 'salida'
    lat = float(data['latitud'])
    lon = float(data['longitud'])
    dispositivo = data.get('dispositivo', 'unknown')
    
    # 1. Validar QR
    try:
        jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        registrar_intento_fallido(empleado_nombre, "QR expirado", lat, lon, dispositivo)
        return jsonify({'error': 'QR expirado. Escanea el código actualizado.'}), 400
    except jwt.InvalidTokenError:
        registrar_intento_fallido(empleado_nombre, "QR inválido", lat, lon, dispositivo)
        return jsonify({'error': 'QR inválido'}), 400
    
    # 2. Validar ubicación GPS
    distancia = calcular_distancia_gps(lat, lon, RESTAURANT_LAT, RESTAURANT_LON)
    
    if distancia > GPS_RADIUS_METERS:
        registrar_intento_fallido(empleado_nombre, f"Fuera de ubicación ({distancia:.0f}m)", lat, lon, dispositivo)
        return jsonify({
            'error': f'Debes estar en el restaurante para marcar. Distancia: {distancia:.0f}m'
        }), 400
    
    # 3. Validar horario
    hora_actual = datetime.datetime.now().time()
    horario_valido, mensaje_horario = verificar_horario_permitido(empleado_nombre, hora_actual)
    
    if not horario_valido:
        registrar_intento_fallido(empleado_nombre, mensaje_horario, lat, lon, dispositivo)
        return jsonify({'error': mensaje_horario}), 400
    
    # 4. Validar duplicados (no marcar dos entradas seguidas sin salida)
    conn = sqlite3.connect('asistencia.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT tipo FROM marcajes 
        WHERE empleado_nombre = ? 
        ORDER BY timestamp DESC LIMIT 1
    ''', (empleado_nombre,))
    
    ultimo_marcaje = c.fetchone()
    
    if ultimo_marcaje and ultimo_marcaje[0] == tipo:
        conn.close()
        return jsonify({
            'error': f'Ya marcaste {tipo} anteriormente. Marca {"salida" if tipo == "entrada" else "entrada"}.'
        }), 400
    
    # 5. Registrar marcaje
    now = datetime.datetime.now()
    
    c.execute('''
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

@app.route('/api/empleados', methods=['GET', 'OPTIONS'])
def listar_empleados():
    if request.method == 'OPTIONS':
        return '', 204
    """Obtener lista de empleados activos"""
    try:
        empleados_df = pd.read_csv('empleados.csv')
        activos = empleados_df[empleados_df['estado'] == 'ACTIVO']
        
        return jsonify({
            'empleados': activos['nombre'].tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/marcajes/hoy', methods=['GET', 'OPTIONS'])
def marcajes_hoy():
    if request.method == 'OPTIONS':
        return '', 204
    """Obtener marcajes del día actual"""
    conn = sqlite3.connect('asistencia.db')
    hoy = datetime.date.today().strftime('%Y-%m-%d')
    
    df = pd.read_sql_query(
        "SELECT * FROM marcajes WHERE fecha = ? ORDER BY timestamp DESC",
        conn,
        params=(hoy,)
    )
    
    conn.close()
    
    return jsonify(df.to_dict('records'))

@app.route('/api/marcajes/empleado/<nombre>', methods=['GET', 'OPTIONS'])
def marcajes_empleado(nombre):
    if request.method == 'OPTIONS':
        return '', 204
    """Obtener marcajes de un empleado (últimos 30 días)"""
    conn = sqlite3.connect('asistencia.db')
    
    hace_30_dias = (datetime.date.today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    
    df = pd.read_sql_query(
        "SELECT * FROM marcajes WHERE empleado_nombre = ? AND fecha >= ? ORDER BY timestamp DESC",
        conn,
        params=(nombre, hace_30_dias)
    )
    
    conn.close()
    
    return jsonify(df.to_dict('records'))

@app.route('/api/reporte/horas', methods=['GET'])
def reporte_horas():
    """
    Generar reporte de horas trabajadas
    Parámetros: fecha_inicio, fecha_fin, empleado (opcional)
    """
    fecha_inicio = request.args.get('fecha_inicio', (datetime.date.today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d'))
    fecha_fin = request.args.get('fecha_fin', datetime.date.today().strftime('%Y-%m-%d'))
    empleado = request.args.get('empleado', None)
    
    conn = sqlite3.connect('asistencia.db')
    
    query = """
        SELECT 
            empleado_nombre,
            fecha,
            tipo,
            hora,
            timestamp
        FROM marcajes 
        WHERE fecha BETWEEN ? AND ?
    """
    params = [fecha_inicio, fecha_fin]
    
    if empleado:
        query += " AND empleado_nombre = ?"
        params.append(empleado)
    
    query += " ORDER BY empleado_nombre, timestamp"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    # Calcular horas trabajadas
    resultados = []
    
    for empleado_nombre in df['empleado_nombre'].unique():
        df_emp = df[df['empleado_nombre'] == empleado_nombre]
        
        entradas = df_emp[df_emp['tipo'] == 'entrada']
        salidas = df_emp[df_emp['tipo'] == 'salida']
        
        horas_totales = 0
        dias_trabajados = []
        
        for fecha in df_emp['fecha'].unique():
            df_dia = df_emp[df_emp['fecha'] == fecha]
            
            entrada = df_dia[df_dia['tipo'] == 'entrada']
            salida = df_dia[df_dia['tipo'] == 'salida']
            
            if not entrada.empty and not salida.empty:
                ts_entrada = entrada.iloc[0]['timestamp']
                ts_salida = salida.iloc[-1]['timestamp']  # última salida del día
                
                horas = (ts_salida - ts_entrada) / 3600
                horas_totales += horas
                
                dias_trabajados.append({
                    'fecha': fecha,
                    'entrada': entrada.iloc[0]['hora'],
                    'salida': salida.iloc[-1]['hora'],
                    'horas': round(horas, 2)
                })
        
        resultados.append({
            'empleado': empleado_nombre,
            'total_horas': round(horas_totales, 2),
            'total_dias': len(dias_trabajados),
            'detalle': dias_trabajados
        })
    
    return jsonify(resultados)

@app.route('/api/exportar/csv', methods=['GET'])
def exportar_csv():
    """Exportar marcajes a CSV para integración con nómina"""
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    conn = sqlite3.connect('asistencia.db')
    
    query = "SELECT * FROM marcajes WHERE fecha BETWEEN ? AND ? ORDER BY empleado_nombre, timestamp"
    df = pd.read_sql_query(query, conn, params=(fecha_inicio, fecha_fin))
    
    conn.close()
    
    # Guardar CSV
    filename = f'asistencia_{fecha_inicio}_{fecha_fin}.csv'
    df.to_csv(filename, index=False)
    
    return jsonify({
        'success': True,
        'filename': filename,
        'registros': len(df)
    })
# ==================== SERVIR REACT APP ====================

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Servir React app en producción"""
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# ==================== MANEJO DE ERRORES ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint no encontrado'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Error interno del servidor'}), 500

# ==================== INICIALIZACIÓN ====================

if __name__ == '__main__':
    # Inicializar base de datos
    init_db()
    print("✅ Base de datos inicializada")
    print(f"📍 Ubicación del restaurante: {RESTAURANT_LAT}, {RESTAURANT_LON}")
    print(f"🔒 Radio de validación: {GPS_RADIUS_METERS}m")
    print(f"⏱️  Expiración de QR: {QR_EXPIRATION_MINUTES} minutos")
    print(f"🔑 SECRET_KEY configurada: {'✅' if SECRET_KEY != 'prueba123' else '⚠️  Usar variable de entorno'}")
    
    # Puerto dinámico para Render
    port = int(os.environ.get('PORT', 5000))
    
    print(f"\n🚀 Iniciando servidor en puerto {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
