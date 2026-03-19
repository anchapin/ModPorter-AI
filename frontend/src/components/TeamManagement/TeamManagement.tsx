import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  ListItemSecondaryAction,
  Avatar,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Divider,
  FormControl,
  InputLabel,
  Select,
  Tab,
  Tabs,
  Paper,
  Grid,
} from '@mui/material';
import {
  GroupAdd,
  PersonAdd,
  MoreVert,
  Delete,
  Edit,
  Email,
  CheckCircle,
  Cancel,
  AdminPanelSettings,
  EditNote,
  Visibility,
} from '@mui/icons-material';
import { API_BASE_URL } from '../../services/api';
import './TeamManagement.css';

export interface TeamMember {
  id: string;
  userId: string;
  name: string;
  email: string;
  avatar?: string;
  role: 'admin' | 'editor' | 'viewer';
  joinedAt: string;
  status: 'active' | 'pending';
}

export interface Team {
  id: string;
  name: string;
  description?: string;
  ownerId: string;
  ownerName: string;
  members: TeamMember[];
  createdAt: string;
  projectCount: number;
}

interface TeamManagementProps {
  teams?: Team[];
  onTeamSelect?: (team: Team) => void;
}

type TabValue = 'my-teams' | 'discover' | 'settings';

const TeamManagement: React.FC<TeamManagementProps> = ({
  teams: initialTeams,
  onTeamSelect,
}) => {
  const [teams, setTeams] = useState<Team[]>(initialTeams || []);
  const [tabValue, setTabValue] = useState<TabValue>('my-teams');
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [newTeam, setNewTeam] = useState({ name: '', description: '' });
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'editor' | 'viewer'>('viewer');
  const [memberMenuAnchor, setMemberMenuAnchor] = useState<{ element: HTMLElement; memberId: string } | null>(null);

  // Fetch user's teams
  const fetchTeams = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/teams`);
      if (!response.ok) throw new Error('Failed to fetch teams');
      const data = await response.json();
      setTeams(data.teams || []);
    } catch (err) {
      console.error('Error fetching teams:', err);
      // Use mock data
      setTeams(getMockTeams());
    }
  }, []);

  useEffect(() => {
    if (!initialTeams) {
      fetchTeams();
    }
  }, [initialTeams, fetchTeams]);

  const handleCreateTeam = async () => {
    if (!newTeam.name.trim()) return;

    try {
      const response = await fetch(`${API_BASE_URL}/teams`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTeam),
      });

      if (!response.ok) throw new Error('Failed to create team');

      const createdTeam = await response.json();
      setTeams([...teams, createdTeam]);
      setCreateDialogOpen(false);
      setNewTeam({ name: '', description: '' });
    } catch (err) {
      console.error('Error creating team:', err);
    }
  };

  const handleInviteMember = async () => {
    if (!inviteEmail.trim() || !selectedTeam) return;

    try {
      const response = await fetch(`${API_BASE_URL}/teams/${selectedTeam.id}/members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });

      if (!response.ok) throw new Error('Failed to invite member');

      const newMember = await response.json();
      setSelectedTeam({
        ...selectedTeam,
        members: [...selectedTeam.members, newMember],
      });
      setInviteDialogOpen(false);
      setInviteEmail('');
      setInviteRole('viewer');
    } catch (err) {
      console.error('Error inviting member:', err);
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!selectedTeam) return;

    try {
      await fetch(`${API_BASE_URL}/teams/${selectedTeam.id}/members/${memberId}`, {
        method: 'DELETE',
      });

      setSelectedTeam({
        ...selectedTeam,
        members: selectedTeam.members.filter((m) => m.id !== memberId),
      });
    } catch (err) {
      console.error('Error removing member:', err);
    }
    setMemberMenuAnchor(null);
  };

  const handleUpdateRole = async (memberId: string, newRole: 'admin' | 'editor' | 'viewer') => {
    if (!selectedTeam) return;

    try {
      await fetch(`${API_BASE_URL}/teams/${selectedTeam.id}/members/${memberId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole }),
      });

      setSelectedTeam({
        ...selectedTeam,
        members: selectedTeam.members.map((m) =>
          m.id === memberId ? { ...m, role: newRole } : m
        ),
      });
    } catch (err) {
      console.error('Error updating role:', err);
    }
    setMemberMenuAnchor(null);
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'admin':
        return <AdminPanelSettings />;
      case 'editor':
        return <EditNote />;
      case 'viewer':
        return <Visibility />;
      default:
        return null;
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'error';
      case 'editor':
        return 'primary';
      case 'viewer':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <Box className="team-management">
      {/* Header */}
      <Paper className="team-header" elevation={2}>
        <Box className="header-content">
          <Typography variant="h5" component="h2">
            Team Management
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage teams and collaborate on conversions
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<GroupAdd />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Team
        </Button>
      </Paper>

      {/* Tabs */}
      <Tabs
        value={tabValue}
        onChange={(_, value) => setTabValue(value)}
        className="team-tabs"
      >
        <Tab value="my-teams" label="My Teams" />
        <Tab value="discover" label="Discover Teams" />
        <Tab value="settings" label="Settings" />
      </Tabs>

      {/* Teams List or Team Detail */}
      <Box className="team-content">
        {tabValue === 'my-teams' && !selectedTeam && (
          <Grid container spacing={2}>
            {teams.map((team) => (
              <Grid item xs={12} sm={6} md={4} key={team.id}>
                <Card
                  className="team-card"
                  onClick={() => {
                    setSelectedTeam(team);
                    onTeamSelect?.(team);
                  }}
                >
                  <CardContent>
                    <Box className="team-card-header">
                      <Avatar className="team-avatar">
                        {team.name.charAt(0).toUpperCase()}
                      </Avatar>
                      <Box className="team-info">
                        <Typography variant="h6">{team.name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {team.members.length} members • {team.projectCount} projects
                        </Typography>
                      </Box>
                    </Box>
                    {team.description && (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        className="team-description"
                      >
                        {team.description}
                      </Typography>
                    )}
                    <Box className="team-members-preview">
                      {team.members.slice(0, 3).map((member) => (
                        <Avatar
                          key={member.id}
                          className="member-avatar"
                          sx={{ width: 28, height: 28, fontSize: 12 }}
                        >
                          {member.name.charAt(0)}
                        </Avatar>
                      ))}
                      {team.members.length > 3 && (
                        <Typography variant="caption">
                          +{team.members.length - 3} more
                        </Typography>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}

        {selectedTeam && (
          <Box className="team-detail">
            <Box className="team-detail-header">
              <Button
                startIcon={<Cancel />}
                onClick={() => setSelectedTeam(null)}
              >
                Back to Teams
              </Button>
              <Typography variant="h5">{selectedTeam.name}</Typography>
              <Button
                variant="contained"
                startIcon={<PersonAdd />}
                onClick={() => setInviteDialogOpen(true)}
              >
                Invite Member
              </Button>
            </Box>

            <Paper className="members-list" elevation={1}>
              <Typography variant="h6" className="section-title">
                Team Members ({selectedTeam.members.length})
              </Typography>
              <List>
                {selectedTeam.members.map((member) => (
                  <ListItem key={member.id} className="member-item">
                    <ListItemAvatar>
                      <Avatar>{member.name.charAt(0)}</Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={member.name}
                      secondary={
                        <>
                          {member.email}
                          {member.status === 'pending' && (
                            <Chip
                              label="Pending"
                              size="small"
                              color="warning"
                              sx={{ ml: 1 }}
                            />
                          )}
                        </>
                      }
                    />
                    <Box className="member-role">
                      <Chip
                        icon={getRoleIcon(member.role)}
                        label={member.role}
                        color={getRoleColor(member.role) as any}
                        size="small"
                      />
                    </Box>
                    <ListItemSecondaryAction>
                      <IconButton
                        onClick={(e) =>
                          setMemberMenuAnchor({
                            element: e.currentTarget,
                            memberId: member.id,
                          })
                        }
                      >
                        <MoreVert />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Box>
        )}

        {tabValue === 'discover' && (
          <Box className="discover-teams">
            <Typography variant="h6">Discover Public Teams</Typography>
            <Typography variant="body2" color="text.secondary">
              Browse teams that are open for new members
            </Typography>
            {/* Placeholder for discover content */}
            <Box className="empty-state">
              <Typography>No public teams to discover</Typography>
            </Box>
          </Box>
        )}

        {tabValue === 'settings' && (
          <Box className="team-settings">
            <Typography variant="h6">Global Team Settings</Typography>
            <Typography variant="body2" color="text.secondary">
              Configure default settings for your teams
            </Typography>
            {/* Placeholder for settings content */}
          </Box>
        )}
      </Box>

      {/* Create Team Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create a New Team</DialogTitle>
        <DialogContent>
          <TextField
            label="Team Name"
            value={newTeam.name}
            onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value })}
            fullWidth
            required
            margin="normal"
          />
          <TextField
            label="Description (optional)"
            value={newTeam.description}
            onChange={(e) =>
              setNewTeam({ ...newTeam, description: e.target.value })
            }
            fullWidth
            multiline
            rows={2}
            margin="normal"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateTeam}>
            Create Team
          </Button>
        </DialogActions>
      </Dialog>

      {/* Invite Member Dialog */}
      <Dialog
        open={inviteDialogOpen}
        onClose={() => setInviteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Invite a Team Member</DialogTitle>
        <DialogContent>
          <TextField
            label="Email Address"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            fullWidth
            required
            margin="normal"
            InputProps={{
              startAdornment: <Email />,
            }}
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Role</InputLabel>
            <Select
              value={inviteRole}
              label="Role"
              onChange={(e) => setInviteRole(e.target.value as any)}
            >
              <MenuItem value="admin">
                <Box className="role-option">
                  <AdminPanelSettings /> Admin - Full access
                </Box>
              </MenuItem>
              <MenuItem value="editor">
                <Box className="role-option">
                  <EditNote /> Editor - Convert and edit
                </Box>
              </MenuItem>
              <MenuItem value="viewer">
                <Box className="role-option">
                  <Visibility /> Viewer - View only
                </Box>
              </MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInviteDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleInviteMember}>
            Send Invite
          </Button>
        </DialogActions>
      </Dialog>

      {/* Member Actions Menu */}
      <Menu
        anchorEl={memberMenuAnchor?.element}
        open={!!memberMenuAnchor}
        onClose={() => setMemberMenuAnchor(null)}
      >
        <MenuItem onClick={() => handleUpdateRole(memberMenuAnchor!.memberId, 'admin')}>
          <AdminPanelSettings /> Admin
        </MenuItem>
        <MenuItem onClick={() => handleUpdateRole(memberMenuAnchor!.memberId, 'editor')}>
          <EditNote /> Editor
        </MenuItem>
        <MenuItem onClick={() => handleUpdateRole(memberMenuAnchor!.memberId, 'viewer')}>
          <Visibility /> Viewer
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => handleRemoveMember(memberMenuAnchor!.memberId)}
          className="remove-item"
        >
          <Delete /> Remove
        </MenuItem>
      </Menu>
    </Box>
  );
};

// Mock data
function getMockTeams(): Team[] {
  return [
    {
      id: '1',
      name: 'Bedrock Devs',
      description: 'Team focused on Bedrock add-on development',
      ownerId: 'user-1',
      ownerName: 'Alex',
      members: [
        {
          id: 'm1',
          userId: 'user-1',
          name: 'Alex',
          email: 'alex@example.com',
          role: 'admin',
          joinedAt: '2024-01-01',
          status: 'active',
        },
        {
          id: 'm2',
          userId: 'user-2',
          name: 'Jordan',
          email: 'jordan@example.com',
          role: 'editor',
          joinedAt: '2024-01-15',
          status: 'active',
        },
        {
          id: 'm3',
          userId: 'user-3',
          name: 'Sam',
          email: 'sam@example.com',
          role: 'viewer',
          joinedAt: '2024-02-01',
          status: 'pending',
        },
      ],
      createdAt: '2024-01-01',
      projectCount: 12,
    },
    {
      id: '2',
      name: 'Mod Converters',
      description: 'Converting Java mods to Bedrock',
      ownerId: 'user-1',
      ownerName: 'Alex',
      members: [
        {
          id: 'm4',
          userId: 'user-1',
          name: 'Alex',
          email: 'alex@example.com',
          role: 'admin',
          joinedAt: '2024-01-01',
          status: 'active',
        },
      ],
      createdAt: '2024-02-15',
      projectCount: 5,
    },
  ];
}

export default TeamManagement;
