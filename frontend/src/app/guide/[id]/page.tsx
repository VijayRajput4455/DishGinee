'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { ChefHat, Clock, Flame, Utensils, CheckCircle, Lightbulb } from 'lucide-react';

export default function CookingGuidePage() {
  const params = useParams();
  const requestId = params.id;

  const [guideData, setGuideData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  useEffect(() => {
    fetchGuideDetails();
  }, [requestId]);

  const fetchGuideDetails = async () => {
    try {
      const res = await fetch(`/api/v1/requests/${requestId}`);
      const json = await res.json();
      if (json.success && json.data?.output?.cooking_guide) {
        setGuideData(json.data.output.cooking_guide);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const toggleStep = (stepNum: number) => {
    if (completedSteps.includes(stepNum)) {
      setCompletedSteps(completedSteps.filter((s) => s !== stepNum));
    } else {
      setCompletedSteps([...completedSteps, stepNum]);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '4rem' }}>Generating Stage 2 Cooking Guide via Ollama...</div>;
  }

  if (!guideData) {
    return <div style={{ textAlign: 'center', padding: '4rem' }}>No cooking guide found.</div>;
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {/* Header Banner */}
      <div className="card" style={{ marginBottom: '2rem', background: 'linear-gradient(135deg, var(--surface) 0%, var(--surface-hover) 100%)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span className="badge badge-completed" style={{ marginBottom: '0.5rem' }}>Stage 2 Complete Guide</span>
            <h1 style={{ fontSize: '2rem', fontWeight: 800 }}>{guideData.title}</h1>
          </div>
          <div style={{ display: 'flex', gap: '1.5rem', textAlign: 'center' }}>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>SERVINGS</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-primary)' }}>{guideData.servings || 2}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>PREP TIME</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-primary)' }}>{guideData.prep_time || '15 mins'}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>COOK TIME</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-primary)' }}>{guideData.cook_time || '20 mins'}</div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
        {/* Left Column: Ingredients & Macros */}
        <div>
          {/* Ingredients Card */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Utensils size={20} className="text-accent" /> Required Ingredients
            </h2>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {guideData.ingredients?.map((ing: any, i: number) => (
                <li key={i} style={{ fontSize: '0.9rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-primary)' }}></span>
                  {typeof ing === 'object' ? `${ing.quantity} ${ing.item}` : ing}
                </li>
              ))}
            </ul>
          </div>

          {/* Macros Card */}
          {guideData.macros && (
            <div className="card" style={{ marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Flame size={20} className="text-accent" /> Nutritional Macros
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div style={{ background: 'var(--input-bg)', padding: '0.75rem', borderRadius: 10, textAlign: 'center' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>CALORIES</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>{guideData.macros.calories} kcal</div>
                </div>
                <div style={{ background: 'var(--input-bg)', padding: '0.75rem', borderRadius: 10, textAlign: 'center' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>PROTEIN</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>{guideData.macros.protein_g}g</div>
                </div>
                <div style={{ background: 'var(--input-bg)', padding: '0.75rem', borderRadius: 10, textAlign: 'center' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>CARBS</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>{guideData.macros.carbs_g}g</div>
                </div>
                <div style={{ background: 'var(--input-bg)', padding: '0.75rem', borderRadius: 10, textAlign: 'center' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>FATS</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>{guideData.macros.fats_g}g</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Step-by-Step Instructions */}
        <div>
          <div className="card">
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: 8 }}>
              <ChefHat size={22} className="text-accent" /> Step-by-Step Cooking Steps
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {guideData.steps?.map((step: any) => {
                const isDone = completedSteps.includes(step.step_number);
                return (
                  <div
                    key={step.step_number}
                    onClick={() => toggleStep(step.step_number)}
                    style={{
                      padding: '1.25rem',
                      borderRadius: 14,
                      border: `1px solid ${isDone ? 'var(--success)' : 'var(--border)'}`,
                      background: isDone ? 'rgba(76, 175, 80, 0.08)' : 'var(--input-bg)',
                      cursor: 'pointer',
                      transition: 'var(--transition)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <span style={{ fontWeight: 800, color: 'var(--accent-primary)' }}>Step {step.step_number}</span>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Clock size={14} /> {step.duration_minutes} mins
                      </span>
                    </div>

                    <p style={{ fontSize: '0.95rem', lineHeight: 1.5, marginBottom: '0.75rem' }}>
                      {step.instruction}
                    </p>

                    {step.equipment && step.equipment.length > 0 && (
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {step.equipment.map((eq: string, idx: number) => (
                          <span key={idx} className="ingredient-chip" style={{ background: 'var(--surface)', fontSize: '0.75rem' }}>
                            🛠️ {eq}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
