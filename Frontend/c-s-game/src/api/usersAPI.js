const API_BASE_URL = '/api/v1';

export const setToken = (token) => localStorage.setItem('access_token', token);
export const getToken = () => localStorage.getItem('access_token');
export const removeToken = () => localStorage.removeItem('access_token');

async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };
  const response = await fetch(`${API_BASE_URL}${url}`, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Ошибка ${response.status}`);
  }
  return response.json();
}

export const loginUser = async (username, password) => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Неверные учётные данные');
  }
  const data = await response.json();
  setToken(data.access_token);
  return data;
};

export const registerUser = async (username, password, fullName) => {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, full_name: fullName }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Ошибка регистрации');
  }
  const data = await response.json();
  setToken(data.access_token);
  return data;
};

export const fetchUserProfile = async () => {
  return authFetch('/users/me');
};

export const logoutUser = () => {
  removeToken();
  window.location.href = '/';
};
