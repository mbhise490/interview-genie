import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { getErrorMessage, isValidEmail } from '../utils/helpers';
import Button from '../components/Button';
import Input from '../components/Input';
import Card from '../components/Card';
import { BrainCircuit } from 'lucide-react';

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [loading, setLoading] = useState(false);

  function validate() {
    const e = {};
    if (!username.trim()) e.username = 'Username is required.';
    else if (username.trim().length > 25) e.username = 'Max 25 characters.';
    if (!email.trim()) e.email = 'Email is required.';
    else if (!isValidEmail(email)) e.email = 'Enter a valid email.';
    if (!password) e.password = 'Password is required.';
    else if (password.length < 8) e.password = 'At least 8 characters.';
    return e;
  }

  async function handleSubmit(evt) {
    evt.preventDefault();
    const e = validate();
    setErrors(e);
    setServerError('');
    if (Object.keys(e).length > 0) return;

    setLoading(true);
    try {
      await register(username.trim(), email.trim(), password);
      navigate('/', { replace: true });
    } catch (err) {
      setServerError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-3 rounded-full bg-green-50 p-3">
            <BrainCircuit className="h-8 w-8 text-primary" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-bold text-heading">Create an account</h1>
          <p className="mt-1 text-sm text-body">Get started with Interview Genie</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {serverError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
                {serverError}
              </div>
            )}

            <Input
              id="username"
              label="Username"
              placeholder="johndoe"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              error={errors.username}
              autoFocus
            />

            <Input
              id="email"
              label="Email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={errors.email}
              autoComplete="email"
            />

            <Input
              id="password"
              label="Password"
              type="password"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.password}
              autoComplete="new-password"
            />

            <Button type="submit" loading={loading} className="w-full">
              Create account
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-body">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </Card>
      </div>
    </div>
  );
}
