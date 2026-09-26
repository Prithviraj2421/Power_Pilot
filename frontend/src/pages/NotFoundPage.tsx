import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FileQuestion, ArrowLeft } from 'lucide-react';
import { PageContainer } from '../components/layout/PageContainer';
import { EmptyState } from '../components/ui/EmptyState';
import { Button } from '../components/ui/Button';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <PageContainer>
      <EmptyState
        title="404 — Page Not Found"
        description="The workspace page or intelligence view you are looking for does not exist."
        icon={<FileQuestion className="w-12 h-12 text-primary" />}
        action={
          <Button onClick={() => navigate('/')} leftIcon={<ArrowLeft className="w-4 h-4" />}>
            Back to Home
          </Button>
        }
      />
    </PageContainer>
  );
};
