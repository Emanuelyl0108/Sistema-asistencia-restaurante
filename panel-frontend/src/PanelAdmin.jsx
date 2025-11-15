import React, { useState, useEffect } from 'react';
import { User, Clock, Users, TrendingUp, LogOut, CheckCircle, Mail, Phone, IdCard } from 'lucide-react';
import LoginAdmin from './LoginAdmin';

const API_URL = process.env.REACT_APP_API_URL || 'https://asistencia-backend-uu7p.onrender.com/api';

export default function PanelAdmin() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [seccion, setSeccion] = useState('dashboard');
  const [marcajes, setMarcajes] = useState([]);
  const [pendientes, setPendientes] = useState([]);
  const [stats, setStats] = useState({});

  useEffect(() => {
    if (isAuthenticated) {
      cargarDatos();
    }
  }, [isAuthenticated]);

  const cargarDatos = async () => {
    try {
      const statsRes = await fetch(`${API_URL}/admin/estadisticas`);
      const statsData = await statsRes.json();
      setStats(statsData);

      const marcajesRes = await fetch(`${API_URL}/admin/marcajes`);
      const marcajesData = await marcajesRes.json();
      setMarcajes(marcajesData);

      const pendRes = await fetch(`${API_URL}/admin/empleados/pendientes`);
      const pendData = await pendRes.json();
      setPendientes(pendData);
    } catch (error) {
      console.error('Error cargando datos:', error);
    }
  };

  const aprobarEmpleado = async (empleado) => {
    try {
      const response = await fetch(`${API_URL}/admin/empleados/aprobar/${empleado.id}`, {
        method: 'POST',
      });
      if (response.ok) {
        alert(`Empleado ${empleado.nombre} aprobado correctamente`);
        cargarDatos();
      }
    } catch (error) {
      console.error('Error aprobando empleado:', error);
    }
  };

  const rechazarEmpleado = async (id) => {
    try {
      const response = await fetch(`${API_URL}/admin/empleados/rechazar/${id}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        alert('Empleado rechazado');
        cargarDatos();
      }
    } catch (error) {
      console.error('Error rechazando empleado:', error);
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setSeccion('dashboard');
  };

  // Mostrar login si no está autenticado
  if (!isAuthenticated) {
    return <LoginAdmin onLoginSuccess={() => setIsAuthenticated(true)} />;
  }

  // Panel admin normal
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-6">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Panel de Administrador</h1>
          <p className="text-purple-300">Gestion de asistencias</p>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg"
        >
          <LogOut size={20} />
          Cerrar Sesion
        </button>
      </div>

      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setSeccion('dashboard')}
          className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
            seccion === 'dashboard' 
              ? 'bg-purple-600 text-white' 
              : 'bg-white/10 text-white/70 hover:bg-white/20'
          }`}
        >
          Dashboard
        </button>
        <button
          onClick={() => setSeccion('marcajes')}
          className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
            seccion === 'marcajes' 
              ? 'bg-purple-600 text-white' 
              : 'bg-white/10 text-white/70 hover:bg-white/20'
          }`}
        >
          Ver Marcajes
        </button>
        <button
          onClick={() => setSeccion('aprobaciones')}
          className={`px-6 py-3 rounded-lg font-semibold transition-colors relative ${
            seccion === 'aprobaciones' 
              ? 'bg-purple-600 text-white' 
              : 'bg-white/10 text-white/70 hover:bg-white/20'
          }`}
        >
          Aprobaciones
          {pendientes.length > 0 && (
            <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs w-6 h-6 rounded-full flex items-center justify-center">
              {pendientes.length}
            </span>
          )}
        </button>
      </div>

      {seccion === 'dashboard' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl p-6 text-white">
            <Users size={40} className="mb-4" />
            <p className="text-blue-100 mb-1">Empleados Activos</p>
            <p className="text-4xl font-bold">{stats.empleados_activos || 0}</p>
          </div>

          <div className="bg-gradient-to-br from-green-500 to-green-700 rounded-xl p-6 text-white">
            <Clock size={40} className="mb-4" />
            <p className="text-green-100 mb-1">Marcajes Hoy</p>
            <p className="text-4xl font-bold">{stats.marcajes_hoy || 0}</p>
          </div>

          <div className="bg-gradient-to-br from-purple-500 to-purple-700 rounded-xl p-6 text-white">
            <TrendingUp size={40} className="mb-4" />
            <p className="text-purple-100 mb-1">Horas Trabajadas (Mes)</p>
            <p className="text-4xl font-bold">{stats.horas_trabajadas_mes || 0}h</p>
          </div>
        </div>
      )}

      {seccion === 'marcajes' && (
        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-4">Historial de Marcajes</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-white">
              <thead>
                <tr className="border-b border-white/20">
                  <th className="text-left py-3 px-4">Empleado</th>
                  <th className="text-left py-3 px-4">Tipo</th>
                  <th className="text-left py-3 px-4">Fecha</th>
                  <th className="text-left py-3 px-4">Hora</th>
                  <th className="text-left py-3 px-4">Distancia</th>
                </tr>
              </thead>
              <tbody>
                {marcajes.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="text-center py-8 text-white/50">
                      No hay marcajes registrados
                    </td>
                  </tr>
                ) : (
                  marcajes.map((m, idx) => (
                    <tr key={idx} className="border-b border-white/10 hover:bg-white/5">
                      <td className="py-3 px-4">{m.empleado_nombre}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          m.tipo === 'entrada' ? 'bg-green-500' : 'bg-red-500'
                        }`}>
                          {m.tipo.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 px-4">{m.fecha}</td>
                      <td className="py-3 px-4">{m.hora}</td>
                      <td className="py-3 px-4">{m.distancia_metros}m</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {seccion === 'aprobaciones' && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white mb-4">Solicitudes Pendientes</h2>
          
          {pendientes.length === 0 ? (
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-12 text-center border border-white/20">
              <CheckCircle size={64} className="mx-auto text-green-400 mb-4" />
              <p className="text-white text-xl">No hay solicitudes pendientes</p>
            </div>
          ) : (
            pendientes.map(emp => (
              <div key={emp.id} className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-white mb-2">{emp.nombre}</h3>
                    <div className="space-y-1 text-white/70 text-sm">
                      <p className="flex items-center gap-2">
                        <IdCard size={16} /> Cedula: {emp.cedula}
                      </p>
                      <p className="flex items-center gap-2">
                        <Mail size={16} /> Email: {emp.email}
                      </p>
                      <p className="flex items-center gap-2">
                        <Phone size={16} /> Telefono: {emp.telefono}
                      </p>
                      <p className="flex items-center gap-2">
                        <User size={16} /> Rol: <span className="font-semibold text-purple-300">{emp.rol.toUpperCase()}</span>
                      </p>
                    </div>
                  </div>
                </div>

                {emp.rol === 'mesero' && emp.usuario_fudo && (
                  <div className="bg-purple-500/20 border border-purple-500 rounded-lg p-4 mb-4">
                    <p className="text-white font-semibold mb-2">Credenciales FUDO:</p>
                    <div className="font-mono text-sm text-white/90 space-y-1">
                      <p>Usuario: <span className="text-purple-300">{emp.usuario_fudo}</span></p>
                      <p>Contrasena: <span className="text-purple-300">{emp.password_fudo}</span></p>
                    </div>
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    onClick={() => aprobarEmpleado(emp)}
                    className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg font-semibold"
                  >
                    Aprobar
                  </button>
                  <button
                    onClick={() => rechazarEmpleado(emp.id)}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg font-semibold"
                  >
                    Rechazar
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
