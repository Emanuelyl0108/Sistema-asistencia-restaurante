import React, { useState, useEffect, useCallback } from 'react';
import { Clock, MapPin, Wifi, WifiOff, AlertCircle, CheckCircle } from 'lucide-react';

export default function PanelQR() {
  const [qrData, setQrData] = useState(null);
  const [timeRemaining, setTimeRemaining] = useState(300);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isOnline, setIsOnline] = useState(true);
  const [recentMarks, setRecentMarks] = useState([]);
  const [errorMsg, setErrorMsg] = useState('');

  // URLs de producción
  const API_URL = process.env.REACT_APP_API_URL || 'https://asistencia-backend-uu7p.onrender.com/api';
  const FRONTEND_URL = 'https://asistencia-restaurante.netlify.app';
  
  // Generar nuevo QR
  const generateQR = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/generar-qr`, {
        method: 'GET',
        mode: 'cors',
      });

      const data = await response.json();
      
      if (data.token) {
        setQrData(data);
        setTimeRemaining(data.valid_for_seconds);
        setErrorMsg('');
      }
    } catch (error) {
      console.error('Error generando QR:', error);
      setErrorMsg('Error de conexión. Reintentando...');
      setIsOnline(false);
    }
  }, [API_URL]);

  // Obtener marcajes recientes
  const fetchRecentMarks = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/marcajes/hoy`, {
        method: 'GET',
        mode: 'cors',
      });
      const data = await response.json();
      setRecentMarks(data.slice(0, 5));
      setIsOnline(true);
    } catch (error) {
      console.error('Error obteniendo marcajes:', error);
    }
  }, [API_URL]);

  // Inicialización
  useEffect(() => {
    generateQR();
    fetchRecentMarks();
    
    const qrInterval = setInterval(generateQR, 5 * 60 * 1000);
    const marksInterval = setInterval(fetchRecentMarks, 10000);
    
    return () => {
      clearInterval(qrInterval);
      clearInterval(marksInterval);
    };
  }, [generateQR, fetchRecentMarks]);

  // Contador de tiempo
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeRemaining(prev => Math.max(0, prev - 1));
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Regenerar cuando expire
  useEffect(() => {
    if (timeRemaining === 0) {
      generateQR();
    }
  }, [timeRemaining, generateQR]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getProgressColor = () => {
    const percentage = (timeRemaining / 300) * 100;
    if (percentage > 50) return 'bg-green-500';
    if (percentage > 20) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">🍽️ Enruanados Gourmet</h1>
            <p className="text-xl opacity-80">Sistema de Asistencia</p>
          </div>
          
          <div className="text-right">
            <div className="text-5xl font-mono font-bold mb-2">
              {currentTime.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
            </div>
            <div className="text-lg opacity-80">
              {currentTime.toLocaleDateString('es-CO', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}
            </div>
            
            <div className="flex items-center justify-end gap-2 mt-2">
              {isOnline ? (
                <>
                  <Wifi className="w-5 h-5 text-green-400" />
                  <span className="text-sm text-green-400">En línea</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-5 h-5 text-red-400" />
                  <span className="text-sm text-red-400">Sin conexión</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-12 border border-white/20 shadow-2xl">
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold mb-4">Escanea para marcar asistencia</h2>
                <p className="text-xl opacity-80">Acerca tu celular al código QR</p>
              </div>

              <div className="flex justify-center mb-8">
                {qrData ? (
                  <div className="bg-white p-8 rounded-2xl shadow-xl">
                    <img
                      src={`https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(`${FRONTEND_URL}/marcar?token=${qrData.token}`)}`}
                      alt="QR Code"
                      className="w-96 h-96"
                    />
                  </div>
                ) : (
                  <div className="w-96 h-96 bg-white/20 rounded-2xl flex items-center justify-center">
                    <div className="text-center">
                      <Clock className="w-16 h-16 mx-auto mb-4 animate-spin" />
                      <p className="text-xl">Generando código...</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-lg opacity-80">Código válido por:</span>
                  <span className="text-3xl font-mono font-bold">{formatTime(timeRemaining)}</span>
                </div>
                
                <div className="w-full bg-white/20 rounded-full h-4 overflow-hidden">
                  <div 
                    className={`h-full ${getProgressColor()} transition-all duration-1000 ease-linear`}
                    style={{ width: `${(timeRemaining / 300) * 100}%` }}
                  />
                </div>

                {timeRemaining < 60 && (
                  <div className="flex items-center gap-2 text-yellow-400 animate-pulse">
                    <AlertCircle className="w-5 h-5" />
                    <span>El código expirará pronto. Escanea ahora.</span>
                  </div>
                )}
              </div>

              {errorMsg && (
                <div className="mt-6 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-center">
                  {errorMsg}
                </div>
              )}
            </div>

            <div className="mt-6 bg-blue-500/20 backdrop-blur-lg rounded-2xl p-6 border border-blue-500/30">
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                <MapPin className="w-6 h-6" />
                Instrucciones
              </h3>
              <ul className="space-y-2 text-lg opacity-90">
                <li>✅ Abre la cámara de tu celular</li>
                <li>✅ Apunta al código QR</li>
                <li>✅ Selecciona tu nombre</li>
                <li>✅ Confirma tu marcaje</li>
                <li>⚠️ Debes estar dentro del restaurante</li>
              </ul>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20">
              <h3 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <CheckCircle className="w-7 h-7 text-green-400" />
                Marcajes Recientes
              </h3>

              <div className="space-y-3">
                {recentMarks.length > 0 ? (
                  recentMarks.map((mark, idx) => (
                    <div 
                      key={idx}
                      className="bg-white/10 rounded-xl p-4 border border-white/10 hover:bg-white/20 transition-all"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-lg">{mark.empleado_nombre}</span>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                          mark.tipo === 'entrada' 
                            ? 'bg-green-500/30 text-green-200' 
                            : 'bg-blue-500/30 text-blue-200'
                        }`}>
                          {mark.tipo === 'entrada' ? '🟢 Entrada' : '🔵 Salida'}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-4 text-sm opacity-80">
                        <span>
                          <Clock className="w-4 h-4 inline mr-1" />
                          {new Date(mark.timestamp * 1000).toLocaleTimeString('es-CO', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                          })}
                        </span>
                        <span>
                          <MapPin className="w-4 h-4 inline mr-1" />
                          {mark.distancia_metros}m
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-12 opacity-60">
                    <Clock className="w-12 h-12 mx-auto mb-4" />
                    <p>Sin marcajes hoy</p>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-500/20 to-blue-500/20 backdrop-blur-lg rounded-2xl p-6 border border-white/20">
              <h4 className="text-xl font-bold mb-4">📊 Estadísticas de Hoy</h4>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="opacity-80">Total marcajes:</span>
                  <span className="text-2xl font-bold">{recentMarks.length}</span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="opacity-80">Empleados presentes:</span>
                  <span className="text-2xl font-bold text-green-400">
                    {new Set(recentMarks.filter(m => m.tipo === 'entrada').map(m => m.empleado_nombre)).size}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
