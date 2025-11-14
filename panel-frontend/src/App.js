import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import PanelQR from './panel_qr_display';
import AppMarcaje from './AppMarcaje';
import PanelAdmin from './PanelAdmin';
import RegistroEmpleado from './RegistroEmpleado';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<PanelQR />} />
        <Route path="/marcar" element={<AppMarcaje />} />
        <Route path="/admin" element={<PanelAdmin />} />
        <Route path="/registro" element={<RegistroEmpleado />} />
      </Routes>
    </Router>
  );
}

export default App;
