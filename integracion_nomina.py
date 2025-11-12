"""
Integración del Sistema de Asistencia con el Sistema de Nóminas
Calcula horas trabajadas y las integra automáticamente en los turnos
"""

import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os

class IntegradorAsistenciaNomina:
    """
    Integra los datos de asistencia con el sistema de nóminas existente
    """
    
    def __init__(self, db_asistencia='asistencia.db', archivo_turnos='turnos.csv'):
        self.db_asistencia = db_asistencia
        self.archivo_turnos = archivo_turnos
    
    def calcular_horas_empleado(self, nombre_empleado, fecha_inicio, fecha_fin):
        """
        Calcula las horas trabajadas por un empleado en un período
        """
        conn = sqlite3.connect(self.db_asistencia)
        
        query = """
            SELECT fecha, tipo, hora, timestamp
            FROM marcajes
            WHERE empleado_nombre = ?
            AND fecha BETWEEN ? AND ?
            AND validado = 1
            ORDER BY timestamp
        """
        
        df = pd.read_sql_query(
            query, 
            conn, 
            params=(nombre_empleado, fecha_inicio, fecha_fin)
        )
        conn.close()
        
        if df.empty:
            return {
                'total_horas': 0,
                'dias_trabajados': 0,
                'entradas_sin_salida': 0,
                'detalle_dias': []
            }
        
        # Agrupar por día
        dias_detalle = []
        total_horas = 0
        entradas_sin_salida = 0
        
        for fecha in df['fecha'].unique():
            df_dia = df[df['fecha'] == fecha].sort_values('timestamp')
            
            entradas = df_dia[df_dia['tipo'] == 'entrada']
            salidas = df_dia[df_dia['tipo'] == 'salida']
            
            if not entradas.empty and not salidas.empty:
                # Tomar primera entrada y última salida del día
                ts_entrada = entradas.iloc[0]['timestamp']
                ts_salida = salidas.iloc[-1]['timestamp']
                
                horas_trabajadas = (ts_salida - ts_entrada) / 3600
                total_horas += horas_trabajadas
                
                # Determinar tipo de turno
                tipo_turno = 'completo' if horas_trabajadas >= 8 else 'medio'
                
                dias_detalle.append({
                    'fecha': fecha,
                    'entrada': entradas.iloc[0]['hora'],
                    'salida': salidas.iloc[-1]['hora'],
                    'horas': round(horas_trabajadas, 2),
                    'tipo_turno': tipo_turno
                })
            elif not entradas.empty:
                entradas_sin_salida += 1
                dias_detalle.append({
                    'fecha': fecha,
                    'entrada': entradas.iloc[0]['hora'],
                    'salida': 'Sin marcar',
                    'horas': 0,
                    'tipo_turno': 'incompleto'
                })
        
        return {
            'total_horas': round(total_horas, 2),
            'dias_trabajados': len([d for d in dias_detalle if d['horas'] > 0]),
            'entradas_sin_salida': entradas_sin_salida,
            'detalle_dias': dias_detalle
        }
    
    def generar_reporte_quincena(self, fecha_inicio, fecha_fin):
        """
        Genera un reporte completo de asistencia para la quincena
        """
        # Cargar empleados activos
        empleados_df = pd.read_csv('empleados.csv')
        empleados_activos = empleados_df[empleados_df['estado'] == 'ACTIVO']
        
        reporte = []
        
        for _, emp in empleados_activos.iterrows():
            nombre = emp['nombre']
            tipo_pago = emp['tipo_pago']
            
            # Solo procesar empleados quincenales en reporte de quincena
            if tipo_pago != 'quincenal':
                continue
            
            datos = self.calcular_horas_empleado(nombre, fecha_inicio, fecha_fin)
            
            reporte.append({
                'nombre': nombre,
                'sueldo_mensual': emp['sueldo_mensual'],
                'total_horas': datos['total_horas'],
                'dias_trabajados': datos['dias_trabajados'],
                'entradas_sin_salida': datos['entradas_sin_salida'],
                'detalle': datos['detalle_dias']
            })
        
        return pd.DataFrame(reporte)
    
    def convertir_horas_a_turnos(self, horas_trabajadas):
        """
        Convierte horas trabajadas a equivalente en turnos
        1 día completo = 8-9 horas
        Medio turno = 4-5 horas
        """
        dias_completos = int(horas_trabajadas // 8)
        horas_restantes = horas_trabajadas % 8
        
        medios_turnos = 0
        if horas_restantes >= 4:
            medios_turnos = 1
            horas_restantes -= 4
        
        return {
            'dias_completos': dias_completos,
            'medios_turnos': medios_turnos,
            'horas_extra': round(horas_restantes, 2)
        }
    
    def actualizar_turnos_desde_asistencia(self, nombre_empleado, fecha_inicio, fecha_fin):
        """
        Actualiza el archivo turnos.csv con datos reales de asistencia
        """
        # Calcular horas del período
        datos = self.calcular_horas_empleado(nombre_empleado, fecha_inicio, fecha_fin)
        
        if datos['total_horas'] == 0:
            print(f"⚠️  {nombre_empleado}: Sin registros de asistencia en el período")
            return False
        
        # Convertir a turnos
        turnos = self.convertir_horas_a_turnos(datos['total_horas'])
        
        # Cargar archivo de turnos existente
        if os.path.exists(self.archivo_turnos):
            turnos_df = pd.read_csv(self.archivo_turnos)
        else:
            turnos_df = pd.DataFrame(columns=[
                'id_turno', 'nombre', 'dias_completos', 'medios_sustitutos',
                'medios_adicionales', 'dias_extras', 'faltas', 
                'quincena_inicio', 'quincena_fin'
            ])
        
        # Buscar si ya existe registro para este período
        existe = turnos_df[
            (turnos_df['nombre'] == nombre_empleado) & 
            (turnos_df['quincena_inicio'] == fecha_inicio)
        ]
        
        if not existe.empty:
            # Actualizar registro existente
            idx = existe.index[0]
            turnos_df.at[idx, 'dias_completos'] = turnos['dias_completos']
            turnos_df.at[idx, 'medios_turnos'] = turnos['medios_turnos']
            print(f"✅ Actualizado: {nombre_empleado} - {turnos['dias_completos']} días, {turnos['medios_turnos']} medios")
        else:
            # Crear nuevo registro
            nuevo_turno = {
                'id_turno': f"TR-AUTO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'nombre': nombre_empleado,
                'dias_completos': turnos['dias_completos'],
                'medios_sustitutos': turnos['medios_turnos'],
                'medios_adicionales': 0,
                'dias_extras': 0,
                'faltas': max(0, 15 - turnos['dias_completos'] - turnos['medios_turnos']),
                'quincena_inicio': fecha_inicio,
                'quincena_fin': fecha_fin
            }
            turnos_df = pd.concat([turnos_df, pd.DataFrame([nuevo_turno])], ignore_index=True)
            print(f"✅ Creado: {nombre_empleado} - {turnos['dias_completos']} días, {turnos['medios_turnos']} medios")
        
        # Guardar
        turnos_df.to_csv(self.archivo_turnos, index=False)
        return True
    
    def generar_reporte_excel(self, fecha_inicio, fecha_fin, archivo_salida='reporte_asistencia.xlsx'):
        """
        Genera un reporte Excel completo para análisis
        """
        reporte_df = self.generar_reporte_quincena(fecha_inicio, fecha_fin)
        
        with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
            # Hoja resumen
            resumen = reporte_df[['nombre', 'total_horas', 'dias_trabajados', 'entradas_sin_salida']]
            resumen.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Hoja detallada por empleado
            for _, emp in reporte_df.iterrows():
                if emp['detalle']:
                    detalle_df = pd.DataFrame(emp['detalle'])
                    sheet_name = emp['nombre'][:25]  # Excel limita a 31 caracteres
                    detalle_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"📊 Reporte generado: {archivo_salida}")
        return archivo_salida
    
    def detectar_anomalias(self, fecha_inicio, fecha_fin):
        """
        Detecta patrones anormales en asistencia:
        - Entradas muy tarde
        - Salidas muy temprano
        - Entradas sin salida
        - Jornadas muy cortas/largas
        """
        reporte = self.generar_reporte_quincena(fecha_inicio, fecha_fin)
        
        anomalias = []
        
        for _, emp in reporte.iterrows():
            # Entradas sin salida
            if emp['entradas_sin_salida'] > 0:
                anomalias.append({
                    'empleado': emp['nombre'],
                    'tipo': 'entrada_sin_salida',
                    'cantidad': emp['entradas_sin_salida'],
                    'gravedad': 'media'
                })
            
            # Analizar detalle de días
            for dia in emp['detalle']:
                if dia['tipo_turno'] == 'incompleto':
                    continue
                
                # Jornadas muy cortas (menos de 6 horas en turno completo)
                if dia['horas'] < 6 and dia['tipo_turno'] == 'completo':
                    anomalias.append({
                        'empleado': emp['nombre'],
                        'tipo': 'jornada_corta',
                        'fecha': dia['fecha'],
                        'horas': dia['horas'],
                        'gravedad': 'alta'
                    })
                
                # Jornadas muy largas (más de 10 horas)
                if dia['horas'] > 10:
                    anomalias.append({
                        'empleado': emp['nombre'],
                        'tipo': 'jornada_larga',
                        'fecha': dia['fecha'],
                        'horas': dia['horas'],
                        'gravedad': 'baja'
                    })
        
        return pd.DataFrame(anomalias)


# ==================== FUNCIONES DE USO RÁPIDO ====================

def sincronizar_quincena_actual():
    """
    Sincroniza automáticamente la quincena actual
    """
    integrador = IntegradorAsistenciaNomina()
    
    # Determinar quincena actual
    hoy = datetime.now()
    if hoy.day <= 15:
        fecha_inicio = hoy.replace(day=1).strftime('%Y-%m-%d')
        fecha_fin = hoy.replace(day=15).strftime('%Y-%m-%d')
    else:
        fecha_inicio = hoy.replace(day=16).strftime('%Y-%m-%d')
        # Último día del mes
        siguiente_mes = hoy.replace(day=28) + timedelta(days=4)
        ultimo_dia = siguiente_mes - timedelta(days=siguiente_mes.day)
        fecha_fin = ultimo_dia.strftime('%Y-%m-%d')
    
    print(f"📅 Sincronizando quincena: {fecha_inicio} a {fecha_fin}")
    
    # Cargar empleados
    empleados_df = pd.read_csv('empleados.csv')
    empleados_activos = empleados_df[
        (empleados_df['estado'] == 'ACTIVO') & 
        (empleados_df['tipo_pago'] == 'quincenal')
    ]
    
    for _, emp in empleados_activos.iterrows():
        integrador.actualizar_turnos_desde_asistencia(
            emp['nombre'],
            fecha_inicio,
            fecha_fin
        )
    
    print("\n✅ Sincronización completada")

def generar_reporte_completo():
    """
    Genera un reporte completo de la quincena actual
    """
    integrador = IntegradorAsistenciaNomina()
    
    # Determinar quincena actual
    hoy = datetime.now()
    if hoy.day <= 15:
        fecha_inicio = hoy.replace(day=1).strftime('%Y-%m-%d')
        fecha_fin = hoy.replace(day=15).strftime('%Y-%m-%d')
    else:
        fecha_inicio = hoy.replace(day=16).strftime('%Y-%m-%d')
        siguiente_mes = hoy.replace(day=28) + timedelta(days=4)
        ultimo_dia = siguiente_mes - timedelta(days=siguiente_mes.day)
        fecha_fin = ultimo_dia.strftime('%Y-%m-%d')
    
    # Generar Excel
    archivo = integrador.generar_reporte_excel(fecha_inicio, fecha_fin)
    
    # Detectar anomalías
    anomalias = integrador.detectar_anomalias(fecha_inicio, fecha_fin)
    
    if not anomalias.empty:
        print("\n⚠️  ANOMALÍAS DETECTADAS:")
        print(anomalias.to_string())
    else:
        print("\n✅ No se detectaron anomalías")
    
    return archivo


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        
        if comando == 'sincronizar':
            sincronizar_quincena_actual()
        elif comando == 'reporte':
            generar_reporte_completo()
        else:
            print("Comandos disponibles:")
            print("  python integracion.py sincronizar  - Sincroniza asistencia con turnos")
            print("  python integracion.py reporte      - Genera reporte Excel completo")
    else:
        # Menú interactivo
        print("\n" + "="*60)
        print("INTEGRACIÓN ASISTENCIA → NÓMINA")
        print("="*60)
        print("\n1. Sincronizar quincena actual")
        print("2. Generar reporte completo")
        print("3. Detectar anomalías")
        print("0. Salir")
        
        opcion = input("\nSeleccione opción: ").strip()
        
        if opcion == '1':
            sincronizar_quincena_actual()
        elif opcion == '2':
            generar_reporte_completo()
        elif opcion == '3':
            integrador = IntegradorAsistenciaNomina()
            hoy = datetime.now()
            if hoy.day <= 15:
                fecha_inicio = hoy.replace(day=1).strftime('%Y-%m-%d')
                fecha_fin = hoy.replace(day=15).strftime('%Y-%m-%d')
            else:
                fecha_inicio = hoy.replace(day=16).strftime('%Y-%m-%d')
                siguiente_mes = hoy.replace(day=28) + timedelta(days=4)
                ultimo_dia = siguiente_mes - timedelta(days=siguiente_mes.day)
                fecha_fin = ultimo_dia.strftime('%Y-%m-%d')
            
            anomalias = integrador.detectar_anomalias(fecha_inicio, fecha_fin)
            if not anomalias.empty:
                print("\n⚠️  ANOMALÍAS DETECTADAS:")
                print(anomalias.to_string())
            else:
                print("\n✅ No se detectaron anomalías")
