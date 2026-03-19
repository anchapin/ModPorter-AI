import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Button,
  Paper,
} from '@mui/material';
import { ArrowBack, Download, Share } from '@mui/icons-material';
import { VisualConversionEditor, ConversionFile, CodeMapping } from '../components/VisualConversionEditor';
import * as api from '../services/api';
import './VisualEditorPage.css';

interface ConversionData {
  id: string;
  name: string;
  status: string;
  java_files: {
    name: string;
    path: string;
    content: string;
  }[];
  bedrock_files: {
    name: string;
    path: string;
    content: string;
  }[];
  mappings: {
    java_file: string;
    bedrock_file: string;
    mappings: CodeMapping[];
  }[];
}

const VisualEditorPage: React.FC = () => {
  const { conversionId } = useParams<{ conversionId: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [conversionData, setConversionData] = useState<ConversionData | null>(null);
  const [files, setFiles] = useState<ConversionFile[]>([]);

  useEffect(() => {
    const fetchConversion = async () => {
      if (!conversionId) {
        setError('No conversion ID provided');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        
        // Fetch conversion details
        const data = await api.getConversion(conversionId);
        setConversionData(data);

        // Transform API data to VisualConversionEditor format
        const transformedFiles: ConversionFile[] = data.mappings?.map((mapping: any, index: number) => {
          const javaFile = data.java_files?.find((f: any) => f.path === mapping.java_file);
          const bedrockFile = data.bedrock_files?.find((f: any) => f.path === mapping.bedrock_file);
          
          return {
            id: mapping.java_file || `file-${index}`,
            name: mapping.java_file?.split('/').pop() || `File ${index + 1}`,
            path: mapping.java_file || '',
            javaContent: javaFile?.content || '',
            bedrockContent: bedrockFile?.content || '',
            mappings: mapping.mappings || [],
          };
        }) || [];

        // If no mappings, create basic files from the data
        if (transformedFiles.length === 0 && data.bedrock_files) {
          data.bedrock_files.forEach((bf: any, index: number) => {
            const jf = data.java_files?.[index];
            transformedFiles.push({
              id: bf.path || `file-${index}`,
              name: bf.name || `File ${index + 1}`,
              path: bf.path || '',
              javaContent: jf?.content || '',
              bedrockContent: bf.content || '',
              mappings: [],
            });
          });
        }

        setFiles(transformedFiles);
        setError(null);
      } catch (err) {
        console.error('Error fetching conversion:', err);
        setError(err instanceof Error ? err.message : 'Failed to load conversion data');
      } finally {
        setLoading(false);
      }
    };

    fetchConversion();
  }, [conversionId]);

  const handleSave = useCallback(async (fileId: string, content: string) => {
    if (!conversionId) return;

    try {
      // Call API to save edited content
      await api.updateConversionFile(conversionId, fileId, { content });
      console.log('File saved successfully');
    } catch (err) {
      console.error('Error saving file:', err);
      throw err;
    }
  }, [conversionId]);

  const handleDownload = useCallback(() => {
    if (!conversionData) return;

    // Generate download of all edited files
    const blob = new Blob(
      files.map(f => `// ${f.name}\n${f.bedrockContent}`).join('\n\n'),
      { type: 'text/plain' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${conversionData.name || 'conversion'}-edited.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [conversionData, files]);

  if (loading) {
    return (
      <Box className="visual-editor-loading">
        <CircularProgress />
        <Typography variant="body1" sx={{ mt: 2 }}>
          Loading conversion data...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box className="visual-editor-error">
        <Alert severity="error">{error}</Alert>
        <Button
          startIcon={<ArrowBack />}
          href="/dashboard"
          sx={{ mt: 2 }}
        >
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  return (
    <Box className="visual-editor-page">
      {/* Header */}
      <Paper className="visual-editor-header" elevation={2}>
        <Box className="header-left">
          <Button
            startIcon={<ArrowBack />}
            href="/dashboard"
            size="small"
          >
            Back
          </Button>
          <Typography variant="h5" component="h1" className="conversion-title">
            {conversionData?.name || 'Visual Conversion Editor'}
          </Typography>
          <Typography variant="body2" className="conversion-id">
            ID: {conversionId}
          </Typography>
        </Box>
        <Box className="header-right">
          <Button
            startIcon={<Share />}
            variant="outlined"
            size="small"
          >
            Share
          </Button>
          <Button
            startIcon={<Download />}
            variant="contained"
            size="small"
            onClick={handleDownload}
          >
            Download
          </Button>
        </Box>
      </Paper>

      {/* Editor */}
      <Box className="visual-editor-content">
        <VisualConversionEditor
          conversionId={conversionId || ''}
          files={files}
          onSave={handleSave}
          readOnly={false}
        />
      </Box>
    </Box>
  );
};

export default VisualEditorPage;
