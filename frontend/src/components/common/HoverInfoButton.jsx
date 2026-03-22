import React from 'react';

const ALIGNMENT_CLASS = {
  left: 'left-0',
  center: 'left-1/2 -translate-x-1/2',
  right: 'right-0',
};

function cx(...classes) {
  return classes.filter(Boolean).join(' ');
}

export default function HoverInfoButton({
  tooltip,
  ariaLabel = 'More information',
  align = 'right',
  widthClass = 'w-72',
  icon = 'i',
  stopEvent = true,
  containerClassName = '',
  buttonClassName = '',
  tooltipClassName = '',
  iconClassName = '',
}) {
  const alignmentClass = ALIGNMENT_CLASS[align] || ALIGNMENT_CLASS.right;
  const onClick = stopEvent
    ? (event) => {
        event.preventDefault();
        event.stopPropagation();
      }
    : undefined;

  return (
    <div className={cx('relative inline-flex group/info', containerClassName)}>
      <button
        type="button"
        onClick={onClick}
        aria-label={ariaLabel}
        className={cx(
          'inline-flex h-5 w-5 items-center justify-center rounded-full border border-neutral-700 bg-neutral-800 text-[10px] font-bold text-neutral-400 transition-colors duration-200 hover:border-amber-500/60 hover:text-amber-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/20 focus-visible:border-amber-500/60 focus-visible:text-amber-300',
          buttonClassName,
        )}
      >
        <span className={cx('leading-none', iconClassName)}>{icon}</span>
      </button>
      <div
        className={cx(
          'pointer-events-none absolute top-full z-50 mt-2 max-w-[calc(100vw-2rem)] rounded-xl border border-neutral-700 bg-[#0d0d0d] p-4 text-xs leading-relaxed text-neutral-400 opacity-0 shadow-2xl transition-all duration-200 translate-y-1 group-hover/info:translate-y-0 group-hover/info:opacity-100 group-focus-within/info:translate-y-0 group-focus-within/info:opacity-100',
          widthClass,
          alignmentClass,
          tooltipClassName,
        )}
      >
        {tooltip}
      </div>
    </div>
  );
}
