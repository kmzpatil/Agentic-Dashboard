import React, { useState, useEffect, useRef } from "react";
import { ChevronDown } from "lucide-react";

export default function FloatingDropdown({
  value,
  onChange,
  options,
  isGroups = false,
  minWidth = "240px",
  className = "",
  themeColor = "red",
  disabled = false,
  multiSelect = false,
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const getLabel = (val) => {
    if (multiSelect && Array.isArray(val)) {
      if (val.length === 0 || val.includes("All")) return "All";
      if (val.length === 1) return val[0];
      return `${val.length} selected`;
    }
    if (isGroups) {
      for (const group of options) {
        const opt = group.options.find((o) => o.value === val);
        if (opt) return opt.label;
      }
    } else {
      const opt = options.find(
        (o) => o.value === (Array.isArray(val) ? val[0] : val),
      );
      if (opt) return opt.label;
    }
    return Array.isArray(val) ? val[0] : val;
  };

  const handleSelect = (itemValue) => {
    if (!multiSelect) {
      onChange(itemValue);
      setOpen(false);
      return;
    }

    const current = Array.isArray(value) ? value : [value];
    let next;

    if (itemValue === "All") {
      next = ["All"];
    } else {
      const withoutAll = current.filter((v) => v !== "All");
      if (withoutAll.includes(itemValue)) {
        next = withoutAll.filter((v) => v !== itemValue);
        if (next.length === 0) next = ["All"];
      } else {
        next = [...withoutAll, itemValue];
      }
    }
    onChange(next);
  };

  const isOptionActive = (optValue) => {
    if (Array.isArray(value)) return value.includes(optValue);
    return value === optValue;
  };

  const themeClasses =
    themeColor === "red"
      ? "border-neutral-800 bg-[#0a0a0a]/80 text-neutral-200 hover:border-neutral-700 hover:bg-[#121212] focus:ring-red-500/30"
      : "border-red-500/30 bg-red-500/5 text-red-100 hover:bg-red-500/10 focus:ring-red-500/50";
  const dotColor = themeColor === "red" ? "bg-red-500" : "bg-red-400";

  const renderOption = (opt) => {
    const active = isOptionActive(opt.value);
    return (
      <button
        key={opt.value}
        onClick={() => handleSelect(opt.value)}
        className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all flex items-center justify-between group/item ${
          active
            ? "bg-red-500/10 text-red-500 font-bold"
            : "text-neutral-400 hover:bg-neutral-800 hover:text-white"
        }`}
      >
        <span className="flex items-center gap-2">
          {multiSelect && (
            <div
              className={`w-3.5 h-3.5 rounded border flex items-center justify-center transition-all ${
                active
                  ? "bg-red-500 border-red-500"
                  : "border-neutral-700 bg-neutral-900"
              }`}
            >
              {active && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
            </div>
          )}
          {opt.label}
        </span>
        {active && !multiSelect && (
          <div
            className={`w-1.5 h-1.5 rounded-full shadow-[0_0_8px_rgba(239,68,68,0.6)] ${dotColor}`}
          />
        )}
      </button>
    );
  };

  return (
    <div
      ref={ref}
      className={`relative ${className}`}
      style={minWidth ? { minWidth } : {}}
    >
      <button
        type="button"
        disabled={disabled}
        onClick={() => {
          if (!disabled) setOpen((o) => !o);
        }}
        className={`group w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl border backdrop-blur-md text-sm font-bold transition-all outline-none shadow-lg ${themeClasses} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        <span className="truncate">{getLabel(value)}</span>
        <ChevronDown
          size={16}
          className={`text-neutral-500 transition-transform duration-300 ${open ? "rotate-180 text-red-500" : "rotate-0"}`}
        />
      </button>
      {open && (
        <div
          className="absolute left-0 mt-2 w-full max-h-[400px] overflow-y-auto rounded-xl border border-neutral-800 bg-[#0d0d0d] backdrop-blur-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[100] animate-in fade-in slide-in-from-top-2 duration-200"
          style={{ scrollbarWidth: "thin", scrollbarColor: "#333 #0d0d0d" }}
        >
          {isGroups ? (
            options.map((group, gi) => (
              <div
                key={group.label}
                className={gi > 0 ? "border-t border-neutral-900" : ""}
              >
                <div className="px-4 py-2 text-[10px] font-black uppercase tracking-[0.2em] text-neutral-600 bg-neutral-900/50">
                  {group.label}
                </div>
                <div className="p-1">
                  {group.options.map((opt) => renderOption(opt))}
                </div>
              </div>
            ))
          ) : (
            <div className="p-1">{options.map((opt) => renderOption(opt))}</div>
          )}
        </div>
      )}
    </div>
  );
}
