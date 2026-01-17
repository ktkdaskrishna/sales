import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Briefcase, Plus, X, TrendingUp, Target, Activity } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Portfolios = () => {
  const navigate = useNavigate();
  const [portfolios, setPortfolios] = useState([]);
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    team_id: '',
    product_lines: '',
    strategic_priority: 'medium',
    description: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [portfoliosRes, teamsRes] = await Promise.all([
        api.get('/portfolios'),
        api.get('/teams')
      ]);
      setPortfolios(portfoliosRes.data);
      setTeams(teamsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/portfolios', {
        ...formData,
        product_lines: formData.product_lines.split(',').map(p => p.trim()).filter(Boolean)
      });
      setShowModal(false);
      setFormData({ name: '', team_id: '', product_lines: '', strategic_priority: 'medium', description: '' });
      fetchData();
    } catch (error) {
      console.error('Error creating portfolio:', error);
    }
  };

  const getPriorityColor = (priority) => {
    const colors = {
      high: 'bg-red-100 text-red-700 border-red-200',
      medium: 'bg-amber-100 text-amber-700 border-amber-200',
      low: 'bg-green-100 text-green-700 border-green-200'
    };
    return colors[priority] || colors.medium;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Portfolios</h1>
          <p className="text-slate-600 mt-1">Manage product portfolios and strategic initiatives</p>
        </div>
        <Button onClick={() => setShowModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          New Portfolio
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {portfolios.map(portfolio => {
            const team = teams.find(t => t.id === portfolio.team_id);
            
            return (
              <div key={portfolio.id} className="card p-6 border-l-4 border-indigo-500 hover:shadow-lg transition-all">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <span className={`inline-block px-2 py-1 rounded text-xs font-bold mb-2 ${getPriorityColor(portfolio.strategic_priority)}`}>
                      {portfolio.strategic_priority.toUpperCase()} PRIORITY
                    </span>
                    <h3 className="text-xl font-bold text-slate-900">{portfolio.name}</h3>
                    {team && (
                      <p className="text-sm text-slate-600 mt-1">
                        {team.name}
                      </p>
                    )}
                  </div>
                  <Briefcase className="w-8 h-8 text-indigo-500" />
                </div>

                {portfolio.product_lines && portfolio.product_lines.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-4">
                    {portfolio.product_lines.map((product, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded border border-blue-200">
                        {product}
                      </span>
                    ))}
                  </div>
                )}

                {portfolio.description && (
                  <p className="text-sm text-slate-500 mb-4">{portfolio.description}</p>
                )}

                <div className="grid grid-cols-2 gap-3 mt-4">
                  <div className="bg-slate-50 p-3 rounded">
                    <p className="text-xs text-slate-500">Initiatives</p>
                    <p className="text-2xl font-bold text-slate-900">0</p>
                  </div>
                  <div className="bg-slate-50 p-3 rounded">
                    <p className="text-xs text-slate-500">KPIs</p>
                    <p className="text-2xl font-bold text-slate-900">0</p>
                  </div>
                </div>

                <Button className="w-full mt-4" onClick={() => navigate(`/portfolios/${portfolio.id}/dashboard`)}>
                  View Dashboard →
                </Button>
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
              <h2 className="text-xl font-bold">Create New Portfolio</h2>
              <button onClick={() => setShowModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <Label>Portfolio Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Application Security"
                  required
                />
              </div>

              <div>
                <Label>Team</Label>
                <select
                  className="input w-full"
                  value={formData.team_id}
                  onChange={(e) => setFormData({ ...formData, team_id: e.target.value })}
                  required
                >
                  <option value="">Select a team</option>
                  {teams.map(team => (
                    <option key={team.id} value={team.id}>{team.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <Label>Product Lines (comma-separated)</Label>
                <Input
                  value={formData.product_lines}
                  onChange={(e) => setFormData({ ...formData, product_lines: e.target.value })}
                  placeholder="e.g., Penetration Testing, Code Review"
                />
              </div>

              <div>
                <Label>Strategic Priority</Label>
                <select
                  className="input w-full"
                  value={formData.strategic_priority}
                  onChange={(e) => setFormData({ ...formData, strategic_priority: e.target.value })}
                >
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
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
                  Create Portfolio
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Portfolios;
