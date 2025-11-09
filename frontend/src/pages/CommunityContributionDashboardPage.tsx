import React from 'react';
import { Container, Typography } from '@mui/material';
import CommunityContributionDashboard from '../components/CommunityContribution/CommunityContributionDashboard';

const CommunityContributionDashboardPage: React.FC = () => {
  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Community Contributions
      </Typography>
      <CommunityContributionDashboard />
    </Container>
  );
};

export default CommunityContributionDashboardPage;
