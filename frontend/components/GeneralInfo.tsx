'use client';

interface ParticipatingAssociate {
  name: string;
  id: string;
}

interface GeneralInfo {
  document_no?: string;
  revision_no?: string;
  title?: string;
  equipment_description?: string;
  eam_equipment_id?: string;
  alias?: string;
  plant?: string;
  group_responsible?: string;
  participating_associates?: {
    initiator?: ParticipatingAssociate;
    pe?: ParticipatingAssociate;
    d_and_a?: ParticipatingAssociate;
    maintenance_tech?: ParticipatingAssociate;
    indirect_procurement?: ParticipatingAssociate;
  };
}

interface GeneralInfoProps {
  generalInfo: GeneralInfo | null;
}

export default function GeneralInfo({ generalInfo }: GeneralInfoProps) {
  if (!generalInfo) {
    return null;
  }

  const formatValue = (value: string | undefined) => {
    return value && value.trim() !== '' ? value : '-';
  };

  const formatAssociate = (associate: ParticipatingAssociate | undefined) => {
    if (!associate || (!associate.name && !associate.id)) {
      return '-';
    }
    const name = associate.name || '';
    const id = associate.id || '';
    return name && id ? `${name} (${id})` : name || id || '-';
  };

  return (
    <div className="mb-6 rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-200 bg-gray-50 px-6 py-3">
        <h2 className="text-lg font-semibold text-gray-800">General Information</h2>
      </div>
      <div className="p-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Document Information */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
              Document Information
            </h3>
            <div className="space-y-1">
              <div>
                <span className="text-xs font-medium text-gray-600">Document No:</span>
                <p className="text-sm text-gray-900">{formatValue(generalInfo.document_no)}</p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">Revision No:</span>
                <p className="text-sm text-gray-900">{formatValue(generalInfo.revision_no)}</p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">Title:</span>
                <p className="text-sm text-gray-900">{formatValue(generalInfo.title)}</p>
              </div>
            </div>
          </div>

          {/* Equipment Information */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
              Equipment Information
            </h3>
            <div className="space-y-1">
              <div>
                <span className="text-xs font-medium text-gray-600">Equipment Description:</span>
                <p className="text-sm text-gray-900">{formatValue(generalInfo.equipment_description)}</p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">EAM Equipment ID:</span>
                <p className="text-sm text-gray-900">{formatValue(generalInfo.eam_equipment_id)}</p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">Alias:</span>
                <p className="text-sm text-gray-900">{formatValue(generalInfo.alias)}</p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">Plant:</span>
                <p className="text-sm text-gray-900">{formatValue(generalInfo.plant)}</p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">Group Responsible:</span>
                <p className="text-sm text-gray-900">{formatValue(generalInfo.group_responsible)}</p>
              </div>
            </div>
          </div>

          {/* Participating Associates */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
              Participating Associates
            </h3>
            <div className="space-y-1">
              <div>
                <span className="text-xs font-medium text-gray-600">Initiator (PE/QE):</span>
                <p className="text-sm text-gray-900">
                  {formatAssociate(generalInfo.participating_associates?.initiator)}
                </p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">PE (if not initiator):</span>
                <p className="text-sm text-gray-900">
                  {formatAssociate(generalInfo.participating_associates?.pe)}
                </p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">D&A:</span>
                <p className="text-sm text-gray-900">
                  {formatAssociate(generalInfo.participating_associates?.d_and_a)}
                </p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">Maintenance Tech:</span>
                <p className="text-sm text-gray-900">
                  {formatAssociate(generalInfo.participating_associates?.maintenance_tech)}
                </p>
              </div>
              <div>
                <span className="text-xs font-medium text-gray-600">Indirect Procurement:</span>
                <p className="text-sm text-gray-900">
                  {formatAssociate(generalInfo.participating_associates?.indirect_procurement)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

