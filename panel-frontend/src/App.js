import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import PanelQR from './panel_qr_display';
import AppMarcaje from './AppMarcaje';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<PanelQR />} />
        <Route path="/marcar" element={<AppMarcaje />} />
      </Routes>
    </Router>
  );
}

export default App;
