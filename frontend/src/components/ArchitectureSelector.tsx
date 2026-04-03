import { cn } from '@/lib/utils';
import type { Architecture } from '@/types';

interface ArchitectureSelectorProps {
  selected: Architecture;
  onSelect: (arch: Architecture) => void;
  disabled?: boolean;
}

const ARCH_INFO = {
  'linux/amd64': {
    label: 'X86_64',
    fullLabel: 'Intel / AMD (64位)',
    description: '传统云服务器、桌面应用',
    icon: '🖥️',
    badge: '最常用',
    gradient: 'from-slate-500 to-slate-600',
  },
  'linux/arm64': {
    label: 'ARM64',
    fullLabel: 'ARM (64位)',
    description: 'Apple Silicon、新一代云服务器',
    icon: '🍎',
    badge: '推荐',
    gradient: 'from-orange-500 to-orange-600',
  },
  'linux/arm/v7': {
    label: 'ARMv7',
    fullLabel: 'ARM (32位)',
    description: '树莓派、嵌入式设备',
    icon: '🛠️',
    badge: 'IoT',
    gradient: 'from-emerald-500 to-emerald-600',
  },
};

export function ArchitectureSelector({
  selected,
  onSelect,
  disabled = false,
}: ArchitectureSelectorProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {(Object.keys(ARCH_INFO) as Architecture[]).map((arch) => {
        const info = ARCH_INFO[arch];
        const isSelected = selected === arch;

        return (
          <button
            key={arch}
            type="button"
            onClick={() => onSelect(arch)}
            disabled={disabled}
            className={cn(
              'group relative rounded-xl border-2 p-4 text-left transition-all duration-200',
              isSelected
                ? 'border-primary bg-primary/5 shadow-lg shadow-primary/10'
                : 'border-border hover:border-primary/30 hover:bg-muted/30',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
          >
            {/* Badge */}
            {info.badge && (
              <span
                className={cn(
                  'absolute -top-2 -right-2 rounded-full px-2 py-0.5 text-xs font-medium text-white',
                  'bg-gradient-to-r ' + info.gradient
                )}
              >
                {info.badge}
              </span>
            )}

            {/* Icon */}
            <span className="mb-3 block text-3xl">{info.icon}</span>

            {/* Label */}
            <h3 className="mb-1 font-semibold text-foreground">
              {info.fullLabel}
            </h3>

            {/* Description */}
            <p className="text-sm text-muted-foreground">{info.description}</p>

            {/* Architecture code */}
            <p className="mt-2 font-mono text-xs text-muted-foreground/70">
              {arch}
            </p>

            {/* Selection indicator */}
            {isSelected && (
              <div className="absolute -bottom-px left-1/2 -translate-x-1/2">
                <div className="h-1 w-16 rounded-t-full bg-primary" />
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
