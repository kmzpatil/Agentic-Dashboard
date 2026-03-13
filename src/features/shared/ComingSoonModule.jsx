import React from 'react';
import { Stethoscope } from 'lucide-react';

export default function ComingSoonModule({ title }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-neutral-600 gap-2">
      <Stethoscope className="opacity-40" size={26} />
      <h2 className="text-xl font-bold text-neutral-400">{title}</h2>
      <p className="text-sm">Not part of this build scope.</p>
    </div>
  );
}
