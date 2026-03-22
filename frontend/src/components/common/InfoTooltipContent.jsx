import React from 'react';

export default function InfoTooltipContent({
  eyebrow = 'Context',
  summary = '',
  bullets = [],
  takeaway = '',
}) {
  return (
    <div className="space-y-2">
      <div className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
        {eyebrow}
      </div>
      {summary ? <p className="leading-relaxed">{summary}</p> : null}
      {Array.isArray(bullets) && bullets.length ? (
        <ul className="space-y-1.5">
          {bullets.map((item, index) => (
            <li key={`${item.label || 'item'}-${index}`}>
              <span className="font-semibold text-neutral-200">{item.label}</span>
              {' - '}
              {item.text}
            </li>
          ))}
        </ul>
      ) : null}
      {takeaway ? <p className="leading-relaxed text-neutral-500">{takeaway}</p> : null}
    </div>
  );
}
