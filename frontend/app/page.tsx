'use client';

import { useState, useRef, useEffect } from 'react';
import { Product, AnalysisResult } from '@/types';
import { uploadExcelFile, analyzeProducts, analyzeProductsStream } from '@/lib/api';
import Table from '@/components/Table';
import FieldSelector, { FieldConfig } from '@/components/FieldSelector';
import FilterBar from '@/components/FilterBar';
import { FIELD_CONFIGS, DEFAULT_VISIBLE_FIELDS } from '@/lib/fieldConfig';

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [visibleFields, setVisibleFields] = useState<Set<string>>(DEFAULT_VISIBLE_FIELDS);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<(() => void) | null>(null);

  // Initialize filtered products when products change
  useEffect(() => {
    setFilteredProducts(products);
  }, [products]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError('');
    setProducts([]);
    setFilteredProducts([]);
    setResults([]);

    try {
      const response = await uploadExcelFile(file);
      if (response.success) {
        setProducts(response.products);
        setFilteredProducts(response.products);
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

    setAnalyzing(true);
    setError('');
    setResults([]);
    setProgress('Starting analysis...');

    try {
      // Use streaming for better UX
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
            setResults((prev) => [...prev, ...event.data.results]);
          } else if (event.type === 'complete' && event.results) {
            setResults(event.results);
            setProgress(`Analysis complete! Analyzed ${event.total_analyzed} products.`);
          } else if (event.type === 'error') {
            setError(event.message || 'Analysis error occurred');
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
    setError('');
    setProgress('');
    setVisibleFields(DEFAULT_VISIBLE_FIELDS);
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
    <div className="min-h-screen">
      <div className="mx-auto">
        <div className="rounded-2xl">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-8 text-white">
            <h1 className="text-3xl font-bold">Parts Lifecycle Checker</h1>
            <p className="mt-2 text-purple-100">Automated status checking with confidence scoring</p>
          </div>

          <div className="p-6">
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

            {/* Product List Display */}
            {products.length > 0 && results.length === 0 && (
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
                  <button
                    onClick={handleAnalyze}
                    disabled={analyzing}
                    className="rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-2 text-white font-medium hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {analyzing ? 'Analyzing...' : 'Analyze Products'}
                  </button>
                </div>

                <FilterBar products={products} onFilterChange={setFilteredProducts} />

                <div className="max-h-96 overflow-auto">
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
            {results.length > 0 && (
              <div className="mb-6">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-800">
                    Analysis Results ({results.length})
                  </h2>
                  {analyzing && (
                    <button
                      onClick={handleCancel}
                      className="rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
                    >
                      Cancel
                    </button>
                  )}
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
                      {results.map((result, index) => (
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
      </div>
    </div>
  );
}
