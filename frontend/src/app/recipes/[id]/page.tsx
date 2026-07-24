'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Clock, ChefHat, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';

export default function RecipeDiscoveryPage() {
  const params = useParams();
  const router = useRouter();
  const requestId = params.id;

  const [requestData, setRequestData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selecting, setSelecting] = useState(false);

  useEffect(() => {
    fetchRequestDetails();
  }, [requestId]);

  const fetchRequestDetails = async () => {
    try {
      const res = await fetch(`/api/v1/requests/${requestId}`);
      const json = await res.json();
      if (json.success) {
        setRequestData(json.data);
      }
    } catch (err) {
      console.error('Error fetching request details:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectRecipe = async (recipeTitle: string) => {
    setSelecting(true);
    try {
      const res = await fetch(`/api/v1/requests/${requestId}/select-recipe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipe_title: recipeTitle }),
      });
      const json = await res.json();
      if (json.success) {
        router.push(`/guide/${requestId}`);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSelecting(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '4rem' }}>Loading Ollama recipe options...</div>;
  }

  const recipes = requestData?.output?.ingredients || [];

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>Ollama Stage 1 Recipe Candidates 📜</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Select your favorite recipe from the 5 AI-generated options for Request #{requestId} (Cuisine: {requestData?.cuisine || 'Any'})
        </p>
      </div>

      <div className="recipes-grid">
        {recipes.map((recipe: any, idx: number) => (
          <div key={idx} className="recipe-card">
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                <span className="badge badge-completed">Option #{idx + 1}</span>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Clock size={14} /> {recipe.prep_time || '20 mins'}
                </span>
              </div>
              <h3 className="recipe-title">{recipe.title}</h3>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: 1.4 }}>
                {recipe.description}
              </p>

              {/* Matched Ingredients */}
              {recipe.matched_ingredients && (
                <div style={{ marginBottom: '0.75rem' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 4 }}>MATCHED INGREDIENTS:</div>
                  {recipe.matched_ingredients.map((ing: string, i: number) => (
                    <span key={i} className="ingredient-chip">{ing}</span>
                  ))}
                </div>
              )}

              {/* Missing Ingredients */}
              {recipe.missing_ingredients && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 4 }}>EXTRA STAPLES NEEDED:</div>
                  {recipe.missing_ingredients.map((ing: string, i: number) => (
                    <span key={i} className="ingredient-chip" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#DC2626' }}>{ing}</span>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={() => handleSelectRecipe(recipe.title)}
              className="btn-primary"
              disabled={selecting}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              <Sparkles size={16} />
              <span>{selecting ? 'Generating Guide...' : 'Select Recipe & Get Guide'}</span>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
