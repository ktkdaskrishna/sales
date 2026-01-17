import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Rocket, Plus, X, Calendar, CheckCircle2, Clock, Pause } from 'lucide-react';
import { formatDate } from '../lib/utils';

const Initiatives = () => {
  const [initiatives, setInitiatives] = useState([]);
  const [portfolios, setPortfolios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [formData, setFormData] = useState({
    name: '',
    portfolio_id: '',
    type: 'campaign',
    start_date: '',
    end_date: '',
    description: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [initiativesRes, portfoliosRes] = await Promise.all([
        api.get('/initiatives'),
        api.get('/portfolios')
      ]);
      setInitiatives(initiativesRes.data);
      setPortfolios(portfoliosRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/initiatives', formData);
      setShowModal(false);
      setFormData({ name: '', portfolio_id: '', type: 'campaign', start_date: '', end_date: '', description: '' });
      fetchData();
    } catch (error) {
      console.error('Error creating initiative:', error);
    }
  };

  const getStatusIcon = (status) => {
    const icons = {
      planning: Clock,
      active: Rocket,
      completed: CheckCircle2,
      paused: Pause
    };
    return icons[status] || Clock;
  };

  const getStatusColor = (status) => {
    const colors = {
      planning: 'bg-amber-100 text-amber-700 border-amber-200',
      active: 'bg-blue-100 text-blue-700 border-blue-200',
      completed: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      paused: 'bg-slate-100 text-slate-700 border-slate-200'
    };
    return colors[status] || colors.planning;
  };

  const filteredInitiatives = filterStatus === 'all' 
    ? initiatives 
    : initiatives.filter(i => i.status === filterStatus);

  const groupedByStatus = {
    planning: filteredInitiatives.filter(i => i.status === 'planning'),
    active: filteredInitiatives.filter(i => i.status === 'active'),
    completed: filteredInitiatives.filter(i => i.status === 'completed')
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Initiatives</h1>
          <p className="text-slate-600 mt-1">Track campaigns, programs, and strategic projects</p>
        </div>
        <Button onClick={() => setShowModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          New Initiative
        </Button>
      </div>

      {/* Status Filter */}
      <div className="flex gap-2">
        {['all', 'planning', 'active', 'completed'].map(status => (
          <button
            key={status}
            onClick={() => setFilterStatus(status)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
              filterStatus === status
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedByStatus).map(([status, items]) => {
            if (filterStatus !== 'all' && filterStatus !== status) return null;
            if (items.length === 0) return null;
            
            const StatusIcon = getStatusIcon(status);
            
            return (
              <div key={status}>
                <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2 capitalize">
                  <StatusIcon className="w-5 h-5" />
                  {status} ({items.length})
                </h2>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {items.map(initiative => {
                    const portfolio = portfolios.find(p => p.id === initiative.portfolio_id);
                    
                    return (
                      <div key={initiative.id} className="card p-6 hover:shadow-lg transition-all">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium mb-2 ${getStatusColor(initiative.status)}`}>
                              {initiative.status}
                            </span>
                            <h3 className="text-lg font-bold text-slate-900">{initiative.name}</h3>
                            {portfolio && (
                              <p className="text-sm text-indigo-600 mt-1">
                                {portfolio.name}
                              </p>
                            )}
                          </div>
                          <Rocket className="w-6 h-6 text-indigo-500" />
                        </div>

                        <div className="flex items-center gap-4 text-sm text-slate-600 mb-4">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            {formatDate(initiative.start_date)}
                          </span>
                          <span>→</span>
                          <span>{formatDate(initiative.end_date)}</span>
                        </div>

                        {initiative.description && (
                          <p className="text-sm text-slate-500 mb-4 line-clamp-2">
                            {initiative.description}
                          </p>
                        )}

                        <div className="grid grid-cols-2 gap-2">
                          <div className="bg-slate-50 p-2 rounded text-center">
                            <p className="text-xs text-slate-500">Type</p>
                            <p className="text-sm font-medium capitalize">{initiative.type}</p>
                          </div>
                          <div className="bg-slate-50 p-2 rounded text-center">
                            <p className="text-xs text-slate-500">Progress</p>
                            <p className="text-sm font-medium">0%</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Create New Initiative</h2>
              <button onClick={() => setShowModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <Label>Initiative Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Q2 2026 Demo Campaign"
                  required
                />
              </div>

              <div>
                <Label>Portfolio</Label>
                <select
                  className="input w-full"
                  value={formData.portfolio_id}
                  onChange={(e) => setFormData({ ...formData, portfolio_id: e.target.value })}
                  required
                >
                  <option value="">Select a portfolio</option>
                  {portfolios.map(portfolio => (
                    <option key={portfolio.id} value={portfolio.id}>{portfolio.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <Label>Type</Label>
                <select
                  className="input w-full"
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                >
                  <option value="campaign">Campaign</option>
                  <option value="program">Program</option>
                  <option value="project">Project</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div>
                <Label>Description</Label>
                <textarea
                  className="input w-full"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                />
              </div>

              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setShowModal(false)} className="flex-1">
                  Cancel
                </Button>
                <Button type="submit" className="flex-1">
                  Create Initiative
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Initiatives;
