import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { HomePage } from '../pages/HomePage';
import { WorkspacePage } from '../pages/WorkspacePage';
import { SettingsPage } from '../pages/SettingsPage';
import { NotFoundPage } from '../pages/NotFoundPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Personality 1: Full-Screen Marketing & Landing Upload Experience */}
      <Route path="/" element={<HomePage />} />

      {/* Personality 2: Calm Application Workspace with Sidebar & Navbar */}
      <Route element={<AppLayout />}>
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
};
