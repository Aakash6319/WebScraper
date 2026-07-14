'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { cn, formatDate, getStatusColor } from '@/lib/utils';
import {
  Plus,
  Loader2,
  Monitor,
  Trash2,
  RefreshCw,
  Globe,
  X,
  ExternalLink,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function SessionsPage() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: '',
    stealth_mode: 'ultra',
    viewport_width: 1920,
    viewport_height: 1080,
    proxy_country: '',
  });

  const fetchSessions = async () => {
    try {
      const data = await api.get<any>('/sessions');
      setSessions(data.sessions || []);
    } catch {
      toast.error('Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSessions(); }, []);

  const createSession = async () => {
    setCreating(true);
    try {
      const body: any = {
        name: form.name || undefined,
        stealth_mode: form.stealth_mode,
        viewport_width: form.viewport_width,
        viewport_height: form.viewport_height,
      };
      if (form.proxy_country) body.proxy_country = form.proxy_country;

      await api.post('/sessions', body);
      toast.success('Session created!');
      setShowCreate(false);
      setForm({ name: '', stealth_mode: 'ultra', viewport_width: 1920, viewport_height: 1080, proxy_country: '' });
      fetchSessions();
    } catch (err: any) {
      toast.error(err.message || 'Failed to create session');
    } finally {
      setCreating(false);
    }
  };

  const closeSession = async (sessionId: string) => {
    if (!confirm('Close this session? All browser state will be lost.')) return;
    try {
      await api.delete(`/sessions/${sessionId}`);
      toast.success('Session closed');
      fetchSessions();
    } catch (err: any) {
      toast.error(err.message || 'Failed to close session');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Browser Sessions</h1>
          <p className="text-surface-500 mt-1">Isolated browser contexts with stealth</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchSessions} className="btn-secondary">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </button>
          <button onClick={() => setShowCreate(true)} className="btn-primary">
            <Plus className="w-4 h-4 mr-2" />
            New Session
          </button>
        </div>
      </div>

      {/* Create Session Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4 animate-slide-up" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">New Browser Session</h3>
              <button onClick={() => setShowCreate(false)} className="p-1 rounded-lg hover:bg-surface-100">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Name (optional)</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  className="input-field"
                  placeholder="My Session"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Stealth Mode</label>
                <select
                  value={form.stealth_mode}
                  onChange={e => setForm({ ...form, stealth_mode: e.target.value })}
                  className="input-field"
                >
                  <option value="basic">Basic</option>
                  <option value="advanced">Advanced</option>
                  <option value="ultra">Ultra (Recommended)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Width</label>
                  <input
                    type="number"
                    value={form.viewport_width}
                    onChange={e => setForm({ ...form, viewport_width: +e.target.value })}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Height</label>
                  <input
                    type="number"
                    value={form.viewport_height}
                    onChange={e => setForm({ ...form, viewport_height: +e.target.value })}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Proxy Country (optional)</label>
                <select
                  value={form.proxy_country}
                  onChange={e => setForm({ ...form, proxy_country: e.target.value })}
                  className="input-field"
                >
                  <option value="">Default</option>
                  <option value="US">🇺🇸 United States</option>
                  <option value="GB">🇬🇧 United Kingdom</option>
                  <option value="DE">🇩🇪 Germany</option>
                  <option value="JP">🇯🇵 Japan</option>
                  <option value="AU">🇦🇺 Australia</option>
                </select>
              </div>

              <button onClick={createSession} disabled={creating} className="btn-primary w-full">
                {creating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Create Session
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sessions List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
        </div>
      ) : sessions.length === 0 ? (
        <div className="card text-center py-12">
          <Monitor className="w-12 h-12 mx-auto mb-3 text-surface-300" />
          <p className="text-surface-500">No active sessions</p>
          <button onClick={() => setShowCreate(true)} className="text-primary-600 text-sm mt-1">
            Create your first session →
          </button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sessions.map((session: any) => (
            <div key={session.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-medium text-surface-900 text-sm">
                    {session.name || `Session ${session.id.slice(0, 8)}`}
                  </h3>
                  <span className={cn(
                    'inline-block px-2 py-0.5 rounded-full text-xs font-medium mt-1',
                    getStatusColor(session.status)
                  )}>
                    {session.status}
                  </span>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => closeSession(session.id)}
                    className="p-1.5 rounded-lg hover:bg-red-50 text-surface-400 hover:text-red-600"
                    title="Close"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="space-y-2 text-sm">
                {session.current_url && (
                  <div className="flex items-center gap-1 text-surface-500 truncate">
                    <Globe className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{session.current_url}</span>
                  </div>
                )}
                <div className="flex items-center justify-between text-surface-400">
                  <span>{session.viewport_width}×{session.viewport_height}</span>
                  <span className="capitalize">{session.stealth_mode}</span>
                </div>
                {session.proxy_country && (
                  <div className="text-xs text-surface-400">
                    Proxy: {session.proxy_country}
                  </div>
                )}
                <div className="flex justify-between text-xs text-surface-400 pt-1 border-t border-surface-100">
                  <span>{session.pages_visited} pages</span>
                  <span>{session.tasks_completed} tasks</span>
                  <span>{session.captchas_solved} captchas</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
