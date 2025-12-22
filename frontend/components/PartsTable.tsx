'use client';

import { Part } from '@/lib/api';
import { FIELD_CONFIGS } from '@/lib/fieldConfig';

interface PartsTableProps {
  parts: Part[];
  visibleFields: Set<string>;
}

export default function PartsTable({ parts, visibleFields }: PartsTableProps) {
  // Get visible field configs in order
  const visibleFieldConfigs = FIELD_CONFIGS.filter((field) => visibleFields.has(field.key));

  // Add machines column if not already in visible fields
  const showMachines = true; // Always show machines column for parts view

  return (
    <div className="w-full">
      <div 
        className="overflow-x-scroll overflow-y-auto rounded-lg border border-gray-200" 
        style={{ 
          maxHeight: '600px',
          overflowX: 'scroll',
          overflowY: 'auto'
        }}
      >
        <table className="min-w-full divide-y divide-gray-200" style={{ minWidth: 'max-content' }}>
          <thead className="bg-gray-50 sticky top-0 z-10 shadow-sm">
            <tr>
              {visibleFieldConfigs.map((field) => (
                <th
                  key={field.key}
                  className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-700 whitespace-nowrap bg-gray-50"
                >
                  {field.label}
                </th>
              ))}
              {showMachines && (
                <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-700 whitespace-nowrap bg-gray-50">
                  Machines
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {parts.length === 0 ? (
              <tr>
                <td colSpan={visibleFieldConfigs.length + (showMachines ? 1 : 0)} className="px-6 py-4 text-center text-sm text-gray-500">
                  No parts found
                </td>
              </tr>
            ) : (
              parts.map((part, index) => (
                <tr key={part.id || index} className="hover:bg-gray-50">
                  {visibleFieldConfigs.map((field) => {
                    const value = (part as any)[field.key];
                    return (
                      <td
                        key={field.key}
                        className="px-3 py-2 text-sm text-gray-900 whitespace-nowrap"
                      >
                        {value !== null && value !== undefined ? String(value) : '-'}
                      </td>
                    );
                  })}
                  {showMachines && (
                    <td className="px-3 py-2 text-sm text-gray-900">
                      {part.machines && part.machines.length > 0 ? (
                        <div className="space-y-1">
                          {part.machines.map((machine, idx) => (
                            <div key={idx} className="text-xs">
                              <span className="font-medium">
                                {machine.equipment_alias || machine.equipment_id}
                              </span>
                              {machine.plant && (
                                <span className="text-gray-500 ml-1">({machine.plant})</span>
                              )}
                              {machine.quantity && machine.quantity !== 1 && (
                                <span className="text-gray-500 ml-1">x{machine.quantity}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

