import React, { useState } from 'react';
import { X, Sparkles, FlaskConical, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

const FORMULA_ATOMS = [
  'uploaded_count', 'created_count', 'published_count',
  'uploaded_duration', 'created_duration', 'published_duration',
];
const SINGLE_METRICS = [
  'publish_conversion_rate', 'creation_rate', 'processing_efficiency', 'waste_index',
];

const FORMULA_HINTS = [
  'created_count / uploaded_count * 100',
  'published_count / created_count * 100',
  'published_duration / created_duration * 100',
  'created_count - published_count',
];

const NL_HINTS = [
  'Percentage of created clips that get published',
  'Total hours of uploaded content per month',
  'Ratio of published posts to raw uploads',
  'Average efficiency of the creation pipeline',
];

export default function KPICreator({ onCreated, onClose, initialData }) {
  const [name, setName] = useState(initialData?.name || '');
  const [description, setDescription] = useState(initialData?.description || '');
  const [mode, setMode] = useState(initialData?.mode || 'formula');
  const [expression, setExpression] = useState(initialData?.expression || '');
  const [granularity, setGranularity] = useState(initialData?.time_granularity || 'month');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !expression.trim()) {
      setError('KPI name and expression are required.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const token = localStorage.getItem('frammer_auth_token');
      const response = await fetch(`${API_BASE}/kpi/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          mode,
          expression: expression.trim(),
          time_granularity: granularity,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to create KPI');
      }

      setSuccess(data);
      if (onCreated) onCreated(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleHint = (hint) => {
    setExpression(hint);
    setError(null);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-[2px] p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-3xl border border-neutral-700/80 bg-[#101216] p-8 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <button
          onClick={onClose}
          className="absolute right-6 top-6 text-neutral-400 hover:text-white transition-colors bg-black/45 border border-neutral-700 p-2 rounded-full"
        >
          <X size={20} />
        </button>

        <div className="mb-6 border-b border-neutral-800 pb-5">
          <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-neutral-400 mb-1">
            Custom KPI Builder
          </div>
          <h3 className="text-2xl font-black text-white tracking-tight">Create a New KPI</h3>
        </div>

        {success ? (
          <div className="text-center py-8 space-y-4">
            <CheckCircle2 size={48} className="mx-auto text-emerald-400" />
            <div>
              <div className="text-lg font-bold text-white">{success.name}</div>
              <div className="text-sm text-neutral-400 mt-1">KPI created successfully</div>
            </div>
            <div className="rounded-xl bg-[#141414] border border-neutral-800 p-4 text-left">
              <div className="text-xs font-bold uppercase tracking-wider text-neutral-500 mb-2">DSL Preview</div>
              <pre className="text-xs text-emerald-300 overflow-auto max-h-32">
                {JSON.stringify(success.dsl_json, null, 2)}
              </pre>
            </div>
            <button
              onClick={onClose}
              className="mt-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-6 py-2 transition-colors"
            >
              View on Dashboard
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Name */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-neutral-500 mb-2">
                KPI Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Publish Success Rate"
                className="w-full rounded-xl bg-[#111317] border border-neutral-700 text-white placeholder-neutral-600 px-4 py-3 text-sm focus:outline-none focus:border-neutral-500 transition-colors"
                disabled={loading}
              />
            </div>

            {/* Description (optional) */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-neutral-500 mb-2">
                Description <span className="text-neutral-400 normal-case font-normal">(optional)</span>
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of what this KPI measures"
                className="w-full rounded-xl bg-[#111317] border border-neutral-700 text-white placeholder-neutral-600 px-4 py-3 text-sm focus:outline-none focus:border-neutral-500 transition-colors"
                disabled={loading}
              />
            </div>

            {/* Mode Toggle */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-neutral-500 mb-2">
                Input Mode
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => { setMode('formula'); setExpression(''); setError(null); }}
                  className={`flex items-center gap-2 flex-1 rounded-xl px-4 py-3 text-sm font-semibold border transition-colors ${
                    mode === 'formula'
                      ? 'bg-sky-950/35 border-sky-700 text-sky-200'
                      : 'bg-[#111317] border-neutral-700 text-neutral-300 hover:text-white hover:border-neutral-500'
                  }`}
                  disabled={loading}
                >
                  <FlaskConical size={16} />
                  Formula
                </button>
                <button
                  type="button"
                  onClick={() => { setMode('natural_language'); setExpression(''); setError(null); }}
                  className={`flex items-center gap-2 flex-1 rounded-xl px-4 py-3 text-sm font-semibold border transition-colors ${
                    mode === 'natural_language'
                      ? 'bg-violet-950/35 border-violet-700 text-violet-200'
                      : 'bg-[#111317] border-neutral-700 text-neutral-300 hover:text-white hover:border-neutral-500'
                  }`}
                  disabled={loading}
                >
                  <Sparkles size={16} />
                  Natural Language
                </button>
              </div>
            </div>

            {/* Expression Input */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-neutral-500 mb-2">
                {mode === 'formula' ? 'Formula Expression *' : 'Describe Your KPI *'}
              </label>
              <textarea
                value={expression}
                onChange={(e) => { setExpression(e.target.value); setError(null); }}
                placeholder={
                  mode === 'formula'
                    ? 'e.g.  created_count / uploaded_count * 100'
                    : 'e.g.  Percentage of clips that get published after creation'
                }
                rows={3}
                className="w-full rounded-xl bg-[#111317] border border-neutral-700 text-white placeholder-neutral-600 px-4 py-3 text-sm font-mono focus:outline-none focus:border-neutral-500 transition-colors resize-none"
                disabled={loading}
              />

              {/* Quick Hints */}
              <div className="mt-2">
                <div className="text-[10px] text-neutral-400 mb-1 uppercase tracking-wider">Quick examples:</div>
                <div className="flex flex-wrap gap-2">
                  {(mode === 'formula' ? FORMULA_HINTS : NL_HINTS).map((hint) => (
                    <button
                      key={hint}
                      type="button"
                      onClick={() => handleHint(hint)}
                      className="text-[11px] rounded-lg bg-[#12151a] border border-neutral-700 text-neutral-300 hover:text-white hover:border-neutral-500 px-2 py-1 transition-colors font-mono"
                      disabled={loading}
                    >
                      {hint.length > 40 ? hint.slice(0, 40) + '…' : hint}
                    </button>
                  ))}
                </div>
              </div>

              {/* Formula atom reference */}
              {mode === 'formula' && (
                <div className="mt-3 rounded-xl bg-sky-950/10 border border-sky-900/30 p-3">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-sky-300 mb-1">
                    Available Metric Atoms
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {FORMULA_ATOMS.map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setExpression((prev) => prev ? `${prev} ${m}` : m)}
                        className="text-[11px] rounded bg-sky-950/30 border border-sky-900/40 text-sky-200 px-2 py-0.5 hover:bg-sky-900/30 font-mono transition-colors"
                        disabled={loading}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 mt-2 mb-1">
                    Pre-built Single Metrics
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {SINGLE_METRICS.map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setExpression(m)}
                        className="text-[11px] rounded bg-neutral-800/40 border border-neutral-700 text-neutral-200 px-2 py-0.5 hover:bg-neutral-700 font-mono transition-colors"
                        disabled={loading}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Granularity */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-neutral-500 mb-2">
                Time Granularity
              </label>
              <div className="flex gap-2">
                {['day', 'week', 'month'].map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setGranularity(g)}
                    className={`flex-1 rounded-xl px-4 py-2 text-sm font-semibold border capitalize transition-colors ${
                      granularity === g
                        ? 'bg-neutral-700/70 border-neutral-500 text-white'
                        : 'bg-[#111317] border-neutral-700 text-neutral-300 hover:text-white hover:border-neutral-500'
                    }`}
                    disabled={loading}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2 rounded-xl bg-red-950/30 border border-red-900/40 p-3">
                <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
                <p className="text-sm text-red-300">{error}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !name.trim() || !expression.trim()}
              className="w-full rounded-xl bg-white text-black font-bold py-3 text-sm uppercase tracking-wider hover:bg-neutral-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  {mode === 'natural_language' ? 'Analyzing with AI…' : 'Creating KPI…'}
                </>
              ) : (
                'Create KPI'
              )}
            </button>

            {mode === 'natural_language' && (
              <p className="text-center text-[11px] text-neutral-400">
                AI is used only during creation to interpret your description.
                Execution is fully deterministic.
              </p>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
