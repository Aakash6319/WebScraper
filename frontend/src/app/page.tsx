'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { Zap, Shield, Bot, Globe, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function HomePage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface-950 via-surface-900 to-surface-950 text-white">
      {/* Navigation */}
      <nav className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-primary-500 flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold">AutoWebAgent</span>
            </div>
            <div className="flex items-center gap-4">
              {isAuthenticated ? (
                <Link href="/dashboard" className="btn-primary">
                  Dashboard
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
              ) : (
                <>
                  <Link
                    href="/auth/login"
                    className="text-sm text-surface-300 hover:text-white transition-colors"
                  >
                    Sign In
                  </Link>
                  <Link href="/auth/register" className="btn-primary text-sm">
                    Get Started
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16">
        <div className="text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-sm mb-8">
            <Zap className="w-4 h-4" />
            Production-Grade Web Automation
          </div>
          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-6">
            AI-Powered Web
            <br />
            <span className="text-primary-400">Automation Agent</span>
          </h1>
          <p className="text-xl text-surface-400 mb-10 leading-relaxed">
            Describe any web task in natural language. Our AI agent executes it
            with military-grade stealth — bypassing CAPTCHAs, bot detection, and
            fingerprinting.
          </p>
          <div className="flex items-center justify-center gap-4">
            {isAuthenticated ? (
              <Link href="/dashboard/tasks" className="btn-primary text-lg px-8 py-3">
                Create Task
                <ArrowRight className="w-5 h-5 ml-2" />
              </Link>
            ) : (
              <Link href="/auth/register" className="btn-primary text-lg px-8 py-3">
                Start Free
                <ArrowRight className="w-5 h-5 ml-2" />
              </Link>
            )}
            <a href="#features" className="btn-secondary text-lg px-8 py-3 !text-white !bg-white/10 !ring-white/20 hover:!bg-white/20">
              Learn More
            </a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <h2 className="text-3xl font-bold text-center mb-16">
          Why AutoWebAgent?
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {[
            {
              icon: Shield,
              title: 'Ultra Stealth',
              desc: 'Canvas, WebGL, AudioContext fingerprint spoofing. Bypass Cloudflare, DataDome, Akamai.',
            },
            {
              icon: Bot,
              title: 'AI Agent',
              desc: 'Powered by DeepSeek. Natural language prompts become multi-step action plans.',
            },
            {
              icon: Globe,
              title: 'Global Proxy',
              desc: 'Webshare rotating residential proxies. Geo-targeting with fingerprint consistency.',
            },
            {
              icon: CheckCircle2,
              title: 'CAPTCHA Auto-Solve',
              desc: 'Auto-detects & solves reCAPTCHA, hCaptcha, Turnstile via Anti-Captcha.',
            },
          ].map((feat) => (
            <div
              key={feat.title}
              className="p-6 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
            >
              <div className="w-12 h-12 rounded-lg bg-primary-500/10 flex items-center justify-center mb-4">
                <feat.icon className="w-6 h-6 text-primary-400" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{feat.title}</h3>
              <p className="text-surface-400 text-sm leading-relaxed">{feat.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <h2 className="text-3xl font-bold text-center mb-16">How It Works</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            { step: '1', title: 'Describe', desc: 'Type your task in natural language — like talking to a human assistant.' },
            { step: '2', title: 'Execute', desc: 'Our AI agent plans, navigates, and interacts with sites using human-like behavior.' },
            { step: '3', title: 'Extract', desc: 'Get structured results — data, screenshots, and execution logs.' },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-primary-500/20 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-primary-400">{item.step}</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
              <p className="text-surface-400">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="rounded-2xl bg-gradient-to-r from-primary-600 to-primary-800 p-12 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Automate?</h2>
          <p className="text-primary-100 mb-8 max-w-lg mx-auto">
            Start automating web tasks with the most advanced stealth technology available.
          </p>
          {isAuthenticated ? (
            <Link href="/dashboard/tasks" className="inline-flex items-center gap-2 rounded-lg bg-white px-8 py-3 text-primary-700 font-semibold hover:bg-primary-50 transition-colors">
              Go to Dashboard
              <ArrowRight className="w-4 h-4" />
            </Link>
          ) : (
            <Link href="/auth/register" className="inline-flex items-center gap-2 rounded-lg bg-white px-8 py-3 text-primary-700 font-semibold hover:bg-primary-50 transition-colors">
              Get Started Free
              <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center text-surface-500 text-sm">
          © {new Date().getFullYear()} AutoWebAgent. Built with Next.js, FastAPI & DeepSeek.
        </div>
      </footer>
    </div>
  );
}
