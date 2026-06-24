import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';

const TradingTerminal = lazy(() => import('./pages/TradingTerminal'));

function App() {
  return (
    <Router>
      <div style={{ display: 'flex', height: '100vh', backgroundColor: '#0B0E11', color: '#EAECEF', fontFamily: 'sans-serif' }}>
        {/* Basit Sol Menü */}
        <nav style={{ width: '60px', backgroundColor: '#1E2329', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '20px 0' }}>
          <div style={{ fontWeight: 'bold', color: '#FCD535', marginBottom: '40px' }}>ZKR</div>
          <div style={{ cursor: 'pointer', color: '#00C087' }}>📊</div>
        </nav>
        
        {/* Ana Sahne */}
        <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <header style={{ height: '50px', backgroundColor: '#181A20', borderBottom: '1px solid #2B3139', display: 'flex', alignItems: 'center', padding: '0 20px', justifyContent: 'space-between' }}>
            <h2 style={{ margin: 0, fontSize: '16px' }}>Terminal</h2>
            <span style={{ fontSize: '12px', color: '#00C087' }}>🟢 WebSocket: Live</span>
          </header>
          
          <div style={{ flex: 1, position: 'relative' }}>
            <Suspense fallback={<div style={{ padding: '20px' }}>Yükleniyor...</div>}>
              <Routes>
                <Route path="/" element={<TradingTerminal />} />
              </Routes>
            </Suspense>
          </div>
        </main>
      </div>
    </Router>
  );
}

export default App;
