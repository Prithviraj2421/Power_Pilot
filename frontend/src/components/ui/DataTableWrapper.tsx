import React from 'react';
import { cn } from '../../utils/cn';

export interface ColumnDef<T> {
  header: string;
  accessorKey: keyof T | ((row: T) => React.ReactNode);
  className?: string;
}

export interface DataTableWrapperProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  keyExtractor: (item: T, index: number) => string | number;
  emptyMessage?: string;
  className?: string;
}

export function DataTableWrapper<T>({
  data,
  columns,
  keyExtractor,
  emptyMessage = 'No records found.',
  className,
}: DataTableWrapperProps<T>) {
  return (
    <div className={cn('w-full overflow-x-auto border border-border rounded-xl bg-card', className)}>
      <table className="w-full text-left text-sm border-collapse">
        <thead className="bg-surface/80 text-xs uppercase tracking-wider text-gray-400 border-b border-border">
          <tr>
            {columns.map((col, idx) => (
              <th key={idx} className={cn('px-4 py-3 font-semibold', col.className)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border text-gray-200">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-500">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rIdx) => (
              <tr key={keyExtractor(row, rIdx)} className="hover:bg-surface/50 transition-colors">
                {columns.map((col, cIdx) => {
                  const content =
                    typeof col.accessorKey === 'function'
                      ? col.accessorKey(row)
                      : (row[col.accessorKey] as React.ReactNode);
                  return (
                    <td key={cIdx} className={cn('px-4 py-3 whitespace-nowrap', col.className)}>
                      {content}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
