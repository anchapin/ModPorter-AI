import React, { useState } from 'react';
import { 
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Stepper,
  Step,
  StepLabel,
  Box,
  Typography,
  Alert,
  Stack,
  Grid
} from '@mui/material';
import { CheckCircle } from '@mui/icons-material';
import { useApi } from '../../hooks/useApi';

interface CommunityContributionData {
  contributor_id: string;
  contribution_type: string;
  title: string;
  description: string;
  contribution_data: Record<string, any>;
  minecraft_version: string;
  tags: string[];
}

interface CommunityContributionFormProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (contribution: any) => void;
}

const steps = [
  'Select Type',
  'Provide Details',
  'Review & Submit'
];

const contributionTypes = [
  { value: 'pattern', label: 'Conversion Pattern', description: 'A new Java to Bedrock conversion pattern' },
  { value: 'node', label: 'Knowledge Node', description: 'A new concept or entity' },
  { value: 'relationship', label: 'Relationship', description: 'A connection between concepts' },
  { value: 'correction', label: 'Correction', description: 'Fix for incorrect information' }
];

export const CommunityContributionForm: React.FC<CommunityContributionFormProps> = ({
  open,
  onClose,
  onSuccess
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [contributionType, setContributionType] = useState('');
  const [formData, setFormData] = useState<Partial<CommunityContributionData>>({
    contribution_type: '',
    title: '',
    description: '',
    minecraft_version: 'latest',
    tags: [],
    contribution_data: {}
  });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  
  const api = useApi();

  const handleNext = () => {
    if (activeStep === 0 && !contributionType) {
      return;
    }
    if (activeStep === 1) {
      if (!formData.title || !formData.description) {
        return;
      }
    }
    setActiveStep((prevStep) => prevStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevStep) => prevStep - 1);
  };

  const handleTypeSelect = (type: string) => {
    setContributionType(type);
    setFormData(prev => ({ ...prev, contribution_type: type }));
    setActiveStep(1);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const contributionData: CommunityContributionData = {
        ...formData,
        contributor_id: 'demo-user', // TODO: Get from auth
        tags: formData.tags || []
      } as CommunityContributionData;

      const response = await api.post('/api/v1/knowledge-graph/contributions', contributionData);
      
      setSubmitted(true);
      onSuccess?.(response.data);
      setTimeout(() => {
        onClose();
        resetForm();
      }, 2000);
    } catch (error) {
      console.error('Submission error:', error);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setActiveStep(0);
    setContributionType('');
    setFormData({
      contribution_type: '',
      title: '',
      description: '',
      minecraft_version: 'latest',
      tags: [],
      contribution_data: {}
    });
    setSubmitted(false);
  };

  const handleClose = () => {
    onClose();
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              What would you like to contribute?
            </Typography>
            <Grid container spacing={2}>
              {contributionTypes.map((type) => (
                <Grid item xs={12} sm={6} key={type.value}>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => handleTypeSelect(type.value)}
                    sx={{ 
                      height: 120, 
                      flexDirection: 'column',
                      textTransform: 'none',
                      border: contributionType === type.value ? '2px solid #1976d2' : '1px solid #ddd'
                    }}
                  >
                    <Typography variant="subtitle1" gutterBottom>
                      {type.label}
                    </Typography>
                    <Typography variant="body2" align="center">
                      {type.description}
                    </Typography>
                  </Button>
                </Grid>
              ))}
            </Grid>
          </Box>
        );

      case 1:
        return (
          <Stack spacing={3}>
            <TextField
              label="Title"
              fullWidth
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              required
            />
            
            <TextField
              label="Description"
              fullWidth
              multiline
              rows={4}
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              required
            />

            <FormControl fullWidth>
              <InputLabel>Minecraft Version</InputLabel>
              <Select
                value={formData.minecraft_version}
                label="Minecraft Version"
                onChange={(e) => setFormData(prev => ({ ...prev, minecraft_version: e.target.value }))}
              >
                <MenuItem value="latest">Latest</MenuItem>
                <MenuItem value="1.20">1.20</MenuItem>
                <MenuItem value="1.19">1.19</MenuItem>
                <MenuItem value="1.18">1.18</MenuItem>
                <MenuItem value="1.17">1.17</MenuItem>
                <MenuItem value="1.16">1.16</MenuItem>
              </Select>
            </FormControl>

            {contributionType === 'pattern' && (
              <Stack spacing={2}>
                <TextField
                  label="Java Pattern Description"
                  fullWidth
                  multiline
                  rows={3}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    contribution_data: { ...prev.contribution_data, java_pattern: e.target.value }
                  }))}
                />
                <TextField
                  label="Bedrock Pattern Description"
                  fullWidth
                  multiline
                  rows={3}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    contribution_data: { ...prev.contribution_data, bedrock_pattern: e.target.value }
                  }))}
                />
              </Stack>
            )}

            {contributionType === 'node' && (
              <Stack spacing={2}>
                <TextField
                  label="Node Name"
                  fullWidth
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    contribution_data: { ...prev.contribution_data, name: e.target.value }
                  }))}
                />
                <FormControl fullWidth>
                  <InputLabel>Platform</InputLabel>
                  <Select
                    label="Platform"
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      contribution_data: { ...prev.contribution_data, platform: e.target.value }
                    }))}
                  >
                    <MenuItem value="java">Java Only</MenuItem>
                    <MenuItem value="bedrock">Bedrock Only</MenuItem>
                    <MenuItem value="both">Both Platforms</MenuItem>
                  </Select>
                </FormControl>
              </Stack>
            )}
          </Stack>
        );

      case 2:
        return (
          <Stack spacing={3}>
            <Typography variant="h6">
              Review Your Contribution
            </Typography>
            
            <Alert severity="info">
              Please review your contribution before submitting. Our team will review it and may contact you with questions.
            </Alert>

            <Box sx={{ background: '#f9f9f9', p: 2, borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Contribution Summary
              </Typography>
              
              <Stack spacing={1}>
                <Typography><strong>Type:</strong> {formData.contribution_type}</Typography>
                <Typography><strong>Title:</strong> {formData.title}</Typography>
                <Typography><strong>Description:</strong> {formData.description}</Typography>
                <Typography><strong>Version:</strong> {formData.minecraft_version}</Typography>
              </Stack>
            </Box>

            {submitted && (
              <Alert 
                severity="success" 
                icon={<CheckCircle />}
              >
                Contribution submitted successfully! It will be reviewed by our team.
              </Alert>
            )}
          </Stack>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: 600 }
      }}
    >
      <DialogTitle>
        Community Contribution Form
      </DialogTitle>
      
      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
        
        <Box sx={{ mt: 2, mb: 2 }}>
          {renderStepContent(activeStep)}
        </Box>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={handleClose}>
          {activeStep === 2 && submitted ? 'Close' : 'Cancel'}
        </Button>
        
        <Button 
          color="inherit" 
          disabled={activeStep === 0} 
          onClick={handleBack}
          sx={{ mr: 1 }}
        >
          Back
        </Button>
        
        {activeStep < 2 && (
          <Button onClick={handleNext} variant="contained">
            Next
          </Button>
        )}
        
        {activeStep === 2 && !submitted && (
          <Button 
            onClick={handleSubmit} 
            variant="contained"
            disabled={loading}
          >
            Submit Contribution
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default CommunityContributionForm;
