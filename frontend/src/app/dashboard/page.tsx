'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import { cn, formatDuration } from '@/lib/utils';
import {
  Bot,
  Monitor,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  TrendingUp,
  AlertTriangle,
  Shield,
} from 'lucide-react';
import Link from 'next/link';

interface DashboardStats {
  total_users: number;
  active_users: number;
  total_tasks: number;
  active_sessions: number;
  completed_tasks: number;
  failed_tasks: number;
  stealth_mode: string;
  version: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [agentStatus, setAgentStatus] = useState<any>(null);
  const [recentTasks, setRecentTasks] = useState<any[]>([]);

  useEffect(() => {
    api.get<any>('/tasks?page=1&page_size=5').then((d) => setRecentTasks(d.tasks || [])).catch(() => {});
    api.get<any>('/agent/status').then(setAgentStatus).catch(() => {});
    if (user?.role === 'superadmin') {
      api.get<any>('/admin/dashboard').then(setStats).catch(() => {});
    }
  }, [user?.role]);

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold text-surface-900">
          Welcome back, {user?.username || 'User'} 👋
        </h1>
        <p className="text-surface-500 mt-1">
          Your AI-powered web automation dashboard
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Active Sessions',
            value: agentStatus?.active_sessions ?? '-',
            icon: Monitor,
            color: 'text-emerald-600 bg-emerald-100',
            href: '/dashboard/sessions',
          },
          {
            label: 'Active Tasks',
            value: agentStatus?.active_tasks ?? '-',
            icon: Bot,
            color: 'text-blue-600 bg-blue-100',
            href: '/dashboard/tasks',
          },
          {
            label: 'Stealth Mode',
            value: agentStatus?.stealth_mode ?? 'ultra',
            icon: Shield,
            color: 'text-purple-600 bg-purple-100',
          },
          {
            label: 'Total Tasks Done',
            value: user?.total_tasks_executed ?? 0,
            icon: CheckCircle2,
            color: 'text-green-600 bg-green-100',
          },
        ].map((stat) => (
          <div key={stat.label} className="card hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-surface-500">{stat.label}</p>
                <p className="text-2xl font-bold text-surface-900 mt-1">{stat.value}</p>
              </div>
              <div className={cn('p-2 rounded-lg', stat.color)}>
                <stat.icon className="w-5 h-5" />
              </div>
            </div>
            {stat.href && (
              <Link href={stat.href} className="text-xs text-primary-600 hover:text-primary-700 mt-3 inline-block">
                View all →
              </Link>
            )}
          </div>
        ))}
      </div>

      {/* Superadmin stats */}
      {stats && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">System Overview</h2>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-surface-500">Total Users</p>
              <p className="text-xl font-bold">{stats.total_users}</p>
            </div>
            <div>
              <p className="text-surface-500">Total Tasks</p>
              <p className="text-xl font-bold">{stats.total_tasks}</p>
            </div>
            <div>
              <p className="text-surface-500">Success Rate</p>
              <p className="text-xl font-bold">
                {stats.total_tasks > 0
                  ? Math.round((stats.completed_tasks / stats.total_tasks) * 100)
                  : 0}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Recent Tasks */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Tasks</h2>
          <Link href="/dashboard/tasks" className="text-sm text-primary-600 hover:text-primary-700">
            View All
          </Link>
        </div>

        {recentTasks.length === 0 ? (
          <div className="text-center py-8 text-surface-500">
            <Bot className="w-12 h-12 mx-auto mb-3 text-surface-300" />
            <p>No tasks yet</p>
            <Link href="/dashboard/tasks" className="text-primary-600 text-sm mt-1 inline-block">
              Create your first task →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {recentTasks.map((task: any) => (
              <Link
                key={task.id}
                href={`/dashboard/tasks/${task.id}`}
                className="flex items-center gap-4 p-3 rounded-lg hover:bg-surface-50 transition-colors"
              >
                <div className={cn(
                  'p-2 rounded-lg',
                  task.status === 'completed' ? 'bg-green-100' :
                  task.status === 'failed' ? 'bg-red-100' :
                  task.status === 'running' ? 'bg-blue-100' :
                  'bg-surface-100'
                )}>
                  {task.status === 'completed' ? (
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                  ) : task.status === 'failed' ? (
                    <XCircle className="w-4 h-4 text-red-600" />
                  ) : (
                    <Clock className="w-4 h-4 text-blue-600 animate-pulse" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-surface-900 truncate">{task.prompt}</p>
                  <p className="text-xs text-surface-500">
                    {task.status} · {task.duration_ms ? formatDuration(task.duration_ms) : 'In progress'}
                  </p>
                </div>
                <span className={cn(
                  'text-xs px-2 py-0.5 rounded-full font-medium',
                  task.status === 'completed' ? 'bg-green-100 text-green-700' :
                  task.status === 'failed' ? 'bg-red-100 text-red-700' :
                  'bg-blue-100 text-blue-700'
                )}>
                  {task.status}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid sm:grid-cols-3 gap-4">
          <Link
            href="/dashboard/tasks"
            className="flex items-center gap-3 p-4 rounded-lg border border-surface-200 hover:border-primary-300 hover:bg-primary-50 transition-all"
          >
            <Bot className="w-5 h-5 text-primary-600" />
            <span className="text-sm font-medium">New Task</span>
          </Link>
          <Link
            href="/dashboard/sessions"
            className="flex items-center gap-3 p-4 rounded-lg border border-surface-200 hover:border-primary-300 hover:bg-primary-50 transition-all"
          >
            <Monitor className="w-5 h-5 text-primary-600" />
            <span className="text-sm font-medium">Manage Sessions</span>
          </Link>
          <Link
            href="/dashboard/settings"
            className="flex items-center gap-3 p-4 rounded-lg border border-surface-200 hover:border-primary-300 hover:bg-primary-50 transition-all"
          >
            <Zap className="w-5 h-5 text-primary-600" />
            <span className="text-sm font-medium">API Keys</span>
          </Link>
        </div>
      </div>
    </div>
  );
}


