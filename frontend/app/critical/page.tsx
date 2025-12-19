'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Product, AnalysisResult, GeneralInfo as GeneralInfoType } from '@/types';
import { uploadExcelFile, analyzeProductsStream, findReplacementsStream, exportExcelFile } from '@/lib/api';
import Table from '@/components/Table';
import FieldSelector from '@/components/FieldSelector';
import FilterBar from '@/components/FilterBar';
import GeneralInfoComponent from '@/components/GeneralInfo';
import { FIELD_CONFIGS, CRITICAL_DEFAULT_VISIBLE_FIELDS } from '@/lib/fieldConfig';

export default function CriticalPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [generalInfo, setGeneralInfo] = useState<GeneralInfoType | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [exporting, setExporting] = useState(false);
  const [visibleFields, setVisibleFields] = useState<Set<string>>(CRITICAL_DEFAULT_VISIBLE_FIELDS);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<(() => void) | null>(null);
  const [isAnalyzed, setIsAnalyzed] = useState(false);
  const [isLookingForReplacements, setIsLookingForReplacements] = useState(false);
  const [filteredResults, setFilteredResults] = useState<AnalysisResult[]>([]);
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('');

  const normalize = useCallback((value?: string) => value?.trim().toUpperCase() || '', []);
  
  const pickGeneralInfo = {
    machine_description: generalInfo?.equipment_description,
    machine_equipment_number: generalInfo?.eam_equipment_id,
    equipment_alias: generalInfo?.alias,
    plant: generalInfo?.plant,
    group_responsibility: generalInfo?.group_responsible,
    initiator: generalInfo?.participating_associates?.initiator?.name || ""
  }  
  const mergeResultList = useCallback(
    (existing: AnalysisResult[], incoming: AnalysisResult[]) => {
      const merged = new Map<string, AnalysisResult>();
      existing.forEach((item) => {
        const key = `${normalize(item.manufacturer)}|${normalize(item.part_number)}`;
        merged.set(key, item);
      });
      incoming.forEach((item) => {
        const key = `${normalize(item.manufacturer)}|${normalize(item.part_number)}`;
        merged.set(key, item);
      });
      return Array.from(merged.values());
    },
    [normalize]
  );

  const mergeResultsIntoProducts = useCallback(
    (current: Product[], incoming: AnalysisResult[]) =>
      current.map((product) => {
        const productManufacturers = [
          normalize(product.manufacturer),
          normalize(product.part_manufacturer),
        ].filter(Boolean);
        const productPartNumbers = [
          normalize(product.manufacturer_part_number),
          normalize(product.part_number_ai_modified),
        ].filter(Boolean);

        const match = incoming.find((result) => {
          const resultManufacturer = normalize(result.manufacturer);
          const resultPartNumber = normalize(result.part_number);

          const manufacturerMatches =
            resultManufacturer &&
            productManufacturers.some((value) => value === resultManufacturer);
          const partMatches =
            resultPartNumber && productPartNumbers.some((value) => value === resultPartNumber);

          return manufacturerMatches && partMatches;
        });

        if (!match) return product;

        return {
          ...product,
          ai_status: match.ai_status,
          notes_by_ai: match.notes_by_ai,
          ai_confidence: match.ai_confidence,
          manufacturer: product.manufacturer || match.manufacturer,
        };
      }),
    [normalize]
  );

  useEffect(() => {
    setFilteredProducts(products);
  }, [products]);

  // Filter results by AI Status
  useEffect(() => {
    if (selectedStatusFilter) {
      const filtered = results.filter((result) => result.ai_status === selectedStatusFilter);
      setFilteredResults(filtered);
    } else {
      setFilteredResults([]); // Empty array means show all results
    }
  }, [results, selectedStatusFilter]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError('');
    setProducts([]);
    setFilteredProducts([]);
    setResults([]);
    setGeneralInfo(null);

    try {
      const response = await uploadExcelFile(file);
      if (response.success) {
        setProducts(response.products);
        setFilteredProducts(response.products);
        if (response.general_info) {
          setGeneralInfo(response.general_info);
        }
      } else {
        setError(response.error || 'Failed to parse Excel file');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (products.length === 0) {
      setError('Please upload an Excel file first');
      return;
    }

    setIsAnalyzed(false);
    setAnalyzing(true);
    setError('');
    setResults([]);
    setProgress('Starting analysis...');

    try {
      const abort = analyzeProductsStream(
        products,
        (event) => {
          if (event.type === 'start') {
            setProgress(`Processing ${event.total_products} products in ${event.total_chunks} chunks...`);
          } else if (event.type === 'chunk_start') {
            setProgress(`Analyzing chunk ${event.chunk}/${event.total_chunks} (${event.products_in_chunk} products)...`);
          } else if (event.type === 'chunk_complete') {
            setProgress(`Completed chunk ${event.chunk}/${event.total_chunks}`);
          } else if (event.type === 'result' && event.data?.results) {
            setResults((prev) => mergeResultList(prev, event.data.results));
            setProducts((prev) => mergeResultsIntoProducts(prev, event.data.results));
          } else if (event.type === 'complete' && event.results) {
            setResults((prev) => mergeResultList(prev, event.results));
            setProducts((prev) => mergeResultsIntoProducts(prev, event.results));
            setProgress(`Analysis complete! Analyzed ${event.total_analyzed} products.`);
            setAnalyzing(false);
            setIsAnalyzed(true);
          } else if (event.type === 'error') {
            setError(event.message || 'Analysis error occurred');
            setAnalyzing(false);
          }
        },
        (err) => {
          setError(err.message);
          setAnalyzing(false);
        }
      );

      abortControllerRef.current = abort;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis');
      setAnalyzing(false);
    }
  };

  const handleFindReplacements = async () => {
    if (products.length === 0) {
      setError('Please upload an Excel file first');
      return;
    }

    // Filter to only obsolete products
    const obsoleteProducts = products.filter((product) => {
      const status = product.ai_status || '';
      return status.includes('Obsolete') || status === '🔴 Obsolete';
    });

    if (obsoleteProducts.length === 0) {
      setError('No obsolete products found. Please analyze products first to identify obsolete parts.');
      return;
    }

    setIsLookingForReplacements(true);
    setError('');
    setProgress('Starting replacement search...');

    try {
      const abort = findReplacementsStream(
        obsoleteProducts,
        (event) => {
          if (event.type === 'start') {
            setProgress(`Finding replacements for ${event.total_products} obsolete products in ${event.total_chunks} chunks...`);
          } else if (event.type === 'chunk_start') {
            setProgress(`Processing chunk ${event.chunk}/${event.total_chunks} (${event.products_in_chunk} products)...`);
          } else if (event.type === 'chunk_complete') {
            setProgress(`Completed chunk ${event.chunk}/${event.total_chunks}`);
          } else if (event.type === 'result' && event.data?.results) {
            // Merge replacement results into products
            const replacementResults = event.data.results;
            setProducts((prev) =>
              prev.map((product) => {
                const replacement = replacementResults.find(
                  (r: any) =>
                    normalize(r.obsolete_part_number || r.part_number || '') ===
                      normalize(product.manufacturer_part_number || product.part_number_ai_modified || '') &&
                    normalize(r.manufacturer || '') === normalize(product.part_manufacturer || product.manufacturer || '')
                );
                if (replacement) {
                  return {
                    ...product,
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
                return product;
              })
            );
          } else if (event.type === 'complete' && event.results) {
            // Merge final replacement results
            const replacementResults = event.results;
            setProducts((prev) =>
              prev.map((product) => {
                const replacement = replacementResults.find(
                  (r: any) =>
                    normalize(r.obsolete_part_number || r.part_number || '') ===
                      normalize(product.manufacturer_part_number || product.part_number_ai_modified || '') &&
                    normalize(r.manufacturer || '') === normalize(product.part_manufacturer || product.manufacturer || '')
                );
                if (replacement) {
                  return {
                    ...product,
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
                return product;
              })
            );
            setProgress(`Replacement search complete! Processed ${event.total_analyzed} products.`);
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

  const handleExportExcel = async () => {
    if (products.length === 0) {
      setError('Please upload an Excel file first');
      return;
    }
    setExporting(true);
    setError('');
    try {
      // Export all product fields including replacement fields
      // Use products array which contains all fields including replacement data
      await exportExcelFile({
        cols: Array.from(FIELD_CONFIGS),
        products: products.map((product: Product) => ({
          ...product,
          ...pickGeneralInfo
        }))
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export Excel file');
    } finally {
      setExporting(false);
    }
  };
  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current();
      abortControllerRef.current = null;
    }
    setAnalyzing(false);
    setProgress('');
  };

  const handleReset = () => {
    setProducts([]);
    setFilteredProducts([]);
    setResults([]);
    setFilteredResults([]);
    setGeneralInfo(null);
    setError('');
    setProgress('');
    setVisibleFields(CRITICAL_DEFAULT_VISIBLE_FIELDS);
    setIsAnalyzed(false);
    setSelectedStatusFilter('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };


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
        <h1 className="text-2xl font-bold text-gray-800">Critical Separate Parts</h1>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* File Upload Section */}
        <div className="mb-6">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Upload Excel File
          </label>
          <div className="flex items-center gap-4">
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileUpload}
              disabled={loading || analyzing}
              className="block w-full text-sm text-gray-500 file:mr-4 file:rounded-lg file:border-0 file:bg-purple-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-purple-700 hover:file:bg-purple-100 disabled:opacity-50"
            />
            {products.length > 0 && (
              <button
                onClick={handleReset}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Reset
              </button>
            )}
          </div>
          {loading && (
            <p className="mt-2 text-sm text-gray-600">Parsing Excel file...</p>
          )}
          {products.length > 0 && (
            <p className="mt-2 text-sm text-green-600">
              ✓ Loaded {products.length} products
            </p>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Progress Display */}
        {progress && (
          <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 p-4">
            <p className="text-sm text-blue-800">{progress}</p>
          </div>
        )}

        {/* General Information Display */}
        {generalInfo && <GeneralInfoComponent generalInfo={generalInfo} />}

        {/* Product List Display */}
        {products.length > 0 && (
          <div className="mb-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <h2 className="text-lg font-semibold text-gray-800">
                  Products ({filteredProducts.length} of {products.length})
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
                {!isAnalyzed && (
                  <button
                    onClick={handleAnalyze}
                    disabled={analyzing}
                    className="rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-2 text-white font-medium hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {analyzing ? 'Analyzing...' : 'Analyze Products'}
                  </button>
                )}
              </div>
            </div>

            <FilterBar products={products} onFilterChange={setFilteredProducts} />

            <div>
              {filteredProducts.length > 0 ? (
                <Table
                  products={filteredProducts}
                  visibleFields={visibleFields}
                  onAnalyze={handleAnalyze}
                  analyzing={analyzing}
                />
              ) : (
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
                  <p className="text-gray-500">No products match the current filters.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Analysis Results */}
        {results.length > 0  && (
          <div className="mb-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <h2 className="text-lg font-semibold text-gray-800">
                  Analysis Results ({selectedStatusFilter ? filteredResults.length : results.length} of {results.length})
                </h2>
                {/* AI Status Filter Dropdown */}
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-gray-700">
                    Filter by Status:
                  </label>
                  <select
                    value={selectedStatusFilter}
                    onChange={(e) => setSelectedStatusFilter(e.target.value)}
                    className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="">All Statuses</option>
                    <option value="Active">Active</option>
                    <option value="🔴 Obsolete">🔴 Obsolete</option>
                    <option value="Review">Review</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {analyzing && (
                  <button
                    onClick={handleCancel}
                    className="rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
                  >
                    Cancel
                  </button>
                )}
                {isAnalyzed && (
                  <>
                    <button
                      onClick={handleFindReplacements}
                      disabled={isLookingForReplacements}
                      className="rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-2 text-white font-medium hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isLookingForReplacements ? 'Finding Replacements...' : 'Find Replacement Parts'}
                    </button>
                    <button
                      onClick={handleExportExcel}
                      disabled={exporting}
                      className="rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 px-6 py-2 text-white font-medium hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {exporting ? 'Exporting...' : 'Export Analyze Result'}
                    </button>
                  </>
                )}
              </div>
            </div>
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                      No
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                      Manufacturer
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                      Part Number
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                      AI Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                      Notes by AI
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                      AI Confidence
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {(selectedStatusFilter ? filteredResults : results).map((result, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
                        {index + 1}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
                        {result.manufacturer}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
                        {result.part_number}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-sm">
                        <span
                          className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                            result.ai_status === 'Active'
                              ? 'bg-green-100 text-green-800'
                              : result.ai_status === '🔴 Obsolete'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {result.ai_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 max-w-md">
                        <div className="max-h-32 overflow-y-auto">
                          {result.notes_by_ai}
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-sm">
                        <span
                          className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                            result.ai_confidence === 'High'
                              ? 'bg-green-100 text-green-800'
                              : result.ai_confidence === 'Medium'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {result.ai_confidence}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Empty State */}
        {products.length === 0 && results.length === 0 && !loading && (
          <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <p className="text-gray-500">
              Upload an Excel file (.xlsx or .xls) to get started.
            </p>
            <p className="mt-2 text-sm text-gray-400">
              The file should contain all required columns matching the template structure.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

