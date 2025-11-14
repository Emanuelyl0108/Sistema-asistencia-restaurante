import React, { useState } from 'react';
import { CheckCircle, UserPlus } from 'lucide-react';

const API_URL = process.env.REACT_APP_API_URL || 'https://asistencia-backend-uu7p.onrender.com/api';

export default function RegistroEmpleado() {
  const [formData, setFormData] = useState({
    nombre: '',
    cedula: '',
    email: '',
    telefono: '',
    rol: ''
  });
  const [credencialesFudo, setCredencialesFudo] = useState(null);
  const [registroExitoso, setRegistroExitoso] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const response = await fetch(`${API_URL}/empleados/registrar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (response.ok) {
        if (data.credenciales) {
          setCredencialesFudo(data.credenciales);
        }
        setRegistroExitoso(true);
      } else {
        alert('Error: ' + data.error);
      }
    } catch (error) {
      alert('Error de conexión: ' + error.message);
    }
  };

  if (registroExitoso) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 max-w-md w-full border border-white/20">
          <CheckCircle size={64} className="mx-auto text-green-400 mb-6" />
          <h2 className="text-2xl font-bold text-white text-center mb-4">
            ¡Registro Enviado!
          </h2>
          <p className="text-white/70 text-center mb-6">
            Tu solicitud está pendiente de aprobación por el administrador.
          </p>

          {credencialesFudo && (
            <div className="bg-purple-500/20 border border-purple-500 rounded-lg p-4 mb-6">
              <p className="text-white font-semibold mb-3">🔑 Tus Credenciales FUDO:</p>
              <div className="bg-black/20 rounded p-3 font-mono text-sm text-white space-y-2">
                <p><span className="text-purple-300">Usuario:</span> {credencialesFudo.usuario}</p>
                <p><span className="text-purple-300">Contraseña:</span> {credencialesFudo.password}</p>
              </div>
              <p className="text-xs text-white/60 mt-3">
                ⚠️ Guarda estas credenciales. Las necesitarás cuando tu cuenta sea aprobada.
              </p>
            </div>
          )}

          
            href="/"
            className="block w-full bg-purple-600 hover:bg-purple-700 text-white text-center py-3 rounded-lg font-semibold transition-colors"
          >
            Volver al Inicio
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 max-w-md w-full border border-white/20">
        <div className="text-center mb-6">
          <UserPlus size={48} className="mx-auto text-purple-400 mb-4" />
          <h2 className="text-3xl font-bold text-white mb-2">Registro de Empleado</h2>
          <p className="text-purple-300">Completa tus datos</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-white mb-2">Nombre Completo *</label>
            <input
              type="text"
              name="nombre"
              value={formData.nombre}
              onChange={handleChange}
              className="w-full px-4 py-3 rounded-lg bg-white/20 text-white placeholder-white/50 border border-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Juan Pérez"
              required
            />
          </div>

          <div>
            <label className="block text-white mb-2">Cédula *</label>
            <input
              type="text"
              name="cedula"
              value={formData.cedula}
              onChange={handleChange}
              className="w-full px-4 py-3 rounded-lg bg-white/20 text-white placeholder-white/50 border border-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="1234567890"
              required
            />
          </div>

          <div>
            <label className="block text-white mb-2">Email *</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full px-4 py-3 rounded-lg bg-white/20 text-white placeholder-white/50 border border-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="ejemplo@email.com"
              required
            />
          </div>

          <div>
            <label className="block text-white mb-2">Teléfono *</label>
            <input
              type="tel"
              name="telefono"
              value={formData.telefono}
              onChange={handleChange}
              className="w-full px-4 py-3 rounded-lg bg-white/20 text-white placeholder-white/50 border border-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="+57 300 123 4567"
              required
            />
          </div>

          <div>
            <label className="block text-white mb-2">Rol *</label>
            <select
              name="rol"
              value={formData.rol}
              onChange={handleChange}
              className="w-full px-4 py-3 rounded-lg bg-white/20 text-white border border-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500"
              required
            >
              <option value="">-- Seleccionar Rol --</option>
              <option value="mesero">Mesero</option>
              <option value="cocina">Cocina</option>
              <option value="cajero">Cajero</option>
              <option value="otro">Otro</option>
            </select>
          </div>

          {formData.rol === 'mesero' && (
            <div className="bg-yellow-500/20 border border-yellow-500 rounded-lg p-4">
              <p className="text-yellow-200 text-sm">
                ℹ️ Como mesero, se generarán credenciales FUDO automáticamente.
              </p>
            </div>
          )}

          <button
            type="submit"
            className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-semibold transition-colors"
          >
            Enviar Solicitud
          </button>

          
            href="/"
            className="block w-full text-center bg-white/10 hover:bg-white/20 text-white py-3 rounded-lg font-semibold transition-colors"
          >
            Cancelar
          </a>
        </form>
      </div>
    </div>
  );
}
