import React, { useState } from 'react';
import { Users, Plus, Trash2, Send, CheckCircle, AlertCircle } from 'lucide-react';
import FormField from './FormField';
import TeamMemberCard from './TeamMemberCard';
import { validateEmail } from '../utils/validation';
import { saveTeamToDatabase } from '../services/databaseService';
import { useOpenConnectModal, useWallets } from '@0xsequence/connect';

interface TeamMember {
  id: number;
  srn: string;
  name: string;
  email: string;
  walletAddress: string;
}

interface FormData {
  teamName: string;
  idea: string;
  ideaDescription: string;
  captainSrn: string;
  captainName: string;
  captainEmail: string;
  walletAddress: string;
}

const TeamOnboardingForm: React.FC = () => {
  const [formData, setFormData] = useState<FormData>({
    teamName: '',
    idea: '',
    ideaDescription: '',
    captainSrn: '',
    captainName: '',
    captainEmail: '',
    walletAddress: ''
  });

  interface DuplicateCheckResult {
    hasDuplicates: boolean;
    duplicates: {
      teamName?: boolean;
      emails: string[];
      srns: string[];
    };
    message?: string;
  }

  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error' | 'duplicate'>('idle');
  const [duplicateMessage, setDuplicateMessage] = useState<string>('');

  const { setOpenConnectModal } = useOpenConnectModal();
  const { wallets } = useWallets();

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
    if (submitStatus === 'duplicate') {
      setSubmitStatus('idle');
      setDuplicateMessage('');
    }
  };

  const addTeamMember = () => {
    if (teamMembers.length < 4) {
      const newMember: TeamMember = {
        id: Date.now(),
        srn: '',
        name: '',
        email: '',
        walletAddress: ''
      };
      setTeamMembers(prev => [...prev, newMember]);
    }
  };

  const removeTeamMember = (id: number) => {
    setTeamMembers(prev => prev.filter(member => member.id !== id));
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[`member_${id}_srn`];
      delete newErrors[`member_${id}_name`];
      delete newErrors[`member_${id}_email`];
      return newErrors;
    });
    if (submitStatus === 'duplicate') {
      setSubmitStatus('idle');
      setDuplicateMessage('');
    }
  };

  const updateTeamMember = (id: number, field: keyof Omit<TeamMember, 'id'>, value: string) => {
    setTeamMembers(prev =>
      prev.map(member =>
        member.id === id ? { ...member, [field]: value } : member
      )
    );
    const errorKey = `member_${id}_${field}`;
    if (errors[errorKey]) {
      setErrors(prev => ({ ...prev, [errorKey]: '' }));
    }
    if (submitStatus === 'duplicate' && field === 'email') {
      setSubmitStatus('idle');
      setDuplicateMessage('');
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    const requiredFields = {
      teamName: 'Team Name',
      idea: 'Idea',
      ideaDescription: 'Idea Description',
      captainSrn: 'Captain SRN',
      captainName: 'Captain Name',
      captainEmail: 'Captain Email'
    };

    Object.entries(requiredFields).forEach(([field, label]) => {
      if (!formData[field as keyof FormData].trim()) {
        newErrors[field] = `${label} is required`;
      }
    });

    if (formData.teamName.length > 50) newErrors.teamName = 'Team Name must be 50 characters or less';
    if (formData.idea.length > 100) newErrors.idea = 'Idea must be 100 characters or less';
    if (formData.ideaDescription.length > 250) newErrors.ideaDescription = 'Idea Description must be 250 characters or less';
    if (formData.captainSrn.length > 20) newErrors.captainSrn = 'Captain SRN must be 20 characters or less';
    if (formData.captainName.length > 50) newErrors.captainName = 'Captain Name must be 50 characters or less';
    if (formData.captainEmail.length > 30) newErrors.captainEmail = 'Captain Email must be 30 characters or less';

    if (formData.captainEmail && !validateEmail(formData.captainEmail)) {
      newErrors.captainEmail = 'Email must be from @pes.edu domain';
    }

    teamMembers.forEach(member => {
      if (member.srn && !member.name) newErrors[`member_${member.id}_name`] = 'Name is required';
      if (member.srn && !member.email) newErrors[`member_${member.id}_email`] = 'Email is required';
      if (member.name && !member.srn) newErrors[`member_${member.id}_srn`] = 'SRN is required';
      if (member.email && !member.srn) newErrors[`member_${member.id}_srn`] = 'SRN is required';
      if (member.email && !validateEmail(member.email)) {
        newErrors[`member_${member.id}_email`] = 'Email must be from @pes.edu domain';
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  function buildDuplicateErrorMessage(duplicates: DuplicateCheckResult['duplicates']): string {
    let message = '';
    if (duplicates.teamName) message += 'Team is already registered. ';
    const emailList = duplicates.emails.join(', ');
    const srnList = duplicates.srns.join(', ');
    if (duplicates.emails.length > 0 || duplicates.srns.length > 0) {
      message += 'The following ';
      if (duplicates.emails.length > 0) message += `emails are already in use: ${emailList}`;
      if (duplicates.emails.length > 0 && duplicates.srns.length > 0) message += ' and ';
      if (duplicates.srns.length > 0) message += `SRNs are already in use: ${srnList}`;
      message += '. ';
    }
    message += 'Team not created.';
    return message;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
  
    setIsSubmitting(true);
    setSubmitStatus('idle');
    setDuplicateMessage('');
  
    try {
      await setOpenConnectModal(true);
      //await setOpenConnectModal(true);
  
      // Wait until wallet is connected
      const checkWalletConnection = async (): Promise<string | null> => {
        return new Promise((resolve) => {
          const interval = setInterval(() => {
            const activeWallet = wallets.find(wallet => wallet.isActive);
            if (activeWallet?.address) {
              clearInterval(interval);
              resolve(activeWallet.address);
            }
          }, 500);
  
          // Timeout after 10 seconds
          setTimeout(() => {
            clearInterval(interval);
            resolve(null);
          }, 10000);
        });
      };
  
      const walletAddress = await checkWalletConnection();
  
      if (!walletAddress) {
        console.error('Wallet connection failed or timed out.');
        setSubmitStatus('error');
        return;
      }
  
      formData.walletAddress = walletAddress;
      console.log('Wallet Address:', walletAddress);
  
  

      const teamData = {
        teamName: formData.teamName,
        idea: formData.idea,
        ideaDescription: formData.ideaDescription,
        captain: {
          srn: formData.captainSrn,
          name: formData.captainName,
          email: formData.captainEmail,
          walletAddress: formData.walletAddress
        },
        members: teamMembers.filter(member => member.srn && member.name && member.email).map(member => ({
          ...member,
          walletAddress: ''
        })),
        createdAt: new Date().toISOString()
      };

      const dbResult = await saveTeamToDatabase(teamData);
      //await saveTeamWalletToJson(teamData.teamName, teamData.captain.walletAddress);


      if (dbResult.success) {
        setSubmitStatus('success');
        setFormData({
          teamName: '',
          idea: '',
          ideaDescription: '',
          captainSrn: '',
          captainName: '',
          captainEmail: '',
          walletAddress: ''
        });
        setTeamMembers([]);
      } else if (!dbResult.success && dbResult.data?.hasDuplicates) {
        const fullMessage = buildDuplicateErrorMessage(dbResult.data.duplicates);
        setSubmitStatus('duplicate');
        setDuplicateMessage(fullMessage);
      } else {
        throw new Error('Failed to save team data');
      }
    } catch (error) {
      console.error('Submission error:', error);
      setSubmitStatus('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 px-8 py-6">
          <div className="flex items-center space-x-3">
            <Users className="h-8 w-8 text-white" />
            <div>
              <h1 className="text-3xl font-bold text-white">Ignite Team Onboarding</h1>
              <p className="text-blue-100 mt-1">Register your innovative team for the competition</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-8">
          {/* Team Information */}
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                <span className="text-blue-600 font-bold text-sm">1</span>
              </div>
              Team Information
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormField
                label="Team Name"
                value={formData.teamName}
                onChange={(value) => handleInputChange('teamName', value)}
                placeholder="Enter your team name"
                maxLength={50}
                error={errors.teamName}
                required
              />
              
              <FormField
                label="Idea"
                value={formData.idea}
                onChange={(value) => handleInputChange('idea', value)}
                placeholder="Brief idea title"
                maxLength={100}
                error={errors.idea}
                required
              />
            </div>
            
            <div className="mt-6">
              <FormField
                label="Idea Description"
                value={formData.ideaDescription}
                onChange={(value) => handleInputChange('ideaDescription', value)}
                placeholder="Describe your innovative idea in detail..."
                maxLength={250}
                error={errors.ideaDescription}
                required
                textarea
                rows={4}
              />
            </div>
          </section>

          {/* Team Captain Information */}
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                <span className="text-blue-600 font-bold text-sm">2</span>
              </div>
              Team Captain Information
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                label="Captain SRN"
                value={formData.captainSrn}
                onChange={(value) => handleInputChange('captainSrn', value)}
                placeholder="PES1UG20CS001"
                maxLength={20}
                error={errors.captainSrn}
                required
              />
              
              <FormField
                label="Captain Name"
                value={formData.captainName}
                onChange={(value) => handleInputChange('captainName', value)}
                placeholder="Full name"
                maxLength={50}
                error={errors.captainName}
                required
              />
              
              <FormField
                label="Captain Email"
                value={formData.captainEmail}
                onChange={(value) => handleInputChange('captainEmail', value)}
                placeholder="name@pes.edu"
                maxLength={30}
                error={errors.captainEmail}
                required
                type="email"
              />
            </div>
          </section>

          {/* Team Members */}
          <section className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                  <span className="text-blue-600 font-bold text-sm">3</span>
                </div>
                Team Members ({teamMembers.length}/4)
              </h2>
              
              {teamMembers.length < 4 && (
                <button
                  type="button"
                  onClick={addTeamMember}
                  className="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors duration-200"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Member
                </button>
              )}
            </div>
            
            {teamMembers.length === 0 ? (
              <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                <Users className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600">No team members added yet</p>
                <p className="text-sm text-gray-500 mt-1">Click "Add Member" to start building your team</p>
              </div>
            ) : (
              <div className="space-y-4">
                {teamMembers.map((member) => (
                  <TeamMemberCard
                    key={member.id}
                    member={member}
                    onUpdate={updateTeamMember}
                    onRemove={removeTeamMember}
                    errors={{
                      srn: errors[`member_${member.id}_srn`],
                      name: errors[`member_${member.id}_name`],
                      email: errors[`member_${member.id}_email`]
                    }}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Submit Button */}
          <div className="flex items-center justify-between pt-6 border-t border-gray-200">
            <div className="flex items-center space-x-4">
              {submitStatus === 'success' && (
                <div className="flex items-center text-green-600">
                  <CheckCircle className="h-5 w-5 mr-2" />
                  <span>Team registered successfully!</span>
                  <span>Each member of the Team must visit the Wallet Management Page and Create their Crypto Wallet </span>
                </div>
              )}
              
              {submitStatus === 'error' && (
                <div className="flex items-center text-red-600">
                  <AlertCircle className="h-5 w-5 mr-2" />
                  <span>Registration failed. Please try again.</span>
                </div>
              )}

              {submitStatus === 'duplicate' && (
                <div className="flex items-center text-orange-600 max-w-md">
                  <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
                  <span className="text-sm">{duplicateMessage}</span>
                </div>
              )}
            </div>
            
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-700 hover:from-blue-700 hover:to-indigo-800 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold rounded-lg shadow-lg transition-all duration-200 transform hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {submitStatus === 'idle' ? 'Checking...' : 'Registering...'}
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Register Team
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TeamOnboardingForm;
