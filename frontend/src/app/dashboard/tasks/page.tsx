'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { cn, formatDuration, getStatusColor } from '@/lib/utils';
import {
  Loader2,
  Bot,
  Send,
  AlertTriangle,
  Trash2,
  RefreshCw,
  Eye,
  X,
  ShieldAlert,
  Mail,
  KeyRound,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import toast from 'react-hot-toast';

// ─── Global OTP / Verification Popup ─────────────────────────────
function OTPVerificationPopup({
  task,
  onSubmit,
  onDismiss,
}: {
  task: any;
  onSubmit: (taskId: string, code: string) => Promise<void>;
  onDismiss: () => void;
}) {
  const [code, setCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [countdown, setCountdown] = useState(300); // 5 minutes
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus input when popup opens
  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 100);
  }, []);

  // Countdown timer
  useEffect(() => {
    const t = setInterval(() => setCountdown(c => Math.max(0, c - 1)), 1000);
    return () => clearInterval(t);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(task.id, code.trim());
      setCode('');
    } finally {
      setSubmitting(false);
    }
  };

  const mins = Math.floor(countdown / 60);
  const secs = countdown % 60;
  const isExpired = countdown === 0;

  return (
    // Full-screen backdrop with blur — always visible regardless of modal state
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-md animate-fade-in">
      {/* Popup card */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden animate-slide-up">
        {/* Top accent bar */}
        <div className="h-1.5 w-full bg-gradient-to-r from-amber-400 via-orange-500 to-red-500" />

        <div className="p-6">
          {/* Header */}
          <div className="flex items-start gap-3 mb-5">
            <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
              <Mail className="w-6 h-6 text-amber-600 animate-pulse" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-bold text-gray-900">Email Verification Required</h2>
              <p className="text-sm text-gray-500 mt-0.5">LinkedIn sent a code to your email</p>
            </div>
            <button
              onClick={onDismiss}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Prompt message */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 mb-5">
            <p className="text-sm text-amber-800 font-medium">
              {task.user_input_prompt || 'Enter the verification code sent to your registered email address.'}
            </p>
          </div>

          {/* Task info */}
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs text-gray-400">Task:</span>
            <span className="text-xs font-medium text-gray-600 truncate max-w-[280px]">{task.prompt?.slice(0, 60)}...</span>
          </div>

          {/* OTP Input form */}
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="relative">
              <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                ref={inputRef}
                type="text"
                value={code}
                onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 8))}
                placeholder="Enter 6-digit code..."
                className="w-full pl-10 pr-4 py-3 border-2 border-amber-300 focus:border-amber-500 rounded-xl text-center text-xl font-bold tracking-[0.4em] text-gray-800 focus:outline-none focus:ring-4 focus:ring-amber-100 transition-all placeholder:text-gray-300 placeholder:text-base placeholder:tracking-normal"
                maxLength={8}
                disabled={isExpired}
                required
              />
            </div>

            <button
              type="submit"
              disabled={submitting || !code.trim() || isExpired}
              className="w-full py-3 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-bold rounded-xl transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Submitting...</>
              ) : (
                <><CheckCircle2 className="w-5 h-5" /> Verify & Continue</>
              )}
            </button>
          </form>

          {/* Countdown */}
          <div className="mt-4 flex items-center justify-center gap-2">
            <Clock className="w-4 h-4 text-gray-400" />
            <span className={cn('text-sm font-medium', isExpired ? 'text-red-500' : 'text-gray-500')}>
              {isExpired ? 'Code expired — task will fail' : `Expires in ${mins}:${String(secs).padStart(2, '0')}`}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────
export default function TasksPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [sessions, setSessions] = useState<any[]>([]);
  const [filter, setFilter] = useState('');
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [userInputValue, setUserInputValue] = useState('');
  const [isSendingInput, setIsSendingInput] = useState(false);

  const screenshotContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest screenshot when new ones are added
  useEffect(() => {
    if (screenshotContainerRef.current) {
      screenshotContainerRef.current.scrollTo({
        left: screenshotContainerRef.current.scrollWidth,
        behavior: 'smooth',
      });
    }
  }, [selectedTask?.screenshots?.length]);

  // Global OTP popup state — tracks the task waiting for user input
  const [otpTask, setOtpTask] = useState<any>(null);
  const otpTaskRef = useRef<any>(null); // for stable access in interval
  const otpAlertedIds = useRef<Set<string>>(new Set()); // prevent repeated alerts

  const fetchTasks = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: '1', page_size: '50' });
      if (filter) params.set('status', filter);
      const data = await api.get<any>(`/tasks?${params}`);
      const fetchedTasks = data.tasks || [];
      setTasks(fetchedTasks);

      // ── Check ALL tasks for waiting_user_input ─────────────────
      const waitingTask = fetchedTasks.find(
        (t: any) => t.status === 'waiting_user_input' && t.user_input_required
      );

      if (waitingTask) {
        // Only trigger popup if not already shown for this task
        if (!otpAlertedIds.current.has(waitingTask.id)) {
          otpAlertedIds.current.add(waitingTask.id);
          setOtpTask(waitingTask);
          otpTaskRef.current = waitingTask;

          // Browser notification (if permission granted)
          if (Notification.permission === 'granted') {
            new Notification('🔐 OTP Required!', {
              body: `LinkedIn sent a verification code. Please enter it to continue your task.`,
              icon: '/favicon.ico',
            });
          } else if (Notification.permission !== 'denied') {
            Notification.requestPermission();
          }

          // Toast alert
          toast('🔔 OTP Required! Check your email.', {
            duration: 8000,
            style: { background: '#f59e0b', color: '#fff', fontWeight: 'bold' },
          });
        } else {
          // Update the task data in case it changed
          setOtpTask((prev: any) => prev?.id === waitingTask.id ? waitingTask : prev);
        }
      } else {
        // Task is no longer waiting — close popup if open
        if (otpTaskRef.current) {
          const prevTask = fetchedTasks.find((t: any) => t.id === otpTaskRef.current?.id);
          if (prevTask && prevTask.status !== 'waiting_user_input') {
            setOtpTask(null);
            otpTaskRef.current = null;
          }
        }
      }

      // Update selectedTask if open
      if (selectedTask) {
        const updated = fetchedTasks.find((t: any) => t.id === selectedTask.id);
        if (updated) setSelectedTask(updated);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [filter, selectedTask?.id]);

  const fetchSessions = async () => {
    try {
      const data = await api.get<any>('/sessions');
      setSessions(data.sessions?.filter((s: any) => s.status === 'active') || []);
    } catch {}
  };

  // Initial load
  useEffect(() => {
    fetchTasks();
    fetchSessions();
  }, [filter]);

  // ── Global polling — every 3 seconds, ALL tasks ──────────────
  useEffect(() => {
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const createTask = async () => {
    if (!prompt.trim()) return;
    setCreating(true);
    try {
      const body: any = { prompt: prompt.trim() };
      if (sessionId) body.session_id = sessionId;
      const createdTask = await api.post<any>('/tasks', body);
      toast.success('Task created & queued!');
      setPrompt('');
      setSessionId('');
      fetchTasks();
    } catch (err: any) {
      toast.error(err.message || 'Failed to create task');
    } finally {
      setCreating(false);
    }
  };

  const cancelTask = async (taskId: string) => {
    try {
      await api.post(`/tasks/${taskId}/cancel`);
      toast.success('Task cancelled');
      fetchTasks();
    } catch (err: any) {
      toast.error(err.message || 'Failed to cancel');
    }
  };

  const deleteTask = async (taskId: string) => {
    if (!confirm('Delete this task?')) return;
    try {
      await api.delete(`/tasks/${taskId}`);
      toast.success('Task deleted');
      fetchTasks();
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete');
    }
  };

  // ── OTP submit handler — used by BOTH global popup and modal ──
  const handleSubmitOTP = async (taskId: string, code: string) => {
    try {
      const data = await api.post<any>(`/tasks/${taskId}/submit-input`, { value: code });
      setTasks(prev => prev.map(t => t.id === data.id ? data : t));
      if (selectedTask?.id === taskId) setSelectedTask(data);
      toast.success('✅ Verification code submitted!');
      // Close global popup & remove from alerted set so it can re-trigger if needed
      setOtpTask(null);
      otpTaskRef.current = null;
      otpAlertedIds.current.delete(taskId);
    } catch (err: any) {
      toast.error(err.message || 'Failed to submit code');
      throw err;
    }
  };

  // Legacy modal submit (keeps backward compat)
  const handleSendUserInput = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInputValue.trim() || !selectedTask) return;
    setIsSendingInput(true);
    try {
      await handleSubmitOTP(selectedTask.id, userInputValue.trim());
      setUserInputValue('');
    } catch {
    } finally {
      setIsSendingInput(false);
    }
  };

  return (
    <>
      {/* ── Global OTP Verification Popup ──────────────────────── */}
      {otpTask && (
        <OTPVerificationPopup
          task={otpTask}
          onSubmit={handleSubmitOTP}
          onDismiss={() => {
            // Dismiss but keep in alerted set so it doesn't re-popup immediately
            setOtpTask(null);
            otpTaskRef.current = null;
          }}
        />
      )}

      <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">Tasks</h1>
          <p className="text-surface-500 mt-1">Create and manage automation tasks</p>
        </div>

        {/* ── Active OTP Alert Banner (when popup is dismissed) ── */}
        {tasks.some((t: any) => t.status === 'waiting_user_input') && !otpTask && (
          <div
            className="bg-amber-50 border-2 border-amber-400 rounded-xl p-4 flex items-center gap-3 cursor-pointer hover:bg-amber-100 transition-colors"
            onClick={() => {
              const t = tasks.find((t: any) => t.status === 'waiting_user_input');
              if (t) {
                otpAlertedIds.current.delete(t.id);
                setOtpTask(t);
                otpTaskRef.current = t;
              }
            }}
          >
            <div className="w-10 h-10 rounded-full bg-amber-500 flex items-center justify-center animate-pulse flex-shrink-0">
              <Mail className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1">
              <p className="font-bold text-amber-900">⚠️ OTP Verification Pending!</p>
              <p className="text-sm text-amber-700">A task is waiting for your email verification code. Click to enter it.</p>
            </div>
            <span className="px-3 py-1.5 bg-amber-500 text-white rounded-lg text-sm font-bold">Enter OTP →</span>
          </div>
        )}

        {/* Create Task Form */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">New Task</h2>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe your task in natural language... e.g., 'Go to amazon.com, search for wireless headphones, and extract the top 5 product names and prices'"
                className="input-field min-h-[80px] resize-y"
                rows={3}
              />
            </div>
            <div className="flex flex-col gap-2 sm:w-48">
              <select
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                className="input-field text-sm"
              >
                <option value="">New Session</option>
                {sessions.map((s: any) => (
                  <option key={s.id} value={s.id}>
                    {s.name || s.id.slice(0, 8)}
                  </option>
                ))}
              </select>
              <button
                onClick={createTask}
                disabled={creating || !prompt.trim()}
                className="btn-primary"
              >
                {creating ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Send className="w-4 h-4 mr-2" />
                )}
                Execute
              </button>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          {['', 'running', 'completed', 'failed', 'pending', 'waiting_user_input', 'waiting_captcha'].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={cn(
                'px-3 py-1.5 rounded-full text-xs font-medium transition-colors',
                filter === s
                  ? 'bg-primary-600 text-white'
                  : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
              )}
            >
              {s || 'All'}
            </button>
          ))}
          <button
            onClick={fetchTasks}
            className="ml-auto p-2 rounded-lg hover:bg-surface-100 text-surface-500"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Task List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="card text-center py-12">
            <Bot className="w-12 h-12 mx-auto mb-3 text-surface-300" />
            <p className="text-surface-500">No tasks found</p>
            <p className="text-surface-400 text-sm mt-1">Create your first task above</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task: any) => (
              <div
                key={task.id}
                className={cn(
                  'card hover:shadow-md transition-shadow',
                  task.status === 'waiting_user_input' && 'border-2 border-amber-400 bg-amber-50/30'
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(task.status))}>
                        {task.status}
                      </span>
                      {task.status === 'waiting_user_input' && (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-amber-500 text-white animate-pulse">
                          <Mail className="w-3 h-3" /> OTP Required
                        </span>
                      )}
                      {task.status === 'waiting_captcha' && (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-purple-500 text-white">
                          <ShieldAlert className="w-3 h-3" /> Solving CAPTCHA...
                        </span>
                      )}
                      {task.captcha_detected && (
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                          CAPTCHA {task.captcha_solved ? '✓' : '!'}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-surface-900 whitespace-pre-wrap line-clamp-2">{task.prompt}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-surface-500">
                      <span>Step {task.current_step}/{task.total_steps}</span>
                      {task.duration_ms && <span>{formatDuration(task.duration_ms)}</span>}
                      {task.retry_count > 0 && (
                        <span className="text-amber-600">{task.retry_count} retries</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    {task.status === 'waiting_user_input' && (
                      <button
                        onClick={() => {
                          otpAlertedIds.current.delete(task.id);
                          setOtpTask(task);
                          otpTaskRef.current = task;
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-xs font-bold transition-colors"
                      >
                        <KeyRound className="w-3.5 h-3.5" />
                        Enter OTP
                      </button>
                    )}
                    <button
                      onClick={() => setSelectedTask(task)}
                      className="p-2 rounded-lg hover:bg-surface-100 text-surface-600 hover:text-primary-600"
                      title="View Details"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => cancelTask(task.id)}
                      disabled={!['running', 'pending', 'retrying', 'waiting_user_input'].includes(task.status)}
                      className="p-2 rounded-lg hover:bg-surface-100 text-surface-400 disabled:opacity-30"
                      title="Cancel"
                    >
                      <AlertTriangle className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => deleteTask(task.id)}
                      className="p-2 rounded-lg hover:bg-red-50 text-surface-400 hover:text-red-600"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Task Details Modal */}
        {selectedTask && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={() => setSelectedTask(null)}
          >
            <div
              className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto mx-4 animate-slide-up"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between border-b pb-4 mb-4">
                <div>
                  <span className={cn('px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase', getStatusColor(selectedTask.status))}>
                    {selectedTask.status}
                  </span>
                  <h3 className="text-xl font-bold text-surface-900 mt-2">Task Details</h3>
                  <p className="text-xs text-surface-400 mt-1">ID: {selectedTask.id}</p>
                </div>
                <button onClick={() => setSelectedTask(null)} className="p-1.5 rounded-lg hover:bg-surface-100 text-surface-500">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* ── OTP section inside modal (in case global popup dismissed) ── */}
              {selectedTask.status === 'waiting_user_input' && (
                <div className="bg-amber-50 border-2 border-amber-300 rounded-xl p-4 mb-6 space-y-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-full bg-amber-500 flex items-center justify-center flex-shrink-0 animate-pulse">
                      <Mail className="w-4.5 h-4.5 text-white" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-amber-900">Email Verification Required (OTP)</h4>
                      <p className="text-xs text-amber-700 mt-0.5">
                        {selectedTask.user_input_prompt || 'Enter the verification code sent to your email.'}
                      </p>
                    </div>
                  </div>
                  <form onSubmit={handleSendUserInput} className="flex gap-2">
                    <input
                      type="text"
                      value={userInputValue}
                      onChange={e => setUserInputValue(e.target.value)}
                      placeholder="Enter verification code..."
                      className="flex-grow px-3 py-2 border-2 border-amber-300 focus:border-amber-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-200 text-sm font-mono font-bold tracking-widest"
                      required
                    />
                    <button
                      type="submit"
                      disabled={isSendingInput}
                      className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg font-bold text-sm transition-colors disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {isSendingInput && <Loader2 className="w-4 h-4 animate-spin" />}
                      Submit
                    </button>
                  </form>
                </div>
              )}

              {/* ── CAPTCHA solving status ── */}
              {selectedTask.status === 'waiting_captcha' && (
                <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 mb-6 flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-purple-500 flex items-center justify-center flex-shrink-0">
                    <ShieldAlert className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-purple-900">Solving CAPTCHA Automatically</h4>
                    <p className="text-xs text-purple-700 mt-0.5">CapSolver is working on the security challenge. Please wait...</p>
                  </div>
                  <Loader2 className="w-5 h-5 text-purple-500 animate-spin ml-auto" />
                </div>
              )}

              {/* Top Section: Full Width Screenshots */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-surface-700 uppercase tracking-wider mb-2">
                  Screenshots ({selectedTask.screenshots?.length || 0})
                </h4>
                {selectedTask.screenshots && selectedTask.screenshots.length > 0 ? (
                  <div className="border rounded-lg overflow-hidden bg-surface-900 p-3 relative">
                    <div 
                      ref={screenshotContainerRef}
                      className="flex gap-4 overflow-x-auto scrollbar-thin scrollbar-thumb-surface-700 snap-x scroll-smooth"
                    >
                      {selectedTask.screenshots.map((s_b64: string, idx: number) => (
                        <div key={idx} className="snap-center flex-shrink-0 w-full md:w-[75%] aspect-video relative bg-black flex items-center justify-center border border-surface-800 rounded-lg overflow-hidden">
                          <img
                            src={`data:image/png;base64,${s_b64}`}
                            alt={`Step ${idx + 1}`}
                            className="max-h-[450px] max-w-full object-contain"
                          />
                          <span className="absolute bottom-2 left-2 px-2 py-0.5 bg-black/70 text-white rounded text-[10px] font-bold">
                            Screenshot {idx + 1}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="border border-dashed rounded-lg p-8 text-center text-surface-400 bg-surface-50 text-xs">
                    No screenshots captured yet.
                    <p className="mt-1 text-[10px] text-surface-400">Screenshots are captured automatically every 3 seconds as the agent runs.</p>
                  </div>
                )}
              </div>

              {/* Bottom Columns: Prompt/Steps on the left, Plan/Extracted Data on the right */}
              <div className="grid md:grid-cols-2 gap-6">
                {/* Left Column: Prompt & Executed Steps */}
                <div className="space-y-6">
                  <div>
                    <h4 className="text-sm font-semibold text-surface-700 uppercase tracking-wider mb-2">Prompt</h4>
                    <div className="bg-surface-50 p-4 rounded-lg border border-surface-200 text-sm text-surface-800 whitespace-pre-wrap">
                      {selectedTask.prompt}
                    </div>
                  </div>

                  {selectedTask.steps_executed && selectedTask.steps_executed.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-surface-700 uppercase tracking-wider mb-2">
                        Executed Steps ({selectedTask.steps_executed.length})
                      </h4>
                      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                        {selectedTask.steps_executed.map((step: any, idx: number) => (
                          <div key={idx} className={cn('p-2.5 rounded-lg border text-xs', step.success ? 'bg-green-50/50 border-green-200' : 'bg-red-50/50 border-red-200')}>
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-surface-900 uppercase">Step {idx + 1}: {step.action}</span>
                              <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-bold uppercase', step.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700')}>
                                {step.success ? 'SUCCESS' : 'FAILED'}
                              </span>
                            </div>
                            {step.description && <p className="text-surface-600 mt-1">{step.description}</p>}
                            {step.error && <p className="text-red-600 font-mono mt-1 text-[11px] bg-red-50 p-1.5 rounded">{step.error}</p>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Right Column: Generated Plan & Extracted Data */}
                <div className="space-y-6">
                  {selectedTask.plan && selectedTask.plan.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-surface-700 uppercase tracking-wider mb-2">
                        Generated Plan ({selectedTask.plan.length} steps)
                      </h4>
                      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                        {selectedTask.plan.map((step: any, idx: number) => (
                          <div key={idx} className="flex gap-3 p-2.5 rounded-lg bg-surface-50 border border-surface-200 text-xs">
                            <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-700 font-bold flex items-center justify-center flex-shrink-0">
                              {idx + 1}
                            </span>
                            <div>
                              <span className="font-semibold text-surface-900 uppercase">{step.action}</span>
                              {step.selector && <code className="block mt-1 text-purple-600 bg-purple-50 px-1 py-0.5 rounded">{step.selector}</code>}
                              {step.description && <p className="text-surface-500 mt-0.5">{step.description}</p>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedTask.extracted_data && (
                    <div>
                      <h4 className="text-sm font-semibold text-surface-700 uppercase tracking-wider mb-2">Extracted Data</h4>
                      <pre className="bg-surface-900 text-green-400 p-4 rounded-lg text-xs font-mono overflow-x-auto border max-h-[250px]">
                        {JSON.stringify(selectedTask.extracted_data, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
