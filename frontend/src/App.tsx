import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import SidebarLayout from './components/Navbar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Contas from './pages/Contas';
import Categorias from './pages/Categorias';
import Relatorios from './pages/Relatorios';
import { AuthProvider, useAuth } from './services/AuthContext';

function AppContent() {
  const { token } = useAuth();

  if (!token) {
    return <Login />;
  }

  return (
    <SidebarLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/contas" element={<Contas />} />
        <Route path="/categorias" element={<Categorias />} />
        <Route path="/relatorios" element={<Relatorios />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </SidebarLayout>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;