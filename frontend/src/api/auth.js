import client from './client';

export async function loginUser(email, password) {
  /* Login uses HTTP Basic directly; we temporarily set auth for this request */
  const response = await client.post('/auth/login', null, {
    auth: { username: email, password },
  });
  return response.data;
}

export async function registerUser(username, email, password) {
  const response = await client.post('/auth/register', {
    username,
    email,
    password,
  });
  return response.data;
}
