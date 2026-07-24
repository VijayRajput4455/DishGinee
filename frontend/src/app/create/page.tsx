'use client';

import React, { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Camera, Mic, Type, Sparkles, UploadCloud, Check } from 'lucide-react';

const CUISINE_OPTIONS = [
  { id: 'Indian', name: 'Indian 🇮🇳', color: '#FF9933' },
  { id: 'Italian', name: 'Italian 🇮🇹', color: '#008C45' },
  { id: 'Mexican', name: 'Mexican 🇲🇽', color: '#006847' },
  { id: 'Asian', name: 'Asian ⛩️', color: '#DE2910' },
  { id: 'Mediterranean', name: 'Mediterranean 🌴', color: '#0077B6' },
  { id: 'French', name: 'French 🇫🇷', color: '#002395' },
];

export default function CreateRequestPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialType = searchParams.get('type') || 'text';

  const [inputType, setInputType] = useState<'text' | 'image' | 'voice'>(initialType as any);
  const [selectedCuisine, setSelectedCuisine] = useState<string>('Indian');
  const [textInput, setTextInput] = useState('tomato, potato, butter, garlic, chicken');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      let endpoint = '/api/v1/requests/text';
      let body: any;

      if (inputType === 'text') {
        body = JSON.stringify({
          raw_text_input: textInput,
          cuisine: selectedCuisine,
        });
      } else if (inputType === 'image' && selectedFile) {
        endpoint = '/api/v1/requests/image';
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('cuisine', selectedCuisine);
        body = formData;
      } else if (inputType === 'voice' && selectedFile) {
        endpoint = '/api/v1/requests/voice';
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('cuisine', selectedCuisine);
        body = formData;
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: inputType === 'text' ? { 'Content-Type': 'application/json' } : undefined,
        body: body,
      });

      const json = await res.json();
      if (json.success && json.data?.id) {
        router.push(`/recipes/${json.data.id}`);
      } else {
        alert(json.detail || 'Error creating request');
      }
    } catch (err) {
      console.error(err);
      alert('Could not connect to FastAPI backend on http://localhost:8000');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 800, marginBottom: '0.25rem' }}>Create New Recipe Request</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
        Select your input method and target cuisine preference for Ollama AI recipe generation.
      </p>

      {/* Input Type Selector Tabs */}
      <div className="tab-container">
        <button
          className={`tab-btn ${inputType === 'text' ? 'active' : ''}`}
          onClick={() => setInputType('text')}
        >
          <Type size={16} style={{ display: 'inline', marginRight: 6 }} /> Text Input
        </button>
        <button
          className={`tab-btn ${inputType === 'image' ? 'active' : ''}`}
          onClick={() => setInputType('image')}
        >
          <Camera size={16} style={{ display: 'inline', marginRight: 6 }} /> Refrigerator Photo (YOLO)
        </button>
        <button
          className={`tab-btn ${inputType === 'voice' ? 'active' : ''}`}
          onClick={() => setInputType('voice')}
        >
          <Mic size={16} style={{ display: 'inline', marginRight: 6 }} /> Voice Recording (Whisper)
        </button>
      </div>

      <form onSubmit={handleSubmit} className="card">
        {/* Cuisine Selector */}
        <div style={{ marginBottom: '1.75rem' }}>
          <label style={{ display: 'block', fontWeight: 700, marginBottom: '0.5rem', fontSize: '0.95rem' }}>
            Choose Target Cuisine Preference:
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '0.75rem' }}>
            {CUISINE_OPTIONS.map((c) => (
              <div
                key={c.id}
                onClick={() => setSelectedCuisine(c.id)}
                style={{
                  padding: '0.75rem',
                  borderRadius: 12,
                  border: `2px solid ${selectedCuisine === c.id ? c.color : 'var(--border)'}`,
                  background: selectedCuisine === c.id ? 'var(--surface-hover)' : 'var(--input-bg)',
                  cursor: 'pointer',
                  textAlign: 'center',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  transition: 'var(--transition)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.35rem',
                }}
              >
                <span>{c.name}</span>
                {selectedCuisine === c.id && <Check size={16} style={{ color: c.color }} />}
              </div>
            ))}
          </div>
        </div>

        {/* Input Type Specific Controls */}
        {inputType === 'text' && (
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontWeight: 700, marginBottom: '0.5rem', fontSize: '0.95rem' }}>
              Ingredients List (Comma-separated):
            </label>
            <textarea
              className="input-field"
              rows={4}
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="e.g. tomatoes, potatoes, butter, garlic, spinach, chicken"
              required
            />
          </div>
        )}

        {(inputType === 'image' || inputType === 'voice') && (
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontWeight: 700, marginBottom: '0.5rem', fontSize: '0.95rem' }}>
              {inputType === 'image' ? 'Upload Refrigerator / Food Image:' : 'Upload Voice Audio Recording:'}
            </label>
            <div
              style={{
                border: '2px dashed var(--border)',
                borderRadius: 14,
                padding: '2.5rem',
                textAlign: 'center',
                background: 'var(--input-bg)',
                cursor: 'pointer',
              }}
            >
              <UploadCloud size={40} style={{ color: 'var(--accent-primary)', marginBottom: '0.5rem' }} />
              <p style={{ fontWeight: 600 }}>Click or drag file to upload</p>
              <input
                type="file"
                accept={inputType === 'image' ? 'image/*' : 'audio/*'}
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                style={{ marginTop: '0.75rem' }}
                required
              />
            </div>
          </div>
        )}

        <button type="submit" className="btn-primary" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
          <Sparkles size={18} />
          <span>{loading ? 'Processing via Ollama...' : 'Generate 5 Recipe Options'}</span>
        </button>
      </form>
    </div>
  );
}
