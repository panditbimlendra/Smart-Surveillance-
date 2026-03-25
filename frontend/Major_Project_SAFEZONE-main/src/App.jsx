import React, { createContext, useContext, useState } from 'react'
import AppRoutes from './routes/AppRoutes'

export const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

function App() {
  const [user, setUser] = useState(null)

  const login = (email) => {
    setUser({ email, name: 'Admin ', role: 'Security Analyst' })
  }

  const logout = () => {
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <AppRoutes />
    </AuthContext.Provider>
  )
}

export default App
