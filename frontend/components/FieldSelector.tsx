'use client';

import { useState } from 'react';

export interface FieldConfig {
  key: string;
  label: string;
  category?: string;
}

interface FieldSelectorProps {
  fields: FieldConfig[];
  visibleFields: Set<string>;
  onToggleField: (fieldKey: string) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
}

export default function FieldSelector({
  fields,
  visibleFields,
  onToggleField,
  onSelectAll,
  onDeselectAll,
}: FieldSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredFields = fields.filter((field) =>
    field.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
    field.key.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const categories = Array.from(new Set(fields.map((f) => f.category || 'Other')));
  const fieldsByCategory = categories.reduce((acc, category) => {
    acc[category] = filteredFields.filter((f) => (f.category || 'Other') === category);
    return acc;
  }, {} as Record<string, FieldConfig[]>);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
          />
        </svg>
        Fields ({visibleFields.size}/{fields.length})
        <svg
          className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-full z-20 mt-2 w-80 rounded-lg border border-gray-200 bg-white shadow-lg">
            <div className="p-4">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-900">Select Fields</h3>
                <div className="flex gap-2">
                  <button
                    onClick={onSelectAll}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    All
                  </button>
                  <button
                    onClick={onDeselectAll}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    None
                  </button>
                </div>
              </div>

              <input
                type="text"
                placeholder="Search fields..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="mb-4 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />

              <div className="max-h-96 space-y-4 overflow-y-auto">
                {categories.map((category) => {
                  const categoryFields = fieldsByCategory[category];
                  if (categoryFields.length === 0) return null;

                  return (
                    <div key={category}>
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {category}
                      </h4>
                      <div className="space-y-1">
                        {categoryFields.map((field) => (
                          <label
                            key={field.key}
                            className="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-gray-50 cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={visibleFields.has(field.key)}
                              onChange={() => onToggleField(field.key)}
                              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                            <span className="text-sm text-gray-700">{field.label}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

