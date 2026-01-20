'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Product, AnalysisResult, GeneralInfo as GeneralInfoType } from '@/types';
import { uploadExcelFile, analyzeProductsStream, findReplacementsStream, exportExcelFile, saveData } from '@/lib/api';
import Table from '@/components/Table';
import FieldSelector from '@/components/FieldSelector';
import FilterBar from '@/components/FilterBar';
import GeneralInfoComponent from '@/components/GeneralInfo';
import { FIELD_CONFIGS, CRITICAL_DEFAULT_VISIBLE_FIELDS } from '@/lib/fieldConfig';

export default function CriticalPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [generalInfo, setGeneralInfo] = useState<GeneralInfoType | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [exporting, setExporting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [visibleFields, setVisibleFields] = useState<Set<string>>(CRITICAL_DEFAULT_VISIBLE_FIELDS);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<(() => void) | null>(null);
  const [isAnalyzed, setIsAnalyzed] = useState(false);
  const [isLookingForReplacements, setIsLookingForReplacements] = useState(false);

  const normalize = useCallback((value?: string) => value?.trim().toUpperCase() || '', []);
  
  const pickGeneralInfo = {
    machine_description: generalInfo?.equipment_description,
    machine_equipment_number: generalInfo?.eam_equipment_id,
    equipment_alias: generalInfo?.alias,
    plant: generalInfo?.plant,
    group_responsibility: generalInfo?.group_responsible,
    initiator: generalInfo?.participating_associates?.initiator?.name || ""
  }  
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

        // If no match found, check if this product should be skipped (missing/no stocking_decision)
        if (!match) {
          const stockingDecision = (product.stocking_decision || '').trim().toLowerCase();
          const shouldSkip = !stockingDecision || stockingDecision === 'no';
          
          // For skipped products, explicitly set AI fields to null/undefined
          if (shouldSkip) {
            return {
              ...product,
              ai_status: null,
              notes_by_ai: null,
              ai_confidence: null,
            };
          }
          // If not skipped but no match, return product as-is (might be analyzed later)
          return product;
        }

        // For products with matches, merge AI results
        // If AI fields are null/undefined in match, it means product was skipped from analysis
        return {
          ...product,
          ai_status: match.ai_status ?? null,
          notes_by_ai: match.notes_by_ai ?? null,
          ai_confidence: match.ai_confidence ?? null,
          manufacturer: product.manufacturer || match.manufacturer,
        };
      }),
    [normalize]
  );

  // Handle filtering - memoized callback to prevent infinite loops
  const handleFilterChange = useCallback((filtered: Product[]) => {
    setFilteredProducts(filtered);
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError('');
    setProducts([]);
    setFilteredProducts([]);
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
    setProgress('Starting analysis...');

    try {
      const abort = analyzeProductsStream(
        products,
        (event) => {
          if (event.type === 'start') {
            const skippedMsg = event.total_skipped > 0 ? ` (${event.total_skipped} skipped - no stocking decision)` : '';
            setProgress(`Processing ${event.total_products} products in ${event.total_chunks} chunks...${skippedMsg}`);
          } else if (event.type === 'chunk_start') {
            setProgress(`Analyzing chunk ${event.chunk}/${event.total_chunks} (${event.products_in_chunk} products)...`);
          } else if (event.type === 'chunk_complete') {
            setProgress(`Completed chunk ${event.chunk}/${event.total_chunks}`);
          } else if (event.type === 'result' && event.data?.results) {
            // Merge incremental chunk results for real-time updates
            setProducts((prev) => mergeResultsIntoProducts(prev, event.data.results));
          } else if (event.type === 'complete' && event.results) {
            // Final merge with all results to ensure consistency
            setProducts((prev) => mergeResultsIntoProducts(prev, event.results));
            const skippedMsg = event.total_skipped > 0 ? ` (${event.total_skipped} skipped - no stocking decision)` : '';
            setProgress(`Analysis complete! Analyzed ${event.total_analyzed} products.${skippedMsg}`);
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

  const handleSave = async () => {
    if (products.length === 0) {
      setError('Please upload an Excel file first');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const response = await saveData({
        general_info: generalInfo ? {
          eam_equipment_id: generalInfo.eam_equipment_id,
          equipment_description: generalInfo.equipment_description,
          alias: generalInfo.alias,
          plant: generalInfo.plant,
          group_responsible: generalInfo.group_responsible,
          participating_associates: generalInfo.participating_associates
        } : undefined,
        products: products.map((product: Product) => ({
          ...product,
          ...pickGeneralInfo
        })),
        create_log: true
      });
      
      if (response.success) {
        setProgress(
          `Data saved successfully! ` +
          `${response.parts_saved} parts saved, ` +
          `${response.parts_updated} parts updated, ` +
          `${response.machine_parts_linked} machine-part links created.`
        );
      } else {
        setError(response.error || 'Failed to save data');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save data');
    } finally {
      setSaving(false);
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
    setGeneralInfo(null);
    setError('');
    setProgress('');
    setVisibleFields(CRITICAL_DEFAULT_VISIBLE_FIELDS);
    setIsAnalyzed(false);
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
                {/* AI Status Filter Dropdown */}
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
                {!isAnalyzed && (
                  <>
                    <button
                      onClick={handleAnalyze}
                      disabled={analyzing}
                      className="rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-2 text-white font-medium hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {analyzing ? 'Analyzing...' : 'Analyze Products'}
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-2 text-white font-medium hover:from-blue-700 hover:to-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {saving ? 'Saving...' : 'Save to Database'}
                    </button>
                  </>
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
                      onClick={handleSave}
                      disabled={saving}
                      className="rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-2 text-white font-medium hover:from-blue-700 hover:to-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {saving ? 'Saving...' : 'Save to Database'}
                    </button>
                    <button
                      onClick={handleExportExcel}
                      disabled={exporting}
                      className="rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 px-6 py-2 text-white font-medium hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {exporting ? 'Exporting...' : 'Export Excel'}
                    </button>
                  </>
                )}
              </div>
            </div>

            <FilterBar products={products} onFilterChange={handleFilterChange} />

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


        {/* Empty State */}
        {products.length === 0 && !loading && (
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

