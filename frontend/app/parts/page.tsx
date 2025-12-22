'use client';

import { useState, useEffect, useCallback } from 'react';
import { getParts, getMachines, Part, Machine } from '@/lib/api';
import PartsTable from '@/components/PartsTable';
import PartsFilterBar from '@/components/PartsFilterBar';
import FieldSelector from '@/components/FieldSelector';
import { FIELD_CONFIGS, CRITICAL_DEFAULT_VISIBLE_FIELDS } from '@/lib/fieldConfig';

export default function PartsPage() {
  const [parts, setParts] = useState<Part[]>([]);
  const [filteredParts, setFilteredParts] = useState<Part[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [visibleFields, setVisibleFields] = useState<Set<string>>(CRITICAL_DEFAULT_VISIBLE_FIELDS);
  const [total, setTotal] = useState(0);

  // Fetch parts and machines on component mount
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      // Fetch parts and machines in parallel
      const [partsResponse, machinesResponse] = await Promise.all([
        getParts({ limit: 10000 }), // Get all parts
        getMachines()
      ]);

      if (partsResponse.success) {
        setParts(partsResponse.parts);
        setFilteredParts(partsResponse.parts);
        setTotal(partsResponse.total);
      } else {
        setError(partsResponse.error || 'Failed to fetch parts');
      }

      if (machinesResponse.success) {
        setMachines(machinesResponse.machines);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  // Handle filtering - memoized callback to prevent infinite loops
  const handleFilterChange = useCallback((filtered: Part[]) => {
    setFilteredParts(filtered);
  }, []);

  const handleToggleField = (fieldKey: string) => {
    setVisibleFields((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(fieldKey)) {
        newSet.delete(fieldKey);
      } else {
        newSet.add(fieldKey);
      }
      return newSet;
    });
  };

  const handleSelectAllFields = () => {
    setVisibleFields(new Set(FIELD_CONFIGS.map((f) => f.key)));
  };

  const handleDeselectAllFields = () => {
    setVisibleFields(new Set());
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-800">All Parts</h1>
        <p className="mt-1 text-sm text-gray-600">
          View and filter all parts stored in the database
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Loading State */}
        {loading && (
          <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 p-4">
            <p className="text-sm text-blue-800">Loading parts...</p>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 p-4">
            <p className="text-sm text-red-800">{error}</p>
            <button
              onClick={fetchData}
              className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
            >
              Retry
            </button>
          </div>
        )}

        {/* Parts Display */}
        {!loading && !error && (
          <div className="mb-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <h2 className="text-lg font-semibold text-gray-800">
                  Parts ({filteredParts.length} of {total})
                </h2>
                <FieldSelector
                  fields={FIELD_CONFIGS}
                  visibleFields={visibleFields}
                  onToggleField={handleToggleField}
                  onSelectAll={handleSelectAllFields}
                  onDeselectAll={handleDeselectAllFields}
                />
              </div>
            </div>

            <PartsFilterBar
              parts={parts}
              machines={machines}
              onFilterChange={handleFilterChange}
            />

            <div>
              {filteredParts.length > 0 ? (
                <PartsTable
                  parts={filteredParts}
                  visibleFields={visibleFields}
                />
              ) : (
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
                  <p className="text-gray-500">No parts match the current filters.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && parts.length === 0 && (
          <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <p className="text-gray-500">
              No parts found in the database.
            </p>
            <p className="mt-2 text-sm text-gray-400">
              Save parts from the Critical Separate Parts page to see them here.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

