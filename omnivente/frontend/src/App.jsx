import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Inbox from './pages/Inbox.jsx'
import Login from './pages/Login.jsx'
import Orders from './pages/Orders.jsx'
import Products from './pages/Products.jsx'
import Profile from './pages/Profile.jsx'
import Register from './pages/Register.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/connexion" element={<Login />} />
      <Route path="/inscription" element={<Register />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="/commandes" element={<Orders />} />
        <Route path="/messages" element={<Inbox />} />
        <Route path="/catalogue" element={<Products />} />
        <Route path="/profil" element={<Profile />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
