'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChefHat, LayoutDashboard, PlusCircle, BookOpen, History, Sun, Moon } from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    const savedTheme = localStorage.getItem('dishgenie-theme') || 'light';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(nextTheme);
    localStorage.setItem('dishgenie-theme', nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  };

  const navItems = [
    { label: 'Dashboard', href: '/', icon: LayoutDashboard },
    { label: 'Create Request', href: '/create', icon: PlusCircle },
    { label: 'Recipe Discovery', href: '/recipes', icon: BookOpen },
    { label: 'Request History', href: '/history', icon: History },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <ChefHat className="text-accent" />
        <span>DishGenie</span>
      </div>

      <nav style={{ flex: 1 }}>
        <div className="nav-section-title">Navigation</div>
        <div className="nav-links">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      <div style={{ paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
        <button
          onClick={toggleTheme}
          className="btn-primary"
          style={{
            width: '100%',
            justifyContent: 'center',
            background: 'var(--surface)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
          }}
        >
          {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          <span>{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
        </button>
      </div>
    </aside>
  );
}
