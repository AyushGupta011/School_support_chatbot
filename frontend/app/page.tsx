'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
import Markdown from 'markdown-to-jsx';
import {
  Send,
  LogOut,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  GraduationCap,
  MessageSquare,
  Plus,
  Trash2,
  Clock,
  BookOpen,
  Calendar,
  CreditCard,
  UserCheck,
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  ExternalLink,
  Info,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  Eye,
  EyeOff,
  Search,
  FileText,
  HelpCircle,
  X,
  Bell,
  Home as HomeIcon,
  Bookmark,
  Settings,
  BarChart3,
  MapPin,
  Paperclip,
  ArrowRight,
  MoreHorizontal
} from 'lucide-react';

interface ChatMessageItem {
  id?: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  runId?: string;
  created_at?: string;
}

interface ChatSessionItem {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

interface StudentProfile {
  enrollment_no: string;
  name: string;
  department: string;
  semester: number;
}

// Demo student credentials for the login screen
const DEMO_STUDENTS = [
  {
    id: 'demo_student_1',
    name: 'Liam Sterling',
    dept: 'Computer Science & Engineering',
    deptCode: 'CSE',
    sem: 2,
    avatar: 'S',
    tag: '82% Attendance • Clear Dues'
  },
  {
    id: 'demo_student_2',
    name: 'Maya Chen',
    dept: 'Electrical Engineering',
    deptCode: 'EE',
    sem: 2,
    avatar: 'M',
    tag: '71% Attendance • Due Pending'
  },
  {
    id: 'demo_student_3',
    name: 'Jordan Vance',
    dept: 'Mechanical Engineering',
    deptCode: 'ME',
    sem: 1,
    avatar: 'J',
    tag: '94% Attendance • Honors'
  }
];

// Regulations handbook clauses
const HANDBOOK_TOPICS = [
  {
    code: 'REG §4.2',
    title: 'Minimum Attendance Requirement',
    badge: 'Mandatory Policy',
    summary: 'A minimum of 75% attendance is required in each course to be eligible for end-semester examinations. Condonation up to 10% may be granted by the Academic Dean only on verified medical grounds submitted within 7 working days.',
    query: 'What are the rules and penalties if my attendance drops below 75%?'
  },
  {
    code: 'FIN §6.1',
    title: 'Tuition Fee Deadlines & Penalties',
    badge: 'Financial Regulation',
    summary: 'Semester fees must be cleared by the 10th of the academic commencement month. A late fine of $50/week applies thereafter. Students with unresolved dues exceeding 30 days are blocked from examination registration.',
    query: 'What are my pending tuition dues, fee breakdown, and late penalty deadlines?'
  },
  {
    code: 'ACAD §8.3',
    title: 'Examination & Assessment Weightage',
    badge: 'Grading Framework',
    summary: 'Course evaluation comprises: Continuous Internal Assessment (20%), Mid-Semester Examination (30%), and Comprehensive Final Examination (50%). Passing grade requires an aggregate minimum of 40% with at least 35% in finals.',
    query: 'How are my internal marks, midterms, and final exam grades weighted?'
  },
  {
    code: 'FAC §2.4',
    title: 'Faculty Consultation & Cabins',
    badge: 'Campus Services',
    summary: 'Faculty members hold mandatory office hours twice weekly. Appointments can be scheduled through the student portal or by visiting their designated department cabins during designated consultation windows.',
    query: 'Who are my course professors and what are their cabin numbers and office hours?'
  }
];

export default function Home() {
  const [apiUrl, setApiUrl] = useState<string>('http://localhost:8000');
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState('demo_student_1');
  const [password, setPassword] = useState('demopass');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [student, setStudent] = useState<StudentProfile | null>(null);

  // View state
  const [activeTab, setActiveTab] = useState<'home' | 'chat' | 'records' | 'handbook'>('home');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [handbookDrawerOpen, setHandbookDrawerOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  // Chat and Sessions State
  const [sessions, setSessions] = useState<ChatSessionItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<Record<string, number>>({});
  const [copiedId, setCopiedId] = useState<string | number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const detected = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      setApiUrl(detected);
    }
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
      setToken(storedToken);
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchStudentProfile();
      fetchSessions();
    }
  }, [token]);

  useEffect(() => {
    if (activeTab === 'chat') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading, activeTab]);

  const fetchStudentProfile = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/me/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setStudent(data);
      } else if (res.status === 401) {
        handleLogout();
      }
    } catch (e) {
      console.error('Failed to fetch profile', e);
    }
  };

  const fetchSessions = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/chat/sessions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data: ChatSessionItem[] = await res.json();
        setSessions(data);
      }
    } catch (e) {
      console.error('Failed to fetch sessions', e);
    }
  };

  const selectSession = async (sessionId: string) => {
    setCurrentSessionId(sessionId);
    setActiveTab('chat');
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/chat/sessions/${sessionId}/messages`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const msgs = await res.json();
        setMessages(msgs.map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          runId: m.run_id,
          created_at: m.created_at
        })));
      }
    } catch (e) {
      console.error('Failed to load session messages', e);
    }
  };

  const handleCreateNewSession = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/chat/sessions`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title: 'New Conversation' })
      });
      if (res.ok) {
        const newSess = await res.json();
        setSessions(prev => [newSess, ...prev]);
        setCurrentSessionId(newSess.id);
        setMessages([]);
        setActiveTab('chat');
        if (inputRef.current) inputRef.current.focus();
      }
    } catch (e) {
      console.error('Failed to create session', e);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/chat/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.id !== sessionId));
        if (currentSessionId === sessionId) {
          const remaining = sessions.filter(s => s.id !== sessionId);
          if (remaining.length > 0) {
            selectSession(remaining[0].id);
          } else {
            setCurrentSessionId(null);
            setMessages([]);
            setActiveTab('home');
          }
        }
      }
    } catch (err) {
      console.error('Failed to delete session', err);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', username.trim());
      formData.append('password', password);

      const res = await fetch(`${apiUrl}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Invalid enrollment number or password');
      }

      const data = await res.json();
      localStorage.setItem('access_token', data.access_token);
      setToken(data.access_token);
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify credentials or check backend.');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setToken(null);
    setStudent(null);
    setSessions([]);
    setCurrentSessionId(null);
    setMessages([]);
    setActiveTab('home');
    setProfileMenuOpen(false);
  };

  const handleFeedback = async (runId: string, score: number) => {
    if (!token || !runId) return;
    try {
      await fetch(`${apiUrl}/chat/feedback`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ run_id: runId, score })
      });
      setFeedbackSubmitted(prev => ({ ...prev, [runId]: score }));
    } catch (e) {
      console.error('Feedback failed', e);
    }
  };

  const copyMessage = (text: string, id: string | number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const sendMessage = async (overrideMsg?: string) => {
    const textToSend = overrideMsg || input;
    if (!textToSend.trim() || !token || loading) return;

    setInput('');
    setActiveTab('chat');
    setMessages(prev => [...prev, { role: 'user', content: textToSend }]);
    setLoading(true);

    try {
      const res = await fetch(`${apiUrl}/chat/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: textToSend,
          session_id: currentSessionId
        })
      });

      if (!res.ok) {
        if (res.status === 401) handleLogout();
        throw new Error(`Request failed with status ${res.status}`);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      let currentRunId = '';

      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.session_id && !currentSessionId) {
                  setCurrentSessionId(data.session_id);
                  fetchSessions();
                }
                if (data.run_id) currentRunId = data.run_id;
                if (data.token) {
                  assistantContent += data.token;
                  setMessages(prev => {
                    const next = [...prev];
                    next[next.length - 1] = {
                      role: 'assistant',
                      content: assistantContent,
                      runId: currentRunId
                    };
                    return next;
                  });
                }
                if (data.final_answer) {
                  assistantContent = data.final_answer;
                  setMessages(prev => {
                    const next = [...prev];
                    next[next.length - 1] = {
                      role: 'assistant',
                      content: assistantContent,
                      runId: currentRunId
                    };
                    return next;
                  });
                }
                if (data.error) {
                  assistantContent += `\n\n> ⚠️ **Notice:** ${data.error}`;
                  setMessages(prev => {
                    const next = [...prev];
                    next[next.length - 1] = {
                      role: 'assistant',
                      content: assistantContent,
                      runId: currentRunId
                    };
                    return next;
                  });
                }
              } catch (_) {}
            }
          }
        }
      }
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Unable to connect to the campus assistant service. Please verify backend status.'
        }
      ]);
    } finally {
      setLoading(false);
      fetchSessions();
    }
  };

  // Six Topic Cards matching the reference layout
  const topicCards = [
    {
      title: 'Check Attendance',
      desc: 'View subject-wise attendance and overall percentage',
      icon: BarChart3,
      query: 'What is my current attendance percentage across all courses?'
    },
    {
      title: 'Fee Details',
      desc: 'Check pending dues, payment status and last dates',
      icon: CreditCard,
      query: 'What are my pending fee dues and when is the payment deadline?'
    },
    {
      title: "Today's Timetable",
      desc: 'See your class schedule, subjects, rooms and faculty',
      icon: Calendar,
      query: 'What is my course schedule and timetable for today?'
    },
    {
      title: 'Exam Schedule',
      desc: 'View upcoming exams, dates and detailed timetable',
      icon: FileText,
      query: 'When are my upcoming exams and what is the timetable?'
    },
    {
      title: 'Find Classrooms',
      desc: 'Get building information, room locations and campus map',
      icon: MapPin,
      query: 'Where are my enrolled classrooms and faculty cabins located?'
    },
    {
      title: 'University Regulations',
      desc: 'Ask about rules, leaves, grading, hostel policy and more',
      icon: BookOpen,
      query: 'What are the formal university rules for minimum 75% attendance and grading?'
    }
  ];

  // Fallback demo recent conversations if empty
  const defaultRecentThreads = [
    { id: 't1', title: 'My attendance', time: '2h ago' },
    { id: 't2', title: 'Fee payment last date', time: '5h ago' },
    { id: 't3', title: 'Exam schedule May 2026', time: '1d ago' },
    { id: 't4', title: 'Where is CSE block?', time: '2d ago' },
    { id: 't5', title: 'Hostel rules', time: '3d ago' },
    { id: 't6', title: 'Credit system explain', time: '5d ago' },
    { id: 't7', title: 'How to apply for leave?', time: '6d ago' },
  ];

  // ----------------------------------------------------
  // LOGIN SCREEN: Clean Light Institutional Aesthetic
  // ----------------------------------------------------
  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F8FAFC] p-4 font-sans text-slate-900">
        <div className="w-full max-w-md overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
          
          {/* Header */}
          <div className="border-b border-slate-100 p-8 text-center bg-white">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-slate-900 shadow-sm">
              <GraduationCap size={30} />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">Apex University</h1>
            <p className="mt-1 text-xs text-slate-500 font-medium">Campus Copilot & Student Portal</p>
          </div>

          <form onSubmit={handleLogin} className="p-8 space-y-4">
            {error && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-600">
                {error}
              </div>
            )}

            {/* Demo Student Selectors */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Select Demo Student
                </span>
                <span className="text-[10px] text-slate-400">1-click test login</span>
              </div>
              <div className="grid grid-cols-3 gap-2 mb-4">
                {DEMO_STUDENTS.map(s => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => {
                      setUsername(s.id);
                      setPassword('demopass');
                      setError('');
                    }}
                    className={`rounded-xl border p-2 text-left transition-all ${
                      username === s.id
                        ? 'border-slate-900 bg-slate-50 shadow-sm'
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <p className="text-xs font-bold text-slate-900">{s.name.split(' ')[0]}</p>
                    <p className="text-[10px] text-slate-500 font-mono">{s.deptCode} • Sem {s.sem}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold text-slate-700">
                Enrollment Number
              </label>
              <input
                type="text"
                placeholder="e.g. demo_student_1"
                value={username}
                onChange={e => setUsername(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-900 focus:bg-white focus:outline-none focus:ring-1 focus:ring-slate-900"
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold text-slate-700">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3.5 py-2.5 pr-10 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-900 focus:bg-white focus:outline-none focus:ring-1 focus:ring-slate-900"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="w-full rounded-xl bg-slate-900 py-3 text-sm font-semibold text-white shadow transition-colors hover:bg-slate-800"
            >
              Sign In to Portal
            </button>

            <p className="pt-2 text-center text-[11px] text-slate-400">
              Grounded in official ERP & student handbook records.
            </p>
          </form>
        </div>
      </div>
    );
  }

  // ----------------------------------------------------
  // MAIN APPLICATION: Matching the Exact Reference UI
  // ----------------------------------------------------
  return (
    <div className="flex h-screen bg-[#F8FAFC] font-sans text-slate-900 antialiased overflow-hidden">
      
      {/* ------------------------------------------------ */}
      {/* LEFT SIDEBAR                                    */}
      {/* ------------------------------------------------ */}
      <aside className={`flex flex-col border-r border-slate-200 bg-white transition-all duration-200 ${sidebarCollapsed ? 'w-16' : 'w-64'} shrink-0`}>
        
        {/* Logo / Brand Header */}
        <div className="flex h-16 items-center justify-between border-b border-slate-100 px-4">
          {!sidebarCollapsed && (
            <div className="flex items-center space-x-2.5 overflow-hidden">
              <GraduationCap size={24} className="text-slate-900 shrink-0" />
              <div>
                <h1 className="text-sm font-bold text-slate-900 leading-tight">Apex University</h1>
                <p className="text-[10px] text-slate-400 font-medium">Campus Copilot</p>
              </div>
            </div>
          )}

          {sidebarCollapsed && (
            <div className="mx-auto">
              <GraduationCap size={24} className="text-slate-900" />
            </div>
          )}

          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="rounded-md border border-slate-200 p-1 text-slate-400 hover:bg-slate-50 hover:text-slate-700 transition-colors"
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={handleCreateNewSession}
            className={`flex w-full items-center rounded-xl bg-slate-900 px-3.5 py-2.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-slate-800 ${
              sidebarCollapsed ? 'justify-center' : 'justify-between'
            }`}
          >
            <div className="flex items-center space-x-2">
              <Plus size={16} />
              {!sidebarCollapsed && <span>New Chat</span>}
            </div>
            {!sidebarCollapsed && (
              <span className="text-[10px] text-slate-400 font-mono">
                Ctrl + K
              </span>
            )}
          </button>
        </div>

        {/* Primary Navigation Links */}
        <nav className="px-3 space-y-1">
          <button
            onClick={() => {
              setActiveTab('home');
              setMessages([]);
            }}
            className={`flex w-full items-center rounded-xl px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === 'home'
                ? 'bg-slate-100 text-slate-900 font-semibold'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            } ${sidebarCollapsed ? 'justify-center' : 'space-x-3'}`}
            title="Home"
          >
            <HomeIcon size={16} className="text-slate-700 shrink-0" />
            {!sidebarCollapsed && <span>Home</span>}
          </button>

          <button
            onClick={() => sendMessage('Show my complete student records and enrolled courses.')}
            className={`flex w-full items-center rounded-xl px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors ${
              sidebarCollapsed ? 'justify-center' : 'space-x-3'
            }`}
            title="My Records"
          >
            <FileText size={16} className="text-slate-600 shrink-0" />
            {!sidebarCollapsed && <span>My Records</span>}
          </button>

          <button
            onClick={() => setHandbookDrawerOpen(true)}
            className={`flex w-full items-center rounded-xl px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors ${
              sidebarCollapsed ? 'justify-center' : 'justify-between'
            }`}
            title="Regulations Handbook"
          >
            <div className="flex items-center space-x-3">
              <BookOpen size={16} className="text-slate-600 shrink-0" />
              {!sidebarCollapsed && <span>Regulations Handbook</span>}
            </div>
            {!sidebarCollapsed && (
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-mono text-slate-500">
                v4.2
              </span>
            )}
          </button>

          <button
            onClick={() => sendMessage('What are the latest campus announcements and notices?')}
            className={`flex w-full items-center rounded-xl px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors ${
              sidebarCollapsed ? 'justify-center' : 'space-x-3'
            }`}
            title="Announcements"
          >
            <Bell size={16} className="text-slate-600 shrink-0" />
            {!sidebarCollapsed && <span>Announcements</span>}
          </button>

          <button
            onClick={() => sendMessage('Show my saved query notes or bookmarked information.')}
            className={`flex w-full items-center rounded-xl px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors ${
              sidebarCollapsed ? 'justify-center' : 'space-x-3'
            }`}
            title="Saved"
          >
            <Bookmark size={16} className="text-slate-600 shrink-0" />
            {!sidebarCollapsed && <span>Saved</span>}
          </button>

          <button
            onClick={() => setProfileMenuOpen(true)}
            className={`flex w-full items-center rounded-xl px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors ${
              sidebarCollapsed ? 'justify-center' : 'space-x-3'
            }`}
            title="Settings"
          >
            <Settings size={16} className="text-slate-600 shrink-0" />
            {!sidebarCollapsed && <span>Settings</span>}
          </button>
        </nav>

        {/* Recent Conversations List */}
        {!sidebarCollapsed && (
          <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
            <div className="flex items-center justify-between px-2 py-1 text-[11px] font-semibold text-slate-400">
              <span>Recent Conversations</span>
              <button
                onClick={() => {}}
                className="hover:text-slate-600 text-[10px]"
              >
                See all
              </button>
            </div>

            {sessions.length > 0 ? (
              sessions.map(s => {
                const isSelected = s.id === currentSessionId && activeTab === 'chat';
                return (
                  <div
                    key={s.id}
                    onClick={() => selectSession(s.id)}
                    className={`group flex cursor-pointer items-center justify-between rounded-lg px-2.5 py-2 text-xs transition-colors ${
                      isSelected
                        ? 'bg-slate-100 text-slate-900 font-medium'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5 overflow-hidden">
                      <MessageSquare size={14} className="text-slate-400 shrink-0" />
                      <span className="truncate">{s.title || 'Conversation'}</span>
                    </div>
                    <button
                      onClick={e => handleDeleteSession(s.id, e)}
                      className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition-opacity p-0.5"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                );
              })
            ) : (
              defaultRecentThreads.map(t => (
                <div
                  key={t.id}
                  onClick={() => sendMessage(`Query regarding: ${t.title}`)}
                  className="flex cursor-pointer items-center justify-between rounded-lg px-2.5 py-2 text-xs text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                >
                  <div className="flex items-center space-x-2.5 overflow-hidden">
                    <MessageSquare size={14} className="text-slate-400 shrink-0" />
                    <span className="truncate">{t.title}</span>
                  </div>
                  <span className="text-[10px] text-slate-400 shrink-0">{t.time}</span>
                </div>
              ))
            )}
          </div>
        )}

        {/* Bottom Student Profile Card */}
        <div className="border-t border-slate-100 p-3 bg-white mt-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5 overflow-hidden">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-xs font-bold text-slate-700 shrink-0">
                {student?.name ? student.name[0] : 'S'}
              </div>
              {!sidebarCollapsed && (
                <div className="overflow-hidden">
                  <p className="truncate text-xs font-bold text-slate-900">
                    {student?.name ? student.name.split(' ')[0] : 'Student'}
                  </p>
                  <p className="text-[10px] text-slate-400">View profile</p>
                </div>
              )}
            </div>

            {!sidebarCollapsed && (
              <div className="relative">
                <button
                  onClick={() => setProfileMenuOpen(!profileMenuOpen)}
                  className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
                >
                  <MoreHorizontal size={16} />
                </button>

                {profileMenuOpen && (
                  <div className="absolute bottom-10 right-0 w-44 rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg z-50">
                    <div className="px-3 py-2 border-b border-slate-100">
                      <p className="text-xs font-bold text-slate-900">{student?.name || 'Verified Student'}</p>
                      <p className="text-[10px] text-slate-400 font-mono">{student?.enrollment_no || 'STU'}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="flex w-full items-center space-x-2 rounded-lg px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50 transition-colors mt-1"
                    >
                      <LogOut size={14} />
                      <span>Sign Out</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

      </aside>

      {/* ------------------------------------------------ */}
      {/* CENTER WORKSPACE (Header, Main, and Input)       */}
      {/* ------------------------------------------------ */}
      <div className="flex flex-1 flex-col overflow-hidden bg-white">
        
        {/* Top Header Bar */}
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6">
          <div className="flex items-center space-x-2.5 text-xs text-slate-600">
            <GraduationCap size={16} className="text-slate-800" />
            <span className="font-bold text-slate-900">Apex Campus Core</span>
            <span className="text-slate-300">|</span>
            <span>ERP v4.1 • RAG Online</span>
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse shadow-sm" />
          </div>

          <div className="flex items-center space-x-3 text-xs">
            {/* Bell notification */}
            <button
              onClick={() => sendMessage('Show all current university notices.')}
              className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-50 hover:text-slate-800 transition-colors"
            >
              <Bell size={16} />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-rose-500" />
            </button>

            {/* Authenticated identity badge */}
            <div className="flex items-center space-x-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm">
              <ShieldCheck size={14} className="text-slate-800" />
              <span>Identity: Authenticated</span>
            </div>

            {/* Handbook drawer trigger */}
            <button
              onClick={() => setHandbookDrawerOpen(true)}
              className="flex items-center space-x-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
            >
              <BookOpen size={14} className="text-slate-800" />
              <span>Handbook</span>
            </button>
          </div>
        </header>

        {/* Main Viewport */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="mx-auto max-w-4xl space-y-6">

            {/* DASHBOARD VIEW (When on Home or Messages are empty) */}
            {activeTab === 'home' || messages.length === 0 ? (
              <div className="space-y-6">
                
                {/* Hero Banner Section */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
                  
                  {/* Left Column Text */}
                  <div className="md:col-span-7 space-y-3">
                    <p className="text-[11px] font-bold tracking-widest text-slate-400 uppercase">
                      Official Academic Copilot
                    </p>
                    <h2 className="text-3xl lg:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
                      Your campus,<br />one conversation away.
                    </h2>
                    <p className="text-xs lg:text-sm text-slate-500 leading-relaxed max-w-lg">
                      Get instant answers about your attendance, fees, timetable, exams, classrooms and university policies — directly from official records.
                    </p>
                  </div>

                  {/* Right Column Campus Photo */}
                  <div className="md:col-span-5">
                    <div className="relative overflow-hidden rounded-2xl border border-slate-200 shadow-sm">
                      <img
                        src="/campus_hero.jpg"
                        alt="Apex University Campus"
                        className="w-full h-44 object-cover hover:scale-105 transition-transform duration-500"
                        onError={(e: any) => {
                          // Graceful fallback to CSS gradient card if image not yet loaded
                          e.target.style.display = 'none';
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* 3 Metric Stat Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  
                  {/* Attendance Card with Circular Ring */}
                  <div
                    onClick={() => sendMessage('What is my attendance percentage across all courses?')}
                    className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300 hover:shadow transition-all cursor-pointer"
                  >
                    <div className="flex items-center space-x-3.5">
                      {/* Circular Gauge */}
                      <div className="relative flex h-12 w-12 items-center justify-center shrink-0">
                        <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 36 36">
                          <path
                            className="text-slate-100"
                            strokeWidth="3.5"
                            stroke="currentColor"
                            fill="none"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          />
                          <path
                            className="text-slate-900"
                            strokeDasharray="82, 100"
                            strokeWidth="3.5"
                            strokeLinecap="round"
                            stroke="currentColor"
                            fill="none"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          />
                        </svg>
                        <span className="absolute text-xs font-bold text-slate-900">82%</span>
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-900">Attendance (This Semester)</p>
                        <p className="text-[11px] text-slate-500">Above required threshold (75%)</p>
                      </div>
                    </div>
                    <ArrowRight size={14} className="text-slate-400 group-hover:text-slate-900 group-hover:translate-x-0.5 transition-all" />
                  </div>

                  {/* Fees & Dues Card */}
                  <div
                    onClick={() => sendMessage('What are my pending fee dues and when is the deadline?')}
                    className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300 hover:shadow transition-all cursor-pointer"
                  >
                    <div className="flex items-center space-x-3.5">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-700 shrink-0">
                        <CreditCard size={18} />
                      </div>
                      <div>
                        <p className="text-[11px] font-semibold text-slate-500">Fees & Dues</p>
                        <p className="text-base font-extrabold text-slate-900">₹ 12,500</p>
                        <p className="text-[10px] text-slate-400">Due for next semester</p>
                      </div>
                    </div>
                    <ArrowRight size={14} className="text-slate-400 group-hover:text-slate-900 group-hover:translate-x-0.5 transition-all" />
                  </div>

                  {/* Next Class Card */}
                  <div
                    onClick={() => sendMessage('What is my course schedule for today?')}
                    className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300 hover:shadow transition-all cursor-pointer"
                  >
                    <div className="flex items-center space-x-3.5">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-700 shrink-0">
                        <Calendar size={18} />
                      </div>
                      <div>
                        <p className="text-[11px] font-semibold text-slate-500">Next Class</p>
                        <p className="text-sm font-bold text-slate-900">Data Structures</p>
                        <p className="text-[10px] text-slate-400">Today, 11:30 AM • A-204</p>
                      </div>
                    </div>
                    <ArrowRight size={14} className="text-slate-400 group-hover:text-slate-900 group-hover:translate-x-0.5 transition-all" />
                  </div>

                </div>

                {/* "How can I help you today?" Section */}
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-bold text-slate-900">How can I help you today?</h3>
                      <p className="text-xs text-slate-500">Choose a topic or ask anything about your university.</p>
                    </div>
                    <button
                      onClick={() => setHandbookDrawerOpen(true)}
                      className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center space-x-1"
                    >
                      <span>View all topics</span>
                      <ArrowRight size={12} />
                    </button>
                  </div>

                  {/* 6 Grid Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
                    {topicCards.map((topic, idx) => {
                      const Icon = topic.icon;
                      return (
                        <div
                          key={idx}
                          onClick={() => sendMessage(topic.query)}
                          className="group flex items-start justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300 hover:shadow transition-all cursor-pointer"
                        >
                          <div className="flex items-start space-x-3">
                            <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl bg-slate-50 border border-slate-100 text-slate-700 shrink-0 group-hover:bg-slate-100 transition-colors">
                              <Icon size={18} />
                            </div>
                            <div>
                              <p className="text-xs font-bold text-slate-900 group-hover:text-slate-800">
                                {topic.title}
                              </p>
                              <p className="mt-0.5 text-[11px] text-slate-500 leading-relaxed">
                                {topic.desc}
                              </p>
                            </div>
                          </div>
                          <ChevronRight size={16} className="text-slate-400 group-hover:text-slate-900 shrink-0 mt-1 transition-colors" />
                        </div>
                      );
                    })}
                  </div>
                </div>

              </div>
            ) : (
              /* ACTIVE CONVERSATION STREAM */
              <div className="space-y-6">
                
                {/* Back to Home bar */}
                <div className="flex items-center justify-between border-b border-slate-100 pb-3 text-xs text-slate-500">
                  <button
                    onClick={() => {
                      setActiveTab('home');
                    }}
                    className="flex items-center space-x-1 text-slate-600 hover:text-slate-900 font-medium"
                  >
                    <ChevronLeft size={14} />
                    <span>Back to Campus Overview</span>
                  </button>
                  <span className="font-mono text-[11px]">
                    Verified ERP Session
                  </span>
                </div>

                {messages.map((msg, idx) => {
                  const isUser = msg.role === 'user';
                  return (
                    <div key={idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                      <div
                        className={`max-w-[85%] rounded-2xl px-5 py-3.5 ${
                          isUser
                            ? 'bg-slate-900 text-white shadow-sm'
                            : 'border border-slate-200 bg-white text-slate-900 shadow-sm'
                        }`}
                        style={{ color: isUser ? '#FFFFFF' : '#0F172A' }}
                      >
                        {/* Header for assistant message */}
                        {!isUser && (
                          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 mb-3 text-xs">
                            <div className="flex items-center space-x-2">
                              <div className="flex h-5 w-5 items-center justify-center rounded-md bg-slate-100 text-slate-800">
                                <GraduationCap size={13} />
                              </div>
                              <span className="font-bold text-slate-900 text-xs">Apex Academic Copilot</span>
                              <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-mono text-emerald-700 border border-emerald-200">
                                Verified Record
                              </span>
                            </div>
                            <button
                              onClick={() => copyMessage(msg.content, msg.id || idx)}
                              className="text-slate-400 hover:text-slate-700 transition-colors"
                              title="Copy response"
                            >
                              {copiedId === (msg.id || idx) ? (
                                <span className="text-[10px] text-emerald-600 font-medium flex items-center space-x-1">
                                  <Check size={11} /> <span>Copied</span>
                                </span>
                              ) : (
                                <Copy size={13} />
                              )}
                            </button>
                          </div>
                        )}

                        {/* Markdown Content */}
                        <div
                          className={`markdown-body ${isUser ? 'user-markdown text-white [&_*]:!text-white' : ''}`}
                          style={{ color: isUser ? '#FFFFFF' : '#0F172A' }}
                        >
                          <Markdown
                            options={{
                              overrides: {
                                a: {
                                  component: ({ href, children }: any) => (
                                    <a
                                      href={href}
                                      target="_blank"
                                      rel="noreferrer"
                                      className={`inline-flex items-center hover:underline font-medium ${
                                        isUser ? 'text-sky-300' : 'text-blue-600'
                                      }`}
                                    >
                                      {children} <ExternalLink size={11} className="ml-1" />
                                    </a>
                                  )
                                }
                              }
                            }}
                          >
                            {msg.content}
                          </Markdown>
                        </div>

                        {/* Feedback Bar */}
                        {!isUser && msg.runId && (
                          <div className="mt-3.5 flex items-center justify-between border-t border-slate-100 pt-2.5 text-[11px] text-slate-400">
                            <span className="font-mono text-[10px]">
                              Scoped to {student?.enrollment_no || 'STU'}
                            </span>

                            <div className="flex items-center space-x-2">
                              {feedbackSubmitted[msg.runId] !== undefined ? (
                                <span className="text-emerald-600 font-medium text-[11px] flex items-center space-x-1">
                                  <Check size={11} /> <span>Feedback recorded</span>
                                </span>
                              ) : (
                                <div className="flex items-center space-x-1">
                                  <button
                                    onClick={() => handleFeedback(msg.runId!, 1)}
                                    className="rounded p-1 hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors"
                                    title="Helpful"
                                  >
                                    <ThumbsUp size={13} />
                                  </button>
                                  <button
                                    onClick={() => handleFeedback(msg.runId!, 0)}
                                    className="rounded p-1 hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors"
                                    title="Not accurate"
                                  >
                                    <ThumbsDown size={13} />
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                      </div>
                    </div>
                  );
                })}

                {loading && (
                  <div className="flex justify-start">
                    <div className="flex items-center space-x-2.5 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600 shadow-sm">
                      <Loader2 size={16} className="animate-spin text-slate-900" />
                      <span>Retrieving verified records from campus database...</span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}

          </div>
        </main>

        {/* ------------------------------------------------ */}
        {/* INPUT DOCK (Matching Reference Pill Container)   */}
        {/* ------------------------------------------------ */}
        <footer className="border-t border-slate-200 bg-white p-4">
          <div className="mx-auto max-w-4xl space-y-2">
            
            <form
              onSubmit={e => {
                e.preventDefault();
                sendMessage();
              }}
              className="flex items-center rounded-2xl border border-slate-200 bg-white px-3.5 py-2 shadow-sm focus-within:border-slate-400 focus-within:ring-1 focus-within:ring-slate-400 transition-all"
            >
              <button
                type="button"
                className="text-slate-400 hover:text-slate-600 p-1.5 transition-colors"
                title="Attach document or note"
              >
                <Paperclip size={18} />
              </button>

              <input
                ref={inputRef}
                type="text"
                placeholder="Ask about attendance, fees, classes, exams, or campus policies..."
                value={input}
                onChange={e => setInput(e.target.value)}
                disabled={loading}
                className="flex-1 bg-transparent px-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none"
              />

              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-white transition-opacity hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed shadow-sm shrink-0"
              >
                {loading ? <Loader2 size={14} className="animate-spin" /> : <Send size={13} className="ml-0.5" />}
              </button>
            </form>

            <div className="flex items-center justify-between px-2 text-[10px] text-slate-400">
              <span className="flex items-center space-x-1">
                <ShieldCheck size={11} className="text-slate-500" />
                <span>Responses are grounded in official university records (ERP + Handbook + RAG).</span>
              </span>
              <span className="hidden sm:inline font-mono">
                Press Enter to send • Shift + Enter for new line
              </span>
            </div>

          </div>
        </footer>

      </div>

      {/* ------------------------------------------------ */}
      {/* RIGHT SIDEBAR (Matching Reference Layout)        */}
      {/* ------------------------------------------------ */}
      <aside className="hidden xl:flex w-72 flex-col border-l border-slate-200 bg-white p-5 space-y-6 overflow-y-auto">
        
        {/* Date & Semester Card */}
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div>
            <p className="text-xs font-bold text-slate-900">Mon, 26 Oct 2026</p>
            <p className="text-[11px] text-slate-500">2nd Semester</p>
          </div>
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
            <Calendar size={18} />
          </div>
        </div>

        {/* Today's Classes Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900">Today's Classes</h4>
            <button
              onClick={() => sendMessage('Show my full schedule of classes for today.')}
              className="text-[11px] text-slate-500 hover:text-slate-900"
            >
              View all
            </button>
          </div>

          <div className="space-y-3 relative pl-2 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-[1.5px] before:bg-slate-200">
            
            {/* Class 1 */}
            <div className="flex items-start space-x-3 relative">
              <span className="h-2.5 w-2.5 rounded-full bg-slate-300 ring-4 ring-white mt-1 shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400 font-mono">09:00 AM - 10:00 AM</p>
                <p className="text-xs font-bold text-slate-900">DBMS</p>
                <p className="text-[10px] text-slate-500">A-201 • Dr. Sharma</p>
              </div>
            </div>

            {/* Class 2 (Active highlighted) */}
            <div className="flex items-start space-x-3 relative">
              <span className="h-2.5 w-2.5 rounded-full bg-slate-900 ring-4 ring-white mt-1 shrink-0" />
              <div>
                <p className="text-[10px] text-slate-900 font-bold font-mono">11:30 AM - 12:30 PM</p>
                <p className="text-xs font-extrabold text-slate-900">Data Structures</p>
                <p className="text-[10px] text-slate-500">A-204 • Prof. Singh</p>
              </div>
            </div>

            {/* Class 3 */}
            <div className="flex items-start space-x-3 relative">
              <span className="h-2.5 w-2.5 rounded-full bg-slate-300 ring-4 ring-white mt-1 shrink-0" />
              <div>
                <p className="text-[10px] text-slate-400 font-mono">02:00 PM - 03:00 PM</p>
                <p className="text-xs font-bold text-slate-900">Web Technologies</p>
                <p className="text-[10px] text-slate-500">B-101 • Dr. Verma</p>
              </div>
            </div>

          </div>
        </div>

        {/* Important Dates Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900">Important Dates</h4>
            <button
              onClick={() => sendMessage('What are the important upcoming dates and exam deadlines?')}
              className="text-[11px] text-slate-500 hover:text-slate-900"
            >
              View all
            </button>
          </div>

          <div className="space-y-3 relative pl-2 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-[1.5px] before:bg-slate-200">
            
            <div className="flex items-start space-x-3 relative">
              <span className="h-2.5 w-2.5 rounded-full bg-slate-900 ring-4 ring-white mt-1 shrink-0" />
              <div>
                <p className="text-xs font-bold text-slate-900">Nov 05, 2026</p>
                <p className="text-[10px] text-slate-500">Mid Sem Marks Release</p>
              </div>
            </div>

            <div className="flex items-start space-x-3 relative">
              <span className="h-2.5 w-2.5 rounded-full bg-slate-900 ring-4 ring-white mt-1 shrink-0" />
              <div>
                <p className="text-xs font-bold text-slate-900">Nov 15, 2026</p>
                <p className="text-[10px] text-slate-500">Fee Payment Last Date</p>
              </div>
            </div>

            <div className="flex items-start space-x-3 relative">
              <span className="h-2.5 w-2.5 rounded-full bg-slate-900 ring-4 ring-white mt-1 shrink-0" />
              <div>
                <p className="text-xs font-bold text-slate-900">Dec 10, 2026</p>
                <p className="text-[10px] text-slate-500">End Semester Exams Start</p>
              </div>
            </div>

          </div>
        </div>

        {/* Quick Links Section */}
        <div className="space-y-2 pt-2 border-t border-slate-100">
          <h4 className="text-xs font-bold text-slate-900 mb-2">Quick Links</h4>
          <div className="space-y-1 text-xs">
            
            <button
              onClick={() => sendMessage('Show the official academic calendar for this term.')}
              className="flex w-full items-center justify-between py-1.5 text-slate-600 hover:text-slate-900 transition-colors"
            >
              <div className="flex items-center space-x-2">
                <Calendar size={14} className="text-slate-500" />
                <span>Academic Calendar</span>
              </div>
              <ArrowRight size={12} className="text-slate-400" />
            </button>

            <button
              onClick={() => sendMessage('How can I register for upcoming semester examinations?')}
              className="flex w-full items-center justify-between py-1.5 text-slate-600 hover:text-slate-900 transition-colors"
            >
              <div className="flex items-center space-x-2">
                <FileText size={14} className="text-slate-500" />
                <span>Exam Portal</span>
              </div>
              <ArrowRight size={12} className="text-slate-400" />
            </button>

            <button
              onClick={() => sendMessage('What is the procedure and portal link for fee payment?')}
              className="flex w-full items-center justify-between py-1.5 text-slate-600 hover:text-slate-900 transition-colors"
            >
              <div className="flex items-center space-x-2">
                <CreditCard size={14} className="text-slate-500" />
                <span>Fee Payment</span>
              </div>
              <ArrowRight size={12} className="text-slate-400" />
            </button>

            <button
              onClick={() => setHandbookDrawerOpen(true)}
              className="flex w-full items-center justify-between py-1.5 text-slate-600 hover:text-slate-900 transition-colors"
            >
              <div className="flex items-center space-x-2">
                <BookOpen size={14} className="text-slate-500" />
                <span>Student Handbook</span>
              </div>
              <ArrowRight size={12} className="text-slate-400" />
            </button>

            <button
              onClick={() => sendMessage('How do I submit a leave application or medical certificate?')}
              className="flex w-full items-center justify-between py-1.5 text-slate-600 hover:text-slate-900 transition-colors"
            >
              <div className="flex items-center space-x-2">
                <FileText size={14} className="text-slate-500" />
                <span>Leave Application</span>
              </div>
              <ArrowRight size={12} className="text-slate-400" />
            </button>

          </div>
        </div>

      </aside>

      {/* ------------------------------------------------ */}
      {/* HANDBOOK SLIDE-OVER DRAWER                       */}
      {/* ------------------------------------------------ */}
      {handbookDrawerOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div
            onClick={() => setHandbookDrawerOpen(false)}
            className="absolute inset-0 bg-black/40 backdrop-blur-xs transition-opacity"
          />

          <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
            <div className="w-screen max-w-md border-l border-slate-200 bg-white shadow-2xl flex flex-col">
              
              <div className="flex items-center justify-between border-b border-slate-100 p-5 bg-white">
                <div className="flex items-center space-x-2.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-800">
                    <BookOpen size={16} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Academic Regulations</h3>
                    <p className="text-[10px] text-slate-400 font-mono">Handbook Edition 2025–2026</p>
                  </div>
                </div>

                <button
                  onClick={() => setHandbookDrawerOpen(false)}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-800"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-5 space-y-4">
                <p className="text-xs text-slate-500 leading-relaxed">
                  These verified policy excerpts are stored in the RAG knowledge base. Click any article to query the assistant regarding your standing.
                </p>

                <div className="space-y-3 pt-2">
                  {HANDBOOK_TOPICS.map((item, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-2 hover:border-slate-300 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                          {item.code}
                        </span>
                        <span className="text-[10px] text-slate-400">{item.badge}</span>
                      </div>

                      <h4 className="text-xs font-bold text-slate-900">
                        {item.title}
                      </h4>

                      <p className="text-[11px] text-slate-600 leading-relaxed">
                        {item.summary}
                      </p>

                      <button
                        onClick={() => {
                          setHandbookDrawerOpen(false);
                          sendMessage(item.query);
                        }}
                        className="mt-2 flex items-center space-x-1.5 text-[11px] font-semibold text-slate-900 hover:underline"
                      >
                        <span>Query Assistant on this Policy</span>
                        <ArrowRight size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-t border-slate-100 p-4 text-[11px] text-slate-400 flex items-center justify-between bg-slate-50">
                <span>Apex Academic Senate</span>
                <span>Ref: APX-REG-2026</span>
              </div>

            </div>
          </div>
        </div>
      )}

    </div>
  );
}
