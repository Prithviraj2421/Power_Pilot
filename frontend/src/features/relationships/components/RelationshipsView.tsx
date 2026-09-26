import React from 'react';
import { RelationshipReport } from '../../../types';
import { RelationshipCard } from './RelationshipCard';

export interface RelationshipsViewProps {
  report: RelationshipReport;
}

export const RelationshipsView: React.FC<RelationshipsViewProps> = ({ report }) => {
  if (!report || report.all_relationships.length === 0) return null;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-bold text-white mb-1">Entity Relationships & Key Linkages</h3>
        <p className="text-xs text-gray-400">
          Detected Primary Keys, Foreign Keys, Dimensional Parent-Child Hierarchies, and Semantic Associations for Data Modeling.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {report.all_relationships.map((rel, idx) => (
          <RelationshipCard key={idx} relationship={rel} />
        ))}
      </div>
    </div>
  );
};
