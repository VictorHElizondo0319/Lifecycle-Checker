
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { getParts, getMachines, Part, Machine, findReplacementsStream, updateParts } from '@/lib/api';
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
  const [isLookingForReplacements, setIsLookingForReplacements] = useState(false);
  const [progress, setProgress] = useState<string>('');
  const abortControllerRef = useRef<(() => void) | null>(null);

  const normalize = useCallback((value?: string) => value?.trim().toUpperCase() || '', []);

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

  const handleFindReplacements = async () => {
    // Filter to only obsolete parts
    const obsoleteParts = parts.filter((part) => {
      const status = part.ai_status || '';
      return status.includes('Obsolete') || status === '🔴 Obsolete';
    });

    if (obsoleteParts.length === 0) {
      setError('No obsolete parts found. Please filter parts with obsolete status to find replacements.');
      return;
    }

    setIsLookingForReplacements(true);
    setError('');
    setProgress('Starting replacement search...');

    try {
      // Convert parts to products format for the API
      // The backend only needs manufacturer and part_number, but we cast to Product[] for type compatibility
      const products = obsoleteParts.map((part) => ({
        manufacturer: part.part_manufacturer || '',
        part_number: part.manufacturer_part_number || part.part_number_ai_modified || '',
      })) as any; // Type assertion since backend only needs manufacturer and part_number

      const abort = findReplacementsStream(
        products,
        async (event) => {
          if (event.type === 'start') {
            setProgress(`Finding replacements for ${event.total_products} obsolete parts in ${event.total_chunks} chunks...`);
          } else if (event.type === 'chunk_start') {
            setProgress(`Processing chunk ${event.chunk}/${event.total_chunks} (${event.products_in_chunk} parts)...`);
          } else if (event.type === 'chunk_complete') {
            setProgress(`Completed chunk ${event.chunk}/${event.total_chunks}`);
          } else if (event.type === 'result' && event.data?.results) {
            // Merge replacement results into parts
            const replacementResults = event.data.results;
            setParts((prev) =>
              prev.map((part) => {
                const replacement = replacementResults.find(
                  (r: any) =>
                    normalize(r.obsolete_part_number || r.part_number || '') ===
                      normalize(part.manufacturer_part_number || part.part_number_ai_modified || '') &&
                    normalize(r.manufacturer || '') === normalize(part.part_manufacturer || '')
                );
                if (replacement) {
                  return {
                    ...part,
                    recommended_replacement: replacement.recommended_replacement,
                    replacement_manufacturer: replacement.replacement_manufacturer,
                    replacement_price: replacement.price,
                    replacement_currency: replacement.currency,
                    replacement_source_type: replacement.source_type,
                    replacement_source_url: replacement.source_url,
                    replacement_notes: replacement.notes,
                    replacement_confidence: replacement.confidence,
                  };
                }
                return part;
              })
            );
          } else if (event.type === 'complete' && event.results) {
            // Merge final replacement results
            const replacementResults = event.results;
            const updatedParts: Part[] = [];
            
            setParts((prev) => {
              const updated = prev.map((part) => {
                const replacement = replacementResults.find(
                  (r: any) =>
                    normalize(r.obsolete_part_number || r.part_number || '') ===
                      normalize(part.manufacturer_part_number || part.part_number_ai_modified || '') &&
                    normalize(r.manufacturer || '') === normalize(part.part_manufacturer || '')
                );
                if (replacement) {
                  const updatedPart = {
                    ...part,
                    recommended_replacement: replacement.recommended_replacement,
                    replacement_manufacturer: replacement.replacement_manufacturer,
                    replacement_price: replacement.price,
                    replacement_currency: replacement.currency,
                    replacement_source_type: replacement.source_type,
                    replacement_source_url: replacement.source_url,
                    replacement_notes: replacement.notes,
                    replacement_confidence: replacement.confidence,
                  };
                  updatedParts.push(updatedPart);
                  return updatedPart;
                }
                return part;
              });
              
              // Update filtered parts as well
              setFilteredParts((prevFiltered) => {
                return prevFiltered.map((part) => {
                  const replacement = replacementResults.find(
                    (r: any) =>
                      normalize(r.obsolete_part_number || r.part_number || '') ===
                        normalize(part.manufacturer_part_number || part.part_number_ai_modified || '') &&
                      normalize(r.manufacturer || '') === normalize(part.part_manufacturer || '')
                  );
                  if (replacement) {
                    return {
                      ...part,
                      recommended_replacement: replacement.recommended_replacement,
                      replacement_manufacturer: replacement.replacement_manufacturer,
                      replacement_price: replacement.price,
                      replacement_currency: replacement.currency,
                      replacement_source_type: replacement.source_type,
                      replacement_source_url: replacement.source_url,
                      replacement_notes: replacement.notes,
                      replacement_confidence: replacement.confidence,
                    };
                  }
                  return part;
                });
              });
              
              return updated;
            });
            
            // Save updated parts to database
            if (updatedParts.length > 0) {
              try {
                await updateParts({
                  parts: updatedParts.map((part) => ({
                    id: part.id,
                    recommended_replacement: part.recommended_replacement,
                    replacement_manufacturer: part.replacement_manufacturer,
                    replacement_price: part.replacement_price,
                    replacement_currency: part.replacement_currency,
                    replacement_source_type: part.replacement_source_type,
                    replacement_source_url: part.replacement_source_url,
                    replacement_notes: part.replacement_notes,
                    replacement_confidence: part.replacement_confidence,
                  })),
                });
                setProgress(`Replacement search complete! Updated ${updatedParts.length} parts in database.`);
              } catch (err) {
                console.error('Failed to update parts in database:', err);
                setProgress(`Replacement search complete! Processed ${event.total_analyzed} parts. (Note: Failed to save to database)`);
              }
            } else {
              setProgress(`Replacement search complete! Processed ${event.total_analyzed} parts.`);
            }
            
            setIsLookingForReplacements(false);
          } else if (event.type === 'error') {
            setError(event.message || 'Replacement search error occurred');
            setIsLookingForReplacements(false);
          }
        },
        (err) => {
          setError(err.message);
          setIsLookingForReplacements(false);
        }
      );

      abortControllerRef.current = abort;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start replacement search');
      setIsLookingForReplacements(false);
    }
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current();
      abortControllerRef.current = null;
    }
    setIsLookingForReplacements(false);
    setProgress('');
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

        {/* Progress Display */}
        {progress && (
          <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 p-4">
            <p className="text-sm text-blue-800">{progress}</p>
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
              <div className="flex items-center gap-4">
                {isLookingForReplacements && (
                  <button
                    onClick={handleCancel}
                    className="rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
                  >
                    Cancel
                  </button>
                )}
                {!isLookingForReplacements && (
                  <button
                    onClick={handleFindReplacements}
                    disabled={parts.filter((p) => {
                      const status = p.ai_status || '';
                      return status.includes('Obsolete') || status === '🔴 Obsolete';
                    }).length === 0}
                    className="rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-2 text-white font-medium hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Find Replacement Parts
                  </button>
                )}
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

