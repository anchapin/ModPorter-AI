import React, { useState } from 'react';
import { 
  Box,
  Typography,
  Tabs,
  Tab,
  Button,
  Stack
} from '@mui/material';
import { Add } from '@mui/icons-material';
import { KnowledgeGraphViewer } from '../components/KnowledgeGraphViewer';
import { CommunityContributionForm } from '../components/CommunityContribution';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`knowledge-graph-tabpanel-${index}`}
      aria-labelledby={`knowledge-graph-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const KnowledgeGraphPage: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0);
  const [showContributionForm, setShowContributionForm] = useState(false);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleContributionSuccess = () => {
    // Refresh the data
    window.location.reload();
  };

  return (
    <Box sx={{ width: '100%', maxWidth: 1400, margin: '0 auto' }}>
      <Stack spacing={3} sx={{ mb: 3 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Knowledge Graph & Community Curation
        </Typography>
        
        <Typography variant="body1" color="text.secondary">
          Explore our semantic knowledge graph of Minecraft modding concepts and contribute to the community database.
        </Typography>
      </Stack>

      <Tabs 
        value={currentTab} 
        onChange={handleTabChange}
        aria-label="Knowledge graph tabs"
      >
        <Tab label="Knowledge Graph Viewer" />
        <Tab label="Community Contributions" />
        <Tab label="Version Compatibility" />
      </Tabs>

      <TabPanel value={currentTab} index={0}>
        <Stack spacing={2} direction="row" sx={{ mb: 2, justifyContent: 'flex-end' }}>
          <Button 
            variant="contained" 
            startIcon={<Add />}
            onClick={() => setShowContributionForm(true)}
          >
            Contribute Knowledge
          </Button>
        </Stack>
        
        <KnowledgeGraphViewer />
      </TabPanel>

      <TabPanel value={currentTab} index={1}>
        <Box>
          <Stack spacing={2} direction="row" sx={{ mb: 3, justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h5">
              Community Contributions
            </Typography>
            <Button 
              variant="contained" 
              startIcon={<Add />}
              onClick={() => setShowContributionForm(true)}
            >
              Add Contribution
            </Button>
          </Stack>
          
          <Typography variant="body1" color="text.secondary">
            Browse and review community-submitted knowledge patterns, nodes, and corrections.
          </Typography>
          
          {/* TODO: Add contributions list component */}
        </Box>
      </TabPanel>

      <TabPanel value={currentTab} index={2}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Version Compatibility Matrix
          </Typography>
          
          <Typography variant="body1" color="text.secondary">
            View compatibility information between different Minecraft Java and Bedrock versions.
          </Typography>
          
          {/* TODO: Add version compatibility matrix component */}
        </Box>
      </TabPanel>

      <CommunityContributionForm
        open={showContributionForm}
        onClose={() => setShowContributionForm(false)}
        onSuccess={handleContributionSuccess}
      />
    </Box>
  );
};

export default KnowledgeGraphPage;
