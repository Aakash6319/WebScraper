'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { cn, formatDate } from '@/lib/utils';
import {
  Shield,
  Users,
  Loader2,
  RefreshCw,
  UserCheck,
  UserX,
  Settings2,
  Monitor,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function AdminPage() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [globalSettings, setGlobalSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [dash, userList, settings] = await Promise.all([
        api.get<any>('/admin/dashboard'),
        api.get<any>('/auth/admin/users?page_size=100'),
        api.get<any>('/admin/settings'),
      ]);
      setDashboard(dash);
      setUsers(userList.users || []);
      setGlobalSettings(settings);
    } catch (err: any) {
      toast.error('Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const changeRole = async (userId: string, role: string) => {
    try {
      await api.put(`/auth/admin/users/${userId}/role?role=${role}`);
      toast.success('Role updated');
      fetchAll();
    } catch (err: any) {
      toast.error(err.message || 'Failed to update role');
    }
  };

  const toggleActive = async (userId: string, active: boolean) => {
    try {
      await api.put(`/auth/admin/users/${userId}/active?is_active=${active}`);
      toast.success(`User ${active ? 'activated' : 'deactivated'}`);
      fetchAll();
    } catch (err: any) {
      toast.error(err.message || 'Failed to toggle');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Admin Panel</h1>
          <p className="text-surface-500 mt-1">Superadmin controls & monitoring</p>
        </div>
        <button onClick={fetchAll} className="btn-secondary">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* System Dashboard */}
      {dashboard && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Total Users', value: dashboard.total_users, icon: Users, color: 'text-blue-600 bg-blue-100' },
            { label: 'Active Users', value: dashboard.active_users, icon: UserCheck, color: 'text-green-600 bg-green-100' },
            { label: 'Total Tasks', value: dashboard.total_tasks, icon: Monitor, color: 'text-purple-600 bg-purple-100' },
            { label: 'Active Sessions', value: dashboard.active_sessions, icon: Monitor, color: 'text-emerald-600 bg-emerald-100' },
          ].map((stat) => (
            <div key={stat.label} className="card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-surface-500">{stat.label}</p>
                  <p className="text-2xl font-bold mt-1">{stat.value}</p>
                </div>
                <div className={cn('p-2 rounded-lg', stat.color)}>
                  <stat.icon className="w-5 h-5" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* System Stats */}
      {dashboard && (
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="card">
            <h3 className="font-semibold mb-3">Task Stats</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-surface-500">Completed</span>
                <span className="text-green-600 font-medium">{dashboard.completed_tasks}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-surface-500">Failed</span>
                <span className="text-red-600 font-medium">{dashboard.failed_tasks}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-surface-500">Success Rate</span>
                <span className="font-medium">
                  {dashboard.total_tasks > 0
                    ? Math.round((dashboard.completed_tasks / dashboard.total_tasks) * 100)
                    : 0}%
                </span>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold mb-3">Global Config</h3>
            <div className="space-y-2 text-sm">
              {globalSettings && Object.entries(globalSettings).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-surface-500 capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="font-medium text-surface-700">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* User Management */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Users className="w-5 h-5" />
          User Management
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-200">
                <th className="text-left py-3 px-3 font-medium text-surface-500">User</th>
                <th className="text-left py-3 px-3 font-medium text-surface-500">Role</th>
                <th className="text-left py-3 px-3 font-medium text-surface-500">Status</th>
                <th className="text-left py-3 px-3 font-medium text-surface-500">Tasks</th>
                <th className="text-left py-3 px-3 font-medium text-surface-500">Keys</th>
                <th className="text-right py-3 px-3 font-medium text-surface-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u: any) => (
                <tr key={u.id} className="border-b border-surface-100 hover:bg-surface-50">
                  <td className="py-3 px-3">
                    <div>
                      <p className="font-medium text-surface-900">{u.username}</p>
                      <p className="text-xs text-surface-500">{u.email}</p>
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <select
                      value={u.role}
                      onChange={(e) => changeRole(u.id, e.target.value)}
                      className="text-xs border rounded px-2 py-1 bg-white"
                    >
                      <option value="normal">Normal</option>
                      <option value="premium">Premium</option>
                      <option value="superadmin">Superadmin</option>
                    </select>
                  </td>
                  <td className="py-3 px-3">
                    <span className={cn(
                      'px-2 py-0.5 rounded-full text-xs',
                      u.is_active
                        ? 'bg-green-100 text-green-700'
                        : 'bg-red-100 text-red-700'
                    )}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-surface-500">{u.total_tasks_executed}</td>
                  <td className="py-3 px-3">
                    <div className="flex gap-1">
                      {u.has_deepseek_key && <span className="text-xs text-green-600">DS</span>}
                      {u.has_anticaptcha_key && <span className="text-xs text-blue-600">AC</span>}
                      {u.has_proxy_credentials && <span className="text-xs text-purple-600">P</span>}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => toggleActive(u.id, !u.is_active)}
                      className={cn(
                        'px-3 py-1 rounded text-xs font-medium',
                        u.is_active
                          ? 'bg-red-50 text-red-700 hover:bg-red-100'
                          : 'bg-green-50 text-green-700 hover:bg-green-100'
                      )}
                    >
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
