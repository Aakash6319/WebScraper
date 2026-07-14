'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';
import {
  Key,
  Loader2,
  Eye,
  EyeOff,
  Shield,
  Globe,
  Zap,
  Save,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [showKeys, setShowKeys] = useState(false);
  const [proxyStatus, setProxyStatus] = useState<any>(null);
  const [checkingProxy, setCheckingProxy] = useState(false);

  const [keys, setKeys] = useState({
    deepseek_api_key: '',
    anticaptcha_api_key: '',
    capsolver_api_key: '',
    webshare_proxy_username: '',
    webshare_proxy_password: '',
    proxy_host: '',
    proxy_port: '',
  });

  const [keyStatus, setKeyStatus] = useState<any>(null);

  useEffect(() => {
    api.get('/auth/me/api-keys').then((status: any) => {
      setKeyStatus(status);
      setKeys(prev => ({
        ...prev,
        webshare_proxy_username: status.webshare_proxy_username || '',
        proxy_host: status.proxy_host || '',
        proxy_port: status.proxy_port ? String(status.proxy_port) : '',
      }));
    }).catch(() => {});
    api.get('/proxy/status').then(setProxyStatus).catch(() => {});
  }, []);

  const saveKeys = async () => {
    setLoading(true);
    try {
      const body: any = {};
      if (keys.deepseek_api_key) body.deepseek_api_key = keys.deepseek_api_key;
      if (keys.anticaptcha_api_key) body.anticaptcha_api_key = keys.anticaptcha_api_key;
      if (keys.capsolver_api_key) body.capsolver_api_key = keys.capsolver_api_key;
      if (keys.webshare_proxy_username) body.webshare_proxy_username = keys.webshare_proxy_username;
      if (keys.webshare_proxy_password) body.webshare_proxy_password = keys.webshare_proxy_password;
      if (keys.proxy_host) body.proxy_host = keys.proxy_host;
      if (keys.proxy_port) body.proxy_port = parseInt(keys.proxy_port);

      if (Object.keys(body).length === 0) {
        toast.error('Enter at least one key to update');
        return;
      }

      await api.put('/auth/me/api-keys', body);
      toast.success('API keys updated!');
      const status: any = await api.get('/auth/me/api-keys');
      setKeyStatus(status);
      setKeys({
        deepseek_api_key: '',
        anticaptcha_api_key: '',
        capsolver_api_key: '',
        webshare_proxy_password: '',
        webshare_proxy_username: status.webshare_proxy_username || '',
        proxy_host: status.proxy_host || '',
        proxy_port: status.proxy_port ? String(status.proxy_port) : '',
      });
      refreshUser();
    } catch (err: any) {
      toast.error(err.message || 'Failed to save keys');
    } finally {
      setLoading(false);
    }
  };

  const validateProxy = async () => {
    setCheckingProxy(true);
    try {
      const result: any = await api.get('/proxy/validate');
      setProxyStatus(result);
      if (result.valid) {
        toast.success(`Proxy OK — IP: ${result.ip} (${result.country})`);
      } else {
        toast.error(result.error || 'Proxy validation failed');
      }
    } catch (err: any) {
      toast.error(err.message || 'Proxy check failed');
    } finally {
      setCheckingProxy(false);
    }
  };

  const rotateProxy = async () => {
    try {
      await api.post('/proxy/rotate');
      toast.success('Proxy rotated!');
      validateProxy();
    } catch (err: any) {
      toast.error(err.message || 'Rotation failed');
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-surface-900">Settings</h1>
        <p className="text-surface-500 mt-1">Manage API keys and proxy configuration</p>
      </div>

      {/* API Keys Section */}
      <div className="card">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-amber-100">
            <Key className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">API Keys</h2>
            <p className="text-sm text-surface-500">Your personal API credentials (encrypted at rest)</p>
          </div>
        </div>

        {/* Current Key Status */}
        {keyStatus && (
          <div className="grid grid-cols-4 gap-4 mb-6 p-4 rounded-lg bg-surface-50">
            <div className="text-center">
              <div className={cn(
                'w-3 h-3 rounded-full mx-auto mb-1',
                keyStatus.has_deepseek_key ? 'bg-green-500' : 'bg-red-400'
              )} />
              <p className="text-xs text-surface-600">DeepSeek</p>
              <p className="text-xs text-surface-400 truncate max-w-[120px] mx-auto" title={keyStatus.deepseek_key_masked || 'Not set'}>
                {keyStatus.deepseek_key_masked || 'Not set'}
              </p>
            </div>
            <div className="text-center">
              <div className={cn(
                'w-3 h-3 rounded-full mx-auto mb-1',
                keyStatus.has_anticaptcha_key ? 'bg-green-500' : 'bg-red-400'
              )} />
              <p className="text-xs text-surface-600">Anti-Captcha</p>
              <p className="text-xs text-surface-400 truncate max-w-[120px] mx-auto" title={keyStatus.anticaptcha_key_masked || 'Not set'}>
                {keyStatus.anticaptcha_key_masked || 'Not set'}
              </p>
            </div>
            <div className="text-center">
              <div className={cn(
                'w-3 h-3 rounded-full mx-auto mb-1',
                keyStatus.has_capsolver_key ? 'bg-green-500' : 'bg-red-400'
              )} />
              <p className="text-xs text-surface-600">CapSolver</p>
              <p className="text-xs text-surface-400 truncate max-w-[120px] mx-auto" title={keyStatus.capsolver_key_masked || 'Not set'}>
                {keyStatus.capsolver_key_masked || 'Not set'}
              </p>
            </div>
            <div className="text-center">
              <div className={cn(
                'w-3 h-3 rounded-full mx-auto mb-1',
                keyStatus.has_proxy_credentials ? 'bg-green-500' : 'bg-red-400'
              )} />
              <p className="text-xs text-surface-600">Proxy</p>
              <p className="text-xs text-surface-400 truncate max-w-[120px] mx-auto" title={keyStatus.has_proxy_credentials ? 'Configured' : 'Not set'}>
                {keyStatus.has_proxy_credentials ? 'Configured' : 'Not set'}
              </p>
            </div>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              <Zap className="w-3 h-3 inline mr-1" />
              DeepSeek API Key
            </label>
            <div className="relative">
              <input
                type={showKeys ? 'text' : 'password'}
                value={keys.deepseek_api_key}
                onChange={(e) => setKeys({ ...keys, deepseek_api_key: e.target.value })}
                className="input-field pr-10"
                placeholder={keyStatus?.deepseek_key_masked || 'sk-...'}
              />
              <button
                onClick={() => setShowKeys(!showKeys)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-600"
              >
                {showKeys ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-surface-400 mt-1">
              Get your key at{' '}
              <a href="https://platform.deepseek.com" target="_blank" className="text-primary-600">
                platform.deepseek.com
              </a>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              <Shield className="w-3 h-3 inline mr-1" />
              Anti-Captcha API Key
            </label>
            <input
              type={showKeys ? 'text' : 'password'}
              value={keys.anticaptcha_api_key}
              onChange={(e) => setKeys({ ...keys, anticaptcha_api_key: e.target.value })}
              className="input-field"
              placeholder={keyStatus?.anticaptcha_key_masked || 'Your Anti-Captcha key'}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              <Shield className="w-3 h-3 inline mr-1" />
              CapSolver API Key (Prioritized)
            </label>
            <input
              type={showKeys ? 'text' : 'password'}
              value={keys.capsolver_api_key}
              onChange={(e) => setKeys({ ...keys, capsolver_api_key: e.target.value })}
              className="input-field"
              placeholder={keyStatus?.capsolver_key_masked || 'Capsolver-xxxxxx...'}
            />
          </div>

          <div className="border-t pt-4">
            <label className="block text-sm font-medium text-surface-700 mb-2">
              <Globe className="w-3 h-3 inline mr-1" />
              Webshare Proxy Credentials
            </label>
            <div className="grid grid-cols-2 gap-3">
              <input
                type="text"
                value={keys.webshare_proxy_username}
                onChange={(e) => setKeys({ ...keys, webshare_proxy_username: e.target.value })}
                className="input-field"
                placeholder="Username"
              />
              <input
                type={showKeys ? 'text' : 'password'}
                value={keys.webshare_proxy_password}
                onChange={(e) => setKeys({ ...keys, webshare_proxy_password: e.target.value })}
                className="input-field"
                placeholder={keyStatus?.has_proxy_credentials ? '••••••••••••' : 'Password'}
              />
            </div>
            <div className="grid grid-cols-2 gap-3 mt-3">
              <input
                type="text"
                value={keys.proxy_host}
                onChange={(e) => setKeys({ ...keys, proxy_host: e.target.value })}
                className="input-field"
                placeholder="Proxy Host (e.g. 198.105.121.200)"
              />
              <input
                type="text"
                value={keys.proxy_port}
                onChange={(e) => setKeys({ ...keys, proxy_port: e.target.value })}
                className="input-field"
                placeholder="Port (e.g. 6462)"
              />
            </div>
          </div>

          <button onClick={saveKeys} disabled={loading} className="btn-primary w-full">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
            Save Keys
          </button>
        </div>
      </div>

      {/* Proxy Status */}
      <div className="card">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-blue-100">
            <Globe className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Proxy Status</h2>
            <p className="text-sm text-surface-500">Webshare rotating residential proxy</p>
          </div>
        </div>

        {proxyStatus?.valid !== undefined ? (
          <div className={cn(
            'p-4 rounded-lg mb-4',
            proxyStatus.valid ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
          )}>
            <div className="flex items-center gap-2">
              {proxyStatus.valid ? (
                <CheckCircle2 className="w-5 h-5 text-green-600" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-red-600" />
              )}
              <span className={proxyStatus.valid ? 'text-green-800 font-medium' : 'text-red-800 font-medium'}>
                {proxyStatus.valid ? 'Connected' : 'Not Connected'}
              </span>
            </div>
            {proxyStatus.valid && (
              <div className="mt-2 text-sm text-green-700 grid grid-cols-2 gap-1">
                <span>IP: {proxyStatus.ip}</span>
                <span>Country: {proxyStatus.country}</span>
                <span>City: {proxyStatus.city}</span>
                <span>Latency: {proxyStatus.response_time_ms}ms</span>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 rounded-lg bg-surface-50 text-surface-500 text-sm mb-4">
            Click "Check Proxy" to validate your connection
          </div>
        )}

        <div className="flex gap-3">
          <button onClick={validateProxy} disabled={checkingProxy} className="btn-secondary flex-1">
            {checkingProxy ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Globe className="w-4 h-4 mr-2" />}
            Check Proxy
          </button>
          <button onClick={rotateProxy} className="btn-secondary flex-1">
            <RefreshCw className="w-4 h-4 mr-2" />
            Rotate IP
          </button>
        </div>
      </div>
    </div>
  );
}


