import React from 'react';
import { Routes, Route } from 'react-router-dom';
import TeamOnboardingForm from './components/TeamOnboardingForm';
import Home from './Home';
import Header from './components/Header';
import LoginButton from './components/LoginButton';
import LoginPage from './components/LoginPage';
import AdminDashboard from './components/AdminDashboard'; // ✅ Make sure this is correct

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
