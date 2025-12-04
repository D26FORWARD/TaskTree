import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { api } from '@/services/api';
import { FolderPicker } from '@/components/FolderPicker';
import {
  Folder,
  CheckCircle2,
  Info,
  AlertCircle,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  ExternalLink,
  Rocket,
  FileText,
  Loader2
} from 'lucide-react';

interface ProjectSetupWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const STEPS = [
  { id: 'project', title: 'Project Details', icon: Folder },
  { id: 'scope', title: 'Project Scope', icon: FileText },
  { id: 'dart', title: 'Dart (Optional)', icon: Rocket },
  { id: 'review', title: 'Review & Create', icon: CheckCircle2 },
];

export function ProjectSetupWizard({ open, onOpenChange }: ProjectSetupWizardProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [folderPickerOpen, setFolderPickerOpen] = useState(false);
  const queryClient = useQueryClient();

  // Form data
  const [projectData, setProjectData] = useState({
    name: '',
    path: '',
    description: '',
    maxAgents: 5,
    projectOverview: '',
    initialPrompt: '',
    dartWorkspace: '',
    dartDartboard: '',
  });

  // Setup status
  const [setupStatus, setSetupStatus] = useState({
    hasApiKey: false,
    isGitRepo: false,
    gitRemoteUrl: '',
    hasDartIntegration: false,
  });

  // Check API key status
  useEffect(() => {
    const checkApiKey = async () => {
      try {
        const config = await api.getOrchestratorConfig();
        setSetupStatus(prev => ({ ...prev, hasApiKey: !!config.api_key }));
      } catch (error) {
        console.error('Failed to check API key:', error);
      }
    };

    if (open && currentStep === 1) {
      checkApiKey();
    }
  }, [open, currentStep]);

  // Check Git status when path changes
  useEffect(() => {
    const checkGitStatus = async () => {
      if (projectData.path && currentStep === 2) {
        try {
          // Check if path exists and is a git repo
          const response = await fetch('/api/filesystem/browse?' + new URLSearchParams({ path: projectData.path }));
          if (response.ok) {
            // Simple check for .git directory
            const gitPath = projectData.path + '/.git';
            const gitCheckResponse = await fetch('/api/filesystem/browse?' + new URLSearchParams({ path: gitPath }));
            setSetupStatus(prev => ({
              ...prev,
              isGitRepo: gitCheckResponse.ok,
              gitRemoteUrl: '',
            }));
          }
        } catch (error) {
          console.error('Failed to check git status:', error);
          setSetupStatus(prev => ({
            ...prev,
            isGitRepo: false,
            gitRemoteUrl: '',
          }));
        }
      }
    };

    checkGitStatus();
  }, [projectData.path, currentStep]);

  const createProjectMutation = useMutation({
    mutationFn: async () => {
      // Extract folder name from path for ID
      const folderName = projectData.path.split('/').pop() || projectData.name;
      const projectId = folderName.toLowerCase().replace(/[^a-z0-9-]/g, '-');

      // Create the project
      const project = await api.createProject({
        id: projectId,
        name: projectData.name,
        path: projectData.path,
        description: projectData.description || undefined,
        max_agents: projectData.maxAgents,
        active: true,
        project_overview: projectData.projectOverview,
        initial_prompt: projectData.initialPrompt,
      });

      // Check and initialize git if needed
      if (!setupStatus.isGitRepo) {
        await api.initGitRepo(projectId);
      }

      // Generate tasks using Task Master AI if we have scope and prompt
      if (projectData.projectOverview && projectData.initialPrompt) {
        await api.generateTaskBreakdown(projectId, {
          project_overview: projectData.projectOverview,
          initial_prompt: projectData.initialPrompt,
        });
      }

      return project;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.refetchQueries({ queryKey: ['projects'] });

      // Reset form
      setProjectData({
        name: '',
        path: '',
        description: '',
        maxAgents: 5,
        projectOverview: '',
        initialPrompt: '',
        dartWorkspace: '',
        dartDartboard: '',
      });
      setCurrentStep(0);

      onOpenChange(false);
    },
    onError: (error: any) => {
      console.error('Failed to create project:', error);
      alert(`Failed to create project: ${error.message}`);
    }
  });


  const canProceed = () => {
    switch (currentStep) {
      case 0: // Project details
        return projectData.name && projectData.path;
      case 1: // Project scope
        return projectData.projectOverview && projectData.initialPrompt;
      case 2: // Dart
        return true; // Dart is optional
      case 3: // Review
        return setupStatus.hasApiKey; // Must have API key to create
      default:
        return true;
    }
  };

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      // Create project
      createProjectMutation.mutate();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const currentStepData = STEPS[currentStep];
  const Icon = currentStepData.icon;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl bg-dark-bg/95 border-electric-cyan/20">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-electric-cyan" />
              Create New Project
            </DialogTitle>
            <DialogDescription>
              Let's set up your project step by step
            </DialogDescription>
          </DialogHeader>

          {/* Progress indicator */}
          <div className="space-y-2">
            <Progress value={(currentStep + 1) / STEPS.length * 100} className="h-2" />
            <div className="flex justify-between text-xs text-muted-foreground">
              {STEPS.map((step, index) => {
                const StepIcon = step.icon;
                return (
                  <div
                    key={step.id}
                    className={`flex items-center gap-1 ${index <= currentStep ? 'text-electric-cyan' : ''
                      }`}
                  >
                    <StepIcon className="h-3 w-3" />
                    <span className="hidden sm:inline">{step.title}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Step content */}
          <div className="min-h-[400px]">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
                className="space-y-4"
              >
                {/* Step 0: Project Details */}
                {currentStep === 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="p-2 rounded-lg bg-electric-cyan/10 text-electric-cyan">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="font-semibold">Project Information</h3>
                        <p className="text-sm text-muted-foreground">Choose a name and location for your project</p>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="name">Project Name</Label>
                        <Input
                          id="name"
                          value={projectData.name}
                          onChange={(e) => setProjectData({ ...projectData, name: e.target.value })}
                          className="bg-deep-indigo/50 border-electric-cyan/20"
                          placeholder="My Awesome Project"
                          autoComplete="off"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="path">Project Path</Label>
                        <div className="flex space-x-2">
                          <Input
                            id="path"
                            value={projectData.path}
                            onChange={(e) => setProjectData({ ...projectData, path: e.target.value })}
                            className="flex-1 bg-deep-indigo/50 border-electric-cyan/20"
                            placeholder="/Users/you/code/my-project"
                            autoComplete="off"
                          />
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            onClick={() => setFolderPickerOpen(true)}
                            className="border-electric-cyan/20 hover:border-electric-cyan/50"
                          >
                            <Folder className="w-4 h-4" />
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Select an existing folder or create a new one
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="description">Description (Optional)</Label>
                        <Input
                          id="description"
                          value={projectData.description}
                          onChange={(e) => setProjectData({ ...projectData, description: e.target.value })}
                          className="bg-deep-indigo/50 border-electric-cyan/20"
                          placeholder="A brief description of your project"
                          autoComplete="off"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="maxAgents">Maximum Concurrent Agents</Label>
                        <Input
                          id="maxAgents"
                          type="number"
                          value={projectData.maxAgents}
                          onChange={(e) => setProjectData({ ...projectData, maxAgents: parseInt(e.target.value) || 5 })}
                          className="bg-deep-indigo/50 border-electric-cyan/20"
                          min="1"
                          max="20"
                          autoComplete="off"
                        />
                        <p className="text-xs text-muted-foreground">
                          Number of AI agents that can work simultaneously
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Step 1: Project Scope */}
                {currentStep === 1 && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="p-2 rounded-lg bg-electric-cyan/10 text-electric-cyan">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="font-semibold">Project Scope & Goals</h3>
                        <p className="text-sm text-muted-foreground">Define what you want to build</p>
                      </div>
                    </div>

                    <Alert className="border-electric-cyan/20 bg-electric-cyan/5">
                      <Info className="h-4 w-4 text-electric-cyan" />
                      <AlertDescription>
                        The Task Master AI will use this information to create a structured development plan with prioritized tasks for your AI agents.
                      </AlertDescription>
                    </Alert>

                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="projectOverview">Project Overview</Label>
                        <textarea
                          id="projectOverview"
                          value={projectData.projectOverview}
                          onChange={(e) => setProjectData({ ...projectData, projectOverview: e.target.value })}
                          className="w-full min-h-[120px] bg-deep-indigo/50 border-electric-cyan/20 rounded-md px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-electric-cyan/50"
                          placeholder="Describe your project in detail. What is it? What problem does it solve? Who is it for? What are the main features?"
                        />
                        <p className="text-xs text-muted-foreground">
                          Be specific about the type of application, target audience, and key features
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="initialPrompt">Initial Development Goals</Label>
                        <textarea
                          id="initialPrompt"
                          value={projectData.initialPrompt}
                          onChange={(e) => setProjectData({ ...projectData, initialPrompt: e.target.value })}
                          className="w-full min-h-[120px] bg-deep-indigo/50 border-electric-cyan/20 rounded-md px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-electric-cyan/50"
                          placeholder="What specific features or functionality do you want to implement first? What should the AI agents focus on building?"
                        />
                        <p className="text-xs text-muted-foreground">
                          List the specific features, pages, or components you want built in this development session
                        </p>
                      </div>

                      <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-2">
                        <h4 className="font-medium text-sm flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-electric-cyan" />
                          Example Project Overview
                        </h4>
                        <p className="text-xs text-muted-foreground">
                          "A modern task management web app for software teams. Built with React and Node.js, it will feature real-time collaboration, sprint planning, and GitHub integration. Target users are small to medium development teams who need a lightweight alternative to Jira."
                        </p>
                      </div>

                      <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-2">
                        <h4 className="font-medium text-sm flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-electric-cyan" />
                          Example Development Goals
                        </h4>
                        <p className="text-xs text-muted-foreground">
                          "Build the foundation: Set up Next.js 14 with TypeScript, create a modern UI with Tailwind CSS and shadcn/ui, implement user authentication with Supabase, create the main dashboard layout, and add CRUD operations for tasks."
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Step 2: Dart Integration (Optional) */}
                {currentStep === 2 && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="p-2 rounded-lg bg-electric-cyan/10 text-electric-cyan">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="font-semibold">Dart Integration (Optional)</h3>
                        <p className="text-sm text-muted-foreground">Advanced project management and analytics</p>
                      </div>
                    </div>

                    <Alert className="border-electric-cyan/20 bg-electric-cyan/5">
                      <Info className="h-4 w-4 text-electric-cyan" />
                      <AlertDescription>
                        Dart is an AI-native project management tool that provides advanced task tracking, analytics, and team collaboration features.
                      </AlertDescription>
                    </Alert>

                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="dartWorkspace">Dart Workspace ID (Optional)</Label>
                        <Input
                          id="dartWorkspace"
                          value={projectData.dartWorkspace}
                          onChange={(e) => setProjectData({ ...projectData, dartWorkspace: e.target.value })}
                          className="bg-deep-indigo/50 border-electric-cyan/20"
                          placeholder="workspace-id"
                          autoComplete="off"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="dartDartboard">Dart Dartboard ID (Optional)</Label>
                        <Input
                          id="dartDartboard"
                          value={projectData.dartDartboard}
                          onChange={(e) => setProjectData({ ...projectData, dartDartboard: e.target.value })}
                          className="bg-deep-indigo/50 border-electric-cyan/20"
                          placeholder="dartboard-id"
                          autoComplete="off"
                        />
                      </div>

                      <div className="space-y-2">
                        <p className="text-sm text-muted-foreground">
                          Find these IDs in your Dart URL:
                        </p>
                        <div className="bg-muted/50 border border-border rounded-lg p-3">
                          <code className="text-xs text-muted-foreground">
                            https://app.itsdart.com/workspace/<span className="text-electric-cyan">{projectData.dartWorkspace || 'workspace-id'}</span>/dartboard/<span className="text-electric-cyan">{projectData.dartDartboard || 'dartboard-id'}</span>
                          </code>
                        </div>
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-between"
                        onClick={() => window.open('https://itsdart.com', '_blank')}
                      >
                        Visit Dart Website
                        <ExternalLink className="h-4 w-4 ml-2" />
                      </Button>
                    </div>
                  </div>
                )}

                {/* Step 3: Review & Create */}
                {currentStep === 3 && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="p-2 rounded-lg bg-electric-cyan/10 text-electric-cyan">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="font-semibold">Review & Create</h3>
                        <p className="text-sm text-muted-foreground">Confirm your project settings</p>
                      </div>
                    </div>

                    <Card className="border-electric-cyan/20 bg-card/50">
                      <CardHeader>
                        <CardTitle className="text-base">Project Summary</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <span className="text-muted-foreground">Name:</span>
                          <span className="font-medium">{projectData.name}</span>

                          <span className="text-muted-foreground">Path:</span>
                          <span className="font-mono text-xs truncate">{projectData.path}</span>

                          {projectData.description && (
                            <>
                              <span className="text-muted-foreground">Description:</span>
                              <span className="truncate">{projectData.description}</span>
                            </>
                          )}

                          <span className="text-muted-foreground">Max Agents:</span>
                          <span>{projectData.maxAgents}</span>

                          <span className="text-muted-foreground">Git Repository:</span>
                          <span className="flex items-center gap-1">
                            {setupStatus.isGitRepo ? (
                              <>
                                <CheckCircle2 className="h-3 w-3 text-green-500" />
                                Existing
                              </>
                            ) : (
                              <>
                                <Info className="h-3 w-3 text-yellow-500" />
                                Will Initialize
                              </>
                            )}
                          </span>

                          <span className="text-muted-foreground">API Key:</span>
                          <span className="flex items-center gap-1">
                            {setupStatus.hasApiKey ? (
                              <>
                                <CheckCircle2 className="h-3 w-3 text-green-500" />
                                Configured
                              </>
                            ) : (
                              <>
                                <AlertCircle className="h-3 w-3 text-red-500" />
                                Not Set (Required)
                              </>
                            )}
                          </span>

                          <span className="text-muted-foreground">Project Scope:</span>
                          <span className="flex items-center gap-1">
                            {projectData.projectOverview ? (
                              <>
                                <CheckCircle2 className="h-3 w-3 text-green-500" />
                                Defined
                              </>
                            ) : (
                              <>
                                <AlertCircle className="h-3 w-3 text-yellow-500" />
                                Not Set
                              </>
                            )}
                          </span>

                          {(projectData.dartWorkspace || projectData.dartDartboard) && (
                            <>
                              <span className="text-muted-foreground">Dart Integration:</span>
                              <span className="flex items-center gap-1">
                                <CheckCircle2 className="h-3 w-3 text-green-500" />
                                Configured
                              </span>
                            </>
                          )}
                        </div>
                      </CardContent>
                    </Card>

                    {!setupStatus.hasApiKey && (
                      <Alert className="border-red-500/20 bg-red-500/5">
                        <AlertCircle className="h-4 w-4 text-red-500" />
                        <AlertDescription>
                          <strong>API Key Required!</strong> You must set your Anthropic API key in the Orchestrator Settings before the AI agents can work. Go to Settings → Orchestrator after creating the project.
                        </AlertDescription>
                      </Alert>
                    )}

                    {projectData.projectOverview && projectData.initialPrompt && (
                      <Alert className="border-electric-cyan/20 bg-electric-cyan/5">
                        <Sparkles className="h-4 w-4 text-electric-cyan" />
                        <AlertDescription>
                          <strong>Task Master AI will:</strong>
                          <ul className="list-disc list-inside mt-2 space-y-1 text-sm">
                            <li>Analyze your project scope and goals</li>
                            <li>Create a structured development plan</li>
                            <li>Generate prioritized tasks for AI agents</li>
                            <li>Set up task dependencies and waves</li>
                          </ul>
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          <DialogFooter className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {currentStep > 0 && (
                <Button
                  variant="ghost"
                  onClick={handleBack}
                  disabled={createProjectMutation.isPending}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Back
                </Button>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={createProjectMutation.isPending}
              >
                Cancel
              </Button>

              <Button
                variant="glow"
                onClick={handleNext}
                disabled={!canProceed() || createProjectMutation.isPending}
              >
                {createProjectMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Creating & Generating Tasks...
                  </>
                ) : currentStep === STEPS.length - 1 ? (
                  <>
                    <Sparkles className="h-4 w-4 mr-1" />
                    Create Project & Generate Tasks
                  </>
                ) : (
                  <>
                    Next
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </>
                )}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <FolderPicker
        open={folderPickerOpen}
        onOpenChange={setFolderPickerOpen}
        onSelect={(selectedPath) => {
          setProjectData({ ...projectData, path: selectedPath });
          // Auto-generate project name from folder name if empty
          if (!projectData.name && selectedPath) {
            const folderName = selectedPath.split('/').pop() || '';
            setProjectData(prev => ({
              ...prev,
              name: folderName.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
            }));
          }
        }}
        currentPath={projectData.path}
      />
    </>
  );
}
