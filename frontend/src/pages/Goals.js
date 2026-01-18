/**
 * Goals Dashboard
 * Track team's quarterly objectives and key results with visual progress indicators
 * Design: Clean cards with progress bars, status badges, and summary stats
 */
import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { formatCurrency, cn } from '../lib/utils';
import { useAuth } from '../context/AuthContext';
import {
  Target,
  Plus,
  Loader2,
  X,
  TrendingUp,
  DollarSign,
  Users,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Calendar,
  BarChart3,
  Percent,
  Hash,
  Award,
  Edit2,
  Trash2,
  ChevronRight,
} from 'lucide-react';

// Goal status color mapping
const getStatusConfig = (percentage, dueDate) => {
  const now = new Date();
  const due = new Date(dueDate);
  const daysRemaining = Math.ceil((due - now) / (1000 * 60 * 60 * 24));
  
  if (percentage >= 100) return { label: 'Achieved', color: 'bg-emerald-100 text-emerald-700 border-emerald-200', icon: CheckCircle2 };
  if (percentage >= 70 || (percentage >= 50 && daysRemaining > 30)) return { label: 'On Track', color: 'bg-blue-100 text-blue-700 border-blue-200', icon: TrendingUp };
  if (percentage >= 40 || daysRemaining > 14) return { label: 'At Risk', color: 'bg-amber-100 text-amber-700 border-amber-200', icon: AlertTriangle };
  return { label: 'Behind', color: 'bg-red-100 text-red-700 border-red-200', icon: Clock };
};

// Icon mapping for goal types
const GOAL_ICONS = {
  revenue: DollarSign,
  leads: Users,
  conversion: Percent,
  clients: Users,
  satisfaction: Award,
  audit: CheckCircle2,
  default: Target,
};

// Summary Card Component
const SummaryCard = ({ title, value, subtitle, color = 'slate', icon: Icon }) => (
  <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-all">
    <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
    <div className="flex items-end justify-between mt-2">
      <p className={cn("text-3xl font-bold", `text-${color}-600`)}>{value}</p>
      {Icon && (
        <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center", `bg-${color}-50`)}>
          <Icon className={cn("w-5 h-5", `text-${color}-500`)} />
        </div>
      )}
    </div>
    {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
  </div>
);

// Goal Card Component
const GoalCard = ({ goal, onEdit, onDelete }) => {
  const percentage = goal.target_value > 0 
    ? Math.round((goal.current_value / goal.target_value) * 100) 
    : 0;
  
  const status = getStatusConfig(percentage, goal.due_date);
  const StatusIcon = status.icon;
  const GoalIcon = GOAL_ICONS[goal.goal_type] || GOAL_ICONS.default;
  
  // Format values based on unit
  const formatValue = (val) => {
    if (goal.unit === 'currency') return formatCurrency(val);
    if (goal.unit === 'percentage') return `${val}%`;
    return val.toLocaleString();
  };

  return (
    <div 
      className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-lg transition-all group"
      data-testid={`goal-card-${goal.id}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <GoalIcon className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">{goal.name}</h3>
          </div>
        </div>
        <span className={cn(
          "px-2.5 py-1 rounded-full text-xs font-semibold border flex items-center gap-1",
          status.color
        )}>
          <StatusIcon className="w-3 h-3" />
          {status.label}
        </span>
      </div>
      
      {/* Description */}
      {goal.description && (
        <p className="text-sm text-slate-500 mb-4">{goal.description}</p>
      )}
      
      {/* Progress */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-slate-500">Progress</span>
          <span className="font-semibold text-slate-900">
            {formatValue(goal.current_value)} / {formatValue(goal.target_value)}
          </span>
        </div>
        <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
          <div 
            className={cn(
              "h-full rounded-full transition-all duration-500",
              percentage >= 100 ? "bg-emerald-500" :
              percentage >= 70 ? "bg-blue-500" :
              percentage >= 40 ? "bg-amber-500" :
              "bg-red-500"
            )}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
      </div>
      
      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{percentage}% complete</span>
        <span className="flex items-center gap-1">
          <Calendar className="w-3.5 h-3.5" />
          {new Date(goal.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
        </span>
      </div>
      
      {/* Actions (visible on hover) */}
      <div className="flex items-center justify-end gap-2 mt-3 pt-3 border-t border-slate-100 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={() => onEdit(goal)}
          className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          title="Edit goal"
        >
          <Edit2 className="w-4 h-4" />
        </button>
        <button
          onClick={() => onDelete(goal.id)}
          className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          title="Delete goal"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

// Main Goals Component
const Goals = () => {
  const { user, isExecutive } = useAuth();
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showTeamAssignModal, setShowTeamAssignModal] = useState(false); // NEW
  const [teamMembers, setTeamMembers] = useState([]); // NEW
  const [selectedGoalForAssignment, setSelectedGoalForAssignment] = useState(null); // NEW
  const [selectedTeamMemberIds, setSelectedTeamMemberIds] = useState([]); // NEW
  const [isManager, setIsManager] = useState(false); // NEW
  const [editingGoal, setEditingGoal] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    target_value: '',
    current_value: '0',
    unit: 'currency',
    goal_type: 'revenue',
    due_date: '',
    assignee_type: 'user',
    assignee_id: '',
  });

  useEffect(() => {
    fetchGoals();
    fetchTeamMembers(); // NEW
  }, []);
  
  // NEW: Fetch team members for managers
  const fetchTeamMembers = async () => {
    try {
      const response = await api.get('/goals/team/subordinates');
      setIsManager(response.data.is_manager);
      setTeamMembers(response.data.subordinates || []);
    } catch (error) {
      console.error('Error fetching team members:', error);
    }
  };

  const fetchGoals = async () => {
    try {
      const response = await api.get('/goals');
      const goalsData = response.data.goals || response.data || [];
      
      // Only use mock data if there are truly no goals in the database
      if (goalsData.length === 0) {
        console.log('No goals found in database, showing empty state');
      }
      
      setGoals(goalsData);
    } catch (error) {
      console.error('Error fetching goals:', error);
      // On error, show empty state instead of mock data
      setGoals([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...formData,
        target_value: parseFloat(formData.target_value),
        current_value: parseFloat(formData.current_value || 0),
      };
      
      if (editingGoal) {
        await api.put(`/goals/${editingGoal.id}`, payload);
      } else {
        await api.post('/goals', payload);
      }
      
      setShowModal(false);
      setEditingGoal(null);
      resetForm();
      fetchGoals();
    } catch (error) {
      console.error('Error saving goal:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (goal) => {
    setEditingGoal(goal);
    setFormData({
      name: goal.name,
      description: goal.description || '',
      target_value: goal.target_value.toString(),
      current_value: goal.current_value.toString(),
      unit: goal.unit,
      goal_type: goal.goal_type || 'revenue',
      due_date: goal.due_date?.split('T')[0] || '',
      assignee_type: goal.assignee_type || 'user',
      assignee_id: goal.assignee_id || '',
    });
    setShowModal(true);
  };

  const handleDelete = async (goalId) => {
    if (!window.confirm('Are you sure you want to delete this goal?')) return;
    
    try {
      await api.delete(`/goals/${goalId}`);
      fetchGoals();
    } catch (error) {
      console.error('Error deleting goal:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      target_value: '',
      current_value: '0',
      unit: 'currency',
      goal_type: 'revenue',
      due_date: '',
      assignee_type: 'user',
      assignee_id: '',
    });
  };

  // Calculate summary stats
  const totalGoals = goals.length;
  const overallProgress = totalGoals > 0
    ? Math.round(goals.reduce((sum, g) => sum + (g.current_value / g.target_value) * 100, 0) / totalGoals)
    : 0;
  const achieved = goals.filter(g => g.current_value >= g.target_value).length;
  const onTrack = goals.filter(g => {
    const pct = (g.current_value / g.target_value) * 100;
    return pct >= 70 && pct < 100;
  }).length;
  const atRisk = goals.filter(g => {
    const pct = (g.current_value / g.target_value) * 100;
    return pct < 70;
  }).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="animate-in space-y-6" data-testid="goals-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Goals</h1>
          <p className="text-slate-500 mt-1">
            Track your team&apos;s quarterly objectives and key results
          </p>
        </div>
        {isExecutive() && (
          <button
            onClick={() => {
              setEditingGoal(null);
              resetForm();
              setShowModal(true);
            }}
            className="btn-primary flex items-center gap-2"
            data-testid="add-goal-btn"
          >
            <Plus className="w-4 h-4" />
            Add Goal
          </button>
        )}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Overall Progress</p>
          <div className="flex items-end justify-between mt-2">
            <p className="text-3xl font-bold text-slate-900">{overallProgress}%</p>
            <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
              <Target className="w-5 h-5 text-blue-500" />
            </div>
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden mt-3">
            <div 
              className="h-full bg-blue-500 rounded-full" 
              style={{ width: `${Math.min(overallProgress, 100)}%` }}
            />
          </div>
        </div>
        
        <SummaryCard
          title="Achieved"
          value={achieved}
          subtitle="goals completed"
          color="emerald"
          icon={CheckCircle2}
        />
        
        <SummaryCard
          title="On Track"
          value={onTrack}
          subtitle="progressing well"
          color="blue"
          icon={TrendingUp}
        />
        
        <SummaryCard
          title="At Risk"
          value={atRisk}
          subtitle="needs attention"
          color="amber"
          icon={AlertTriangle}
        />
      </div>

      {/* Goals Grid */}
      {goals.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {goals.map(goal => (
            <GoalCard 
              key={goal.id} 
              goal={goal} 
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
            <Target className="w-8 h-8 text-slate-400" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No Goals Yet</h3>
          <p className="text-slate-500 mb-6">Create your first goal to start tracking progress</p>
          {isExecutive() && (
            <button onClick={() => setShowModal(true)} className="btn-primary">
              <Plus className="w-4 h-4 mr-2" />
              Create Goal
            </button>
          )}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg max-h-[90vh] overflow-y-auto animate-scale-in">
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-900">
                  {editingGoal ? 'Edit Goal' : 'Create New Goal'}
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  Set targets and track progress
                </p>
              </div>
              <button
                onClick={() => {
                  setShowModal(false);
                  setEditingGoal(null);
                  resetForm();
                }}
                className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Goal Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="input"
                  placeholder="e.g., Q1 Revenue Target"
                  required
                  data-testid="goal-name-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input min-h-[80px]"
                  placeholder="Describe what success looks like..."
                  rows={2}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Target Value *
                  </label>
                  <input
                    type="number"
                    value={formData.target_value}
                    onChange={(e) => setFormData({ ...formData, target_value: e.target.value })}
                    className="input"
                    required
                    min="0"
                    step="any"
                    data-testid="goal-target-input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Current Value
                  </label>
                  <input
                    type="number"
                    value={formData.current_value}
                    onChange={(e) => setFormData({ ...formData, current_value: e.target.value })}
                    className="input"
                    min="0"
                    step="any"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Unit Type
                  </label>
                  <select
                    value={formData.unit}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                    className="input"
                  >
                    <option value="currency">Currency ($)</option>
                    <option value="percentage">Percentage (%)</option>
                    <option value="count">Count (#)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Goal Type
                  </label>
                  <select
                    value={formData.goal_type}
                    onChange={(e) => setFormData({ ...formData, goal_type: e.target.value })}
                    className="input"
                  >
                    <option value="revenue">Revenue</option>
                    <option value="leads">Leads</option>
                    <option value="conversion">Conversion</option>
                    <option value="clients">Clients</option>
                    <option value="satisfaction">Satisfaction</option>
                    <option value="audit">Audit</option>
                  </select>
                </div>
              </div>
              
              {/* Team Member Assignment - Only for managers */}
              {teamMembers.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Assign to Team Member
                  </label>
                  <select
                    value={formData.assignee_id}
                    onChange={(e) => setFormData({ ...formData, assignee_id: e.target.value })}
                    className="input"
                  >
                    <option value="">My Goal (Personal)</option>
                    {teamMembers.map(member => (
                      <option key={member.id} value={member.id}>
                        {member.name} ({member.email})
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-slate-500 mt-1">
                    Assign this goal to a specific team member or keep it as your personal goal
                  </p>
                </div>
              )}
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Due Date *
                </label>
                <input
                  type="date"
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                  className="input"
                  required
                />
              </div>
              
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setEditingGoal(null);
                    resetForm();
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="btn-primary flex items-center gap-2"
                  data-testid="save-goal-btn"
                >
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingGoal ? 'Update Goal' : 'Create Goal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Goals;
