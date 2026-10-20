import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 90000,
});

/* Attach Basic auth credentials from localStorage on every request */
client.interceptors.request.use((config) => {
  const creds = localStorage.getItem('auth_credentials');
  if (creds) {
    const { email, password } = JSON.parse(creds);
    config.auth = { username: email, password };
  }
  return config;
});

/* On 401, clear credentials and redirect to login */
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const isAuthRoute = error.config?.url?.includes('/auth/');
      if (!isAuthRoute) {
        localStorage.removeItem('auth_credentials');
        localStorage.removeItem('auth_user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default client;
