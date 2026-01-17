import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Users, Plus, X, UserPlus, Trash2, Building2 } from 'lucide-react';

const Teams = () => {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    type: 'product',
    description: ''
  });

  useEffect(() => {
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    try {
      const response = await api.get('/teams');
      setTeams(response.data);
    } catch (error) {
      console.error('Error fetching teams:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/teams', formData);
      setShowModal(false);
      setFormData({ name: '', type: 'product', description: '' });
      fetchTeams();
    } catch (error) {
      console.error('Error creating team:', error);
    }
  };

  const getTypeColor = (type) => {
    const colors = {
      product: 'bg-blue-100 text-blue-700 border-blue-200',
      sales: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      strategic: 'bg-purple-100 text-purple-700 border-purple-200',
      ops: 'bg-amber-100 text-amber-700 border-amber-200'
    };
    return colors[type] || colors.product;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Teams</h1>
          <p className="text-slate-600 mt-1">Manage organizational teams and members</p>
        </div>
        <Button onClick={() => setShowModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          New Team
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {teams.map(team => (
            <div key={team.id} className="card p-6 hover:shadow-lg transition-all">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <Users className="w-6 h-6 text-indigo-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-slate-900">{team.name}</h3>
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${getTypeColor(team.type)}`}>
                    {team.type}
                  </span>
                </div>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">Members:</span>
                  <span className="font-medium">{team.member_count}</span>
                </div>
                {team.description && (
                  <p className="text-slate-500 text-xs mt-2">{team.description}</p>
                )}
              </div>

              <Button
                className="w-full mt-4"
                variant="outline"
                onClick={() => setSelectedTeam(team)}
              >
                View Details
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Create New Team</h2>
              <button onClick={() => setShowModal(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <Label>Team Name</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              <div>
                <Label>Team Type</Label>
                <select
                  className="input w-full"
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                >
                  <option value="product">Product</option>
                  <option value="sales">Sales</option>
                  <option value="strategic">Strategic</option>
                  <option value="ops">Operations</option>
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
                  Create Team
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Teams;
