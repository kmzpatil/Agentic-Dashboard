import { X } from 'lucide-react';
import Index from '../../userJourney/pages/Index';

/**
 * HighlightsModule
 *
 * Renders the userJourney 5-screen animated carousel as a full-screen
 * immersive overlay inside the main Frammer dashboard.
 *
 * The Index component uses `fixed inset-0` by design (full-screen experience).
 * A floating "back" button lets the user return to the previous dashboard view.
 */
export default function HighlightsModule({ onNavigate, routeState }) {
  const previousView = routeState?.from || 'mission-control';

  return (
    <>
      {/* Back button — floats above the full-screen Index carousel */}
      <button
        onClick={() => onNavigate({ view: previousView })}
        style={{
          position: 'fixed',
          top: '1rem',
          left: '1rem',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          gap: '0.375rem',
          padding: '0.5rem 0.75rem',
          borderRadius: '9999px',
          background: 'rgba(0,0,0,0.55)',
          border: '1px solid rgba(255,255,255,0.10)',
          backdropFilter: 'blur(10px)',
          WebkitBackdropFilter: 'blur(10px)',
          color: 'rgba(255,255,255,0.75)',
          fontSize: '0.75rem',
          fontWeight: 600,
          cursor: 'pointer',
          transition: 'color 150ms',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
        onMouseLeave={(e) => (e.currentTarget.style.color = 'rgba(255,255,255,0.75)')}
      >
        <X size={13} />
        <span>Dashboard</span>
      </button>

      {/* Full-screen journey carousel */}
      <Index />
    </>
  );
}
