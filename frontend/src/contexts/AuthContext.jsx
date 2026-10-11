import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext();

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/\/+$/, '')
  : '';

const TOKEN_REFRESH_MARGIN = 5 * 60 * 1000; // 5 minutes before expiry

function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

function getTokenExpiration(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000;
  } catch {
    return 0;
  }
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshTimer, setRefreshTimer] = useState(null);

  const storeAuthData = (accessToken, refreshToken, userData) => {
    localStorage.setItem('accessToken', accessToken);
    localStorage.setItem('refreshToken', refreshToken);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const clearAuthData = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    setUser(null);
  };

  const refreshAccessToken = useCallback(async () => {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      clearAuthData();
      return null;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (!response.ok) {
        clearAuthData();
        return null;
      }

      const data = await response.json();
      localStorage.setItem('accessToken', data.access);
      if (data.refresh) {
        localStorage.setItem('refreshToken', data.refresh);
      }
      return data.access;
    } catch {
      clearAuthData();
      return null;
    }
  }, []);

  // Schedule token refresh before expiry
  const scheduleRefresh = useCallback((accessToken) => {
    if (refreshTimer) clearTimeout(refreshTimer);
    const expTime = getTokenExpiration(accessToken);
    const delay = Math.max(0, expTime - Date.now() - TOKEN_REFRESH_MARGIN);
    if (delay > 0) {
      const timer = setTimeout(async () => {
        const newToken = await refreshAccessToken();
        if (newToken) scheduleRefresh(newToken);
      }, delay);
      setRefreshTimer(timer);
    }
  }, [refreshAccessToken, refreshTimer]);

  // Check for stored tokens on mount
  useEffect(() => {
    const initAuth = async () => {
      const accessToken = localStorage.getItem('accessToken');
      const refreshToken = localStorage.getItem('refreshToken');
      const userData = localStorage.getItem('user');

      if (accessToken && userData && refreshToken) {
        if (isTokenExpired(accessToken)) {
          const newToken = await refreshAccessToken();
          if (newToken) {
            scheduleRefresh(newToken);
            setUser(JSON.parse(userData));
          }
        } else {
          scheduleRefresh(accessToken);
          setUser(JSON.parse(userData));
        }
      }
      setLoading(false);
    };
    initAuth();

    return () => {
      if (refreshTimer) clearTimeout(refreshTimer);
    };
  }, []);

  const register = async (email, password1, password2) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/registration/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password1, password2, username: email }),
      });

      const data = await response.json();
      if (!response.ok) {
        const firstError = data.email?.[0] || data.password1?.[0] || data.username?.[0] || data.non_field_errors?.[0] || 'Error al registrarse';
        throw new Error(firstError);
      }

      // If JWT tokens are returned (email_verification=optional), auto-login
      const accessToken = data.access || data.access_token;
      const refreshToken = data.refresh || data.refresh_token;
      if (accessToken && refreshToken) {
        const userResponse = await fetch(`${API_BASE_URL}/auth/user/`, {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        });
        if (userResponse.ok) {
          const userData = await userResponse.json();
          storeAuthData(accessToken, refreshToken, userData);
          scheduleRefresh(accessToken);
        }
      }

      return data;
    } catch (error) {
      throw error;
    }
  };

  const login = async (email, password) => {
    try {
      const tokenResponse = await fetch(`${API_BASE_URL}/auth/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const tokenData = await tokenResponse.json();
      if (!tokenResponse.ok) {
        throw new Error(tokenData.error || tokenData.detail || 'Credenciales incorrectas');
      }

      // Si el usuario tiene MFA activado, el backend no entrega tokens
      // todavía — hay que completar el segundo factor con verifyMfaLogin().
      if (tokenData.mfa_required) {
        return { mfaRequired: true, mfaToken: tokenData.mfa_token };
      }

      localStorage.setItem('accessToken', tokenData.access);
      localStorage.setItem('refreshToken', tokenData.refresh);

      const userResponse = await fetch(`${API_BASE_URL}/auth/user/`, {
        headers: {
          'Authorization': `Bearer ${tokenData.access}`,
        },
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        storeAuthData(tokenData.access, tokenData.refresh, userData);
        scheduleRefresh(tokenData.access);
      }

      return tokenData;
    } catch (error) {
      throw error;
    }
  };

  const verifyMfaLogin = async (mfaToken, code) => {
    const res = await fetch(`${API_BASE_URL}/auth/mfa/verify-login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mfa_token: mfaToken, code }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Código incorrecto');
    }
    localStorage.setItem('accessToken', data.access);
    localStorage.setItem('refreshToken', data.refresh);
    storeAuthData(data.access, data.refresh, data.user);
    scheduleRefresh(data.access);
    return data;
  };

  const logout = () => {
    clearAuthData();
    if (refreshTimer) clearTimeout(refreshTimer);
  };

  const resetPassword = async (email) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/password/reset/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Error al enviar el correo de recuperación');
      }

      return true;
    } catch (error) {
      throw error;
    }
  };

  const confirmResetPassword = async (uid, token, new_password1, new_password2) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/password/reset/confirm/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ uid, token, new_password1, new_password2 }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Error al restablecer la contraseña');
      }

      return true;
    } catch (error) {
      throw error;
    }
  };

  const getProfile = async () => {
    try {
      const accessToken = localStorage.getItem('accessToken');
      if (!accessToken) return null;
      const response = await fetch(`${API_BASE_URL}/profile/`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (response.status === 401) {
        const newToken = await refreshAccessToken();
        if (newToken) {
          const retry = await fetch(`${API_BASE_URL}/profile/`, {
            headers: { 'Authorization': `Bearer ${newToken}` },
          });
          if (retry.ok) return await retry.json();
        }
        return null;
      }

      if (response.ok) {
        return await response.json();
      }
      return null;
    } catch (error) {
      console.error('Error getting profile:', error);
      return null;
    }
  };

  const updateProfile = async (profileData) => {
    try {
      let accessToken = localStorage.getItem('accessToken');
      if (!accessToken) throw new Error('No autenticado');

      let response = await fetch(`${API_BASE_URL}/profile/`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData),
      });

      if (response.status === 401) {
        accessToken = await refreshAccessToken();
        if (!accessToken) throw new Error('Sesión expirada');
        response = await fetch(`${API_BASE_URL}/profile/`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(profileData),
        });
      }

      if (response.ok) {
        const updatedProfile = await response.json();
        if (updatedProfile.user) {
          setUser(updatedProfile.user);
          localStorage.setItem('user', JSON.stringify(updatedProfile.user));
        }
        return updatedProfile;
      }
      throw new Error('Error al actualizar el perfil');
    } catch (error) {
      console.error('Error updating profile:', error);
      throw error;
    }
  };

  const changePassword = async (old_password, new_password1, new_password2) => {
    try {
      let accessToken = localStorage.getItem('accessToken');
      if (!accessToken) throw new Error('No autenticado');

      let response = await fetch(`${API_BASE_URL}/auth/password/change/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ old_password, new_password1, new_password2 }),
      });

      if (response.status === 401) {
        accessToken = await refreshAccessToken();
        if (!accessToken) throw new Error('Sesión expirada');
        response = await fetch(`${API_BASE_URL}/auth/password/change/`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ old_password, new_password1, new_password2 }),
        });
      }

      if (response.ok) {
        return true;
      }
      const data = await response.json();
      throw new Error(data.detail || data.new_password2?.[0] || data.old_password?.[0] || 'Error al cambiar la contraseña');
    } catch (error) {
      console.error('Error changing password:', error);
      throw error;
    }
  };

  const getWorkspace = async () => {
    try {
      const accessToken = localStorage.getItem('accessToken');
      if (!accessToken) return null;
      const response = await fetch(`${API_BASE_URL}/workspace/`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (response.status === 401) {
        const newToken = await refreshAccessToken();
        if (newToken) {
          const retry = await fetch(`${API_BASE_URL}/workspace/`, {
            headers: { 'Authorization': `Bearer ${newToken}` },
          });
          if (retry.ok) return await retry.json();
        }
        return null;
      }

      if (response.ok) {
        return await response.json();
      }
      return null;
    } catch (error) {
      console.error('Error getting workspace:', error);
      return null;
    }
  };

  const updateWorkspace = async (workspaceData) => {
    try {
      let accessToken = localStorage.getItem('accessToken');
      if (!accessToken) throw new Error('No autenticado');

      let response = await fetch(`${API_BASE_URL}/workspace/`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(workspaceData),
      });

      if (response.status === 401) {
        accessToken = await refreshAccessToken();
        if (!accessToken) throw new Error('Sesión expirada');
        response = await fetch(`${API_BASE_URL}/workspace/`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(workspaceData),
        });
      }

      if (response.ok) {
        return await response.json();
      }
      throw new Error('Error al actualizar el espacio de trabajo');
    } catch (error) {
      console.error('Error updating workspace:', error);
      throw error;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        verifyMfaLogin,
        register,
        logout,
        resetPassword,
        confirmResetPassword,
        getProfile,
        updateProfile,
        changePassword,
        refreshAccessToken,
        getWorkspace,
        updateWorkspace,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};