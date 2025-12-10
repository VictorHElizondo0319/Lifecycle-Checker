'use client';

import { Product } from '@/types';
import TableRow from './TableRow';
import { FIELD_CONFIGS } from '@/lib/fieldConfig';

interface TableProps {
  products: Product[];
  visibleFields: Set<string>;
  onAnalyze?: () => void;
  analyzing?: boolean;
}

export default function Table({ products, visibleFields, onAnalyze, analyzing }: TableProps) {
  // Get visible field configs in order
  const visibleFieldConfigs = FIELD_CONFIGS.filter((field) => visibleFields.has(field.key));

  return (
    <div className="w-full">
      <div 
        className="overflow-x-scroll overflow-y-auto rounded-lg border border-gray-200" 
        style={{ 
          maxHeight: '384px',
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
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {products.map((product, index) => (
              <TableRow
                key={product.row_index || index}
                product={product}
                visibleFields={visibleFields}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
