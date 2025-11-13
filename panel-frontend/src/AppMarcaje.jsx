import React, { useState, useEffect, useCallback } from 'react';
import { Camera, MapPin, Clock, CheckCircle, XCircle, AlertTriangle, User, LogIn, LogOut, Wifi, WifiOff } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

export default function AppMarcaje() {
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState('scan');
  const [qrToken, setQrToken] = useState('');
  const [selectedEmployee, setSelectedEmployee] = useState('');
  const [employees, setEmployees] = useState([]);
  const [marcajeType, setMarcajeType] = useState('entrada');
  const [location, setLocation] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [lastMarcajes, setLastMarcajes] = useState([]);

  // ✅ URL dinámica para producción
  const API_URL = process.env.REACT_APP_API_URL;

  // Detectar token del QR en URL
  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      handleScanQR(token);
    }
  }, [searchParams]);

  // Detectar conexión
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Cargar empleados
  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);


  const fetchEmployees = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/empleados`);
      const data = await response.json();
      setEmployees(data.empleados || []);
    } catch (error) {
      console.error('Error cargando empleados:', error);
    }
  }, [API_URL]);


  // Obtener ubicación GPS
  const getLocation = () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocalización no disponible'));
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            latitud: position.coords.latitude,
            longitud: position.coords.longitude,
            precision: position.coords.accuracy
          });
        },
        (error) => {
          reject(error);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        }
      );
    });
  };

  const handleScanQR = (token) => {
    setQrToken(token);
    setStep('select');
  };

  const loadEmployeeMarcajes = async (nombre) => {
    try {
      const response = await fetch(`${API_URL}/marcajes/empleado/${encodeURIComponent(nombre)}`);
      const data = await response.json();
      setLastMarcajes(data.slice(0, 3));
      
      if (data.length > 0) {
        const lastType = data[0].tipo;
        setMarcajeType(lastType === 'entrada' ? 'salida' : 'entrada');
      }
    } catch (error) {
      console.error('Error cargando marcajes:', error);
    }
  };

  const handleSelectEmployee = (nombre) => {
    setSelectedEmployee(nombre);
    loadEmployeeMarcajes(nombre);
    setStep('confirm');
  };

  const handleConfirmMarcaje = async () => {
    setLoading(true);

    try {
      const loc = await getLocation();
      setLocation(loc);

      const response = await fetch(`${API_URL}/marcar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: qrToken,
          empleado_nombre: selectedEmployee,
          tipo: marcajeType,
          latitud: loc.latitud,
          longitud: loc.longitud,
          dispositivo: navigator.userAgent
        })
      });

      const data = await response.json();

      if (response.ok) {
        setResult({
          success: true,
          mensaje: data.mensaje,
          hora: data.hora,
          distancia: data.distancia
        });
      } else {
        setResult({
          success: false,
          error: data.error
        });
      }
    } catch (error) {
      setResult({
        success: false,
        error: 'Error: ' + error.message
      });
    } finally {
      setLoading(false);
      setStep('result');
    }
  };

  const handleReset = () => {
    setStep('scan');
    setQrToken('');
    setSelectedEmployee('');
    setResult(null);
    setLocation(null);
    setLastMarcajes([]);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-indigo-900 to-purple-900 text-white">
      <div className="max-w-md mx-auto p-6">
        <div className="text-center mb-8 pt-8">
          <h1 className="text-3xl font-bold mb-2">🍽️ Marcaje de Asistencia</h1>
          <p className="text-lg opacity-80">Enruanados Gourmet</p>
          
          <div className="flex items-center justify-center gap-2 mt-4">
            {isOnline ? (
              <>
                <Wifi className="w-5 h-5 text-green-400" />
                <span className="text-sm text-green-400">Conectado</span>
              </>
            ) : (
              <>
                <WifiOff className="w-5 h-5 text-red-400" />
                <span className="text-sm text-red-400">Sin conexión</span>
              </>
            )}
          </div>
        </div>

        {step === 'scan' && (
          <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 border border-white/20">
            <div className="text-center mb-8">
              <Camera className="w-20 h-20 mx-auto mb-4 text-blue-400" />
              <h2 className="text-2xl font-bold mb-2">Escanea el código QR</h2>
              <p className="opacity-80">Se abrirá automáticamente al escanear</p>
            </div>
          </div>
        )}

        {step === 'select' && (
          <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 border border-white/20">
            <div className="text-center mb-6">
              <User className="w-16 h-16 mx-auto mb-4 text-green-400" />
              <h2 className="text-2xl font-bold mb-2">Selecciona tu nombre</h2>
              <p className="opacity-80">¿Quién está marcando?</p>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {employees.map((emp, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSelectEmployee(emp)}
                  className="w-full bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl p-4 text-left transition-all transform hover:scale-105"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-2xl font-bold">
                      {emp[0]}
                    </div>
                    <div>
                      <div className="font-semibold text-lg">{emp}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            <button
              onClick={handleReset}
              className="w-full mt-6 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-white font-bold py-3 px-6 rounded-xl transition-all"
            >
              Cancelar
            </button>
          </div>
        )}

        {step === 'confirm' && (
          <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 border border-white/20">
            <div className="text-center mb-6">
              <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-yellow-500 to-orange-500 rounded-full flex items-center justify-center">
                <User className="w-12 h-12" />
              </div>
              <h2 className="text-2xl font-bold mb-2">{selectedEmployee}</h2>
              <p className="opacity-80">Confirma tu marcaje</p>
            </div>

            <div className="mb-6">
              <label className="block text-sm opacity-80 mb-3">Tipo de marcaje:</label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setMarcajeType('entrada')}
                  className={`p-4 rounded-xl border-2 transition-all ${
                    marcajeType === 'entrada'
                      ? 'bg-green-500/30 border-green-500'
                      : 'bg-white/10 border-white/20'
                  }`}
                >
                  <LogIn className="w-8 h-8 mx-auto mb-2" />
                  <div className="font-bold">Entrada</div>
                </button>
                <button
                  onClick={() => setMarcajeType('salida')}
                  className={`p-4 rounded-xl border-2 transition-all ${
                    marcajeType === 'salida'
                      ? 'bg-blue-500/30 border-blue-500'
                      : 'bg-white/10 border-white/20'
                  }`}
                >
                  <LogOut className="w-8 h-8 mx-auto mb-2" />
                  <div className="font-bold">Salida</div>
                </button>
              </div>
            </div>

            {lastMarcajes.length > 0 && (
              <div className="mb-6 p-4 bg-white/5 rounded-xl border border-white/10">
                <div className="text-sm opacity-80 mb-2">Últimos marcajes:</div>
                {lastMarcajes.map((m, idx) => (
                  <div key={idx} className="flex justify-between text-sm py-1">
                    <span>{m.fecha}</span>
                    <span className={m.tipo === 'entrada' ? 'text-green-400' : 'text-blue-400'}>
                      {m.tipo} - {m.hora}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={handleConfirmMarcaje}
              disabled={loading}
              className="w-full bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600 disabled:opacity-50 text-white font-bold py-4 px-6 rounded-xl transition-all transform hover:scale-105 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Clock className="w-6 h-6 animate-spin" />
                  Validando...
                </>
              ) : (
                <>
                  <CheckCircle className="w-6 h-6" />
                  Confirmar {marcajeType}
                </>
              )}
            </button>

            <button
              onClick={() => setStep('select')}
              className="w-full mt-4 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-bold py-3 px-6 rounded-xl transition-all"
            >
              Volver
            </button>
          </div>
        )}

        {step === 'result' && (
          <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 border border-white/20">
            <div className="text-center">
              {result?.success ? (
                <>
                  <div className="w-24 h-24 mx-auto mb-6 bg-green-500 rounded-full flex items-center justify-center animate-bounce">
                    <CheckCircle className="w-16 h-16" />
                  </div>
                  <h2 className="text-3xl font-bold mb-4 text-green-400">
                    ¡Éxito!
                  </h2>
                  <p className="text-xl mb-6">{result.mensaje}</p>
                  
                  <div className="space-y-3 mb-6 text-left bg-white/5 rounded-xl p-4">
                    <div className="flex items-center justify-between">
                      <span className="opacity-80">Hora:</span>
                      <span className="font-bold text-lg">{result.hora}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="opacity-80">Distancia:</span>
                      <span className="font-bold text-lg text-green-400">{result.distancia}</span>
                    </div>
                    {location && (
                      <div className="flex items-center justify-between">
                        <span className="opacity-80">Precisión GPS:</span>
                        <span className="font-bold text-sm">{location.precision?.toFixed(0)}m</span>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <div className="w-24 h-24 mx-auto mb-6 bg-red-500 rounded-full flex items-center justify-center">
                    <XCircle className="w-16 h-16" />
                  </div>
                  <h2 className="text-3xl font-bold mb-4 text-red-400">
                    Error
                  </h2>
                  <p className="text-lg mb-6">{result?.error}</p>
                  
                  <div className="bg-red-500/20 border border-red-500/50 rounded-xl p-4 mb-6">
                    <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-yellow-400" />
                    <p className="text-sm opacity-80">
                      Verifica que estés dentro del restaurante y que el código QR no haya expirado.
                    </p>
                  </div>
                </>
              )}

              <button
                onClick={handleReset}
                className="w-full bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white font-bold py-4 px-6 rounded-xl transition-all transform hover:scale-105"
              >
                Marcar nuevamente
              </button>
            </div>
          </div>
        )}

        <div className="mt-6 text-center text-sm opacity-60">
          <MapPin className="w-4 h-4 inline mr-1" />
          Debes estar dentro del restaurante para marcar
        </div>
      </div>
    </div>
  );
}
