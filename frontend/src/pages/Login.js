/**
 * Login Page
 * Clean, modern login interface with Microsoft SSO using MSAL
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PublicClientApplication, InteractionStatus } from '@azure/msal-browser';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Database, ArrowRight, AlertCircle, Loader2 } from 'lucide-react';
import { getMsalConfig, loginRequest } from '../config/msalConfig';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [msLoading, setMsLoading] = useState(false);
  const [msalInstance, setMsalInstance] = useState(null);
  const [msConfigLoaded, setMsConfigLoaded] = useState(false);
  const { login, loginWithToken } = useAuth();
  const navigate = useNavigate();

  // Initialize MSAL when component mounts
  useEffect(() => {
    const initMsal = async () => {
      try {
        // Fetch Microsoft config from backend
        const configResponse = await fetch(`${API_URL}/api/auth/microsoft/config`);
        const config = await configResponse.json();
        
        if (config.client_id && config.tenant_id) {
          const msalConfig = getMsalConfig(config.client_id, config.tenant_id);
          const pca = new PublicClientApplication(msalConfig);
          await pca.initialize();
          setMsalInstance(pca);
          setMsConfigLoaded(true);
          
          // Handle redirect response if any
          handleRedirectResponse(pca);
        }
      } catch (err) {
        console.error('Failed to initialize MSAL:', err);
      }
    };
    
    initMsal();
  }, []);

  // Handle redirect response after Microsoft login
  const handleRedirectResponse = useCallback(async (pca) => {
    try {
      const response = await pca.handleRedirectPromise();
      
      if (response) {
        setMsLoading(true);
        await completeMicrosoftLogin(response);
      }
    } catch (err) {
      console.error('Redirect response error:', err);
      setError(err.message || 'Microsoft login failed');
      setMsLoading(false);
    }
  }, []);

  // Complete Microsoft login by sending tokens to backend
  const completeMicrosoftLogin = async (msalResponse) => {
    try {
      // Send Microsoft auth data to our backend
      const response = await fetch(`${API_URL}/api/auth/microsoft/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          access_token: msalResponse.accessToken,
          id_token: msalResponse.idToken,
          account: {
            username: msalResponse.account.username,
            name: msalResponse.account.name,
            localAccountId: msalResponse.account.localAccountId,
            tenantId: msalResponse.account.tenantId,
          }
        }),
      });
      
      // FIXED: Check if response is ok before parsing JSON
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Microsoft login error:', errorText);
        setError('Failed to complete Microsoft login');
        return;
      }
      
      const data = await response.json();
      
      if (data.access_token) {
        loginWithToken(data.access_token, data.user);
        navigate('/dashboard');
      } else {
        setError(data.detail || 'Failed to complete login');
      }
    } catch (err) {
      console.error('Microsoft login completion error:', err);
      setError(err.message || 'Failed to complete Microsoft login');
    } finally {
      setMsLoading(false);
    }
  };

  const handleMicrosoftLogin = async () => {
    if (!msalInstance) {
      setError('Microsoft SSO not configured. Please configure O365 integration first.');
      return;
    }

    setMsLoading(true);
    setError('');
    
    try {
      // Use popup login for better UX (no full page redirect)
      const response = await msalInstance.loginPopup(loginRequest);
      await completeMicrosoftLogin(response);
    } catch (err) {
      console.error('Microsoft login error:', err);
      
      // Handle specific MSAL errors
      if (err.errorCode === 'user_cancelled') {
        setError('Login was cancelled');
      } else if (err.errorCode === 'popup_window_error') {
        // Fallback to redirect if popup is blocked
        try {
          await msalInstance.loginRedirect(loginRequest);
        } catch (redirectErr) {
          setError('Failed to initiate Microsoft login');
        }
      } else {
        setError(err.message || 'Microsoft login failed');
      }
      setMsLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      {/* Background Pattern */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-600 mb-4">
            <Database className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Sales Intelligence</h1>
          <p className="text-zinc-500 mt-1">Enterprise Data Platform</p>
        </div>

        {/* Login Card */}
        <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-8">
          {/* Microsoft SSO Button */}
          <Button
            type="button"
            onClick={handleMicrosoftLogin}
            disabled={msLoading || !msConfigLoaded}
            className="w-full bg-[#2F2F2F] hover:bg-[#404040] text-white mb-6 h-12"
            data-testid="microsoft-login-btn"
          >
            {msLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <svg className="w-5 h-5 mr-3" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="1" y="1" width="9" height="9" fill="#F25022"/>
                  <rect x="11" y="1" width="9" height="9" fill="#7FBA00"/>
                  <rect x="1" y="11" width="9" height="9" fill="#00A4EF"/>
                  <rect x="11" y="11" width="9" height="9" fill="#FFB900"/>
                </svg>
                {msConfigLoaded ? 'Sign in with Microsoft' : 'Loading Microsoft SSO...'}
              </>
            )}
          </Button>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-zinc-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-zinc-900/50 text-zinc-500">or continue with email</span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-zinc-300">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@salesintel.com"
                className="bg-zinc-800/50 border-zinc-700 text-white placeholder:text-zinc-500"
                data-testid="login-email-input"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-zinc-300">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="bg-zinc-800/50 border-zinc-700 text-white placeholder:text-zinc-500"
                data-testid="login-password-input"
                required
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white"
              data-testid="login-submit-btn"
            >
              {loading ? (
                'Signing in...'
              ) : (
                <>
                  Sign In
                  <ArrowRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          </form>

          {/* Demo Credentials */}
          <div className="mt-6 pt-6 border-t border-zinc-800">
            <p className="text-zinc-500 text-sm text-center mb-3">Demo Credentials</p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-2 bg-zinc-800/50 rounded-lg">
                <p className="text-zinc-400">Admin</p>
                <p className="text-zinc-300 font-mono">superadmin@salescommand.com</p>
                <p className="text-zinc-500">demo123</p>
              </div>
              <div className="p-2 bg-zinc-800/50 rounded-lg">
                <p className="text-zinc-400">Sales</p>
                <p className="text-zinc-300 font-mono">am1@salescommand.com</p>
                <p className="text-zinc-500">demo123</p>
              </div>
            </div>
          </div>
        </div>

        <p className="text-center text-zinc-600 text-sm mt-6">
          Sales Intelligence Platform v2.0
        </p>
      </div>
    </div>
  );
};

export default Login;
