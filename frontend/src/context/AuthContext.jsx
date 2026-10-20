import { createContext, useState, useCallback } from 'react';
import { loginUser as apiLogin, registerUser as apiRegister } from '../api/auth';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('auth_user');
    return stored ? JSON.parse(stored) : null;
  });

  const login = useCallback(async (email, password) => {
    const userData = await apiLogin(email, password);
    /* Store credentials for HTTP Basic auth on subsequent requests */
    localStorage.setItem('auth_credentials', JSON.stringify({ email, password }));
    localStorage.setItem('auth_user', JSON.stringify(userData));
    setUser(userData);
    return userData;
  }, []);

  const register = useCallback(async (username, email, password) => {
    const userData = await apiRegister(username, email, password);
    /* Auto-login after successful registration */
    localStorage.setItem('auth_credentials', JSON.stringify({ email, password }));
    localStorage.setItem('auth_user', JSON.stringify(userData));
    setUser(userData);
    return userData;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_credentials');
    localStorage.removeItem('auth_user');
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
