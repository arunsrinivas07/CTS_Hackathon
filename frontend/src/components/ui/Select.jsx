import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';

/**
 * Modern Custom Select Dropdown
 * Replaces native HTML select elements with a high-grade SaaS floating menu interface.
 */
export default function Select({
  label,
  value,
  onChange,
  options = [],
  placeholder = 'Select an option',
  className = '',
  disabled = false,
  size = 'md', // 'sm' | 'md' | 'lg'
  icon: PrefixIcon = null,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Normalize options to object format { value, label }
  const normalizedOptions = options.map((opt) => {
    if (typeof opt === 'object' && opt !== null) {
      return { value: opt.value, label: opt.label || opt.value, icon: opt.icon };
    }
    return { value: opt, label: String(opt) };
  });

  const selectedOption = normalizedOptions.find((opt) => String(opt.value) === String(value));

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (disabled) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setIsOpen((prev) => !prev);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const handleSelect = (val) => {
    if (disabled) return;
    onChange(val);
    setIsOpen(false);
  };

  // Size variations
  const sizeStyles = {
    sm: 'py-1.5 px-3 text-xs rounded-xl min-h-[36px]',
    md: label ? 'pt-5 pb-2 px-4 text-sm rounded-2xl min-h-[46px]' : 'py-2.5 px-4 text-sm rounded-2xl min-h-[42px]',
    lg: label ? 'pt-6 pb-2.5 px-4 text-base rounded-2xl min-h-[52px]' : 'py-3.5 px-4 text-base rounded-2xl min-h-[48px]',
  };

  return (
    <div ref={containerRef} className={`relative inline-block w-full text-left ${className}`}>
      {/* Trigger Button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        onKeyDown={handleKeyDown}
        className={`w-full flex items-center justify-between bg-white border border-stone-200 text-stone-900 font-medium transition-all duration-200 ease-in-out cursor-pointer outline-none focus:ring-2 focus:ring-[#7c2d3e]/20 focus:border-[#7c2d3e] hover:border-stone-300 ${isOpen ? 'border-[#7c2d3e] ring-2 ring-[#7c2d3e]/20 shadow-md' : 'shadow-sm'
          } ${disabled ? 'opacity-50 cursor-not-allowed bg-stone-50' : ''} ${sizeStyles[size]}`}
        style={{ borderRadius: '14px' }}
      >
        {/* Left Content (Label + Selected Value or Placeholder) */}
        <div className="flex items-center gap-2.5 overflow-hidden text-left w-full mr-2">
          {PrefixIcon && <PrefixIcon className="w-4 h-4 text-stone-400 shrink-0" />}

          <div className="flex flex-col truncate w-full">
            {label && (
              <span className="text-[11px] font-semibold text-[#a8765a] leading-none mb-0.5 tracking-tight">
                {label}
              </span>
            )}
            <span className={`truncate leading-tight ${selectedOption ? 'text-stone-900 font-medium' : 'text-stone-400 font-normal'}`}>
              {selectedOption ? selectedOption.label : placeholder}
            </span>
          </div>
        </div>

        {/* Right Animated Arrow */}
        <ChevronDown
          className={`w-4 h-4 shrink-0 text-stone-400 transition-transform duration-200 ease-out ${isOpen ? 'rotate-180 text-[#7c2d3e]' : ''
            }`}
        />
      </button>

      {/* Floating Card Options Dropdown */}
      {isOpen && (
        <div
          className="absolute left-0 right-0 z-50 mt-1.5 max-h-60 w-full overflow-auto bg-white/95 backdrop-blur-md border border-stone-200/90 shadow-[0_8px_30px_rgba(0,0,0,0.12)] p-1.5 space-y-0.5 outline-none animate-in fade-in zoom-in-95 duration-150"
          style={{ borderRadius: '16px' }}
        >
          {normalizedOptions.length === 0 ? (
            <div className="px-3.5 py-2.5 text-xs text-stone-400 text-center font-medium">
              No options available
            </div>
          ) : (
            normalizedOptions.map((opt) => {
              const isSelected = String(opt.value) === String(value);
              const OptIcon = opt.icon;

              return (
                <div
                  key={String(opt.value)}
                  onClick={() => handleSelect(opt.value)}
                  className={`px-3.5 py-2.5 text-sm font-medium rounded-xl transition-all duration-150 flex items-center justify-between cursor-pointer select-none ${isSelected
                      ? 'bg-[#7c2d3e]/10 text-[#7c2d3e] font-semibold'
                      : 'text-stone-700 hover:bg-stone-100/80 hover:text-stone-900'
                    }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    {OptIcon && <OptIcon className={`w-4 h-4 ${isSelected ? 'text-[#7c2d3e]' : 'text-stone-400'}`} />}
                    <span className="truncate">{opt.label}</span>
                  </div>

                  {isSelected && <Check className="w-4 h-4 text-[#7c2d3e] shrink-0 ml-2" />}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
