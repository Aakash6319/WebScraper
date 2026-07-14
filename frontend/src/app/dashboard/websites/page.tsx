'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import {
  Plus,
  Loader2,
  Globe,
  Trash2,
  Star,
  ExternalLink,
  X,
  Search,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function WebsitesPage() {
  const [websites, setWebsites] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState('');
  const [form, setForm] = useState({
    name: '',
    url: '',
    description: '',
    login_username: '',
    login_password: '',
    login_url: '',
    tags: '',
    use_proxy: true,
    stealth_mode_override: '',
  });

  const fetchWebsites = async () => {
    try {
      const params = new URLSearchParams({ page: '1', page_size: '50' });
      if (search) params.set('search', search);
      const data = await api.get<any>(`/websites?${params}`);
      setWebsites(data.websites || []);
    } catch {
      toast.error('Failed to load websites');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchWebsites(); }, [search]);

  const createWebsite = async () => {
    if (!form.name || !form.url) return;
    try {
      const body: any = { ...form };
      body.tags = form.tags.split(',').map((t: string) => t.trim()).filter(Boolean);
      if (!form.stealth_mode_override) delete body.stealth_mode_override;
      await api.post('/websites', body);
      toast.success('Website added!');
      setShowCreate(false);
      setForm({ name: '', url: '', description: '', login_username: '', login_password: '', login_url: '', tags: '', use_proxy: true, stealth_mode_override: '' });
      fetchWebsites();
    } catch (err: any) {
      toast.error(err.message || 'Failed to add website');
    }
  };

  const deleteWebsite = async (id: string) => {
    if (!confirm('Delete this website configuration?')) return;
    try {
      await api.delete(`/websites/${id}`);
      toast.success('Website deleted');
      fetchWebsites();
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Websites</h1>
          <p className="text-surface-500 mt-1">Store website configurations with credentials</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <Plus className="w-4 h-4 mr-2" />
          Add Website
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field pl-10"
          placeholder="Search websites..."
        />
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto animate-slide-up" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Add Website</h3>
              <button onClick={() => setShowCreate(false)} className="p-1 rounded-lg hover:bg-surface-100">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Name *</label>
                <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="input-field" placeholder="Amazon" />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">URL *</label>
                <input type="text" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} className="input-field" placeholder="https://amazon.com" />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Description</label>
                <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="input-field" rows={2} />
              </div>

              <div className="border-t pt-3">
                <p className="text-sm font-medium text-surface-700 mb-2">Login Credentials (optional)</p>
                <div className="space-y-3">
                  <input type="text" value={form.login_url} onChange={e => setForm({ ...form, login_url: e.target.value })} className="input-field" placeholder="Login page URL" />
                  <div className="grid grid-cols-2 gap-3">
                    <input type="text" value={form.login_username} onChange={e => setForm({ ...form, login_username: e.target.value })} className="input-field" placeholder="Username" />
                    <input type="password" value={form.login_password} onChange={e => setForm({ ...form, login_password: e.target.value })} className="input-field" placeholder="Password" />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Tags (comma-separated)</label>
                <input type="text" value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} className="input-field" placeholder="shopping, ecommerce" />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex items-center gap-2">
                  <input type="checkbox" checked={form.use_proxy} onChange={e => setForm({ ...form, use_proxy: e.target.checked })} className="rounded" />
                  <label className="text-sm text-surface-700">Use Proxy</label>
                </div>
                <select value={form.stealth_mode_override} onChange={e => setForm({ ...form, stealth_mode_override: e.target.value })} className="input-field text-sm">
                  <option value="">Default Stealth</option>
                  <option value="basic">Basic</option>
                  <option value="advanced">Advanced</option>
                  <option value="ultra">Ultra</option>
                </select>
              </div>

              <button onClick={createWebsite} disabled={!form.name || !form.url} className="btn-primary w-full mt-2">
                Add Website
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Website Cards */}
      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-surface-400" /></div>
      ) : websites.length === 0 ? (
        <div className="card text-center py-12">
          <Globe className="w-12 h-12 mx-auto mb-3 text-surface-300" />
          <p className="text-surface-500">No websites configured</p>
          <button onClick={() => setShowCreate(true)} className="text-primary-600 text-sm mt-1">Add your first website →</button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {websites.map((site: any) => (
            <div key={site.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-surface-900 truncate">{site.name}</h3>
                  <p className="text-xs text-surface-500 truncate mt-0.5">{site.url}</p>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => deleteWebsite(site.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-surface-400 hover:text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap gap-1 mt-2">
                {site.has_login_credentials && (
                  <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">Credentials</span>
                )}
                {site.use_proxy && (
                  <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">Proxy</span>
                )}
                {site.stealth_mode_override && (
                  <span className="px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-700">{site.stealth_mode_override}</span>
                )}
                {site.tags?.map((tag: string) => (
                  <span key={tag} className="px-2 py-0.5 rounded-full text-xs bg-surface-100 text-surface-600">{tag}</span>
                ))}
              </div>

              {site.use_count > 0 && (
                <p className="text-xs text-surface-400 mt-2">Used {site.use_count} times</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
