'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { ChefHat, Camera, Mic, Type, Sparkles, ArrowRight, CheckCircle, Clock } from 'lucide-react';

export default function DashboardPage() {
  const [stats, setStats] = useState({
    totalRequests: 24,
    imageRequests: 14,
    voiceRequests: 6,
    completedGuides: 22,
  });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.85rem', fontWeight: 800 }}>Welcome to DishGenie AI 🍳</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            AI Kitchen Assistant powered by YOLO Vision, Whisper Voice, and Ollama Qwen 2.5
          </p>
        </div>
        <Link href="/create" className="btn-primary">
          <Sparkles size={18} />
          <span>New Recipe Request</span>
        </Link>
      </div>

      {/* Metrics Row */}
      <div className="metrics-grid">
        <div className="card metric-card">
          <div>
            <div className="metric-label">Total Requests</div>
            <div className="metric-val">{stats.totalRequests}</div>
          </div>
          <div className="metric-icon">
            <ChefHat size={24} />
          </div>
        </div>

        <div className="card metric-card">
          <div>
            <div className="metric-label">Image YOLO Scans</div>
            <div className="metric-val">{stats.imageRequests}</div>
          </div>
          <div className="metric-icon">
            <Camera size={24} />
          </div>
        </div>

        <div className="card metric-card">
          <div>
            <div className="metric-label">Voice Whisper Audios</div>
            <div className="metric-val">{stats.voiceRequests}</div>
          </div>
          <div className="metric-icon">
            <Mic size={24} />
          </div>
        </div>

        <div className="card metric-card">
          <div>
            <div className="metric-label">Completed Guides</div>
            <div className="metric-val">{stats.completedGuides}</div>
          </div>
          <div className="metric-icon">
            <CheckCircle size={24} />
          </div>
        </div>
      </div>

      {/* Quick Start Triggers */}
      <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem' }}>Instant Ingredient Input Methods</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
        <Link href="/create?type=image" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="metric-icon" style={{ marginBottom: '1rem' }}>
            <Camera size={26} />
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.35rem' }}>Upload Fridge Photo</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            YOLO object detection scans your refrigerator photo and locates ingredient bounding boxes automatically.
          </p>
        </Link>

        <Link href="/create?type=voice" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="metric-icon" style={{ marginBottom: '1rem' }}>
            <Mic size={26} />
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.35rem' }}>Record Voice Audio</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Speak ingredients aloud into your microphone; Whisper AI transcribes your audio into text.
          </p>
        </Link>

        <Link href="/create?type=text" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="metric-icon" style={{ marginBottom: '1rem' }}>
            <Type size={26} />
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.35rem' }}>Enter Text & Cuisine</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Type ingredient lists directly and choose target cuisines (Indian, Italian, Mexican, Asian).
          </p>
        </Link>
      </div>
    </div>
  );
}
