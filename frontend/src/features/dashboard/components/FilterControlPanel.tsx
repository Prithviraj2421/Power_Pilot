import React from 'react';
import { Filter, Calendar, Layers } from 'lucide-react';
import { Chip } from '../../../components/ui/Chip';

export interface FilterControlPanelProps {
  globalFilters: string[];
  timeDimensions: string[];
}

export const FilterControlPanel: React.FC<FilterControlPanelProps> = ({
  globalFilters,
  timeDimensions,
}) => {
  if (globalFilters.length === 0 && timeDimensions.length === 0) return null;

  return (
    <div className="bg-card/70 backdrop-blur-md border border-border rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider">
          <Filter className="w-4 h-4 text-primary" />
          <span>Global Filters:</span>
        </div>
        {globalFilters.map((filter, idx) => (
          <Chip key={idx} label={filter} icon={<Layers className="w-3 h-3 text-primary" />} />
        ))}
      </div>

      {timeDimensions.length > 0 && (
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-warning" />
          <span className="text-xs text-gray-300 font-medium">
            Time Grain: {timeDimensions.join(' / ')}
          </span>
        </div>
      )}
    </div>
  );
};
