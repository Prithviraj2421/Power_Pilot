import React from 'react';
import { EntityRelationship } from '../../../types';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { ArrowRight, Key, Network, Link, GitMerge } from 'lucide-react';

export interface RelationshipCardProps {
  relationship: EntityRelationship;
}

export const RelationshipCard: React.FC<RelationshipCardProps> = ({ relationship }) => {
  const typeIcons = {
    PRIMARY_KEY: <Key className="w-5 h-5 text-warning" />,
    FOREIGN_KEY: <Link className="w-5 h-5 text-primary" />,
    PARENT_CHILD: <GitMerge className="w-5 h-5 text-success" />,
    CORRELATION_LINK: <Network className="w-5 h-5 text-purple-400" />,
    SEMANTIC_LINK: <Network className="w-5 h-5 text-blue-400" />,
  };

  const typeVariants = {
    PRIMARY_KEY: 'warning' as const,
    FOREIGN_KEY: 'primary' as const,
    PARENT_CHILD: 'success' as const,
    CORRELATION_LINK: 'purple' as const,
    SEMANTIC_LINK: 'info' as const,
  };

  return (
    <Card hoverable className="p-5">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          {typeIcons[relationship.relationship_type] || <Network className="w-5 h-5 text-primary" />}
          <Badge variant={typeVariants[relationship.relationship_type] || 'primary'}>
            {relationship.relationship_type.replace('_', ' ')}
          </Badge>
        </div>
        <span className="text-xs font-mono text-gray-400 bg-surface px-2 py-0.5 rounded border border-border">
          {relationship.cardinality}
        </span>
      </div>

      <div className="flex items-center gap-3 p-3 bg-surface rounded-lg border border-border mb-3 text-sm font-mono text-white">
        <span className="text-primary font-bold">{relationship.source_column}</span>
        <ArrowRight className="w-4 h-4 text-gray-500 flex-shrink-0" />
        <span className="text-success font-bold">{relationship.target_column}</span>
      </div>

      <p className="text-xs text-gray-300 mb-2">{relationship.reasoning}</p>

      <div className="text-xs text-gray-400 flex items-center justify-between pt-2 border-t border-border">
        <span>Confidence:</span>
        <span className="font-semibold text-white">{(relationship.confidence * 100).toFixed(0)}%</span>
      </div>
    </Card>
  );
};
