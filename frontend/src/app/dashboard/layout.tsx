'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Bot,
  Globe,
  Monitor,
  Settings,
  Shield,
  LogOut,
  Menu,
  X,
  Zap,
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/tasks', label: 'Tasks', icon: Bot },
  { href: '/dashboard/sessions', label: 'Sessions', icon: Monitor },
  { href: '/dashboard/websites', label: 'Websites', icon: Globe },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
];

const adminItems = [
  { href: '/dashboard/admin', label: 'Admin Panel', icon: Shield },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isSuperAdmin = user?.role === 'superadmin';

  return (
    <div className="min-h-screen flex bg-surface-50">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-surface-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:z-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-3 px-6 py-5 border-b border-surface-200">
            <div className="w-9 h-9 rounded-lg bg-primary-600 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-surface-900">AutoWebAgent</h1>
              <p className="text-xs text-surface-500">AI Automation</p>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden ml-auto p-1 rounded-lg hover:bg-surface-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900'
                  )}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {item.label}
                </Link>
              );
            })}

            {isSuperAdmin && (
              <>
                <div className="pt-4 pb-1 px-3">
                  <p className="text-xs font-semibold text-surface-400 uppercase tracking-wider">
                    Admin
                  </p>
                </div>
                {adminItems.map((item) => {
                  const isActive = pathname === item.href;
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setSidebarOpen(false)}
                      className={cn(
                        'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-primary-50 text-primary-700'
                          : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900'
                      )}
                    >
                      <Icon className="w-5 h-5 flex-shrink-0" />
                      {item.label}
                    </Link>
                  );
                })}
              </>
            )}
          </nav>

          {/* User section */}
          <div className="border-t border-surface-200 p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-semibold text-sm">
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-surface-900 truncate">
                  {user?.username || 'User'}
                </p>
                <p className="text-xs text-surface-500 truncate">{user?.email}</p>
              </div>
            </div>
            <button
              onClick={() => logout()}
              className="flex items-center gap-2 w-full px-3 py-2 text-sm text-surface-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-sm border-b border-surface-200 px-4 py-3 lg:px-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-surface-100"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex-1" />
            <div className="flex items-center gap-2 text-sm text-surface-500">
              <span className={cn(
                'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                user?.role === 'superadmin'
                  ? 'bg-purple-100 text-purple-700'
                  : user?.role === 'premium'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-surface-100 text-surface-600'
              )}>
                {user?.role || 'user'}
              </span>
            </div>
          </div>
        </header>

        <div className="p-4 lg:p-8">{children}</div>
      </main>
    </div>
  );
}
